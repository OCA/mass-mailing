# Copyright 2015 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2015 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2015 Javier Iniesta <javieria@antiun.com>
# Copyright 2020 Tecnativa - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MailingList(models.Model):
    _inherit = "mailing.list"

    partner_mandatory = fields.Boolean(string="Mandatory Partner", default=False)
    partner_category = fields.Many2one(
        comodel_name="res.partner.category", string="Partner Tag"
    )

    @api.constrains("contact_ids")
    def _check_contact_ids_partner_id(self):
        failures = self.env["mailing.contact"]
        for mailing_list in self:
            partners = self.env["res.partner"]
            for contact in mailing_list.contact_ids:
                if contact.partner_id:
                    if contact.partner_id in partners:
                        failures |= contact
                    partners |= contact.partner_id
        if failures:
            raise ValidationError(
                self.env._(
                    "A partner cannot be multiple times in the same list. "
                    "Failed contacts:\n - %s",
                    "\n- ".join(failures.mapped(lambda c: f"{c.name} ({c.email})")),
                )
            )
