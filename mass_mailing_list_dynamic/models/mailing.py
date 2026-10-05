# Copyright 2017 Tecnativa - Jairo Llopis
# Copyright 2020 Hibou Corp. - Jared Kipe
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MassMailing(models.Model):
    _inherit = "mailing.mailing"

    def action_launch(self):
        # Do the sync prior to putting the mailing in queue. Otherwise, if an error
        # raises, the user won't be able to detect it and the Mass Mailing queue cron
        # will be blocked forever.
        self.contact_list_ids.action_sync()
        return super().action_launch()

    def _get_remaining_recipients(self):
        recipient_ids = super()._get_remaining_recipients()
        if not recipient_ids:
            return recipient_ids

        if self.mailing_model_real != "mailing.contact":
            return recipient_ids

        duplicate_ids = set(
            self.env["mailing.contact"]
            .sudo()
            .search(
                [
                    ("id", "in", recipient_ids),
                    ("duplicated_partner_id", "!=", False),
                ]
            )
            .ids
        )

        return [
            recipient_id
            for recipient_id in recipient_ids
            if recipient_id not in duplicate_ids
        ]
