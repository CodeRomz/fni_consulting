from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
import logging
_logger = logging.getLogger(__name__)

class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    iban = fields.Char(
        string="IBAN",
        help="International Bank Account Number for this bank account.",
    )
