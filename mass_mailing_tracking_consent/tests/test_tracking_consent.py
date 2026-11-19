# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import HttpCase, TransactionCase, tagged
from odoo.tools import mute_logger

from odoo.addons.mass_mailing_tracking_consent.models.mailing_tracking_consent import (
    ADD_FOOTER_LINK_PARAM,
)


class TrackingConsentTestMixin:
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contact = cls.env["mailing.contact"].create(
            {
                "name": "Test Recipient",
                "email": "recipient@example.com",
            }
        )
        cls.mailing = cls.env["mailing.mailing"].create(
            {
                "subject": "Test mailing",
                "mailing_model_id": cls.env["ir.model"]._get_id("mailing.contact"),
                "body_html": "<p>Hello</p>",
            }
        )
        cls.tracker = cls.env["link.tracker"].create(
            {"url": "https://example.com/target?x=1"}
        )
        cls.mail = cls.env["mail.mail"].create(
            {
                "mailing_id": cls.mailing.id,
                "mailing_trace_ids": [
                    (
                        0,
                        0,
                        {
                            "mass_mailing_id": cls.mailing.id,
                            "model": "mailing.contact",
                            "res_id": cls.contact.id,
                            "email": cls.contact.email,
                            "message_id": "<tracking-consent-test@example.com>",
                        },
                    )
                ],
                "model": "mailing.contact",
                "res_id": cls.contact.id,
                "email_from": "noreply@example.com",
                "email_to": cls.contact.email,
                "subject": "Test mailing",
                "body_html": cls.mailing.body_html,
            }
        )
        cls.trace = cls.mail.mailing_trace_ids

    def _set_consent(self, state):
        return self.env["mailing.tracking.consent"]._set_consent(
            self.contact.email, state
        )

    def _email_values(self):
        self.mail.invalidate_recordset()
        return self.mail._prepare_outgoing_list()[0]


