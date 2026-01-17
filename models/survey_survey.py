from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
import logging
_logger = logging.getLogger(__name__)

class Survey(models.Model):
    _inherit = 'survey.survey'

    certification_report_layout = fields.Selection(
        selection_add=[('fni-ack_o-ack', 'HR Emp Acknowledgement')],
    )
