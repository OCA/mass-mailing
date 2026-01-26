# Copyright 2017 Tecnativa - Jairo Llopis
# Copyright 2020 Hibou Corp. - Jared Kipe
# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class DynamicListCase(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tag = cls.env["res.partner.category"].create({"name": "testing tag"})
        cls.partners = cls.env["res.partner"]
        for number in range(5):
            cls.partners |= cls.partners.create(
                {
                    "name": "partner %d" % number,
                    "category_id": [(4, cls.tag.id, False)],
                    "email": "%d@example.com" % number,
                }
            )
        cls.list = cls.env["mailing.list"].create(
            {
                "name": "test list",
                "dynamic": True,
                "sync_domain": repr([("category_id", "in", cls.tag.ids)]),
            }
        )
        cls.mail = cls.env["mailing.mailing"].create(
            {
                "name": "test mass mailing",
                "subject": "test mass mailing",
                "contact_list_ids": [(4, cls.list.id, False)],
            }
        )

    def test_list_sync(self):
        """List is synced correctly."""
        Contact = self.env["mailing.contact"]
        # Partner 0 is not categorized
        self.partners[0].category_id = False
        # Partner 1 has no email
        self.partners[1].email = False
        # Set list as unsynced
        self.list.dynamic = False
        # Create contact for partner 0 in unsynced list
        contact0 = Contact.create(
            {
                "list_ids": [(4, self.list.id)],
                "partner_id": self.partners[0].id,
            }
        )
        self.list.flush_recordset()
        self.assertEqual(self.list.contact_count, 1)
        # Set list as add-synced
        self.list.dynamic = True
        self.list.action_sync()
        self.list.flush_recordset()
        self.assertEqual(self.list.contact_count, 4)
        self.assertTrue(contact0.exists())
        # Set list as full-synced
        self.list.sync_method = "full"
        Contact.search(
            [
                ("list_ids", "in", self.list.ids),
                ("partner_id", "=", self.partners[2].id),
            ]
        ).unlink()
        self.list.action_sync()
        self.list.flush_recordset()
        self.assertEqual(self.list.contact_count, 3)
        self.assertFalse(contact0.exists())
        # Cannot add or edit contacts in fully synced lists
        with self.assertRaises(ValidationError):
            Contact.create(
                {
                    "list_ids": [(4, self.list.id)],
                    "partner_id": self.partners[0].id,
                }
            )
        contact1 = Contact.search([("list_ids", "in", self.list.ids)], limit=1)
        with Form(contact1) as contact1_f:
            # Fields are readonly
            with self.assertRaises(AssertionError):
                contact1_f.name = "other"
            with self.assertRaises(AssertionError):
                contact1_f.email = "other@example.com"
        self.assertEqual(contact1.name, "partner 2")
        self.assertEqual(contact1.email, "2@example.com")
        self.assertTrue(contact1.in_fully_synced_lists)
        # Unset dynamic list
        self.list.dynamic = False
        # Now the contact is created without exception
        Contact.create({"list_ids": [(4, self.list.id)], "email": "test@example.com"})
        # Contacts can now be changed
        self.assertFalse(contact1.in_fully_synced_lists)
        with Form(contact1) as contact1_f:
            contact1_f.partner_id = self.env["res.partner"]
            contact1_f.name = "other"
            contact1_f.email = "other@example.com"
        self.assertEqual(contact1.name, "other")
        self.assertEqual(contact1.email, "other@example.com")

    def test_sync_when_sending_mail(self):
        """Check that list in synced when sending a mass mailing."""
        self.list.action_sync()
        self.list.flush_recordset()
        self.assertEqual(self.list.contact_count, 5)
        # Create a new partner
        self.partners.create(
            {
                "name": "extra partner",
                "category_id": [(4, self.tag.id, False)],
                "email": "extra@example.com",
            }
        )
        # Mock sending low level method, because an auto-commit happens there
        with patch("odoo.addons.mail.models.mail_mail.MailMail.send") as s:
            self.mail.action_send_mail()
            self.assertEqual(1, s.call_count)
        self.list.flush_recordset()
        self.assertEqual(6, self.list.contact_count)

    def test_load_filter(self):
        domain = "[('id', '=', 1)]"
        ir_filter = self.env["ir.filters"].create(
            {
                "name": "Test filter",
                "model_id": "res.partner",
                "domain": domain,
            }
        )
        wizard = (
            self.env["mailing.load.filter"]
            .with_context(active_id=self.list.id)
            .create({"filter_id": ir_filter.id})
        )
        wizard.load_filter()
        self.assertEqual(self.list.sync_domain, domain)

    def test_change_partner(self):
        self.list.sync_method = "full"
        self.list.action_sync()
        # This shouldn't fail
        self.partners[:1].write({"email": "test_mass_mailing_list_dynamic@example.org"})

    def test_delete_contact_from_nondynamic_list(self):
        """Test manual management of contacts.

        A contact linked to both dynamic and manual lists should still
        allow manual management in manual lists.
        """
        manual_list = self.env["mailing.list"].create(
            {
                "name": "test non-dynamic list",
                "dynamic": False,
            }
        )
        self.list.sync_method = "full"
        self.list.action_sync()
        self.list.flush_recordset()
        self.assertEqual(self.list.contact_count, 5)
        self.assertEqual(self.list.contact_ids.partner_id, self.partners)
        contact0 = self.list.contact_ids[0]
        self.assertTrue(contact0.exists())
        contact0_f = Form(contact0)
        with contact0_f.subscription_ids.new() as subscription:
            subscription.list_id = manual_list
        contact0_f.save()
        self.assertEqual(self.list.contact_count, 5)
        self.assertEqual(manual_list.contact_count, 1)
        self.assertIn(contact0, self.list.contact_ids)
        self.assertIn(contact0, manual_list.contact_ids)

    def test_add_fully_synced_contact_to_another_manual_list(self):
        """Test adding a fully synced contact to another manual list."""
        manual_list = self.env["mailing.list"].create(
            {
                "name": "test non-dynamic list",
                "dynamic": False,
            }
        )
        self.list.sync_method = "full"
        self.list.action_sync()
        self.list.flush_recordset()
        self.assertEqual(self.list.contact_count, 5)
        self.assertEqual(self.list.contact_ids.partner_id, self.partners)
        contact0 = self.list.contact_ids[0]
        self.assertTrue(contact0.exists())
        contact0_f = Form(contact0)
        with contact0_f.subscription_ids.new() as subscription:
            subscription.list_id = manual_list
        contact0_f.save()
        contact0.flush_recordset()
        self.assertEqual(self.list.contact_count, 5)
        self.assertEqual(manual_list.contact_count, 1)
        self.assertIn(contact0, self.list.contact_ids)
        self.assertIn(contact0, manual_list.contact_ids)

    def test_is_synced(self):
        self.list.dynamic = False
        self.list._onchange_dynamic()
        # It shouldn't change when list is reversed to normal
        self.assertTrue(self.list.is_synced)
        self.list.dynamic = True
        self.list._onchange_dynamic()
        self.assertFalse(self.list.is_synced)
        self.list.action_sync()
        self.assertTrue(self.list.is_synced)

    def test_partners_merge(self):
        tag2 = self.tag.copy({"name": "Tag 2"})
        self.list.sync_method = "full"
        list2 = self.list.copy(
            {
                "name": "test list 2",
                "sync_domain": repr([("category_id", "in", tag2.ids)]),
            }
        )
        partner_1 = self.partners.create(
            {
                "name": "Demo 1",
                "email": "demo1@demo.com",
                "category_id": [(4, self.tag.id, False)],
            }
        )
        partner_2 = self.partners.create(
            {
                "name": "Demo 2",
                "email": "demo2@demo.com",
                "category_id": [(4, self.tag.id, False), (4, tag2.id, False)],
            }
        )
        self.list.action_sync()
        list2.action_sync()
        self.assertTrue(partner_1.id in self.list.contact_ids.mapped("partner_id").ids)
        self.assertTrue(partner_2.id in self.list.contact_ids.mapped("partner_id").ids)
        self.assertFalse(partner_1.id in list2.contact_ids.mapped("partner_id").ids)
        self.assertTrue(partner_2.id in list2.contact_ids.mapped("partner_id").ids)
        # Wizard partner merge (partner_1 + partner_2) in partner_i1
        wizard = self.env["base.partner.merge.automatic.wizard"].create(
            {
                "state": "option",
                "dst_partner_id": partner_1.id,
                "partner_ids": [(4, partner_1.id), (4, partner_2.id)],
            }
        )
        wizard.action_merge()
        self.assertTrue(partner_1.id in self.list.contact_ids.mapped("partner_id").ids)
        self.assertTrue(partner_1.id in list2.contact_ids.mapped("partner_id").ids)
