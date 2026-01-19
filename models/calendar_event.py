from odoo import api, fields, models
from odoo.exceptions import AccessError


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    has_timesheet_entry = fields.Boolean(
        string="Has Timesheet Entry",
        compute="_compute_has_timesheet_entry",
    )

    @api.depends_context("uid")
    def _compute_has_timesheet_entry(self):
        employee = self.env.user.employee_id
        if not self.ids or not employee:
            for event in self:
                event.has_timesheet_entry = False
            return
        lines = self.env["account.analytic.line"]
        if not lines.check_access_rights("read", raise_exception=False):
            for event in self:
                event.has_timesheet_entry = False
            return
        try:
            grouped = lines.read_group(
                [("event_id", "in", self.ids), ("employee_id", "=", employee.id)],
                ["event_id"],
                ["event_id"],
            )
        except AccessError:
            for event in self:
                event.has_timesheet_entry = False
            return
        event_ids = {data["event_id"][0] for data in grouped if data.get("event_id")}
        for event in self:
            event.has_timesheet_entry = event.id in event_ids
