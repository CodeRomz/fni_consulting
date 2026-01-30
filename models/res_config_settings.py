from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    timesheet_sheet_reminder_enabled = fields.Boolean(
        related="company_id.timesheet_sheet_reminder_enabled",
        readonly=False,
    )
    timesheet_sheet_deadline_weekday = fields.Selection(
        related="company_id.timesheet_sheet_deadline_weekday",
        readonly=False,
    )
    timesheet_sheet_reminder_days_info = fields.Integer(
        related="company_id.timesheet_sheet_reminder_days_info",
        readonly=False,
    )
    timesheet_sheet_reminder_days_warning = fields.Integer(
        related="company_id.timesheet_sheet_reminder_days_warning",
        readonly=False,
    )
    timesheet_sheet_reminder_days_danger = fields.Integer(
        related="company_id.timesheet_sheet_reminder_days_danger",
        readonly=False,
    )
    timesheet_sheet_overdue_reminder_interval_days = fields.Integer(
        related="company_id.timesheet_sheet_overdue_reminder_interval_days",
        readonly=False,
    )
