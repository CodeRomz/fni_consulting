from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
import logging
_logger = logging.getLogger(__name__)

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
