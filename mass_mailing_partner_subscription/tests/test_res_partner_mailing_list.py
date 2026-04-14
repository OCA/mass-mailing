# Copyright 2026 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestResPartnerMailingList(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Test Partner", "email": "test@example.com"}
        )
        cls.list_a = cls.env["mailing.list"].create({"name": "List A"})
        cls.list_b = cls.env["mailing.list"].create({"name": "List B"})

    def test_set_mailing_lists_creates_contact(self):
        """Writing mailing_list_ids on a partner with no contact auto-creates one."""
        partner = self.env["res.partner"].create(
            {"name": "New Partner", "email": "new@example.com"}
        )
        partner.mailing_list_ids = self.list_a
        contact = partner.mass_mailing_contact_ids[:1]
        self.assertTrue(contact)
        self.assertIn(self.list_a, contact.list_ids)

    def test_edit_mailing_lists_updates_contact(self):
        """Updating mailing_list_ids on a partner propagates to the linked contact."""
        contact = self.env["mailing.contact"].create(
            {
                "name": self.partner.name,
                "email": self.partner.email,
                "partner_id": self.partner.id,
                "list_ids": [(4, self.list_a.id)],
            }
        )
        self.assertEqual(self.partner.mailing_list_ids, self.list_a)
        self.partner.mailing_list_ids = self.list_a | self.list_b
        self.assertIn(self.list_b, contact.list_ids)
        self.partner.mailing_list_ids = self.list_b
        self.assertNotIn(self.list_a, contact.list_ids)
