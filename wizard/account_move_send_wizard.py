# wizard/account_move_send_wizard.py
from odoo import models


class AccountMoveSendWizard(models.TransientModel):
    _inherit = "account.move.send.wizard"

    def _fni_apply_report(self, moves):
        """Force the configured invoice report on the wizard when possible."""
        if not moves:
            return
        if len(moves.company_id) > 1:
            return
        report = moves[0]._fni_get_default_report()
        if not report:
            return
        for wizard in self:
            wizard.pdf_report_id = report

    def action_send(self, *args, **kwargs):
        moves = getattr(self, "move_ids", self.env["account.move"])
        if not moves and self._context.get("active_model") == "account.move":
            moves = self.env["account.move"].browse(self._context.get("active_ids", []))
        self._fni_apply_report(moves)
        return super().action_send(*args, **kwargs)

    def action_send_and_print(self, *args, **kwargs):
        moves = getattr(self, "move_ids", self.env["account.move"])
        if not moves and self._context.get("active_model") == "account.move":
            moves = self.env["account.move"].browse(self._context.get("active_ids", []))
        self._fni_apply_report(moves)
        return super().action_send_and_print(*args, **kwargs)
