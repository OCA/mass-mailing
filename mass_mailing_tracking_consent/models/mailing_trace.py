# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class MailingTrace(models.Model):
    _inherit = "mailing.trace"

    def _is_tracking_allowed(self):
        """Return whether tracking is allowed by the mailing policy."""
        self.ensure_one()
        policy = self.mass_mailing_id.tracking_policy or "consent"
        if policy == "none":
            return False
        if policy == "always":
            return True
        return self.env["mailing.tracking.consent"]._is_tracking_allowed(self.email)
