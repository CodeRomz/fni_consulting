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
    def _get_reminder_level_for_days(
        self, company, days_left, last_level=None, days_by_level=None
    ):
        days_by_level = days_by_level or self._get_company_reminder_days(company)
        for level in ("danger", "warning", "info"):
            days = days_by_level.get(level)
            if days is None or days < 0:
                continue
            if days_left <= days:
                if last_level and _REMINDER_LEVEL_RANK.get(last_level, 0) >= _REMINDER_LEVEL_RANK[level]:
                    return False
                return level
        return False

    @api.model
    def _is_overdue_reminder_due(self, sheet, today, deadline):
        if not deadline or not today or today <= deadline:
            return False
        interval_days = sheet.company_id.timesheet_sheet_overdue_reminder_interval_days
        if interval_days is None or interval_days <= 0:
            return False
        if sheet.reminder_last_date:
            if (today - sheet.reminder_last_date).days < interval_days:
                return False
        return True

    @api.model
    def _get_reminder_subject(self, days_left):
        if days_left is None:
            return _("Timesheet sheets reminder")
        if days_left < 0:
            return _("Timesheet sheets overdue by %(days)s days", days=abs(days_left))
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
        today_by_tz = {}
        reminder_days_by_company = {}
        for employee, employee_sheets in sheets_by_employee.items():
            email_to = (
                employee.work_email
                or employee.user_id.email
                or employee.user_id.partner_id.email
            )
            if not email_to:
                continue

            tz = employee.user_id.tz or self.env.user.tz or "UTC"
            if tz not in today_by_tz:
                today_by_tz[tz] = fields.Date.context_today(
                    self.with_context(tz=tz)
                )
            today = today_by_tz[tz]

            display_items = []
            trigger_levels = []
            level_sheets = {
                "info": self.env["hr_timesheet.sheet"],
                "warning": self.env["hr_timesheet.sheet"],
                "danger": self.env["hr_timesheet.sheet"],
            }
            for sheet in employee_sheets:
                if sheet.date_start and sheet.date_start > today:
                    continue
                deadline = sheet._get_sheet_deadline_date()
                if not deadline:
                    continue
                days_left = (deadline - today).days
                is_overdue = days_left < 0
                days_overdue = abs(days_left) if is_overdue else 0

                if is_overdue:
                    level = "danger" if self._is_overdue_reminder_due(sheet, today, deadline) else False
                else:
                    company_id = sheet.company_id.id
                    if company_id not in reminder_days_by_company:
                        reminder_days_by_company[company_id] = self._get_company_reminder_days(
                            sheet.company_id
                        )
                    level = self._get_reminder_level_for_days(
                        sheet.company_id,
                        days_left,
                        sheet.reminder_last_level,
                        reminder_days_by_company[company_id],
                    )

                display_items.append(
                    {
                        "id": sheet.id,
                        "name": sheet.display_name,
                        "date_start": sheet.date_start,
                        "date_end": sheet.date_end,
                        "deadline": deadline,
                        "days_left": days_left,
                        "is_overdue": is_overdue,
                        "days_overdue": days_overdue,
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
            is_overdue = trigger_days_left < 0
            overdue_items = [item for item in display_items if item.get("is_overdue")]
            overdue_count = len(overdue_items)
            max_days_overdue = max(
                (item.get("days_overdue", 0) for item in overdue_items), default=0
            )
            upcoming_items = [item for item in display_items if not item.get("is_overdue")]
            upcoming_count = len(upcoming_items)
            next_due_days = min(
                (item.get("days_left") for item in upcoming_items), default=None
            )
            trigger_deadline = min(
                item["deadline"]
                for item in display_items
                if item.get("level")
            )
            subject = self._get_reminder_subject(trigger_days_left)

            try:
                template.with_context(
                    sheets=sorted(display_items, key=lambda item: item["deadline"]),
                    reminder_level=overall_level,
                    reminder_label=_("Overdue") if is_overdue else level_meta[overall_level]["label"],
                    accent_color=level_meta[overall_level]["color"],
                    deadline_date=trigger_deadline,
                    days_left=trigger_days_left,
                    is_overdue=is_overdue,
                    days_overdue=abs(trigger_days_left) if is_overdue else 0,
                    overdue_count=overdue_count,
                    max_days_overdue=max_days_overdue,
                    upcoming_count=upcoming_count,
                    next_due_days=next_due_days,
                    email_subject=subject,
                ).send_mail(
                    employee.id,
                    force_send=True,
                    email_values={"email_to": email_to},
                )
            except Exception:
                _logger.exception(
                    "Failed to send timesheet sheet reminder to employee %s",
                    employee.display_name,
                )
                continue

            for level, level_sheet in level_sheets.items():
                if level_sheet:
                    level_sheet.write(
                        {
                            "reminder_last_date": today,
                            "reminder_last_level": level,
                        }
                    )

    @api.model
    def _cron_autocreate_weekly_sheets(self):
        stats = {"created": 0, "skipped": 0, "errors": 0}
        manual = bool(self.env.context.get("timesheet_weekly_autocreate_manual"))
        Company = self.env["res.company"].sudo()
        companies = Company.search(
            [
                ("timesheet_sheet_weekly_autocreate_enabled", "=", True),
                ("sheet_range", "=", "WEEKLY"),
            ]
        )
        if not companies:
            return stats

        Employee = self.env["hr.employee"].sudo()
        Sheet = self.env["hr_timesheet.sheet"].sudo()
        now_utc = fields.Datetime.now()

        for company in companies:
            try:
                company_ctx = dict(
                    self.env.context, allowed_company_ids=[company.id]
                )
                employees = Employee.with_context(company_ctx).search(
                    [
                        ("company_id", "=", company.id),
                        ("active", "=", True),
                        ("user_id", "!=", False),
                        ("timesheet_sheet_reminder_opt_in", "=", True),
                    ]
                )
                if not employees:
                    continue

                employees_by_tz = {}
                for emp in employees:
                    tz = (
                        emp.user_id.tz
                        or (emp.company_id.partner_id.tz if emp.company_id and emp.company_id.partner_id else None)
                        or "UTC"
                    )
                    employees_by_tz.setdefault(tz, Employee.browse())
                    employees_by_tz[tz] |= emp

                for tz, employees_tz in employees_by_tz.items():
                    local_now = fields.Datetime.context_timestamp(
                        self.with_context(tz=tz), now_utc
                    )
                    if not manual:
                        if local_now.hour != 1:
                            continue
                        weekday = (
                            company.timesheet_sheet_weekly_autocreate_weekday
                            or company.timesheet_week_start
                            or "0"
                        )
                        if str(local_now.weekday()) != weekday:
                            continue

                    local_date = local_now.date()
                    date_start = Sheet._get_period_start(company, local_date)
                    date_end = Sheet._get_period_end(company, local_date)

                    existing = Sheet.with_context(company_ctx).search(
                        [
                            ("company_id", "=", company.id),
                            ("employee_id", "in", employees_tz.ids),
                            ("date_start", "<=", date_end),
                            ("date_end", ">=", date_start),
                        ]
                    )
                    existing_emp_ids = set(existing.mapped("employee_id").ids)
                    to_create = employees_tz.filtered(
                        lambda emp: emp.id not in existing_emp_ids
                    )
                    stats["skipped"] += len(existing_emp_ids)
                    if not to_create:
                        continue

                    vals_list = [
                        {
                            "employee_id": emp.id,
                            "company_id": company.id,
                            "date_start": date_start,
                            "date_end": date_end,
                        }
                        for emp in to_create
                    ]
                    Sheet.with_context(company_ctx).with_company(company).create(
                        vals_list
                    )
                    stats["created"] += len(vals_list)
            except Exception:
                stats["errors"] += 1
                _logger.exception(
                    "Failed weekly timesheet auto-create for company %s",
                    company.display_name,
                )
                continue

        return stats
