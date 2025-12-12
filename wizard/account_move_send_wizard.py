# wizard/account_move_send_wizard.py
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
import logging
_logger = logging.getLogger(__name__)

class AccountMoveSendWizard(models.TransientModel):
    _inherit = "account.move.send.wizard"

    def _fni_force_report(self, moves):
        """Force the wizard to use the configured invoice report, if available."""
        if not moves:
            return
        report = moves[0]._fni_get_default_report()
        if not report:
            return
        # Replace any M2O field pointing to ir.actions.report
        for field_name, field in self._fields.items():
            if field.comodel_name == "ir.actions.report" and field.type == "many2one":
                self[field_name] = report.id
            if field.comodel_name == "ir.actions.report" and field.type == "many2many":
                self[field_name] = [(6, 0, [report.id])]

    def action_send(self, *args, **kwargs):
        moves = getattr(self, "move_ids", self.env["account.move"])
        if not moves and self._context.get("active_model") == "account.move":
            moves = self.env["account.move"].browse(self._context.get("active_ids", []))
        self._fni_force_report(moves)
        return super().action_send(*args, **kwargs)

    def action_send_and_print(self, *args, **kwargs):
        moves = getattr(self, "move_ids", self.env["account.move"])
        if not moves and self._context.get("active_model") == "account.move":
            moves = self.env["account.move"].browse(self._context.get("active_ids", []))
        self._fni_force_report(moves)
        return super().action_send_and_print(*args, **kwargs)
