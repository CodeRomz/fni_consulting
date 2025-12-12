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
        help="Configure which invoice report is used by default.",
    )
