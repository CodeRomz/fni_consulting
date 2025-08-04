from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
import logging
_logger = logging.getLogger(__name__)

class HrTimesheetTaskType(models.Model):
    _name = 'hr.timesheet.task.type'
    _description = 'Timesheet Task Type'

    name = fields.Char(string='Task Type', required=True)
    active = fields.Boolean(default=True)
