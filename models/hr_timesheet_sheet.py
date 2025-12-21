from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
from odoo.osv import expression
import logging
_logger = logging.getLogger(__name__)


class Sheet(models.Model):
    _inherit = "hr_timesheet.sheet"

    def _get_timesheet_sheet_lines_domain(self):

        self.ensure_one()

        try:
            base_domain = super()._get_timesheet_sheet_lines_domain()
        except Exception:
            _logger.exception("Failed to compute base domain via super().")
            raise

        try:
            sheet_company = self._get_timesheet_sheet_company()
        except Exception:
            _logger.exception("Failed to compute sheet company.")
            raise

        leave_domain = [
            ("date", "<=", self.date_end),
            ("date", ">=", self.date_start),
            ("employee_id", "=", self.employee_id.id),
            ("company_id", "in", [sheet_company.id, False]),
            ("project_id", "!=", False),
            "|",
            ("holiday_id", "!=", False),
            ("global_leave_id", "!=", False),
        ]

        return expression.OR([base_domain, leave_domain])

    def clean_timesheets(self, timesheets):

        try:
            protected = timesheets.filtered(lambda t: t.holiday_id or t.global_leave_id)
            regular = timesheets - protected
            cleaned = super().clean_timesheets(regular)
        except Exception:
            _logger.exception("Failed to clean timesheets in sheet")
            raise
        else:
            return protected | cleaned
