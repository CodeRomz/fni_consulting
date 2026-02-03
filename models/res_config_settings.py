from odoo import fields, models, _
from odoo.exceptions import AccessError


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
    timesheet_sheet_weekly_autocreate_enabled = fields.Boolean(
        related="company_id.timesheet_sheet_weekly_autocreate_enabled",
        readonly=False,
    )
    timesheet_sheet_weekly_autocreate_weekday = fields.Selection(
        related="company_id.timesheet_sheet_weekly_autocreate_weekday",
        readonly=False,
    )

    def action_run_weekly_autocreate(self):
        if not (
            self.env.user.has_group("hr.group_hr_manager")
            or self.env.user.has_group("hr_timesheet.group_hr_timesheet_approver")
        ):
            raise AccessError(_("You do not have the rights to run this action."))
        stats = (
            self.env["hr_timesheet.sheet"]
            .with_context(timesheet_weekly_autocreate_manual=True)
            ._cron_autocreate_weekly_sheets()
        )
        created = (stats or {}).get("created", 0)
        skipped = (stats or {}).get("skipped", 0)
        errors = (stats or {}).get("errors", 0)
        message = _(
            "Created %(created)s draft sheet(s). "
            "Skipped %(skipped)s employee(s) with existing sheets. "
            "Errors: %(errors)s."
        ) % {
            "created": created,
            "skipped": skipped,
            "errors": errors,
        }
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Weekly Auto-Create"),
                "message": message,
                "type": "success" if not errors else "warning",
                "sticky": False,
            },
        }
