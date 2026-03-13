/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { CalendarListModel } from "@calendar/views/list_view/calendar_list_view";
import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { AttendeeCalendarCommonPopover } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_popover";
import { AttendeeCalendarCommonRenderer } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_renderer";

function getPartnerFilterSection(data) {
    return data.filterSections.partner_ids;
}

function isAllFilterActive(section) {
    return Boolean(section?.filters.find((filter) => filter.type === "all")?.active);
}

function getActivePartnerIds(section) {
    return section?.filters
        ?.filter((filter) => filter.type !== "all" && filter.value && filter.active)
        .map((filter) => filter.value) || [];
}

function getNextVirtualRecordId(records) {
    const recordIds = Object.keys(records)
        .map((id) => Number(id))
        .filter((id) => Number.isFinite(id));
    return recordIds.length ? Math.min(...recordIds) - 1 : -1;
}

function stripPartnerFilterDomain(domain) {
    return domain.filter(
        (clause) => !(Array.isArray(clause) && clause[0] === "partner_ids")
    );
}

function getSearchReadFields(model) {
    return [...new Set([...model.meta.fieldNames, ...Object.keys(model.meta.activeFields)])];
}

function isSharedCalendarRecord(record) {
    return Boolean(record?.rawRecord?.fni_show_on_user_calendar);
}

function isCurrentUserAttendeeOrOrganizer(record) {
    const rawRecord = record?.rawRecord;
    const partnerIds = rawRecord?.partner_ids || [];
    const organizerPartnerId = rawRecord?.partner_id?.[0];
    return partnerIds.includes(user.partnerId) || organizerPartnerId === user.partnerId;
}

function isViewerOnlyCalendarRecord(record) {
    return isSharedCalendarRecord(record) && !isCurrentUserAttendeeOrOrganizer(record);
}

function getSelectedSharedPartnerIds(record, activePartnerIds) {
    const rawRecord = record?.rawRecord;
    const sharedPartnerIds = rawRecord?.fni_shared_partner_ids || [];
    const attendeePartnerIds = rawRecord?.partner_ids || [];
    const organizerPartnerId = rawRecord?.partner_id?.[0];
    return activePartnerIds.filter((partnerId) => {
        if (partnerId === organizerPartnerId || attendeePartnerIds.includes(partnerId)) {
            return false;
        }
        if (rawRecord?.fni_visibility_mode === "public_internal") {
            return true;
        }
        return sharedPartnerIds.includes(partnerId);
    });
}

function getSharedVisibilityDomain(selectedPartnerIds) {
    if (!selectedPartnerIds.length) {
        return [];
    }
    return [
        "|",
        ["fni_visibility_mode", "=", "public_internal"],
        "&",
        ["fni_visibility_mode", "=", "shared"],
        ["fni_shared_user_ids.partner_id", "in", selectedPartnerIds],
    ];
}

patch(AttendeeCalendarModel.prototype, {
    async fetchRecords(data) {
        const records = await super.fetchRecords(data);
        const partnerSection = getPartnerFilterSection(data);
        if (!partnerSection || isAllFilterActive(partnerSection)) {
            return records;
        }
        const activePartnerIds = getActivePartnerIds(partnerSection);
        if (!activePartnerIds.length) {
            return records;
        }
        const extraDomain = [
            ...this.meta.domain,
            ...this.computeRangeDomain(data),
            ...stripPartnerFilterDomain(this.computeFiltersDomain(data)),
            ...getSharedVisibilityDomain(activePartnerIds),
        ];
        const extraRecords = await this.orm.searchRead(
            this.meta.resModel,
            extraDomain,
            getSearchReadFields(this)
        );
        const seenIds = new Set(records.map((record) => record.id));
        for (const record of extraRecords) {
            if (!seenIds.has(record.id)) {
                records.push(record);
            }
        }
        return records;
    },

    async updateAttendeeData(data) {
        const originalRecords = { ...data.records };
        await super.updateAttendeeData(data);
        const partnerSection = getPartnerFilterSection(data);
        if (!partnerSection) {
            return;
        }
        if (isAllFilterActive(partnerSection)) {
            for (const record of Object.values(data.records)) {
                if (isSharedCalendarRecord(record) && !record.attendeeStatus) {
                    record.attendeeStatus = "needsAction";
                    record.isCurrentPartner = false;
                    record.calendarAttendeeId = record.calendarAttendeeId || false;
                }
            }
            return;
        }
        const activePartnerIds = getActivePartnerIds(partnerSection);
        if (!activePartnerIds.length) {
            return;
        }
        const existingRecordKeys = new Set(
            Object.values(data.records)
                .filter((record) => activePartnerIds.includes(record.attendeeId))
                .map((record) => `${record.id}:${record.attendeeId}`)
        );
        let nextRecordId = getNextVirtualRecordId(data.records);
        for (const record of Object.values(originalRecords)) {
            for (const partnerId of getSelectedSharedPartnerIds(record, activePartnerIds)) {
                const recordKey = `${record.id}:${partnerId}`;
                if (existingRecordKeys.has(recordKey)) {
                    continue;
                }
                const sharedRecord = {
                    ...record,
                    attendeeId: partnerId,
                    colorIndex: partnerId,
                    attendeeStatus: "needsAction",
                    isAlone: false,
                    isCurrentPartner: partnerId === user.partnerId,
                    calendarAttendeeId: false,
                };
                sharedRecord._recordId = nextRecordId;
                data.records[nextRecordId] = sharedRecord;
                existingRecordKeys.add(recordKey);
                nextRecordId -= 1;
            }
        }
    },
});

patch(AttendeeCalendarCommonRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
    },

    _openViewerOnlyRecord(record) {
        this.dialog.add(FormViewDialog, {
            resModel: this.props.model.resModel,
            resId: record.id,
            viewId: this.props.model.formViewId || false,
            title: record.title,
            mode: "readonly",
            preventCreate: true,
            preventEdit: true,
        });
    },

    onClick(info) {
        const record = this.props.model.records[info.event.id];
        if (isViewerOnlyCalendarRecord(record)) {
            this._openViewerOnlyRecord(record);
            return;
        }
        return super.onClick(info);
    },

    onDblClick(info) {
        const record = this.props.model.records[info.event.id];
        if (isViewerOnlyCalendarRecord(record)) {
            this._openViewerOnlyRecord(record);
            return;
        }
        return super.onDblClick(info);
    },
});

patch(AttendeeCalendarCommonPopover.prototype, {
    get isEventDetailsVisible() {
        if (isSharedCalendarRecord(this.props.record)) {
            return true;
        }
        return super.isEventDetailsVisible;
    },

    get isEventViewable() {
        if (isSharedCalendarRecord(this.props.record)) {
            return true;
        }
        return super.isEventViewable;
    },
});

patch(CalendarListModel.prototype, {
    async load(params = {}) {
        const filters = params?.context?.calendar_filters;
        const emptyDomain = Array.isArray(params?.domain) && params.domain.length === 0;
        if (filters && emptyDomain) {
            const selectedPartnerIds = await this.orm.call(
                "res.users",
                "get_selected_calendars_partner_ids",
                [[user.userId], filters.user]
            );
            if (!filters.all) {
                if (selectedPartnerIds.length) {
                    params.domain = [
                        "|",
                        ["partner_ids", "in", selectedPartnerIds],
                        ...getSharedVisibilityDomain(selectedPartnerIds),
                    ];
                }
            }
        }
        return super.load(params);
    },
});
