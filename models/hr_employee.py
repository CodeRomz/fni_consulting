from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    timesheet_sheet_reminder_opt_in = fields.Boolean(
        string="Timesheet Sheet Reminder",
        default=True,
        help=(
            "If enabled, this employee will receive reminder emails when a "
            "timesheet sheet is still unsubmitted."
        ),
    )

    def init(self):
        """Backfill defaults for existing employees on install/upgrade."""
        self.env.cr.execute(
            """
            UPDATE hr_employee
               SET timesheet_sheet_reminder_opt_in = TRUE
             WHERE timesheet_sheet_reminder_opt_in IS NULL
            """
        )