class TestTrackingConsent(TrackingConsentTestMixin, TransactionCase):
    def test_default_denies_tracking_and_adds_opt_in_footer(self):
        values = self._email_values()
        self.assertNotIn("blank.gif", values["body"])
        self.assertNotIn(f"/m/{self.trace.id}", values["body"])
        self.assertIn(f"/mailing/tracking_consent/{self.trace.id}/", values["body"])
        self.assertIn(
            f"/mailing/tracking_consent/{self.trace.id}/",
            values["body_alternative"],
        )
        self.assertFalse(
            self.env["mailing.tracking.consent"]._is_tracking_allowed(
                self.contact.email
            )
        )

    def test_granted_consent_includes_tracking(self):
        self._set_consent("granted")
        self.mail.body_html = f'<p><a href="{self.tracker.short_url}">link</a></p>'
        values = self._email_values()
        self.assertIn("blank.gif", values["body"])
        self.assertIn(f"/m/{self.trace.id}", values["body"])
        self.assertIn("Withdraw consent", values["body"])
        self.assertIn("Withdraw consent", values["body_alternative"])

    def test_withdrawn_consent_removes_tracking(self):
        self._set_consent("granted")
        self.assertIn("blank.gif", self._email_values()["body"])
        self._set_consent("refused")
        values = self._email_values()
        self.assertNotIn("blank.gif", values["body"])
        self.assertNotIn(f"/m/{self.trace.id}", values["body"])

    def test_footer_can_be_disabled_per_mailing(self):
        self.mailing.tracking_consent_footer = False
        values = self._email_values()
        self.assertNotIn("/mailing/tracking_consent/", values["body"])
        self.assertNotIn("/mailing/tracking_consent/", values["body_alternative"])

    def test_policy_none_removes_tracking_and_footer(self):
        self.mailing.tracking_policy = "none"
        values = self._email_values()
        self.assertNotIn("blank.gif", values["body"])
        self.assertNotIn(f"/m/{self.trace.id}", values["body"])
        self.assertNotIn("/mailing/tracking_consent/", values["body"])

    def test_policy_always_keeps_tracking_without_footer(self):
        self.mailing.tracking_policy = "always"
        self.mail.body_html = f'<p><a href="{self.tracker.short_url}">link</a></p>'
        values = self._email_values()
        self.assertIn("blank.gif", values["body"])
        self.assertIn(f"/m/{self.trace.id}", values["body"])
        self.assertNotIn("/mailing/tracking_consent/", values["body"])

    def test_multiple_recipients_require_each_consent(self):
        self._set_consent("granted")
        self.mail.email_to = "recipient@example.com, other@example.com"
        self.assertFalse(self.mail._mailing_tracking_allowed())
        self.assertNotIn("blank.gif", self._email_values()["body"])
        self.env["mailing.tracking.consent"]._set_consent(
            "other@example.com", "granted"
        )
        self.assertTrue(self.mail._mailing_tracking_allowed())
        self.assertIn("blank.gif", self._email_values()["body"])

    def test_recipient_ids_are_used_when_email_to_is_empty(self):
        partner = self.env["res.partner"].create(
            {"name": "Recipient Partner", "email": "partner@example.com"}
        )
        self.mail.write(
            {
                "email_to": False,
                "recipient_ids": [(6, 0, [partner.id])],
            }
        )
        self.assertFalse(self.mail._mailing_tracking_allowed())
        self.assertNotIn("blank.gif", self._email_values()["body"])
        self.env["mailing.tracking.consent"]._set_consent(partner.email, "granted")
        self.assertTrue(self.mail._mailing_tracking_allowed())
        self.assertIn("blank.gif", self._email_values()["body"])

    def test_short_links_are_restored_without_consent(self):
        self.mail.body_html = f'<p><a href="{self.tracker.short_url}">link</a></p>'
        values = self._email_values()
        self.assertNotIn(self.tracker.short_url, values["body"])
        self.assertIn("https://example.com/target?x=1", values["body"])
        self.assertIn("https://example.com/target?x=1", values["body_alternative"])

    def test_mail_tracking_pixel_is_removed(self):
        self.mail.body_html = (
            '<p>Hello</p><img src="http://localhost:8069/mail/tracking/open/'
            'db/5/token/blank.gif"/>'
        )
        values = self._email_values()
        self.assertNotIn("blank.gif", values["body"])

    def test_mass_mailing_user_cannot_delete_consent(self):
        marketing_user = self.env["res.users"].create(
            {
                "name": "Marketing User",
                "login": "tracking_consent_marketing_user",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("mass_mailing.group_mass_mailing_user").id,
                        ],
                    )
                ],
            }
        )
        consent = self._set_consent("granted")
        with self.assertRaises(AccessError):
            consent.with_user(marketing_user).unlink()

    def test_consent_record_is_normalized_and_updated(self):
        consent_model = self.env["mailing.tracking.consent"]
        consent = consent_model._set_consent(
            "Test Recipient <Recipient@Example.COM>", "granted"
        )
        self.assertEqual(consent.email_normalized, "recipient@example.com")
        consent_date = consent.consent_date
        same_consent = consent_model._set_consent("recipient@example.com", "refused")
        self.assertEqual(consent, same_consent)
        self.assertEqual(same_consent.state, "refused")
        self.assertTrue(same_consent.consent_date >= consent_date)
        self.assertEqual(
            consent_model.search_count(
                [("email_normalized", "=", "recipient@example.com")]
            ),
            1,
        )

    def test_set_consent_records_source_mailing_and_note(self):
        consent = self.env["mailing.tracking.consent"]._set_consent(
            self.contact.email,
            "granted",
            source="link",
            mailing=self.mailing,
            note="Proof of consent",
        )
        self.assertEqual(consent.source, "link")
        self.assertEqual(consent.mailing_id, self.mailing)
        self.assertEqual(consent.note, "Proof of consent")

    def test_get_token_depends_on_trace(self):
        consent_model = self.env["mailing.tracking.consent"]
        self.assertNotEqual(
            consent_model._get_token(self.trace.id),
            consent_model._get_token(self.trace.id + 1),
        )

    def test_source_details_is_preserved_when_not_supplied(self):
        consent_model = self.env["mailing.tracking.consent"]
        consent = consent_model._set_consent(
            self.contact.email,
            "granted",
            source="form",
            source_details="Subscription form 1",
        )
        consent_model._set_consent(self.contact.email, "refused")
        self.assertEqual(consent.source_details, "Subscription form 1")

    def test_consent_model_rejects_invalid_email(self):
        with self.assertRaises(ValidationError):
            self.env["mailing.tracking.consent"].create({"email": "not-an-email"})

    def test_consent_field_is_editable_and_searchable(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Test Partner",
                "email": "partner@example.com",
            }
        )
        self.assertFalse(partner.tracking_consent)
        partner.tracking_consent = "granted"
        partner.invalidate_recordset()
        self.assertEqual(partner.tracking_consent, "granted")
        self.assertIn(
            partner,
            self.env["res.partner"].search([("tracking_consent", "=", "granted")]),
        )
        self.assertEqual(
            self.env["mailing.tracking.consent"]._get_consent(partner.email).state,
            "granted",
        )
        partner.tracking_consent = "refused"
        partner.invalidate_recordset()
        self.assertEqual(partner.tracking_consent, "refused")
        self.assertNotIn(
            partner,
            self.env["res.partner"].search([("tracking_consent", "=", "granted")]),
        )
        self.assertIn(
            partner,
            self.env["res.partner"].search([("tracking_consent", "!=", "granted")]),
        )

    def test_clearing_consent_field_keeps_existing_choice(self):
        partner = self.env["res.partner"].create(
            {"name": "Clearing Partner", "email": "clearing@example.com"}
        )
        partner.tracking_consent = "granted"
        partner.tracking_consent = False
        partner.invalidate_recordset()
        consent = self.env["mailing.tracking.consent"]._get_consent(partner.email)
        self.assertEqual(consent.state, "granted")
        self.assertEqual(partner.tracking_consent, "granted")

    def test_global_footer_default_is_used_for_new_mailings(self):
        self.env["ir.config_parameter"].sudo().set_param(ADD_FOOTER_LINK_PARAM, "False")
        mailing = self.env["mailing.mailing"].create(
            {
                "subject": "Default footer",
                "mailing_model_id": self.env["ir.model"]._get_id("mailing.contact"),
                "body_html": "<p>Hello</p>",
            }
        )
        self.assertFalse(mailing.tracking_consent_footer)

    def test_search_false_granted_refused(self):
        partner_model = self.env["res.partner"]
        unrecorded = partner_model.create(
            {"name": "Unrecorded Partner", "email": "unrecorded@example.com"}
        )
        granted = partner_model.create(
            {"name": "Granted Partner", "email": "granted@example.com"}
        )
        refused = partner_model.create(
            {"name": "Refused Partner", "email": "refused@example.com"}
        )
        consent_model = self.env["mailing.tracking.consent"]
        consent_model._set_consent(granted.email, "granted")
        consent_model._set_consent(refused.email, "refused")
        for partner in (unrecorded, granted, refused):
            partner.invalidate_recordset()

        self.assertIn(
            unrecorded,
            partner_model.search([("tracking_consent", "=", False)]),
        )
        self.assertIn(
            unrecorded,
            partner_model.search([("tracking_consent", "!=", "granted")]),
        )
        self.assertIn(
            unrecorded,
            partner_model.search([("tracking_consent", "not in", ["granted"])]),
        )
        self.assertIn(
            unrecorded,
            partner_model.search([("tracking_consent", "in", [False])]),
        )
        self.assertIn(
            unrecorded,
            partner_model.search([("tracking_consent", "in", [False, "granted"])]),
        )
        self.assertNotIn(
            unrecorded,
            partner_model.search([("tracking_consent", "=", "granted")]),
        )
        self.assertNotIn(
            unrecorded,
            partner_model.search([("tracking_consent", "!=", False)]),
        )
        self.assertNotIn(
            unrecorded,
            partner_model.search([("tracking_consent", "not in", [False])]),
        )

        self.assertIn(
            granted,
            partner_model.search([("tracking_consent", "=", "granted")]),
        )
        self.assertNotIn(
            granted,
            partner_model.search([("tracking_consent", "=", False)]),
        )
        self.assertNotIn(
            granted,
            partner_model.search([("tracking_consent", "!=", "granted")]),
        )
        self.assertNotIn(
            granted,
            partner_model.search([("tracking_consent", "not in", ["granted"])]),
        )
        self.assertIn(
            granted,
            partner_model.search([("tracking_consent", "in", [False, "granted"])]),
        )
        self.assertNotIn(
            granted,
            partner_model.search([("tracking_consent", "not in", [False, "granted"])]),
        )
        self.assertIn(
            granted,
            partner_model.search([("tracking_consent", "not in", [False])]),
        )

        self.assertIn(
            refused,
            partner_model.search([("tracking_consent", "=", "refused")]),
        )
        self.assertNotIn(
            refused,
            partner_model.search([("tracking_consent", "=", False)]),
        )
        self.assertIn(
            refused,
            partner_model.search([("tracking_consent", "!=", "granted")]),
        )
        self.assertIn(
            refused,
            partner_model.search([("tracking_consent", "not in", ["granted"])]),
        )
        self.assertIn(
            refused,
            partner_model.search([("tracking_consent", "not in", [False, "granted"])]),
        )
        self.assertNotIn(
            refused,
            partner_model.search([("tracking_consent", "in", [False, "granted"])]),
        )
        self.assertIn(
            refused,
            partner_model.search([("tracking_consent", "not in", [False])]),
        )

    def test_field_groups_protect_consent(self):
        user = self.env["res.users"].create(
            {
                "name": "Non Marketing User",
                "login": "tracking_consent_non_marketing_user",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        partner = self.env["res.partner"].create(
            {"name": "Protected Partner", "email": "protected@example.com"}
        )
        with self.assertRaises(AccessError):
            partner.with_user(user).write({"tracking_consent": "granted"})

    def test_multi_recipient_footer_uses_own_trace(self):
        partner = self.env["res.partner"].create(
            {"name": "Second Recipient", "email": "other@example.com"}
        )
        second_trace = self.env["mailing.trace"].create(
            {
                "mass_mailing_id": self.mailing.id,
                "mail_mail_id": self.mail.id,
                "model": "res.partner",
                "res_id": partner.id,
                "email": partner.email,
            }
        )
        first_partner = self.env["res.partner"].create(
            {"name": "First Recipient", "email": self.contact.email}
        )
        self.mail.write(
            {
                "email_to": False,
                "recipient_ids": [(6, 0, [first_partner.id, partner.id])],
            }
        )
        first_url = self.mailing._get_tracking_consent_url(self.trace)
        second_url = self.mailing._get_tracking_consent_url(second_trace)
        values_list = self.mail._prepare_outgoing_list()
        self.assertEqual(len(values_list), 2)
        for values in values_list:
            if first_partner.email in ", ".join(values["email_to"]):
                self.assertIn(first_url, values["body"])
                self.assertNotIn(second_url, values["body"])
            else:
                self.assertIn(second_url, values["body"])
                self.assertNotIn(first_url, values["body"])


@tagged("post_install", "-at_install")
class TestTrackingConsentController(TrackingConsentTestMixin, HttpCase):
    def _tracking_page_url(self, token=None):
        token = token or self.env["mailing.tracking.consent"]._get_token(self.trace.id)
        return f"/mailing/tracking_consent/{self.trace.id}/{token}"

    def _csrf_token(self):
        page = self.url_open(self._tracking_page_url())
        marker = 'name="csrf_token" value="'
        return page.text.partition(marker)[2].partition('"')[0]

    def _consent_form_data(self, consent_state, csrf_token):
        return {
            "csrf_token": csrf_token,
            "consent_state": consent_state,
        }

    def test_public_page_and_withdraw_consent(self):
        page = self.url_open(self._tracking_page_url())
        self.assertEqual(page.status_code, 200)
        self.assertIn("Email tracking preferences", page.text)
        csrf_token = self._csrf_token()
        self.assertTrue(csrf_token)
        response = self.url_open(
            self._tracking_page_url(),
            data=self._consent_form_data("refused", csrf_token),
        )
        self.assertEqual(response.status_code, 200)
        consent = self.env["mailing.tracking.consent"]._get_consent(self.contact.email)
        self.assertEqual(consent.state, "refused")
        self.assertEqual(consent.source, "link")
        self.assertEqual(consent.mailing_id, self.mailing)
        self.assertIn("Tracking is currently disabled", response.text)

    def test_public_page_grants_consent(self):
        response = self.url_open(
            self._tracking_page_url(),
            data=self._consent_form_data("granted", self._csrf_token()),
        )
        self.assertEqual(response.status_code, 200)
        consent = self.env["mailing.tracking.consent"]._get_consent(self.contact.email)
        self.assertEqual(consent.state, "granted")
        self.assertIn("Tracking is currently enabled", response.text)

    def test_public_page_get_does_not_change_consent(self):
        response = self.url_open(self._tracking_page_url())
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            self.env["mailing.tracking.consent"]._get_consent(self.contact.email)
        )

    def test_public_page_rejects_invalid_token(self):
        response = self.url_open(self._tracking_page_url(token="wrong"))
        self.assertEqual(response.status_code, 404)

    def test_public_page_rejects_invalid_consent_state(self):
        response = self.url_open(
            self._tracking_page_url(),
            data=self._consent_form_data("invalid", self._csrf_token()),
        )
        self.assertEqual(response.status_code, 400)

    @mute_logger("odoo.http")
    def test_public_page_rejects_missing_csrf_token(self):
        data = self._consent_form_data("refused", self._csrf_token())
        del data["csrf_token"]
        response = self.url_open(self._tracking_page_url(), data=data)
        self.assertEqual(response.status_code, 400)

    def test_public_page_rejects_invalid_token_on_post(self):
        response = self.url_open(
            self._tracking_page_url(token="wrong"),
            data=self._consent_form_data("refused", self._csrf_token()),
        )
        self.assertEqual(response.status_code, 404)

    def test_policy_always_records_without_consent(self):
        self.mailing.tracking_policy = "always"
        token = self.mail._generate_mail_recipient_token(self.mail.id)
        response = self.url_open(f"/mail/track/{self.mail.id}/{token}/blank.gif")
        self.assertEqual(response.status_code, 200)
        self.trace.invalidate_recordset()
        self.assertEqual(self.trace.trace_status, "open")
        response = self.url_open(
            f"/r/{self.tracker.code}/m/{self.trace.id}",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 301)
        self.assertTrue(
            self.env["link.tracker.click"].search_count(
                [("link_id", "=", self.tracker.id)]
            )
        )

    def test_policy_none_does_not_record_with_consent(self):
        self._set_consent("granted")
        self.mailing.tracking_policy = "none"
        token = self.mail._generate_mail_recipient_token(self.mail.id)
        response = self.url_open(f"/mail/track/{self.mail.id}/{token}/blank.gif")
        self.assertEqual(response.status_code, 200)
        self.trace.invalidate_recordset()
        self.assertNotEqual(self.trace.trace_status, "open")
        response = self.url_open(
            f"/r/{self.tracker.code}/m/{self.trace.id}",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 301)
        self.assertFalse(
            self.env["link.tracker.click"].search_count(
                [("link_id", "=", self.tracker.id)]
            )
        )

    def test_pixel_after_mail_deleted_without_consent(self):
        mail_id = self.mail.id
        token = self.mail._generate_mail_recipient_token(mail_id)
        self.mail.unlink()
        response = self.url_open(f"/mail/track/{mail_id}/{token}/blank.gif")
        self.assertEqual(response.status_code, 200)
        self.trace.invalidate_recordset()
        self.assertNotEqual(self.trace.trace_status, "open")

    def test_pixel_after_mail_deleted_with_consent(self):
        self._set_consent("granted")
        mail_id = self.mail.id
        token = self.mail._generate_mail_recipient_token(mail_id)
        self.mail.unlink()
        response = self.url_open(f"/mail/track/{mail_id}/{token}/blank.gif")
        self.assertEqual(response.status_code, 200)
        self.trace.invalidate_recordset()
        self.assertEqual(self.trace.trace_status, "open")

    def test_pixel_is_not_recorded_without_consent(self):
        token = self.mail._generate_mail_recipient_token(self.mail.id)
        url = f"/mail/track/{self.mail.id}/{token}/blank.gif"
        response = self.url_open(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("image/gif", response.headers["Content-Type"])
        self.trace.invalidate_recordset()
        self.assertNotEqual(self.trace.trace_status, "open")

    def test_pixel_is_recorded_with_consent(self):
        self._set_consent("granted")
        token = self.mail._generate_mail_recipient_token(self.mail.id)
        url = f"/mail/track/{self.mail.id}/{token}/blank.gif"
        response = self.url_open(url)
        self.assertEqual(response.status_code, 200)
        self.trace.invalidate_recordset()
        self.assertEqual(self.trace.trace_status, "open")

    def test_click_is_not_recorded_without_consent(self):
        url = f"/r/{self.tracker.code}/m/{self.trace.id}"
        response = self.url_open(url, allow_redirects=False)
        self.assertEqual(response.status_code, 301)
        self.assertFalse(
            self.env["link.tracker.click"].search_count(
                [("link_id", "=", self.tracker.id)]
            )
        )
        self.trace.invalidate_recordset()
        self.assertNotEqual(self.trace.trace_status, "open")

    def test_click_with_missing_trace_is_not_recorded(self):
        response = self.url_open(
            f"/r/{self.tracker.code}/m/999999", allow_redirects=False
        )
        self.assertEqual(response.status_code, 301)
        self.assertFalse(
            self.env["link.tracker.click"].search_count(
                [("link_id", "=", self.tracker.id)]
            )
        )

    def test_click_is_recorded_with_consent(self):
        self._set_consent("granted")
        url = f"/r/{self.tracker.code}/m/{self.trace.id}"
        response = self.url_open(url, allow_redirects=False)
        self.assertEqual(response.status_code, 301)
        self.assertTrue(
            self.env["link.tracker.click"].search_count(
                [("link_id", "=", self.tracker.id)]
            )
        )
        self.trace.invalidate_recordset()
        self.assertEqual(self.trace.trace_status, "open")
