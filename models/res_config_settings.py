# models/res_config_settings.py
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
import logging
_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    fni_default_invoice_report_id = fields.Many2one(
        related="company_id.fni_default_invoice_report_id",
        readonly=False,
        domain="[('model', '=', 'account.move'), ('report_type', '=', 'qweb-pdf'), ('is_invoice_report', '=', True)]",
        help="Configure which invoice report is used by default.",
    )

    # -------------------------------------------------------------------------
    # FNI Invoice Paper Format Configuration
    # -------------------------------------------------------------------------
    #
    # Expose the company’s FNI invoice paper format in the settings UI.  This
    # field is related to :model:`res.company.fni_invoice_paperformat_id`.  When
    # changed and saved, ``set_values`` will propagate the selected format to
    # the company’s ``paperformat_id`` (making it the default for all reports)
    # or to the default FNI invoice report if configured.
    fni_invoice_paperformat_id = fields.Many2one(
        "report.paperformat",
        string="FNI Invoice Paper Format",
        related="company_id.fni_invoice_paperformat_id",
        readonly=False,
        help=(
            "Paper format to use for FNI invoice PDFs.  If set, this value"
            " will propagate to the company’s default paper format when the"
            " settings are saved, ensuring that the preview download and"
            " back‑office printing use the same format."
        ),
    )

    @api.model
    def set_values(self):
        """
        Persist FNI paper format configuration.

        When saving settings, update the company’s default paper format to match
        ``fni_invoice_paperformat_id``, so that all reports—including the
        preview download—use the same paper size and margins.  Also update
        the FNI default invoice report (if one is configured) to use this
        paper format.  Wrap updates in try/except to avoid crashing the UI.
        """
        company = self.company_id
        old_paperformat = company.fni_invoice_paperformat_id
        res = super(ResConfigSettings, self).set_values()
        paperformat = company.fni_invoice_paperformat_id
        report = company.fni_default_invoice_report_id
        try:
            if paperformat:
                company.paperformat_id = paperformat
                if report:
                    report.paperformat_id = paperformat
            else:
                # Clear only if we previously set the same format.
                if old_paperformat and company.paperformat_id == old_paperformat:
                    company.paperformat_id = False
                if report and old_paperformat and report.paperformat_id == old_paperformat:
                    report.paperformat_id = False
        except Exception:
            _logger.exception(
                "Failed to apply FNI invoice paper format settings to company or report"
            )
        return res
