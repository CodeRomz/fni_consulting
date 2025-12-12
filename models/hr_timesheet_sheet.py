from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
import logging
_logger = logging.getLogger(__name__)


class Sheet(models.Model):
    _inherit = 'hr_timesheet.sheet'
    def _get_timesheet_sheet_lines_domain(self):
        try:
            domain = super()._get_timesheet_sheet_lines_domain()
        except Exception:
            _logger.exception(
                "Failed to compute timesheet sheet lines domain via super()."
            )
            raise
        else:
            return expression.AND(
                [
                    domain,
                    [
                        ('holiday_id', '=', False),
                        ('global_leave_id', '=', False),
                    ],
                ]
            )

    def clean_timesheets(self, timesheets):
        try:
            # Extract timesheets linked to a leave or global leave
            protected = timesheets.filtered(
                lambda t: t.holiday_id or t.global_leave_id
            )
            regular = timesheets - protected
            # Run the original cleanup on the remaining lines
            cleaned = super().clean_timesheets(regular)
        except Exception:
            _logger.exception("Failed to clean timesheets in sheet")
            raise
        else:
            # Return the union of cleaned regular lines and protected lines
            return protected | cleaned
