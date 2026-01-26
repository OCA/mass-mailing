# Copyright 2017 Tecnativa - Jairo Llopis
# Copyright 2019 Tecnativa - Victor M.M. Torres
# Copyright 2020 Hibou Corp. - Jared Kipe
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MassMailingContact(models.Model):
    _inherit = "mailing.contact"

    in_fully_synced_lists = fields.Boolean(compute="_compute_in_fully_synced_lists")

    def write(self, vals):
        _self = self.with_context(old_lists={one.id: one.list_ids.ids for one in self})
        return super(MassMailingContact, _self).write(vals)

    @api.depends("list_ids.dynamic", "list_ids.sync_method")
    def _compute_in_fully_synced_lists(self):
        for one in self:
            one.in_fully_synced_lists = (True, "full") in one.list_ids.mapped(
                lambda list: (list.dynamic, list.sync_method)
            )

    @api.constrains("list_ids")
    def _check_no_list_edits_on_fully_synced_lists(self):
        # All is allowed during automatic syncs
        if self.env.context.get("syncing"):
            return
        for one in self:
            # Find changed lists
            previous_list_ids = set(
                self.env.context.get("old_lists", {}).get(one.id, set())
            )
            new_list_ids = set(one.list_ids.ids)
            changed_lists_ids = one.env["mailing.list"].browse(
                previous_list_ids ^ new_list_ids
            )
            # Filter fully synced ones
            full_synced_changed_lists = changed_lists_ids.filtered_domain(
                [
                    ("dynamic", "=", True),
                    ("sync_method", "=", "full"),
                ]
            )
            # Fail if manually changing fully synced status
            if full_synced_changed_lists:
                raise ValidationError(
                    one.env._(
                        "Cannot edit manually fully synchronized lists in the contact. "
                        "Change its sync method or execute a manual sync instead."
                    )
                )
