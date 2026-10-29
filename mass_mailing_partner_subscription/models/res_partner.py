# Copyright 2026 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    mailing_list_ids = fields.Many2many(
        comodel_name="mailing.list",
        string="Mailing Lists",
        compute="_compute_mailing_list_ids",
        inverse="_inverse_mailing_list_ids",
        compute_sudo=True,
    )

    @api.depends("mass_mailing_contact_ids", "mass_mailing_contact_ids.list_ids")
    def _compute_mailing_list_ids(self):
        for partner in self:
            contact = partner.mass_mailing_contact_ids[:1]
            partner.mailing_list_ids = contact.list_ids

    def _inverse_mailing_list_ids(self):
        MailingContact = self.env["mailing.contact"].sudo()
        for partner in self:
            lists = partner.mailing_list_ids
            contact = partner.sudo().mass_mailing_contact_ids[:1]
            if not contact:
                if not lists:
                    continue
                contact = MailingContact.create(
                    {
                        "name": partner.name,
                        "email": partner.email,
                        "partner_id": partner.id,
                    }
                )
            contact.list_ids = lists
