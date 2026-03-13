from odoo import api, fields, models, _
from odoo.exceptions import AccessError
from odoo.osv import expression


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    fni_public_holiday_id = fields.Many2one(
        "resource.calendar.leaves",
        string="Public Holiday Source",
        copy=False,
        index=True,
        readonly=True,
    )
    fni_public_holiday_kind = fields.Selection(
        [
            ("display", "Display"),
            ("shadow", "Shadow"),
        ],
        string="Public Holiday Event Kind",
        copy=False,
        index=True,
        readonly=True,
    )
    fni_public_holiday_user_id = fields.Many2one(
        "res.users",
        string="Public Holiday Target User",
        copy=False,
        index=True,
        readonly=True,
    )
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
    fni_show_on_user_calendar = fields.Boolean(
        compute="_compute_fni_show_on_user_calendar",
        search="_search_fni_show_on_user_calendar",
    )
    has_timesheet_entry = fields.Boolean(
        string="Has Timesheet Entry",
        compute="_compute_has_timesheet_entry",
    )

    def _fni_bypass_public_holiday_guards(self):
        return self.env.su or bool(self.env.context.get("fni_public_holiday_sync"))

    def _fni_bypass_visibility_guards(self):
        return (
            self.env.su
            or bool(self.env.context.get("dont_notify"))
            or bool(self.env.context.get("fni_public_holiday_sync"))
        )

    def _fni_check_public_holiday_write_access(self):
        if self._fni_bypass_public_holiday_guards():
            return
        if self.filtered("fni_public_holiday_id"):
            raise AccessError(
                _(
                    "Public holiday calendar events are managed from Time Off > Configuration > Public Holidays."
                )
            )

    def _fni_check_public_holiday_assignment_access(self, vals_list=None, vals=None):
        if self._fni_bypass_public_holiday_guards():
            return
        protected_keys = {
            "fni_public_holiday_id",
            "fni_public_holiday_kind",
            "fni_public_holiday_user_id",
        }
        if vals_list is not None and any(protected_keys.intersection(entry) for entry in vals_list):
            raise AccessError(
                _(
                    "Public holiday calendar events are managed from Time Off > Configuration > Public Holidays."
                )
            )
        if vals is not None and protected_keys.intersection(vals):
            raise AccessError(
                _(
                    "Public holiday calendar events are managed from Time Off > Configuration > Public Holidays."
                )
            )

    def _fni_is_organizer(self, event, current_user):
        return bool(
            self.env.su
            or (event.user_id and event.user_id == current_user)
            or (not event.user_id and event.create_uid == current_user)
        )

    def _fni_can_view_private_event_details(self, event, current_user):
        current_partner = current_user.partner_id
        return bool(
            self.env.su
            or self._fni_is_organizer(event, current_user)
            or current_partner in event.partner_ids
            or (
                event.fni_visibility_mode == "shared"
                and current_user in event.fni_shared_user_ids
            )
            or (
                event.fni_visibility_mode == "public_internal"
                and current_user._is_internal()
            )
        )

    def _fni_forbidden_event_edits(self):
        current_user = self.env.user
        return self.filtered(lambda event: not self._fni_is_organizer(event, current_user))

    def _check_private_event_conditions(self):
        self.ensure_one()
        if self._fni_can_view_private_event_details(self, self.env.user):
            return False
        return super()._check_private_event_conditions()

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

    def _fni_prepare_public_holiday_mirror_vals(self, vals):
        return dict(vals)

    @api.depends("user_id")
    @api.depends_context("uid")
    def _compute_fni_user_is_organizer(self):
        current_user = self.env.user
        for event in self:
            event.fni_user_is_organizer = self._fni_is_organizer(event, current_user)

    @api.depends("partner_ids", "user_id", "fni_visibility_mode", "fni_shared_user_ids")
    @api.depends_context("uid")
    def _compute_fni_show_on_user_calendar(self):
        current_user = self.env.user
        current_partner = current_user.partner_id
        is_internal_user = current_user._is_internal()
        for event in self:
            is_organizer = self._fni_is_organizer(event, current_user)
            is_attendee = current_partner in event.partner_ids
            is_shared_viewer = current_user in event.fni_shared_user_ids
            is_internal_public_viewer = (
                event.fni_visibility_mode == "public_internal" and is_internal_user
            )
            event.fni_show_on_user_calendar = (
                not is_organizer
                and not is_attendee
                and (is_shared_viewer or is_internal_public_viewer)
            )

    def _search_fni_show_on_user_calendar(self, operator, value):
        if operator not in ("=", "!=") or value not in (True, False):
            return []
        if operator == "!=":
            value = not value
        user = self.env.user
        candidate_domain = [
            "&",
            ("fni_visibility_mode", "=", "shared"),
            ("fni_shared_user_ids", "in", user.id),
        ]
        if user._is_internal():
            candidate_domain = [
                "|",
                *candidate_domain,
                ("fni_visibility_mode", "=", "public_internal"),
            ]
        candidate_events = self.search(candidate_domain)
        current_partner = user.partner_id
        matched_events = candidate_events.filtered(
            lambda event: not self._fni_is_organizer(event, user) and current_partner not in event.partner_ids
        )
        return [("id", "in" if value else "not in", matched_events.ids)]

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

    @api.depends("partner_ids", "user_id", "fni_public_holiday_id")
    @api.depends_context("uid")
    def _compute_user_can_edit(self):
        super()._compute_user_can_edit()
        for event in self.filtered("fni_public_holiday_id"):
            event.user_can_edit = False

    def _get_microsoft_sync_domain(self):
        return expression.AND(
            [
                super()._get_microsoft_sync_domain(),
                [("fni_public_holiday_kind", "!=", "display")],
            ]
        )

    @api.model
    def _restart_microsoft_sync(self):
        domain = self._get_microsoft_sync_domain()
        self.sudo().with_context(dont_notify=True).search(domain).write({
            "need_sync_m": True,
        })

    def _microsoft_values(self, fields_to_sync, initial_values=None):
        self.ensure_one()
        if self.fni_public_holiday_kind == "display":
            return {}
        return super()._microsoft_values(fields_to_sync, initial_values=initial_values or {})

    def _write_from_microsoft(self, microsoft_event, vals):
        public_holiday_events = self.filtered(
            lambda event: event.fni_public_holiday_id and event.fni_public_holiday_kind == "shadow"
        )
        if public_holiday_events:
            reset_vals = {}
            if "need_sync_m" in public_holiday_events._fields:
                reset_vals["need_sync_m"] = True
            if reset_vals:
                public_holiday_events.with_context(
                    dont_notify=True,
                    no_calendar_sync=True,
                    fni_public_holiday_sync=True,
                ).write(reset_vals)
        remaining_events = self - public_holiday_events
        if remaining_events:
            return super(CalendarEvent, remaining_events)._write_from_microsoft(microsoft_event, vals)
        return True

    def _cancel_microsoft(self):
        public_holiday_events = self.filtered(
            lambda event: event.fni_public_holiday_id and event.fni_public_holiday_kind == "shadow"
        )
        if public_holiday_events:
            reset_vals = {}
            if "need_sync_m" in public_holiday_events._fields:
                reset_vals["need_sync_m"] = True
            if "microsoft_id" in public_holiday_events._fields:
                reset_vals["microsoft_id"] = False
            if "ms_universal_event_id" in public_holiday_events._fields:
                reset_vals["ms_universal_event_id"] = False
            if reset_vals:
                public_holiday_events.with_context(
                    dont_notify=True,
                    no_calendar_sync=True,
                    fni_public_holiday_sync=True,
                ).write(reset_vals)
        remaining_events = self - public_holiday_events
        if remaining_events:
            return super(CalendarEvent, remaining_events)._cancel_microsoft()
        return True

    @api.model_create_multi
    def create(self, vals_list):
        self._fni_check_public_holiday_assignment_access(vals_list=vals_list)
        vals_list = [self._fni_prepare_create_vals(vals) for vals in vals_list]
        vals_list = [
            self._fni_prepare_public_holiday_mirror_vals(vals)
            if vals.get("fni_public_holiday_id")
            else vals
            for vals in vals_list
        ]
        return super().create(vals_list)

    def write(self, vals):
        self._fni_check_public_holiday_assignment_access(vals=vals)
        self._fni_check_public_holiday_write_access()
        self._fni_check_owner_write_access()
        vals = self._fni_prepare_write_vals(vals)
        if self.filtered("fni_public_holiday_id"):
            vals = self._fni_prepare_public_holiday_mirror_vals(vals)
        return super().write(vals)

    def unlink(self):
        self._fni_check_public_holiday_write_access()
        self._fni_check_owner_write_access()
        return super().unlink()
