from odoo import fields, models


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    timesheet_sheet_reminder_opt_in = fields.Boolean(
        related="employee_id.timesheet_sheet_reminder_opt_in",
        readonly=True,
        store=True,
        help=(
            "Read-only mirror of the Timesheet Sheet Reminder flag from the "
            "private employee record."
        ),
    )
