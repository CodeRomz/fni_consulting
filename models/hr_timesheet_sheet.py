from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
import logging
_logger = logging.getLogger(__name__)


class Sheet(models.Model):
    _inherit = "hr_timesheet.sheet"

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
