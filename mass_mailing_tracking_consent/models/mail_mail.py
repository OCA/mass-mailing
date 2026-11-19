# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from markupsafe import Markup, escape

from odoo import models, tools

from ..tools import tracking


class MailMail(models.Model):
    _inherit = "mail.mail"

    def _get_mailing_tracking_emails(self):
        self.ensure_one()
        emails = tools.email_normalize_all(self.email_to)
        if not emails and self.recipient_ids:
            emails = [
                email
                for email in self.recipient_ids.mapped("email_normalized")
                if email
            ]
        return emails

    def _mailing_tracking_allowed(self, email_to=None):
        """Return whether tracking is allowed for every recipient."""
        self.ensure_one()
        if email_to is None:
            emails = self._get_mailing_tracking_emails()
        else:
            emails = tools.email_normalize_all(email_to)
        if not emails:
            return False
        consent_model = self.env["mailing.tracking.consent"]
        return all(consent_model._is_tracking_allowed(email) for email in emails)

    def _tracking_consent_is_tracked(self):
        self.ensure_one()
        policy = self.mailing_id.tracking_policy or "consent"
        if policy == "always":
            return True
        if policy == "none":
            return False
        return self._mailing_tracking_allowed()

    def _tracking_consent_hosts(self):
        self.ensure_one()
        recipient = (
            self.env[self.model].browse(self.res_id)
            if self.model and self.res_id
            else self
        )
        base_urls = {
            self.get_base_url(),
            self.mailing_id.get_base_url(),
            recipient.get_base_url(),
            self.env["ir.config_parameter"].sudo().get_param("web.base.url"),
        }
        return tracking.host_variants(base_urls)

    def _tracking_consent_remove(self, email_list):
        """Remove open pixels and per-recipient click tracking."""
        self.ensure_one()
        hosts = self._tracking_consent_hosts()
        codes = set()
        for values in email_list:
            codes |= tracking.find_short_codes(values.get("body") or "", hosts)
            codes |= tracking.find_short_codes(
                values.get("body_alternative") or "", hosts
            )
        code_to_url = {}
        if codes:
            tracker_codes = (
                self.env["link.tracker.code"]
                .sudo()
                .search([("code", "in", list(codes))])
            )
            code_to_url = {
                tracker_code.code: tracker_code.link_id.url
                for tracker_code in tracker_codes
                if tracker_code.link_id.url
            }
        for values in email_list:
            body = values.get("body")
            body_html, body_text = tracking.remove_tracking(
                str(body) if body else body,
                values.get("body_alternative"),
                hosts,
                code_to_url,
            )
            if body:
                values["body"] = (
                    Markup(body_html) if isinstance(body, Markup) else body_html
                )
            if values.get("body_alternative"):
                values["body_alternative"] = body_text
        return email_list

    def _tracking_consent_lang(self):
        self.ensure_one()
        partner = self.recipient_ids[:1]
        return partner.lang or self.mailing_id.user_id.lang or self.env.lang or "en_US"

    def _tracking_consent_add_footer(self, email_list, is_tracked):
        self.ensure_one()
        traces_by_email = {}
        for trace in self.mailing_trace_ids:
            email = tools.email_normalize(trace.email, strict=False)
            if email:
                traces_by_email.setdefault(email, trace)
        if not traces_by_email:
            return email_list
        mail = self.with_context(lang=self._tracking_consent_lang())
        translate = mail.env._
        recipient = (
            self.env[self.model].browse(self.res_id)
            if self.model and self.res_id
            else self.mailing_id
        )
        mailing = self.mailing_id.with_context(mailing_recipient_record=recipient)
        if is_tracked:
            text = translate("This email measures opens and link clicks.")
            label = translate("Withdraw consent")
        else:
            text = translate("Opens and clicks of this email are not tracked.")
            label = translate("Tracking preferences")
        for values in email_list:
            emails = tools.email_normalize_all(", ".join(values.get("email_to") or []))
            trace = next(
                (
                    traces_by_email[email]
                    for email in emails
                    if email in traces_by_email
                ),
                None,
            )
            if not trace:
                continue
            url = mailing._get_tracking_consent_url(trace)
            footer_html = Markup(
                '<p style="font-size:11px;color:#888888;text-align:center;">'
                '%s <a href="%s" style="color:#888888;">%s</a></p>'
            ) % (escape(text), escape(url), escape(label))
            footer_text = f"\n\n{text} {label}: {url}\n"
            body = values.get("body")
            if body:
                new_body = tools.mail.append_content_to_html(
                    str(body), str(footer_html), plaintext=False
                )
                values["body"] = (
                    Markup(new_body) if isinstance(body, Markup) else new_body
                )
            if values.get("body_alternative"):
                values["body_alternative"] += footer_text
        return email_list

    def _prepare_outgoing_list(
        self, mail_server=False, recipients_follower_status=None
    ):
        email_list = super()._prepare_outgoing_list(
            mail_server=mail_server,
            recipients_follower_status=recipients_follower_status,
        )
        if not self.mailing_id:
            return email_list
        is_tracked = self._tracking_consent_is_tracked()
        if not is_tracked:
            self._tracking_consent_remove(email_list)
        if (
            self.mailing_trace_ids
            and self.mailing_id.tracking_policy == "consent"
            and self.mailing_id.tracking_consent_footer
        ):
            self._tracking_consent_add_footer(email_list, is_tracked)
        return email_list
