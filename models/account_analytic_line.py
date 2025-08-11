# -----------------------------------------------------------------------------
# Standard imports and logger setup (place near the top of the file)
from odoo import models, fields, api, tools, _
from odoo.exceptions import (
    UserError, ValidationError, RedirectWarning, AccessDenied,
    AccessError, CacheMiss, MissingError
)
from . import code_romz_ai  # per project standard
import logging
_logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Extend account.analytic.line to filter task_id dropdown (Odoo 17+ safe)
class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    # v17: "open" = not Done/Canceled; stage 'is_closed' is no longer the reliable switch.
    # Include both 'canceled' and 'cancelled' to be robust across locales/customizations.
    task_id = fields.Many2one(
        comodel_name="project.task",
        string="Task",
        domain=[('state', 'not in', ['done', 'canceled', 'cancelled'])],
        # keep other default attributes from core (ondelete/index/check_company) untouched
    )

    @api.onchange('project_id')
    def _onchange_project_id_update_task_domain(self):
        """
        Limit task dropdown to *open* tasks within the selected project.

        Open in Odoo 17 CE = state not in (done, canceled).
        """
        self.ensure_one()
        # Base domain: only not-closed tasks (per v17 statuses)
        domain = [('state', 'not in', ['done', 'canceled', 'cancelled'])]

        try:
            if self.project_id:
                domain.append(('project_id', '=', self.project_id.id))
        except Exception as exc:
            _logger.exception("Failed to compute task domain: %s", exc)
        else:
            _logger.debug("Applying task_id domain: %s", domain)
            return {'domain': {'task_id': domain}}
        finally:
            _logger.debug("Completed onchange for project_id on account.analytic.line")

        return {}

    # ---- keep your other customizations in the same class ----

    task_type_id = fields.Many2one(
        'hr.timesheet.task.type',
        string='Task Type',
        help='Type of task logged in the timesheet line.',
    )

    @api.depends('employee_id', 'unit_amount', 'holiday_id', 'global_leave_id')
    def _compute_show_time_control(self):
        """Hide start/stop icon for timesheets linked to leaves; preserve super behavior."""
        try:
            super()._compute_show_time_control()
            for line in self:
                if getattr(line, 'holiday_id', False) or getattr(line, 'global_leave_id', False):
                    line.show_time_control = False
        except Exception as exc:
            _logger.exception(
                "Error hiding time control for analytic line %s: %s",
                getattr(locals().get('line', self), 'id', 'n/a'),
                exc,
            )
