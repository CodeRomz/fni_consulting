# models/res_company.py
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
import logging
_logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = "res.company"

    fni_default_invoice_report_id = fields.Many2one(
        comodel_name="ir.actions.report",
        string="FNI Default Invoice Report",
        domain="[('model', '=', 'account.move'), ('report_type', '=', 'qweb-pdf'), ('is_invoice_report', '=', True)]",
        help="If set, this report replaces the standard invoice report for printing, sending and downloading.",
    )

    # -------------------------------------------------------------------------
    # FNI Invoice Paper Format Configuration
    # -------------------------------------------------------------------------
    #
    # Odoo allows companies to choose a default paper format for all reports
    # (see Settings → Technical → Reports → Paper Format).  However, the
    # built‑in UI does not expose an easy way to choose a paper format as part
    # of custom module settings.  To support user‑selectable paper formats for
    # FNI invoices, we store the chosen paper format on the company and use
    # it when generating FNI reports.
    #
    # This field points to ``report.paperformat`` records.  It is optional; if
    # unset, the standard company paper format (or the report’s own
    # ``paperformat_id``) will be used.  When this field is set via
    # ``res.config.settings``, it can be propagated to the company’s
    # ``paperformat_id`` or the FNI report actions during ``set_values``.

    fni_invoice_paperformat_id = fields.Many2one(
        comodel_name="report.paperformat",
        string="FNI Invoice Paper Format",
        help=(
            "Custom paper format to use for FNI invoice PDFs.  If set, the"
            " default invoice report and FNI invoice report actions may be"
            " updated to use this format when saving settings.  Leave empty to"
            " use the company default paper format."
        ),
    )
