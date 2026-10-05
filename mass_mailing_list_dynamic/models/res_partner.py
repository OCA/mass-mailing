# Copyright 2017 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def write(self, vals):
        result = super(ResPartner, self.with_context(syncing=True)).write(vals)
        mailing_vals = {}

        if "name" in vals:
            mailing_vals["name"] = vals["name"]
        if "email" in vals:
            mailing_vals["email"] = vals["email"]
        if "title" in vals:
            mailing_vals["title_id"] = vals["title"]
        if "company_id" in vals:
            company = self.env["res.company"].browse(vals["company_id"])
            mailing_vals["company_name"] = company.name if company else False
        if "country_id" in vals:
            mailing_vals["country_id"] = vals["country_id"]

        if mailing_vals:
            contacts = (
                self.env["mailing.contact"]
                .sudo()
                .search(
                    [
                        "|",
                        ("partner_id", "in", self.ids),
                        ("duplicated_partner_id", "in", self.ids),
                    ]
                )
            )
            contacts.with_context(syncing=True).write(mailing_vals)

        return result
