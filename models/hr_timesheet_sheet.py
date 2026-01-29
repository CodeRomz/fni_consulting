from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
from odoo.osv import expression
from dateutil.relativedelta import relativedelta, MO, TU, WE, TH, FR, SA, SU
import logging
_logger = logging.getLogger(__name__)

_DEADLINE_WEEKDAY_MAP = {
    "0": MO,
    "1": TU,
    "2": WE,
    "3": TH,
    "4": FR,
    "5": SA,
    "6": SU,
}
_REMINDER_LEVEL_RANK = {"info": 1, "warning": 2, "danger": 3}


class Sheet(models.Model):
    _inherit = "hr_timesheet.sheet"

    reminder_last_date = fields.Date(
        string="Last Reminder Date",
        readonly=True,
        copy=False,
        help="Internal field to avoid sending duplicate reminder emails.",
    )
    reminder_last_level = fields.Selection(
        selection=[
            ("info", "Info"),
            ("warning", "Warning"),
            ("danger", "Danger"),
        ],
        string="Last Reminder Level",
        readonly=True,
        copy=False,
        help="Internal field to avoid sending duplicate reminder emails.",
    )

    def _get_timesheet_sheet_lines_domain(self):

        self.ensure_one()

        try:
            base_domain = super()._get_timesheet_sheet_lines_domain()
        except Exception:
            _logger.exception("Failed to compute base domain via super().")
            raise

        try:
            sheet_company = self._get_timesheet_sheet_company()
        except Exception:
            _logger.exception("Failed to compute sheet company.")
            raise

        leave_domain = [
            ("date", "<=", self.date_end),
            ("date", ">=", self.date_start),
            ("employee_id", "=", self.employee_id.id),
            ("company_id", "in", [sheet_company.id, False]),
            ("project_id", "!=", False),
            "|",
            ("holiday_id", "!=", False),
            ("global_leave_id", "!=", False),
        ]

        return expression.OR([base_domain, leave_domain])

    def clean_timesheets(self, timesheets):

        try:
            protected = timesheets.filtered(lambda t: t.holiday_id or t.global_leave_id)
            regular = timesheets - protected
            cleaned = super().clean_timesheets(regular)
        except Exception:
            _logger.exception("Failed to clean timesheets in sheet")
            raise
        else:
            return protected | cleaned

    def _get_sheet_deadline_date(self):
        self.ensure_one()
        if not self.date_end:
            return False
        weekday_key = self.company_id.timesheet_sheet_deadline_weekday or "1"
        weekday = _DEADLINE_WEEKDAY_MAP.get(weekday_key, TU)
        return self.date_end + relativedelta(weekday=weekday(+1))

    @api.model
    def _get_company_reminder_days(self, company):
        return {
            "info": company.timesheet_sheet_reminder_days_info,
            "warning": company.timesheet_sheet_reminder_days_warning,
            "danger": company.timesheet_sheet_reminder_days_danger,
        }

    @api.model
    def _get_reminder_level_meta(self):
        return {
            "info": {"label": _("Info"), "color": "#17a2b8"},
            "warning": {"label": _("Warning"), "color": "#f0ad4e"},
            "danger": {"label": _("Danger"), "color": "#d9534f"},
        }

    @api.model
    def _get_reminder_level_for_days(self, company, days_left):
        days_by_level = self._get_company_reminder_days(company)
        for level in ("danger", "warning", "info"):
            days = days_by_level.get(level)
            if days is None or days < 0:
                continue
            if days_left == days:
                return level
        return False

    @api.model
    def _get_reminder_subject(self, days_left):
        if days_left == 0:
            return _("Timesheet sheets due today")
        if days_left == 1:
            return _("Timesheet sheets due in 1 day")
        return _("Timesheet sheets due in %(days)s days", days=days_left)

    @api.model
    def _cron_send_pending_sheet_digest(self):
        domain = [
            ("state", "in", ("new", "draft")),
            ("employee_id", "!=", False),
            ("employee_id.active", "=", True),
            ("employee_id.timesheet_sheet_reminder_opt_in", "=", True),
            ("company_id.timesheet_sheet_reminder_enabled", "=", True),
        ]
        sheets = self.sudo().search(domain)
        if not sheets:
            return

        template = self.env.ref(
            "fni_consulting.mail_template_timesheet_sheet_reminder",
            raise_if_not_found=False,
        )
        if not template:
            _logger.warning(
                "Timesheet reminder template not found: fni_consulting.mail_template_timesheet_sheet_reminder"
            )
            return

        base_url = (
            self.env["ir.config_parameter"].sudo().get_param("web.base.url") or ""
        )
        sheets_by_employee = {}
        for sheet in sheets:
            sheets_by_employee.setdefault(sheet.employee_id, []).append(sheet)

        level_meta = self._get_reminder_level_meta()
        for employee, employee_sheets in sheets_by_employee.items():
            email_to = (
                employee.work_email
                or employee.user_id.email
                or employee.user_id.partner_id.email
            )
            if not email_to:
                continue

            tz = employee.user_id.tz or self.env.user.tz or "UTC"
            today = fields.Date.context_today(self.with_context(tz=tz))

            display_items = []
            trigger_levels = []
            level_sheets = {
                "info": self.env["hr_timesheet.sheet"],
                "warning": self.env["hr_timesheet.sheet"],
                "danger": self.env["hr_timesheet.sheet"],
            }
            for sheet in employee_sheets:
                deadline = sheet._get_sheet_deadline_date()
                if not deadline:
                    continue
                days_left = (deadline - today).days
                level = self._get_reminder_level_for_days(sheet.company_id, days_left)

                display_items.append(
                    {
                        "id": sheet.id,
                        "name": sheet.display_name,
                        "date_start": sheet.date_start,
                        "date_end": sheet.date_end,
                        "deadline": deadline,
                        "days_left": days_left,
                        "level": level,
                        "url": (
                            f"{base_url}/web#id={sheet.id}&model=hr_timesheet.sheet&view_type=form"
                            if base_url
                            else ""
                        ),
                    }
                )

                if not level:
                    continue
                if sheet.reminder_last_date == today and sheet.reminder_last_level == level:
                    continue
                trigger_levels.append(level)
                level_sheets[level] |= sheet

            if not trigger_levels:
                continue

            overall_level = max(
                trigger_levels, key=lambda level: _REMINDER_LEVEL_RANK[level]
            )
            trigger_days_left = min(
                item["days_left"]
                for item in display_items
                if item.get("level")
            )
            trigger_deadline = min(
                item["deadline"]
                for item in display_items
                if item.get("level")
            )
            subject = self._get_reminder_subject(trigger_days_left)

            template.with_context(
                sheets=sorted(display_items, key=lambda item: item["deadline"]),
                reminder_level=overall_level,
                reminder_label=level_meta[overall_level]["label"],
                accent_color=level_meta[overall_level]["color"],
                deadline_date=trigger_deadline,
                days_left=trigger_days_left,
                email_subject=subject,
            ).send_mail(
                employee.id,
                force_send=True,
                email_values={"email_to": email_to},
            )

            for level, level_sheet in level_sheets.items():
                if level_sheet:
                    level_sheet.write(
                        {
                            "reminder_last_date": today,
                            "reminder_last_level": level,
                        }
                    )
