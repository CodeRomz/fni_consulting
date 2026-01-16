/** @odoo-module **/

import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(CalendarCommonPopover.prototype, {
    setup() {
        super.setup(...arguments);
        this.actionService = useService("action");
    },

    get canAddTimesheet() {
        return this.props.model.resModel === "calendar.event";
    },

    get hasTimesheetEntry() {
        if (!this.canAddTimesheet) {
            return false;
        }
        const raw = this.props.record.rawRecord || {};
        return Boolean(raw.has_timesheet_entry);
    },

    onAddTimesheet() {
        if (!this.canAddTimesheet || this.hasTimesheetEntry) {
            return;
        }
        const record = this.props.record;
        const raw = record.rawRecord || {};
        const description = raw.description || record.title || raw.name || "";
        const context = {
            default_event_id: record.id,
            default_name: description,
            default_description: description,
            default_date_time: raw.start || record.start,
            default_date_time_end: raw.stop || record.stop,
            default_company_id: raw.company_id && raw.company_id[0],
        };

        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Add Event to Timesheet",
            res_model: "calendar.event.timesheet.wizard",
            views: [[false, "form"]],
            target: "new",
            context,
        });
    },
});
