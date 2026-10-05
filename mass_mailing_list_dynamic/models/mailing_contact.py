# Copyright 2017 Tecnativa - Jairo Llopis
# Copyright 2019 Tecnativa - Victor M.M. Torres
# Copyright 2020 Hibou Corp. - Jared Kipe
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MassMailingContact(models.Model):
    _inherit = "mailing.contact"

    duplicated_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Duplicated Partner",
        help=(
            "Reference to the original partner when this contact is a passive "
            "duplicate of another mailing contact."
        ),
    )

    @api.depends("partner_id", "partner_id.category_id")
    def _compute_tag_ids(self):
        return super()._compute_tag_ids()

    @api.onchange("duplicated_partner_id")
    def _onchange_duplicated_partner_id(self):
        for contact in self:
            if contact.duplicated_partner_id:
                partner = contact.duplicated_partner_id
                contact.name = partner.name
                contact.email = partner.email
                contact.title_id = partner.title
                contact.company_name = partner.company_id.name or partner.company_name
                contact.country_id = partner.country_id

    def _duplicate_partner_vals(self, partner):
        return {
            "name": partner.name,
            "email": partner.email,
            "title_id": partner.title.id if partner.title else False,
            "company_name": partner.company_id.name or partner.company_name,
            "country_id": partner.country_id.id if partner.country_id else False,
        }

    @staticmethod
    def _get_list_ids_from_commands(commands):
        target_lists = set()
        for command in commands or []:
            if not command:
                continue
            command_type = command[0]
            if command_type == 6:
                target_lists.update(command[2] or [])
            elif command_type == 4:
                target_lists.add(command[1])
            elif command_type == 0:
                list_id = command[2].get("list_id")
                if list_id:
                    target_lists.add(list_id)
        return target_lists

    @staticmethod
    def _get_subscription_list_ids(commands):
        return {
            command[2]["list_id"]
            for command in commands or []
            if command and command[0] == 0 and command[2].get("list_id")
        }

    def _get_target_list_ids(self, vals):
        """Return mailing lists affected by an upcoming create/write."""
        target_lists = self._get_list_ids_from_commands(vals.get("list_ids"))
        target_lists.update(
            self._get_subscription_list_ids(vals.get("subscription_ids"))
        )

        if self.ids and "list_ids" not in vals:
            target_lists.update(self.list_ids.ids)
        if self.ids and "subscription_ids" not in vals:
            target_lists.update(self.subscription_ids.mapped("list_id").ids)

        default_lists = self.env.context.get("default_list_ids")
        if default_lists:
            if isinstance(default_lists, int):
                target_lists.add(default_lists)
            else:
                target_lists.update(default_lists)

        return target_lists

    def _has_partner_collision(self, partner, list_ids, exclude=False):
        if not partner or not list_ids:
            return False
        domain = [
            ("partner_id", "=", partner.id),
            ("list_ids", "in", list(list_ids)),
        ]
        if exclude:
            domain.append(("id", "not in", self.ids))
        return bool(self.env["mailing.contact"].search(domain, limit=1))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            partner_id = vals.get("partner_id")
            if not partner_id:
                continue
            partner = self.env["res.partner"].browse(partner_id).exists()
            if not partner:
                continue

            target_lists = self._get_target_list_ids(vals)
            if self._has_partner_collision(partner, target_lists):
                vals["duplicated_partner_id"] = partner.id
                vals["partner_id"] = False
                for field, value in self._duplicate_partner_vals(partner).items():
                    vals.setdefault(field, value)

        return super().create(vals_list)

    def write(self, vals):
        relevant = (
            "partner_id" in vals or "list_ids" in vals or "subscription_ids" in vals
        )
        if not relevant:
            return super().write(vals)

        normal = self.env["mailing.contact"]
        duplicates = self.env["mailing.contact"]
        for contact in self:
            partner_id = vals.get("partner_id", contact.partner_id.id)
            if not partner_id:
                normal |= contact
                continue

            partner = self.env["res.partner"].browse(partner_id).exists()
            if not partner:
                normal |= contact
                continue

            target_lists = contact._get_target_list_ids(vals)
            if contact._has_partner_collision(partner, target_lists, exclude=True):
                duplicates |= contact
            else:
                normal |= contact

        result = True
        if normal:
            normal_vals = vals
            if "partner_id" in vals:
                normal_vals = dict(vals)
                normal_vals.setdefault("duplicated_partner_id", False)
            result = super(MassMailingContact, normal).write(normal_vals)

        for contact in duplicates:
            partner_id = vals.get("partner_id", contact.partner_id.id)
            partner = self.env["res.partner"].browse(partner_id).exists()

            duplicate_vals = dict(vals)
            duplicate_vals["partner_id"] = False
            duplicate_vals["duplicated_partner_id"] = partner.id

            for field, value in contact._duplicate_partner_vals(partner).items():
                duplicate_vals.setdefault(field, value)

            result = super(MassMailingContact, contact).write(duplicate_vals) and result

        return result

    def _overwrite_partner(self, vals, creating=False):
        """Never let a passive duplicate modify/create its real partner."""
        self.ensure_one()
        if self.duplicated_partner_id:
            return
        return super()._overwrite_partner(vals, creating=creating)

    @api.constrains("partner_id", "list_ids", "name", "email")
    def _check_no_manual_edits_on_fully_synced_lists(self):
        if self.env.context.get("syncing"):
            return
        full_synced_lists = self.mapped("list_ids").filtered(
            lambda x: x.dynamic and x.sync_method == "full"
        )
        if full_synced_lists:
            raise ValidationError(
                self.env._(
                    "Cannot edit manually contacts in a fully "
                    "synchronized list. Change its sync method or execute "
                    "a manual sync instead."
                )
            )
