/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";
import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { AttendeeCalendarCommonPopover } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_popover";
import { CalendarListModel } from "@calendar/views/list_view/calendar_list_view";

function getPartnerFilterSection(data) {
    return data.filterSections.partner_ids;
}

function isAllFilterActive(section) {
    return Boolean(section?.filters.find((filter) => filter.type === "all")?.active);
}

function isCurrentUserFilterActive(section) {
    return Boolean(section?.filters.find((filter) => filter.type === "user")?.active);
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

patch(AttendeeCalendarModel.prototype, {
    async fetchRecords(data) {
        const records = await super.fetchRecords(data);
        const partnerSection = getPartnerFilterSection(data);
        if (!partnerSection || isAllFilterActive(partnerSection) || !isCurrentUserFilterActive(partnerSection)) {
            return records;
        }
        const extraDomain = [
            ...this.meta.domain,
            ...this.computeRangeDomain(data),
            ...stripPartnerFilterDomain(this.computeFiltersDomain(data)),
            ["fni_show_on_user_calendar", "=", true],
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
        if (!isCurrentUserFilterActive(partnerSection)) {
            return;
        }
        const currentPartnerId = user.partnerId;
        const existingRecordIds = new Set(
            Object.values(data.records)
                .filter((record) => record.attendeeId === currentPartnerId)
                .map((record) => record.id)
        );
        let nextRecordId = getNextVirtualRecordId(data.records);
        for (const record of Object.values(originalRecords)) {
            if (!record.rawRecord.fni_show_on_user_calendar || existingRecordIds.has(record.id)) {
                continue;
            }
            const sharedRecord = {
                ...record,
                attendeeId: currentPartnerId,
                colorIndex: currentPartnerId,
                attendeeStatus: "needsAction",
                isAlone: false,
                isCurrentPartner: false,
                calendarAttendeeId: false,
            };
            sharedRecord._recordId = nextRecordId;
            data.records[nextRecordId] = sharedRecord;
            nextRecordId -= 1;
        }
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
                if (filters.user) {
                    params.domain = [
                        "|",
                        ["partner_ids", "in", selectedPartnerIds],
                        ["fni_show_on_user_calendar", "=", true],
                    ];
                } else {
                    params.domain.push(["partner_ids", "in", selectedPartnerIds]);
                }
            }
        }
        return super.load(params);
    },
});
