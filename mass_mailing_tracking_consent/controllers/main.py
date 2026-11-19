# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import base64

from werkzeug.exceptions import BadRequest, NotFound, Unauthorized

from odoo import http
from odoo.http import Response, request
from odoo.tools import consteq, email_normalize

from odoo.addons.mass_mailing.controllers.main import MassMailController

BLANK_GIF = base64.b64decode(
    b"R0lGODlhAQABAIAAANvf7wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
)


class MassMailingTrackingConsentController(MassMailController):
    @http.route(
        "/mail/track/<int:mail_id>/<string:token>/blank.gif",
        type="http",
        auth="public",
    )
    def track_mail_open(self, mail_id, token, **post):
        expected_token = (
            request.env["mail.mail"].sudo()._generate_mail_recipient_token(mail_id)
        )
        if not consteq(token, expected_token):
            raise Unauthorized()
        traces = (
            request.env["mailing.trace"]
            .sudo()
            .search([("mail_mail_id_int", "=", mail_id)])
        )
        if traces and all(trace._is_tracking_allowed() for trace in traces):
            return super().track_mail_open(mail_id, token, **post)
        # The mail itself may already be deleted (auto_delete keeps only the
        # trace): a pixel delivered before the consent was withdrawn must not
        # record the opening. Return the image anyway to avoid a broken icon.
        response = Response()
        response.mimetype = "image/gif"
        response.data = BLANK_GIF
        return response

    @http.route(
        "/r/<string:code>/m/<int:mailing_trace_id>",
        type="http",
        auth="public",
    )
    def full_url_redirect(self, code, mailing_trace_id, **post):
        trace_sudo = request.env["mailing.trace"].sudo().browse(mailing_trace_id)
        if not trace_sudo.exists() or not trace_sudo._is_tracking_allowed():
            redirect_url = request.env["link.tracker"].sudo().get_url_from_code(code)
            if not redirect_url:
                raise NotFound()
            return request.redirect(redirect_url, code=301, local=False)
        return super().full_url_redirect(code, mailing_trace_id, **post)

    def _tracking_consent_get_trace(self, trace_id, token):
        trace = request.env["mailing.trace"].sudo().browse(trace_id).exists()
        if not trace or not token:
            raise NotFound()
        expected = request.env["mailing.tracking.consent"].sudo()._get_token(trace.id)
        if not consteq(expected, token):
            raise NotFound()
        email = email_normalize(trace.email or "")
        if not email:
            raise NotFound()
        return trace, email

    def _tracking_consent_render(self, trace, email, token, saved=False):
        consent = request.env["mailing.tracking.consent"].sudo()._get_consent(email)
        unsubscribe_url = False
        if trace.res_id and trace.mass_mailing_id:
            recipient = trace.mass_mailing_id
            if trace.model and trace.model in request.env:
                recipient = request.env[trace.model].sudo().browse(trace.res_id)
            unsubscribe_url = trace.mass_mailing_id.with_context(
                mailing_recipient_record=recipient
            )._get_unsubscribe_url(email, trace.res_id)
        return request.render(
            "mass_mailing_tracking_consent.page_tracking_consent",
            {
                "main_object": trace.mass_mailing_id,
                "mailing": trace.mass_mailing_id,
                "trace": trace,
                "email": email,
                "token": token,
                "consent_state": consent.state if consent else False,
                "saved": saved,
                "action_url": f"/mailing/tracking_consent/{trace.id}/{token}",
                "unsubscribe_url": unsubscribe_url,
            },
        )

    @http.route(
        "/mailing/tracking_consent/<int:trace_id>/<string:token>",
        type="http",
        auth="public",
        methods=["GET"],
        website=True,
        sitemap=False,
    )
    def tracking_consent_page(self, trace_id, token, **post):
        trace, email = self._tracking_consent_get_trace(trace_id, token)
        return self._tracking_consent_render(trace, email, token)

    @http.route(
        "/mailing/tracking_consent/<int:trace_id>/<string:token>",
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        sitemap=False,
    )
    def tracking_consent_save(self, trace_id, token, consent_state=None, **post):
        trace, email = self._tracking_consent_get_trace(trace_id, token)
        if consent_state not in ("granted", "refused"):
            raise BadRequest()
        request.env["mailing.tracking.consent"].sudo()._set_consent(
            email,
            consent_state,
            source="link",
            mailing=trace.mass_mailing_id,
        )
        return self._tracking_consent_render(trace, email, token, saved=True)
