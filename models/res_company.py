# models/res_company.py
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
import logging
_logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = "res.company"

    external_report_layout_id = fields.Many2one(
        comodel_name="ir.ui.view",
        string="Document Template",
        default=lambda self: self.env.ref(
            "web.external_layout_striped", raise_if_not_found=False
        ),
    )

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

    # -------------------------------------------------------------------------
    # Timesheet Sheet Reminder Configuration
    # -------------------------------------------------------------------------
    timesheet_sheet_reminder_enabled = fields.Boolean(
        string="Timesheet Sheet Reminders",
        default=True,
        help=(
            "Enable periodic reminder emails for employees who have not yet "
            "submitted their timesheet sheet."
        ),
    )
    timesheet_sheet_deadline_weekday = fields.Selection(
        selection=[
            ("0", "Monday"),
            ("1", "Tuesday"),
            ("2", "Wednesday"),
            ("3", "Thursday"),
            ("4", "Friday"),
            ("5", "Saturday"),
            ("6", "Sunday"),
        ],
        string="Timesheet Sheet Deadline Weekday",
        default="1",
        help=(
            "Submission deadline weekday for each timesheet sheet. The system "
            "uses the next occurrence of this weekday after the sheet end date."
        ),
    )
    timesheet_sheet_reminder_days_info = fields.Integer(
        string="Info Reminder (days before deadline)",
        default=4,
        help=(
            "Number of days before the deadline to send an informational reminder."
        ),
    )
    timesheet_sheet_reminder_days_warning = fields.Integer(
        string="Warning Reminder (days before deadline)",
        default=2,
        help=(
            "Number of days before the deadline to send a warning reminder."
        ),
    )
    timesheet_sheet_reminder_days_danger = fields.Integer(
        string="Final Reminder (days before deadline)",
        default=0,
        help=(
            "Number of days before the deadline to send the final reminder. "
            "Use 0 to send on the deadline day."
        ),
    )
    timesheet_sheet_overdue_reminder_interval_days = fields.Integer(
        string="Overdue Reminder Interval (days)",
        default=7,
        help=(
            "Number of days between reminders for overdue timesheet sheets. "
            "Set to 0 to disable overdue reminders."
        ),
    )

    timesheet_sheet_weekly_autocreate_enabled = fields.Boolean(
        string="Weekly Timesheet Auto-Create",
        default=False,
        help=(
            "Create weekly draft timesheet sheets automatically at 1:00 AM in "
            "each employee's timezone."
        ),
    )
    timesheet_sheet_weekly_autocreate_weekday = fields.Selection(
        selection=lambda self: self._fields["timesheet_week_start"].selection,
        string="Timesheet Sheet Auto-Create Weekday",
        default="0",
        help=(
            "Weekday when weekly draft timesheet sheets are created. The system "
            "uses the employee's local timezone."
        ),
    )

    def init(self):
        """Backfill defaults for existing companies on install/upgrade."""
        self.env.cr.execute(
            """
            UPDATE res_company
               SET timesheet_sheet_reminder_enabled = TRUE
             WHERE timesheet_sheet_reminder_enabled IS NULL
            """
        )
        self.env.cr.execute(
            """
            UPDATE res_company
               SET timesheet_sheet_deadline_weekday = '1'
             WHERE timesheet_sheet_deadline_weekday IS NULL
            """
        )
        self.env.cr.execute(
            """
            UPDATE res_company
               SET timesheet_sheet_reminder_days_info = 4
             WHERE timesheet_sheet_reminder_days_info IS NULL
            """
        )
        self.env.cr.execute(
            """
            UPDATE res_company
               SET timesheet_sheet_reminder_days_warning = 2
             WHERE timesheet_sheet_reminder_days_warning IS NULL
            """
        )
        self.env.cr.execute(
            """
            UPDATE res_company
               SET timesheet_sheet_reminder_days_danger = 0
             WHERE timesheet_sheet_reminder_days_danger IS NULL
            """
        )
        self.env.cr.execute(
            """
            UPDATE res_company
               SET timesheet_sheet_overdue_reminder_interval_days = 7
             WHERE timesheet_sheet_overdue_reminder_interval_days IS NULL
            """
        )
        self.env.cr.execute(
            """
            UPDATE res_company
               SET timesheet_sheet_weekly_autocreate_enabled = FALSE
             WHERE timesheet_sheet_weekly_autocreate_enabled IS NULL
            """
        )
        self.env.cr.execute(
            """
            UPDATE res_company
               SET timesheet_sheet_weekly_autocreate_weekday = COALESCE(timesheet_week_start, '0')
             WHERE timesheet_sheet_weekly_autocreate_weekday IS NULL
            """
        )
