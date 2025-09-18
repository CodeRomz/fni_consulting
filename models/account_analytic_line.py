# -----------------------------------------------------------------------------
# Standard imports and logger setup
from odoo import models, fields, api, tools, _
from odoo.exceptions import (
    UserError, ValidationError, RedirectWarning, AccessDenied,
    AccessError, CacheMiss, MissingError
)
import logging
_logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Extend account.analytic.line to filter task_id dropdown
class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    # Keep other customizations unchanged
    task_type_id = fields.Many2one(
        'hr.timesheet.task.type',
        string='Task Type',
        help='Type of task logged in the timesheet line.',
    )

    # Use a domain that combines the native project filter with the open‑state filter
    # Note: In Odoo 17 CE, the closed states are '1_done' and '1_canceled'
    task_id = fields.Many2one(
        comodel_name='project.task',
        string='Task',
        domain=(
            "["
            "('allow_timesheets', '=', True), "
            "('project_id', '=?', project_id), "
            "('state', 'not in', ('1_done', '1_canceled'))"
            "]"
        ),
    )

    @api.model
    def _running_domain(self):
        # get the base domain from OCA project_timesheet_time_control:contentReference[oaicite:0]{index=0}
        domain = super()._running_domain()
        # exclude timesheet lines linked to time off (holiday_id/global_leave_id):contentReference[oaicite:1]{index=1}
        domain += [
            ('holiday_id', '=', False),
            ('global_leave_id', '=', False),
        ]
        return domain

    @api.onchange('project_id')
    def _onchange_project_id_update_task(self):

        self.ensure_one()
        try:
            if self.task_id:
                if (
                    self.task_id.project_id != self.project_id
                    or self.task_id.state in ('1_done', '1_canceled')
                ):
                    _logger.debug(
                        "Resetting task_id %s: mismatch with project %s or task is closed",
                        self.task_id.id, self.project_id.id if self.project_id else None
                    )
                    self.task_id = False
        except Exception as exc:
            _logger.exception(
                "Failed to reset task_id on project change: %s", exc
            )
        else:
            # No need to return a domain: the field-level domain handles filtering
            return
        finally:
            _logger.debug("Completed onchange project_id for account.analytic.line")

    # -------------------------------------------------------------------------

    @api.depends('employee_id', 'unit_amount', 'holiday_id', 'global_leave_id')
    def _compute_show_time_control(self):
        """
        Preserve default show_time_control behavior, then hide controls
        when linked to leaves.
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
