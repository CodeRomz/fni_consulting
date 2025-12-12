# wizard/account_move_send_wizard.py
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
import logging
import base64

_logger = logging.getLogger(__name__)

class AccountMoveSendWizard(models.TransientModel):
    _inherit = "account.move.send.wizard"

    def _fni_force_report(self, moves):
        """
        Force the wizard to use the configured invoice report, if available.

        This helper performs two actions:
          1. Assign the configured report to any many2one/many2many fields that
             reference ``ir.actions.report`` on the wizard.
          2. Render the PDF using the configured report and attach it to the
             wizard so that the email sent to the customer uses the FNI layout.

        Rendering the PDF ensures that the attachment will always be the
        configured report, regardless of how the mail template is defined.
        """
        if not moves:
            return
        # Determine the configured report using the first move's company
        report = moves[0]._fni_get_default_report()
        if not report:
            return
        # Assign the report to any report fields defined on the wizard
        for field_name, field in self._fields.items():
            if field.comodel_name == "ir.actions.report":
                if field.type == "many2one":
                    self[field_name] = report.id
                elif field.type == "many2many":
                    self[field_name] = [(6, 0, [report.id])]

        try:
            # Render the PDF using the configured report.  The method
            # ``_render_qweb_pdf`` returns a tuple (pdf_bytes, file_name).
            pdf_content, pdf_name = report._render_qweb_pdf(moves.ids)
            if not pdf_name:
                pdf_name = report.name
            # Create an attachment with the generated PDF.  The attachment
            # references the first move in the batch; this is consistent with
            # Odoo's behaviour when emailing invoices.
            attachment = self.env['ir.attachment'].create({
                'name': pdf_name,
                'datas': base64.b64encode(pdf_content),
                'res_model': moves._name,
                'res_id': moves[0].id,
                'mimetype': 'application/pdf',
            })
            # Replace or set the wizard's attachments to ensure only our PDF is
            # included.  Using (6, 0, ...) resets the m2m field to the given
            # attachment.
            self.attachment_ids = [(6, 0, [attachment.id])]
        except Exception:
            # If rendering fails, log the exception and continue without
            # attaching our PDF.  This fallbacks to the default behaviour.
            _logger.exception("Failed to render or attach FNI invoice PDF in send wizard")

    def action_send(self, *args, **kwargs):
        moves = getattr(self, "move_ids", self.env["account.move"])
        if not moves and self._context.get("active_model") == "account.move":
            moves = self.env["account.move"].browse(self._context.get("active_ids", []))
        self._fni_force_report(moves)
        # Call the original implementation; attachments and report fields have
        # been adjusted by _fni_force_report().
        return super().action_send(*args, **kwargs)

    def action_send_and_print(self, *args, **kwargs):
        moves = getattr(self, "move_ids", self.env["account.move"])
        if not moves and self._context.get("active_model") == "account.move":
            moves = self.env["account.move"].browse(self._context.get("active_ids", []))
        self._fni_force_report(moves)
        return super().action_send_and_print(*args, **kwargs)
