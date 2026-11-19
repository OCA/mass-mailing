# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models

from .mailing_mailing import POLICIES
from .mailing_tracking_consent import (
    ADD_FOOTER_LINK_PARAM,
    DEFAULT_POLICY_PARAM,
)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mass_mailing_tracking_policy = fields.Selection(
        selection=POLICIES,
        string="Default Tracking Policy",
        config_parameter=DEFAULT_POLICY_PARAM,
        default="consent",
        help="Default open/click tracking policy for new mailings. Change it "
        "on a single mailing when it falls under a legal exemption.",
    )
    mass_mailing_tracking_consent_footer = fields.Boolean(
        string="Add Tracking Preferences Link by Default",
        config_parameter=ADD_FOOTER_LINK_PARAM,
        default=True,
        help="Default for new mailings: add a footer link to the public page "
        "where recipients can give or withdraw their tracking consent.",
    )
