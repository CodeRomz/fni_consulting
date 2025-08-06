from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
import logging
_logger = logging.getLogger(__name__)

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    task_type_id = fields.Many2one(
        'hr.timesheet.task.type',
        string='Task Type',
        help='Type of task logged in the timesheet line.'
    )

    @api.depends('employee_id', 'unit_amount', 'holiday_id', 'global_leave_id')
    def _compute_show_time_control(self):
        super()._compute_show_time_control()
        for line in self:
            try:
                # Hide start/stop icon for timesheets linked to leaves
                if getattr(line, 'holiday_id', False) or getattr(line, 'global_leave_id', False):
                    line.show_time_control = False
            except Exception as exc:
                _logger.exception(
                    "Error hiding time control for analytic line %s: %s", line.id, exc
                )