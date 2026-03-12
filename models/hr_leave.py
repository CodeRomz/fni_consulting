from datetime import datetime, time

import pytz

from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
import logging
_logger = logging.getLogger(__name__)

UTC = pytz.utc

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def _timesheet_prepare_line_values(self, index, *args, **kwargs):
        vals = super()._timesheet_prepare_line_values(index, *args, **kwargs)
        try:
            vals['unit_amount'] = 0.0

            # Determine the leave type name
            leave_type_name = ''
            if getattr(self, 'holiday_status_id', False):
                leave_type_name = self.holiday_status_id.with_context(
                    lang=self.env.user.lang or 'en_US'
                ).name or ''

            # Compute current day and total days from work_hours_data
            current_day = index + 1
            total_days = 1
            if args:
                try:
                    work_hours_data = args[0]
                    total_days = len(work_hours_data)
                except Exception:
                    total_days = 1

            # Build descriptive name with counter, e.g. “Time Off – Paid Time Off 3/15”
            vals['name'] = _("Time Off – %s  [ %s/%s ]") % (
                leave_type_name, current_day, total_days
            )

            # Populate date_time/date_time_end as before (for time-control compatibility)
            date_str = vals.get('date')
            if date_str and not vals.get('date_time'):
                dt_start = fields.Datetime.from_string(date_str)
                dt_start_str = fields.Datetime.to_string(dt_start)
                vals.setdefault('date_time', dt_start_str)
                vals.setdefault('date_time_end', dt_start_str)

        except Exception as exc:
            _logger.exception(
                "Failed to adjust timesheet values for leave %s: %s", self.id, exc
            )
        return vals

