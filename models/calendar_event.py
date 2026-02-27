from odoo import api, fields, models
from odoo.exceptions import AccessError


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    fni_visibility_mode = fields.Selection(
        [
            ("private", "Private"),
            ("shared", "Shared"),
            ("public_internal", "Public (Internal)"),
        ],
        string="Internal Visibility",
        default="private",
        required=True,
        help=(
            "Private: only organizer/attendees. "
            "Shared: organizer/attendees and explicitly shared users. "
            "Public (Internal): all internal users can read."
        ),
    )
    fni_shared_user_ids = fields.Many2many(
        "res.users",
        "calendar_event_fni_shared_user_rel",
        "event_id",
        "user_id",
        string="Shared With",
        domain=[("share", "=", False)],
        help="Additional internal users who can read this event.",
    )
    has_timesheet_entry = fields.Boolean(
        string="Has Timesheet Entry",
        compute="_compute_has_timesheet_entry",
    )

    def _fni_bypass_visibility_guards(self):
        return self.env.su or bool(self.env.context.get("dont_notify"))

    def _fni_forbidden_event_edits(self):
        current_user = self.env.user
        return self.filtered(
            lambda event: (
                (event.user_id and event.user_id != current_user)
                or (not event.user_id and event.create_uid != current_user)
            )
        )

    def _fni_check_owner_write_access(self):
        if self._fni_bypass_visibility_guards():
            return
        forbidden = self._fni_forbidden_event_edits()
        if forbidden:
            raise AccessError("Only the event organizer can modify this event.")

    @api.depends("partner_ids", "user_id")
    @api.depends_context("uid")
    def _compute_user_can_edit(self):
        is_su = self.env.su
        current_user = self.env.user
        for event in self:
            if event.user_id:
                event.user_can_edit = is_su or (event.user_id == current_user)
            else:
                event.user_can_edit = is_su or (event.create_uid == current_user)

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

    def write(self, vals):
        self._fni_check_owner_write_access()
        return super().write(vals)

    def unlink(self):
        self._fni_check_owner_write_access()
        return super().unlink()
