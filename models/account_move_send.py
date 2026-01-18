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
        return super()._get_default_pdf_report_id(move)
