from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
from odoo.osv import expression
from odoo.addons.project.models.project_task import CLOSED_STATES
import logging

_logger = logging.getLogger(__name__)


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    task_id = fields.Many2one(
        domain="project_id and [('company_id', 'in', (company_id, False)), "
        "('project_id.allow_timesheets', '=', True), "
        "('state', 'not in', " + str(list(CLOSED_STATES.keys())) + "), "
        "('project_id', '=', project_id), "
        "('user_ids', 'in', user_id or uid)] "
        "or [('company_id', 'in', (company_id, False)), "
        "('project_id.allow_timesheets', '=', True), "
        "('project_id', '=?', project_id), "
        "('user_ids', 'in', user_id or uid)]",
    )

    event_id = fields.Many2one(
        'calendar.event',
        string='Calendar Event',
        ondelete='set null',
        index=True,
    )

    @api.model
    def _running_domain(self):
        try:
            domain = super()._running_domain()
        except Exception:
            _logger.exception("Failed to compute running domain via super().")
            raise
        else:
            return expression.AND([
                domain,
                [('holiday_id', '=', False), ('global_leave_id', '=', False)],
            ])

    @api.depends('holiday_id', 'global_leave_id')
    def _compute_show_time_control(self):
        """
        Hide time control UI when the line is linked to leave/global leave.
        """
        try:
            super()._compute_show_time_control()
        except Exception:
            _logger.exception("Failed to compute show_time_control via super().")
            raise
        else:
            for line in self:
                if line.holiday_id or line.global_leave_id:
                    line.show_time_control = False

    @api.onchange('project_id')
    def _onchange_project_id_clear_mismatched_task(self):
        for line in self:
            try:
                if line.task_id and line.project_id and line.task_id.project_id != line.project_id:
                    line.task_id = False
            except Exception:
                _logger.exception(
                    "Failed in onchange project/task consistency. line=%s",
                    line.id or "(new)",
                )
                return

    def _timesheet_determine_sale_line(self):
        try:
            so_line = super()._timesheet_determine_sale_line()
        except Exception:
            _logger.exception("Failed to determine sales order line via super().")
            raise
        if so_line:
            return so_line

        self.ensure_one()
        project = self.project_id
        if not (project and project.allow_billable):
            return False
        if project.pricing_type != "employee_rate":
            return False

        employee = self.employee_id or self.env.user.employee_id
        if not employee:
            return False

        map_entries = project.sale_line_employee_ids.filtered(
            lambda m: m.employee_id == employee
        )
        if self.task_id and self.task_id.partner_id and map_entries:
            map_entries = map_entries.filtered(
                lambda m:
                    m.sale_line_id.order_partner_id.commercial_partner_id
                    == self.task_id.partner_id.commercial_partner_id
            )

        return map_entries[:1].sale_line_id if map_entries else False
