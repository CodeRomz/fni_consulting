# wizard/account_move_send_wizard.py
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
import logging
import base64  # <-- needed to encode the PDF
_logger = logging.getLogger(__name__)

class AccountMoveSendWizard(models.TransientModel):
    _inherit = "account.move.send.wizard"

    def _fni_force_report(self, moves):
        """Force the wizard to use the configured invoice report, if available."""
        if not moves:
            return
        # get your configured report
        report = moves[0]._fni_get_default_report()
        if not report:
            return

        # First, attempt to set any many2one/many2many fields that point to ir.actions.report
        for fname, field in self._fields.items():
            if field.comodel_name == "ir.actions.report":
                if field.type == "many2one":
                    self[fname] = report.id
                elif field.type == "many2many":
                    self[fname] = [(6, 0, [report.id])]

        # Next, generate the PDF and attach it to the wizard so the e‑mail uses it
        pdf_content, pdf_name = report._render_qweb_pdf(moves.ids)
        attachment = self.env['ir.attachment'].create({
            'name': pdf_name,
            'datas': base64.b64encode(pdf_content),
            'res_model': moves._name,
            'res_id': moves.id,
            'mimetype': 'application/pdf',
        })
        self.attachment_ids = [(6, 0, [attachment.id])]

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
