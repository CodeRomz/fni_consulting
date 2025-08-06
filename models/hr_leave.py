"""
Extend time off and calendar leave models to force zero worked hours on
generated timesheet lines.

Odoo's `hr_holidays_timesheet` module creates analytic lines when a
leave request is validated or a public holiday is generated.  Those
lines normally carry the number of hours computed from the employee's
working schedule.  To comply with the business requirement that time
off should never contribute to worked hours, this module overrides the
values preparation methods and explicitly sets ``unit_amount`` to
``0.0`` on every automatically generated timesheet line.  A
descriptive name is also provided to help with audits and reports.

The overrides below rely on standard model inheritance.  They call
``super()`` to obtain the default dictionary of values and then
adjust it as needed.  Should upstream signatures change slightly
between Odoo releases, the use of ``*args`` accommodates extra
parameters gracefully without breaking the call chain.
"""

import logging
from odoo import models, _

_logger = logging.getLogger(__name__)


class HrLeave(models.Model):
    """Override leave timesheet preparation to force zero hours."""

    _inherit = 'hr.leave'

    def _timesheet_prepare_line_values(self, index, *args, **kwargs):
        """
        Prepare the dictionary of values used to create a timesheet line.

        This override calls the parent implementation to build the base
        dictionary and then enforces a ``unit_amount`` of ``0.0``.  It also
        replaces the default name with a more descriptive label that
        includes the leave type.  Any exceptions raised while adjusting
        the dictionary are logged but do not prevent the creation of
        analytic lines.

        Parameters
        ----------
        index: int
            The zero‑based index of the day in the leave period.  The
            original implementation uses this to number the timesheet lines.
        *args: tuple
            Additional positional parameters passed by the upstream
            module.  Depending on the Odoo version, these may include
            ``work_hours_data``, ``day_date``, ``work_hours_count``,
            ``project``, ``task``, etc.
        **kwargs: dict
            Additional keyword parameters.  Currently unused but accepted
            for forward compatibility.

        Returns
        -------
        dict
            A dictionary of values suitable for creating an
            ``account.analytic.line`` record.
        """
        # Retrieve the default values from the parent class.  Using
        # ``super()`` ensures that the core business logic (e.g. project
        # assignment, holiday_id linking) remains intact.
        vals = super()._timesheet_prepare_line_values(index, *args, **kwargs)

        # Adjust the analytic line values in a safe manner.  Catch any
        # unexpected errors so that timesheet creation can proceed even
        # if our override fails.
        try:
            # Force the worked hours to zero regardless of the computed
            # schedule.  This prevents leave days from being counted as
            # productive time.
            vals['unit_amount'] = 0.0

            # Build a descriptive label.  Prefer the leave type name if
            # available; fall back to the internal description.  The en
            # dash (–) is used to separate the generic prefix from the
            # specific leave type.  Translation via ``_()`` allows the
            # string to be localised.
            leave_type_name = ''
            # ``holiday_status_id`` may not be set on some edge cases
            # (e.g. during copy), so guard against ``None``.
            if getattr(self, 'holiday_status_id', False):
                leave_type_name = self.holiday_status_id.with_context(
                    lang=self.env.user.lang or 'en_US'
                ).name or ''
            # Use a default prefix; translators can adapt the phrasing.
            vals['name'] = _("Time Off – %s") % leave_type_name
        except Exception as exc:
            # Log the exception with context for debugging purposes.  Do
            # not re‑raise it to avoid blocking the leave validation.
            _logger.exception(
                "Failed to adjust timesheet values for leave %s: %s",
                self.id,
                exc
            )

        return vals


class ResourceCalendarLeaves(models.Model):
    """Override public holiday timesheet preparation to force zero hours."""

    _inherit = 'resource.calendar.leaves'

    def _timesheet_prepare_line_values(self, index, employee,
                                       work_hours_data, day_date,
                                       work_hours_count):
        """
        Prepare the dictionary of values used to create a timesheet line for
        public holidays (global leaves).

        Similar to :meth:`HrLeave._timesheet_prepare_line_values`, this
        override enforces a ``unit_amount`` of ``0.0`` on the generated
        analytic lines.  It also derives a descriptive name from the
        calendar leave.  Should the parent implementation change its
        signature in the future, this method may need to be adapted
        accordingly.

        Parameters
        ----------
        index: int
            The zero‑based index of the day in the global leave period.
        employee: recordset of ``hr.employee``
            The employee for whom the timesheet line is prepared.
        work_hours_data: list
            Aggregated working hours for the global leave.
        day_date: date
            The specific date of the timesheet line.
        work_hours_count: float
            The number of hours normally worked on that date by the employee.

        # Returns
        -------
        dict
            A dictionary of values suitable for creating an
            ``account.analytic.line`` record.
        """
        vals = super()._timesheet_prepare_line_values(
            index, employee, work_hours_data, day_date, work_hours_count
        )
        try:
            vals['unit_amount'] = 0.0
            # ``name`` of a calendar leave is usually the description of the
            # public holiday (e.g. "New Year").  If absent, fall back to a
            # generic label.  ``with_context`` ensures the correct
            # translation for the current user.
            leave_name = self.with_context(
                lang=self.env.user.lang or 'en_US'
            ).name or _('Public Holiday')
            vals['name'] = _("Time Off – %s") % leave_name
        except Exception as exc:
            _logger.exception(
                "Failed to adjust timesheet values for global leave %s: %s",
                self.id,
                exc
            )
        return vals
