from odoo import models, fields, api, tools, _
from odoo.exceptions import (
    UserError, ValidationError, RedirectWarning,
    AccessDenied, AccessError, CacheMiss, MissingError,
)
import logging

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import content_disposition
from odoo.addons.survey.controllers.main import Survey as SurveyController
import werkzeug.exceptions

_logger = logging.getLogger(__name__)


class Survey(SurveyController):
    def _get_certification_report_ref(self, user_input):
        survey = user_input.survey_id
        layout = survey.certification_report_layout or 'firenor-one_seagreen'

        report_ref = 'survey.certification_report'
        if layout == 'fni-ack_o-ack':
            # from custom_survey_reports.xml
            report_ref = 'fni_consulting.hr_emp_ack_report'
        return report_ref

    def _generate_report(self, user_input, download=True):
        """Generate certification PDF according to survey layout."""
        report_ref = self._get_certification_report_ref(user_input)
        pdf_content = b""

        try:
            report_model = request.env["ir.actions.report"].sudo()
            # Inner try: handle MissingError and fallback
            try:
                pdf_content, _ = report_model._render_qweb_pdf(
                    report_ref,
                    [user_input.id],
                    data={'report_type': 'pdf'},
                )
            except MissingError:
                _logger.exception(
                    "Certification report %s not found, falling back to "
                    "survey.certification_report",
                    report_ref,
                )
                pdf_content, _ = request.env["ir.actions.report"].sudo()._render_qweb_pdf(
                    'survey.certification_report',
                    [user_input.id],
                    data={'report_type': 'pdf'},
                )

        except Exception as exc:
            _logger.exception(
                "Error generating certification report %s for user_input %s: %s",
                report_ref,
                user_input.id,
                exc,
            )
            raise UserError(
                _(
                    "Unable to generate the certification document. "
                    "Please contact your system administrator."
                )
            )

        else:
            disposition = content_disposition('Certification.pdf')
            if not download:
                parts = disposition.split(';')
                parts[0] = 'inline'
                disposition = ';'.join(parts)

            headers = [
                ('Content-Type', 'application/pdf'),
                ('Content-Length', len(pdf_content)),
                ('Content-Disposition', disposition),
            ]
            return request.make_response(pdf_content, headers=headers)

        finally:
            _logger.debug(
                "Certification report generated using %s for user_input %s "
                "(survey_id=%s, layout=%s)",
                report_ref,
                user_input.id,
                user_input.survey_id.id,
                user_input.survey_id.certification_report_layout,
            )

    @http.route()
    def survey_get_certification_preview(self, survey, **kwargs):
        if not request.env.user.has_group('survey.group_survey_user'):
            raise werkzeug.exceptions.Forbidden()

        fake_user_input = None
        try:
            fake_user_input = survey._create_answer(
                user=request.env.user,
                test_entry=True,
            )
            response = self._generate_report(fake_user_input, download=False)
        finally:
            if fake_user_input:
                fake_user_input.sudo().unlink()

        return response

    @http.route()
    def survey_get_certification(self, survey_id, **kwargs):
        survey = request.env['survey.survey'].sudo().search(
            [
                ('id', '=', survey_id),
                ('certification', '=', True),
            ],
            limit=1,
        )

        if not survey:
            return request.redirect("/")

        succeeded_attempt = request.env['survey.user_input'].sudo().search(
            [
                ('partner_id', '=', request.env.user.partner_id.id),
                ('survey_id', '=', survey_id),
                ('scoring_success', '=', True),
            ],
            limit=1,
        )

        if not succeeded_attempt:
            raise UserError(_("The user has not succeeded the certification"))

        return self._generate_report(succeeded_attempt, download=True)
