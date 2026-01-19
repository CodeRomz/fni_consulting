from odoo import models


class AccountMoveSend(models.AbstractModel):
    _inherit = "account.move.send"

    def _get_default_pdf_report_id(self, move):
        report = move.company_id.fni_default_invoice_report_id
        if (
            report
            and report.is_invoice_report
            and report.model == "account.move"
            and report.report_type == "qweb-pdf"
        ):
            return report
        fallback = self.env.ref(
            "fni_consulting.action_report_fni_invoice", raise_if_not_found=False
        )
        if (
            fallback
            and fallback.is_invoice_report
            and fallback.model == "account.move"
            and fallback.report_type == "qweb-pdf"
        ):
            return fallback
        return super()._get_default_pdf_report_id(move)
