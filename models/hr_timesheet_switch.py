from odoo import api, models, _
from odoo.exceptions import UserError

class HrTimesheetSwitch(models.TransientModel):
    _inherit = "hr.timesheet.switch"

    @api.model
    def _default_running_timer_id(self, employee=None):
        """
        Find the running timer but ignore timesheets linked to holidays.
        """
        employee = employee or self.env.user.employee_ids
        running = self.env['account.analytic.line'].search([
            ('date_time', '!=', False),
            ('employee_id', 'in', employee.ids),
            ('id', 'not in', self.env.context.get('resuming_lines', [])),
            ('project_id', '!=', False),
            ('unit_amount', '=', 0),
            ('holiday_id', '=', False),        # exclude time-off lines:contentReference[oaicite:2]{index=2}
            ('global_leave_id', '=', False),   # exclude global leave lines:contentReference[oaicite:3]{index=3}
        ])
        if len(running) > 1:
            raise UserError(
                _("%d running timers found. Cannot know which one to stop. Please stop them manually.") % len(running)
            )
        return running
