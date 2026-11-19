# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import werkzeug.urls

from odoo import api, fields, models, tools

from .mailing_tracking_consent import (
    ADD_FOOTER_LINK_PARAM,
    DEFAULT_POLICY_PARAM,
)

POLICIES = [
    ("consent", "Only recipients who gave consent"),
    ("none", "Never"),
    ("always", "Always (exemptions only)"),
]


class MailingMailing(models.Model):
    _inherit = "mailing.mailing"

    tracking_policy = fields.Selection(
        selection=POLICIES,
        string="Open/click tracking",
        required=True,
        default=lambda self: self._default_tracking_policy(),
        help="Only recipients who gave consent: the tracking pixel and the "
        "personalised links are added only for email addresses with a "
        "recorded consent (default).\n"
        "Never: no recipient is tracked individually.\n"
        "Always: every recipient is tracked. Use it only for communications "
        "falling within an exemption of the Garante guidelines.",
    )
    tracking_consent_footer = fields.Boolean(
        string="Add Tracking Preferences Link",
        default=lambda self: self._default_tracking_consent_footer(),
        help="Append a link where the recipient can give or withdraw consent "
        "to tracking, without unsubscribing.",
    )

    @api.model
    def _default_tracking_policy(self):
        policy = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(DEFAULT_POLICY_PARAM, "consent")
        )
        return policy if policy in dict(POLICIES) else "consent"

    @api.model
    def _default_tracking_consent_footer(self):
        return tools.str2bool(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(ADD_FOOTER_LINK_PARAM, "True"),
            True,
        )

    def _get_tracking_consent_url(self, trace):
        """Return the public page where the trace recipient manages tracking."""
        self.ensure_one()
        trace.ensure_one()
        token = self.env["mailing.tracking.consent"]._get_token(trace.id)
        return werkzeug.urls.url_join(
            self._get_recipient_base_url(),
            f"mailing/tracking_consent/{trace.id}/{token}",
        )
