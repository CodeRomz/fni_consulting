# -----------------------------------------------------------------------------
# Standard imports and logger setup (place near the top of the file)
from odoo import models, fields, api, tools, _
from odoo.exceptions import (
    UserError, ValidationError, RedirectWarning, AccessDenied,
    AccessError, CacheMiss, MissingError
)
import logging
_logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Extend account.analytic.line to filter task_id dropdown by project
class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    # Show only open tasks (stage not closed) at model level
    task_id = fields.Many2one(
        comodel_name='project.task',
        string='Task',
        domain=[('stage_id.is_closed', '=', False)],
    )

    @api.onchange('project_id')
    def _onchange_project_id_update_task_domain(self):
        """
        Restrict task selection to open tasks within the selected project.
        Resets task_id if the current task doesn't belong to the new project.
        """
        self.ensure_one()
        # Base domain: tasks whose stage is not closed
        domain = [('stage_id.is_closed', '=', False)]
        try:
            if self.project_id:
                domain.append(('project_id', '=', self.project_id.id))
                # Clear task if it belongs to a different project
                if self.task_id and self.task_id.project_id.id != self.project_id.id:
                    _logger.debug(
                        "Resetting task_id %s as it doesn't belong to selected project %s",
                        self.task_id.id, self.project_id.id
                    )
                    self.task_id = False
        except Exception as exc:
            _logger.exception("Failed to compute task domain on project change: %s", exc)
        else:
            _logger.debug("Applying task_id domain: %s", domain)
            # Return domain so the UI filters the dropdown
            return {'domain': {'task_id': domain}}
        finally:
            _logger.debug("Completed onchange for project_id on account.analytic.line")
        # Fallback return in case of exception
        return {}

    # -------------------------------------------------------------------------
    # Custom task type field
    task_type_id = fields.Many2one(
        'hr.timesheet.task.type',
        string='Task Type',
        help='Type of task logged in the timesheet line.',
    )

    # -------------------------------------------------------------------------
    # Override show_time_control to hide start/stop icons on leave-linked lines
    @api.depends('employee_id', 'unit_amount', 'holiday_id', 'global_leave_id')
    def _compute_show_time_control(self):
        """
        Preserve the original show_time_control logic,
        then hide controls when linked to leaves or global leaves.
        """
        try:
            # Invoke the parent computation
            super()._compute_show_time_control()
            # Post-process: hide time controls if the line relates to a leave
            for line in self:
                if getattr(line, 'holiday_id', False) or getattr(line, 'global_leave_id', False):
                    line.show_time_control = False
        except Exception as exc:
            _logger.exception(
                "Error hiding time control for analytic line %s: %s",
                getattr(locals().get('line', self), 'id', 'n/a'),
                exc,
            )
        else:
            # No additional success actions needed
            pass
        finally:
            # Optional final cleanup or debug logging
            _logger.debug("Completed _compute_show_time_control in account.analytic.line")