class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    calendar_event_id = fields.Many2one(
        'calendar.event',
        string='Calendar Event',
        copy=False,
        readonly=True,
    )

    def _fni_get_public_holiday_sync_context(self):
        return {
            **self.env.context,
            'fni_public_holiday_sync': True,
            'calendar_no_videocall': True,
            'no_calendar_sync': True,
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True,
            'mail_notrack': True,
            'no_mail_to_attendees': True,
            'tracking_disable': True,
        }

    def _fni_ensure_public_holiday_manager_access(self, vals_list=None, vals=None):
        if self.env.su or self.env.context.get('fni_public_holiday_sync'):
            return
        needs_manager = bool(self.filtered(lambda leave: not leave.resource_id))
        if not needs_manager and vals_list is not None:
            needs_manager = any(not entry.get('resource_id') for entry in vals_list)
        if not needs_manager and vals is not None and 'resource_id' in vals:
            needs_manager = not vals.get('resource_id')
        if needs_manager and not self.env.user.has_group('hr_holidays.group_hr_holidays_manager'):
            raise AccessError(
                _(
                    'Public Holidays can only be managed from Time Off > Configuration > Public Holidays.'
                )
            )

    def _fni_get_public_holiday_event_timezone(self):
        self.ensure_one()
        return self.calendar_id.tz or self.company_id.resource_calendar_id.tz or 'UTC'

    def _fni_get_public_holiday_local_datetimes(self):
        self.ensure_one()
        event_tz = pytz.timezone(self._fni_get_public_holiday_event_timezone())
        local_start = UTC.localize(self.date_from).astimezone(event_tz).replace(tzinfo=None)
        local_stop = UTC.localize(self.date_to).astimezone(event_tz).replace(tzinfo=None)
        return local_start, local_stop

    def _fni_is_public_holiday_allday(self, start_value, stop_value):
        return (
            start_value.time() == time(0, 0, 0)
            and stop_value.time() == time(23, 59, 59)
        )

    def _fni_get_linked_public_holiday_events(self):
        event_model = self.env['calendar.event']
        events = self.mapped('calendar_event_id').exists()
        missing_source_ids = self.filtered(lambda leave: not leave.calendar_event_id).ids
        if missing_source_ids:
            events |= event_model.search([('fni_public_holiday_id', 'in', missing_source_ids)])
        return events

    def _fni_prepare_public_holiday_calendar_event_vals(self):
        self.ensure_one()
        local_start, local_stop = self._fni_get_public_holiday_local_datetimes()
        local_start_date = local_start.date()
        local_stop_date = max(local_stop.date(), local_start_date)
        calendar_label = self.calendar_id.display_name or _('All Working Hours')
        organizer_user = self.create_uid or self.env.user
        organizer_partner = organizer_user.partner_id
        vals = {
            'name': self.name or _('Public Holiday'),
            'description': _(
                'Managed from Time Off > Configuration > Public Holidays.\nWorking Hours: %(calendar)s',
                calendar=calendar_label,
            ),
            'user_id': organizer_user.id,
            'event_tz': self._fni_get_public_holiday_event_timezone(),
            'privacy': 'confidential',
            'show_as': 'busy',
            'res_model_id': self.env['ir.model']._get_id('resource.calendar.leaves'),
            'res_id': self.id,
            'fni_visibility_mode': 'public_internal',
            'fni_public_holiday_id': self.id,
            'allday': True,
            'start': datetime.combine(local_start_date, time(0, 0, 0)),
            'stop': datetime.combine(local_stop_date, time(0, 0, 0)),
            'start_date': local_start_date,
            'stop_date': local_stop_date,
            'partner_ids': [fields.Command.set(organizer_partner.ids)],
        }
        if 'need_sync_m' in self.env['calendar.event']._fields:
            vals['need_sync_m'] = False
        return vals

    def _fni_sync_public_holiday_calendar_event(self):
        event_model = self.env['calendar.event'].with_context(self._fni_get_public_holiday_sync_context())
        for leave in self.filtered(lambda record: not record.resource_id):
            event = leave._fni_get_linked_public_holiday_events()[:1]
            vals = leave._fni_prepare_public_holiday_calendar_event_vals()
            if event:
                event.write(vals)
            else:
                event = event_model.create(vals)
                leave.with_context(fni_public_holiday_sync=True).write({'calendar_event_id': event.id})

    def _fni_remove_public_holiday_calendar_event(self):
        events = self._fni_get_linked_public_holiday_events()
        if events:
            events.with_context(self._fni_get_public_holiday_sync_context()).unlink()

    def _timesheet_prepare_line_values(
        self, index, employee, work_hours_data, day_date, work_hours_count
    ):
        vals = super()._timesheet_prepare_line_values(
            index, employee, work_hours_data, day_date, work_hours_count
        )
        try:
            vals['unit_amount'] = 0.0
            # Get the holiday name or default
            leave_name = self.with_context(
                lang=self.env.user.lang or 'en_US'
            ).name or _('Public Holiday')

            # Compute current day/total days from work_hours_data
            current_day = index + 1
            total_days = 1
            try:
                total_days = len(work_hours_data)
            except Exception:
                total_days = 1

            # Compose name with counter
            vals['name'] = _("Time Off – %s %s/%s") % (
                leave_name, current_day, total_days
            )

            # As before, set date_time/date_time_end if missing
            date_str = vals.get('date')
            if date_str and not vals.get('date_time'):
                dt_start = fields.Datetime.from_string(date_str)
                dt_start_str = fields.Datetime.to_string(dt_start)
                vals.setdefault('date_time', dt_start_str)
                vals.setdefault('date_time_end', dt_start_str)

        except Exception as exc:
            _logger.exception(
                "Failed to adjust timesheet values for global leave %s: %s",
                self.id,
                exc,
            )
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        self._fni_ensure_public_holiday_manager_access(vals_list=vals_list)
        records = super().create(vals_list)
        if not self.env.context.get('fni_public_holiday_sync'):
            records.filtered(lambda leave: not leave.resource_id)._fni_sync_public_holiday_calendar_event()
        return records

    def write(self, vals):
        self._fni_ensure_public_holiday_manager_access(vals=vals)
        if self.env.context.get('fni_public_holiday_sync'):
            return super().write(vals)

        public_holidays_before = self.filtered(lambda leave: not leave.resource_id)
        result = super().write(vals)
        public_holidays_after = self.filtered(lambda leave: not leave.resource_id)
        removed_public_holidays = public_holidays_before - public_holidays_after
        if removed_public_holidays:
            removed_public_holidays._fni_remove_public_holiday_calendar_event()
        if public_holidays_after:
            public_holidays_after._fni_sync_public_holiday_calendar_event()
        return result

    def unlink(self):
        self._fni_ensure_public_holiday_manager_access()
        if self.env.context.get('fni_public_holiday_sync'):
            return super().unlink()

        public_holidays = self.filtered(lambda leave: not leave.resource_id)
        linked_events = public_holidays._fni_get_linked_public_holiday_events()
        result = super().unlink()
        if linked_events:
            linked_events.with_context(public_holidays._fni_get_public_holiday_sync_context()).unlink()
        return result
