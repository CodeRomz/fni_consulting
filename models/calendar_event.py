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
    fni_user_is_organizer = fields.Boolean(
        compute="_compute_fni_user_is_organizer",
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

    @api.onchange("fni_visibility_mode")
    def _onchange_fni_visibility_mode(self):
        if self.fni_visibility_mode != "shared":
            self.fni_shared_user_ids = [fields.Command.clear()]

    def _fni_prepare_create_vals(self, vals):
        vals = dict(vals)
        if vals.get("fni_visibility_mode", "private") != "shared":
            vals["fni_shared_user_ids"] = [fields.Command.clear()]
        return vals

    def _fni_prepare_write_vals(self, vals):
        if vals.get("fni_visibility_mode") and vals["fni_visibility_mode"] != "shared":
            vals = dict(vals)
            vals["fni_shared_user_ids"] = [fields.Command.clear()]
        return vals

    @api.depends("user_id")
    @api.depends_context("uid")
    def _compute_fni_user_is_organizer(self):
        is_su = self.env.su
        current_user = self.env.user
        for event in self:
            if event.user_id:
                event.fni_user_is_organizer = is_su or (event.user_id == current_user)
            else:
                event.fni_user_is_organizer = is_su or (event.create_uid == current_user)

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

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._fni_prepare_create_vals(vals) for vals in vals_list]
        return super().create(vals_list)

    def write(self, vals):
        self._fni_check_owner_write_access()
        vals = self._fni_prepare_write_vals(vals)
        return super().write(vals)

    def unlink(self):
        self._fni_check_owner_write_access()
        return super().unlink()
