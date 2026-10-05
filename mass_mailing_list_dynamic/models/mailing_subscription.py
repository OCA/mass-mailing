# Copyright 2024
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MailingSubscription(models.Model):
    _inherit = "mailing.subscription"

    def write(self, vals):
        result = super().write(vals)
        if (
            "opt_out" not in vals
            or not vals["opt_out"]
            or self.env.context.get("bypass_optout_sync")
        ):
            return result

        Contact = self.env["mailing.contact"].sudo()
        Subscription = self.env["mailing.subscription"].sudo()

        for subscription in self:
            email_normalized = subscription.contact_id.email_normalized
            if not email_normalized:
                continue

            matching_contacts = Contact.search(
                [
                    ("email_normalized", "=", email_normalized),
                    ("id", "!=", subscription.contact_id.id),
                ]
            )
            if not matching_contacts:
                continue

            matching_subscriptions = Subscription.search(
                [
                    ("contact_id", "in", matching_contacts.ids),
                    ("list_id", "=", subscription.list_id.id),
                    ("opt_out", "=", False),
                    ("id", "!=", subscription.id),
                ]
            )

            if matching_subscriptions:
                matching_subscriptions.with_context(bypass_optout_sync=True).write(
                    {"opt_out": True}
                )

        return result
