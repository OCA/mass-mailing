# Copyright 2015 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2015 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2015 Javier Iniesta <javieria@antiun.com>
# Copyright 2020 Tecnativa - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.addons.base.tests.common import BaseCommon


class BaseCase(BaseCommon):
    _test_user_groups = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.main_company = cls.env.ref("base.main_company")
        cls.country_es = cls.env.ref("base.es")
        cls.category_0 = cls.env["res.partner.category"].create(
            {"name": "Test Category 0"}
        )
        cls.category_2 = cls.env["res.partner.category"].create(
            {"name": "Test Category 2"}
        )
        cls.partner = cls.create_partner(
            {
                "name": "Partner test",
                "email": "partner@test.com",
                "company_id": cls.main_company.id,
                "country_id": cls.country_es.id,
                "category_id": [(6, 0, (cls.category_0 | cls.category_2).ids)],
            }
        )

        cls.category_3 = cls.env["res.partner.category"].create(
            {"name": "Test Category 3"}
        )
        cls.mailing_list = cls.create_mailing_list({"name": "List test"})
        cls.mailing_list2 = cls.create_mailing_list(
            {
                "name": "List test 2",
                "partner_mandatory": True,
                "partner_category": cls.category_3.id,
            }
        )

    @classmethod
    def create_partner(cls, vals):
        m_partner = cls.env["res.partner"]
        return m_partner.create(vals)

    @classmethod
    def create_mailing_contact(cls, vals):
        m_mailing_contact = cls.env["mailing.contact"]
        return m_mailing_contact.create(vals)

    @classmethod
    def create_mailing_list(cls, vals):
        m_mailing_list = cls.env["mailing.list"]
        return m_mailing_list.create(vals)

    def check_mailing_contact_partner(self, mailing_contact):
        if mailing_contact.partner_id:
            self.assertEqual(mailing_contact.partner_id.email, mailing_contact.email)
            self.assertEqual(mailing_contact.partner_id.name, mailing_contact.name)
            if mailing_contact.partner_id.company_id:
                self.assertEqual(
                    mailing_contact.partner_id.company_id.name,
                    mailing_contact.company_name,
                )
            self.assertEqual(
                mailing_contact.partner_id.country_id, mailing_contact.country_id
            )
            self.assertEqual(
                mailing_contact.partner_id.category_id, mailing_contact.tag_ids
            )
