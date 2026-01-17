# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CalendarEventTimesheetWizard(models.TransientModel):
    _name = "calendar.event.timesheet.wizard"
    _description = "Create Timesheet from Calendar Event"

    event_id = fields.Many2one("calendar.event", required=True, ondelete="cascade")
    name = fields.Char(string="Description", required=True)
    date_time = fields.Datetime(string="Start Time", required=True)
    date_time_end = fields.Datetime(string="End Time", required=True)
    unit_amount = fields.Float(
        string="Duration (Hours)",
        compute="_compute_unit_amount",
        readonly=True,
        store=False,
    )
    project_id = fields.Many2one(
        "project.project",
        string="Project",
        required=True,
        domain="[('allow_timesheets', '=', True)]",
    )
    task_id = fields.Many2one(
        "project.task",
        string="Task",
        domain="[('project_id', '=', project_id), ('allow_timesheets', '=', True)]",
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        default=lambda self: self.env.user.employee_id,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )

    @api.depends("date_time", "date_time_end")
    def _compute_unit_amount(self):
        for wizard in self:
            if wizard.date_time and wizard.date_time_end:
                delta = wizard.date_time_end - wizard.date_time
                wizard.unit_amount = round(delta.total_seconds() / 3600, 2)
            else:
                wizard.unit_amount = 0.0

    @api.onchange("project_id")
    def _onchange_project_id(self):
        for wizard in self:
            if wizard.task_id and wizard.task_id.project_id != wizard.project_id:
                wizard.task_id = False

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if res.get("date_time") and not res.get("date_time_end"):
            start = fields.Datetime.to_datetime(res["date_time"])
            res["date_time_end"] = start + timedelta(hours=1)
        return res

    def action_create_timesheet(self):
        self.ensure_one()
        if not self.date_time or not self.date_time_end:
            raise UserError(_("Start and end time are required."))
        if self.date_time_end <= self.date_time:
            raise UserError(_("End time must be after start time."))
        if not self.employee_id:
            raise UserError(_("No employee found for the current user."))

        existing_line = self.env["account.analytic.line"].search(
            [
                ("event_id", "=", self.event_id.id),
                ("employee_id", "=", self.employee_id.id),
            ],
            limit=1,
        )
        if existing_line:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Timesheet"),
                    "message": _("This event is already in your timesheet."),
                    "type": "warning",
                    "sticky": False,
                    "next": {"type": "ir.actions.act_window_close"},
                },
            }

        vals = {
            "name": self.name,
            "project_id": self.project_id.id,
            "task_id": self.task_id.id if self.task_id else False,
            "employee_id": self.employee_id.id,
            "company_id": self.company_id.id,
            "event_id": self.event_id.id,
            "date_time": self.date_time,
            "date_time_end": self.date_time_end,
            "unit_amount": self.unit_amount,
            "date": fields.Date.context_today(self, self.date_time),
        }
        self.env["account.analytic.line"].create(vals)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Timesheet"),
                "message": _("Added in timesheet."),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
