# models/account_move.py
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    def _fni_get_default_report(self):
        """Return the company's configured invoice report or an empty recordset."""
        self.ensure_one()
        report = self.company_id.fni_default_invoice_report_id
        try:
            if report and report.model == "account.move" and report.report_type == "qweb-pdf":
                return report
        except Exception:
            _logger.exception("Error resolving FNI default invoice report")
        return self.env["ir.actions.report"]

    def _fni_report_action_or_super(self, super_method_name):
        """Use the default report if configured; otherwise call the super method."""
        moves = self
        if not moves:
            return True
        report = moves[0]._fni_get_default_report()
        if report:
            try:
                return report.report_action(moves)
            except Exception:
                _logger.exception("Configured invoice report failed; falling back")
        super_method = getattr(super(AccountMove, moves), super_method_name, None)
        return super_method() if super_method else True

    # Print menu and batch print
    def action_invoice_print(self):
        return self._fni_report_action_or_super("action_invoice_print")

    # Print → PDF / PDF without payment
    def action_print_pdf(self):
        return self._fni_report_action_or_super("action_print_pdf")

    # Portal / Preview download path (dynamic injection:contentReference[oaicite:1]{index=1})
    def action_invoice_download_pdf(self):
        return self._fni_report_action_or_super("action_invoice_download_pdf")
