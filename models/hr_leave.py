"""
Override time off and calendar leave models to force zero worked hours
and populate date/time fields on generated timesheet lines.
"""
from datetime import datetime, time

from odoo import models, fields, api, tools, _
from odoo.exceptions import (
    UserError,
    ValidationError,
    RedirectWarning,
    AccessDenied,
    AccessError,
    CacheMiss,
    MissingError,
)
import logging

_logger = logging.getLogger(__name__)


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def _timesheet_prepare_line_values(self, index, *args, **kwargs):
        vals = super()._timesheet_prepare_line_values(index, *args, **kwargs)
        try:
            vals['unit_amount'] = 0.0
            leave_type_name = ''
            if getattr(self, 'holiday_status_id', False):
                leave_type_name = self.holiday_status_id.with_context(
                    lang=self.env.user.lang or 'en_US'
                ).name or ''
            vals['name'] = _("Time Off – %s") % leave_type_name
            # Set date_time and date_time_end so time-control module has values.
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
            leave_name = self.with_context(
                lang=self.env.user.lang or 'en_US'
            ).name or _('Public Holiday')
            vals['name'] = _("Time Off – %s") % leave_name
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
