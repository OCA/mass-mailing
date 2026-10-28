# Copyright 2026 Moduon Team S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from . import base


class MailingContactToListCase(base.BaseCase):
    def _add_partners_to_list(self, partners, mailing_list):
        wizard = self.env["mailing.contact.to.list"].create(
            {
                "partner_ids": [(6, 0, partners.ids)],
                "mailing_list_ids": [(6, 0, mailing_list.ids)],
            }
        )
        wizard.action_add_contacts()

    def test_add_partner_to_list(self):
        self._add_partners_to_list(self.partner, self.mailing_list)
        contact = self.partner.mass_mailing_contact_ids
        self.assertEqual(len(contact), 1)
        self.assertEqual(contact.list_ids, self.mailing_list)
        self.check_mailing_contact_partner(contact)
        # Adding the partner again does not create a new contact
        self._add_partners_to_list(self.partner, self.mailing_list)
        self.assertEqual(self.partner.mass_mailing_contact_ids, contact)
        # Adding the partner to another list reuses its contact
        list_2 = self.create_mailing_list({"name": "Test Add to List"})
        self._add_partners_to_list(self.partner, list_2)
        self.assertEqual(self.partner.mass_mailing_contact_ids, contact)
        self.assertEqual(contact.list_ids, self.mailing_list | list_2)

    def test_add_partner_to_list_existing_contact(self):
        contact = self.create_mailing_contact(
            {"email": "PARTNER@test.com", "list_ids": [(6, 0, self.mailing_list.ids)]}
        )
        self.assertEqual(contact.partner_id, self.partner)
        list_2 = self.create_mailing_list({"name": "Test Add to List"})
        self._add_partners_to_list(self.partner, list_2)
        self.assertEqual(self.partner.mass_mailing_contact_ids, contact)
        self.assertEqual(contact.list_ids, self.mailing_list | list_2)

    def test_add_partner_without_email(self):
        partner = self.create_partner({"name": "No email partner"})
        self._add_partners_to_list(partner, self.mailing_list)
        self.assertFalse(partner.mass_mailing_contact_ids)
        self.assertFalse(self.mailing_list.contact_ids)
