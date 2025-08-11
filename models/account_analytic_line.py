# -------------------------------------------------------------------------------
# Standard imports and logger setup (place near the top of the file)
from odoo import models, fields, api, tools, _
from odoo.exceptions import (
    UserError, ValidationError, RedirectWarning, AccessDenied,
    AccessError, CacheMiss, MissingError
)
import logging
_logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------------
# Extend account.analytic.line to filter task_id dropdown by project and status
class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    # Use the correct closed-state values for Odoo 17 CE: '1_done' and '1_canceled'
    task_id = fields.Many2one(
        comodel_name='project.task',
        string='Task',
        domain=[('state', 'not in', ['1_done', '1_canceled'])],
    )

    @api.onchange('project_id')
    def _onchange_project_id_update_task_domain(self):
        """
        Restrict task selection to open tasks within the selected project.
        Reset task_id if it belongs to a different project.
        """
        self.ensure_one()
        # Base domain for open tasks in Odoo 17 CE
        domain = [('state', 'not in', ['1_done', '1_canceled'])]
        try:
            if self.project_id:
                # Add project filter when a project is selected
                domain.append(('project_id', '=', self.project_id.id))
                # Clear task if it does not belong to the selected project
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
            # Return the domain so the UI filters tasks correctly
            return {'domain': {'task_id': domain}}
        finally:
            _logger.debug("Completed onchange for project_id on account.analytic.line")
        # Fallback return if an exception occurred
        return {}

    # ---------------------------------------------------------------------------
    # Additional customizations (keep these unchanged)
    task_type_id = fields.Many2one(
        'hr.timesheet.task.type',
        string='Task Type',
        help='Type of task logged in the timesheet line.',
    )

    @api.depends('employee_id', 'unit_amount', 'holiday_id', 'global_leave_id')
    def _compute_show_time_control(self):
        """
        Preserve default time-control behavior,
        then hide controls when the line is linked to a leave.
        """
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
        else:
            pass
        finally:
            _logger.debug("Completed _compute_show_time_control in account.analytic.line")
