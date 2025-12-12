from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
from odoo.osv import expression
import logging

_logger = logging.getLogger(__name__)


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    @api.model
    def _running_domain(self):
        try:
            domain = super()._running_domain()
        except Exception:
            _logger.exception("Failed to compute running domain via super().")
            raise
        else:
            # Keep your custom rules; they are independent from OCA task domain logic
            # Use expression.AND from odoo.osv to combine domains rather than tools.expression,
            # which does not expose the expression submodule in Odoo 18.0. See `odoo.osv.expression`
            # for utilities to safely combine search domains. This prevents AttributeError
            # on `odoo.tools.expression` while preserving the intent to filter out leave-related
            # analytic lines.
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