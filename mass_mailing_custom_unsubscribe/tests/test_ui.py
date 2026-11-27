# Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from werkzeug import urls

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tests.common import HttpCase

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class UICase(BaseCommon, HttpCase):
    # Keep the superadmin user the tests always ran as; the tours log in explicitly
    _test_user_groups = None

    def _set_unsubscribe_url(self, res_id):
        """Set the unsubscription link of ``self.email`` for ``res_id``.

        Mails are not sent during tests, so the link is built with the same
        method that renders it in the mail body.
        """
        url = self.mailing._get_unsubscribe_url(self.email, res_id)
        self.assertTrue(urls.url_parse(url).decode_query().get("hash_token"))
        self.assertTrue(url.startswith(self.domain))
        self.url = url.replace(self.domain, "", 1)

    def setUp(self):
        super().setUp()
        self.email = "test.contact@example.com"
        self.url = ""
        self.domain = self.env["ir.config_parameter"].get_str("web.base.url")
        # Demo data is not installed by default since 19.0: create the user here
        self.user = self.env["res.users"].create(
            {
                "name": "Unsubscribe tester",
                "login": "unsubscribe_tester",
                "password": "unsubscribe_tester",
                "group_ids": [Command.set([self.env.ref("base.group_user").id])],
            }
        )
        List = self.lists = self.env["mailing.list"]
        for n in range(4):
            self.lists += List.create({"name": f"test list {n}"})
        self.contact = self.env["mailing.contact"].create(
            {
                "name": "test contact",
                "email": self.email,
                "list_ids": [Command.set(self.lists[:3].ids)],
            }
        )
        self.mailing = self.env["mailing.mailing"].create(
            {
                "mailing_model_id": self.env.ref("mass_mailing.model_mailing_list").id,
                "contact_list_ids": [(6, 0, [self.lists[0].id, self.lists[3].id])],
                "reply_to_mode": "update",
                "subject": "Test",
            }
        )

    def tearDown(self):
        del self.email, self.lists, self.contact, self.mailing, self.url
        super().tearDown()

    def test_contact_unsubscription(self):
        """Test a mass mailing contact that wants to unsubscribe."""
        self._set_unsubscribe_url(self.contact.id)
        self.start_tour(
            self.url, "mass_mailing_custom_unsubscribe_tour_contact", login="admin"
        )
        # Check results from running tour
        subscription = self.contact.subscription_ids.filtered("opt_out")
        self.assertTrue("REMOTE_ADDR" in subscription.metadata)

    def test_partner_unsubscription(self):
        """Test a partner that wants to unsubscribe."""
        # Change mailing to be sent to partner
        partner_id = self.env["res.partner"].name_create(
            f"Demo Partner <{self.email}>"
        )[0]
        self.mailing.mailing_model_id = self.env.ref("base.model_res_partner")
        self.mailing.mailing_domain = repr(
            [("is_blacklisted", "=", False), ("id", "=", partner_id)]
        )
        self._set_unsubscribe_url(partner_id)
        self.start_tour(
            self.url,
            "mass_mailing_custom_unsubscribe_tour_partner",
            login=self.user.login,
        )
        # Check results from running tour
        partner = self.env["res.partner"].browse(partner_id)
        self.assertTrue(partner.is_blacklisted)
        blacklist = self.env["mail.blacklist"].search([("email", "=", partner.email)])
        self.assertEqual(blacklist.opt_out_reason_id.name, "Other")
        self.assertTrue("REMOTE_ADDR" in "".join(blacklist.message_ids.mapped("body")))

    def test_mailing_unsubscribe_redirect(self):
        """Test that /confirm_unsubscribe redirects to /unsubscribe."""
        # Create parameter to enable redirect
        self.env["ir.config_parameter"].sudo().set_bool(
            "mass_mailing.mailing_lists_unsubscribe_redirect", True
        )
        # Change mailing to be sent to partner
        partner_id = self.env["res.partner"].name_create(
            f"Demo Partner <{self.email}>"
        )[0]
        self.mailing.mailing_model_id = self.env.ref("base.model_res_partner")
        self.mailing.mailing_domain = repr(
            [("is_blacklisted", "=", False), ("id", "=", partner_id)]
        )
        self._set_unsubscribe_url(partner_id)
        result = self.url_open(self.url, allow_redirects=False)
        self.assertTrue(result.ok)
        self.assertTrue(result.is_redirect)
        self.assertFalse(result.is_permanent_redirect)
        self.assertIn("/unsubscribe", result.next.url)
