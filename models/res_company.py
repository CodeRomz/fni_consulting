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
        domain="[('model', '=', 'account.move'), ('report_type', '=', 'qweb-pdf')]",
        help="If set, this report replaces the standard invoice report for printing, sending and downloading.",
    )
