# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from psycopg2 import IntegrityError

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError

ADD_FOOTER_LINK_PARAM = "mass_mailing_tracking_consent.add_footer_link"
DEFAULT_POLICY_PARAM = "mass_mailing_tracking_consent.default_policy"
TOKEN_SCOPE = "mass_mailing_tracking_consent"


class MailingTrackingConsent(models.Model):
    """Consent to the use of tracking pixels and tracked links in emails.

    A record is the explicit choice of a recipient, identified by email
    address. The absence of a record means that no consent was collected:
    tracking is disabled by default.
    """

    _name = "mailing.tracking.consent"
    _description = "Email Tracking Consent"
    _inherit = ["mail.thread"]
    _order = "email_normalized, id"
    _rec_name = "email"

    email = fields.Char(required=True, tracking=True)
    email_normalized = fields.Char(
        compute="_compute_email_normalized",
        store=True,
        index=True,
        readonly=True,
    )
    state = fields.Selection(
        selection=[("granted", "Granted"), ("refused", "Refused")],
        default="refused",
        required=True,
        tracking=True,
    )
    consent_date = fields.Datetime(
        default=fields.Datetime.now,
        readonly=True,
        tracking=True,
        help="Date of the last recorded choice.",
    )
    source = fields.Selection(
        selection=[
            ("manual", "Manual"),
            ("import", "Import"),
            ("link", "Preference Page"),
            ("form", "Subscription Form"),
            ("api", "API"),
            ("other", "Other"),
        ],
        default="manual",
        required=True,
        tracking=True,
    )
    source_details = fields.Char(
        tracking=True,
        help="Free text used to document where the consent was collected.",
    )
    mailing_id = fields.Many2one(
        comodel_name="mailing.mailing",
        string="From Mailing",
        ondelete="set null",
        readonly=True,
        tracking=True,
        help="Mailing from which the consent was last changed, if any.",
    )
    note = fields.Text(
        help="Free text used to keep evidence about the consent.",
    )

    _sql_constraints = [
        (
            "email_normalized_uniq",
            "unique (email_normalized)",
            "A tracking consent already exists for this email address.",
        ),
    ]

    @api.depends("email")
    def _compute_email_normalized(self):
        for consent in self:
            consent.email_normalized = (
                tools.email_normalize(consent.email, strict=False) or False
            )

    @api.constrains("email")
    def _check_email(self):
        for consent in self:
            if not tools.email_normalize(consent.email, strict=False):
                raise ValidationError(
                    _("Invalid email address: %(email)s", email=consent.email or "")
                )

    def _invalidate_tracking_consent_owners(self):
        fields = ["tracking_consent", "tracking_consent_id"]
        self.env["res.partner"].invalidate_model(fields)
        self.env["mailing.contact"].invalidate_model(fields)

    @api.model_create_multi
    def create(self, vals_list):
        consents = super().create(vals_list)
        consents._invalidate_tracking_consent_owners()
        return consents

    def write(self, vals):
        if "state" in vals and any(consent.state != vals["state"] for consent in self):
            vals = dict(vals, consent_date=fields.Datetime.now())
        result = super().write(vals)
        if any(field in vals for field in ("email", "state", "email_normalized")):
            self._invalidate_tracking_consent_owners()
        return result

    def unlink(self):
        result = super().unlink()
        self._invalidate_tracking_consent_owners()
        return result

    def action_grant(self):
        self.write({"state": "granted"})

    def action_refuse(self):
        self.write({"state": "refused"})

    @api.model
    def _get_consent(self, email):
        """Return the consent record for ``email``, if any."""
        email_normalized = tools.email_normalize(email, strict=False)
        if not email_normalized:
            return self.browse()
        return self.sudo().search(
            [("email_normalized", "=", email_normalized)],
            limit=1,
        )

    @api.model
    def _get_consented_emails(self, emails):
        """Return the set of normalized emails that granted consent."""
        normalized = {
            tools.email_normalize(email, strict=False) for email in emails if email
        } - {False}
        if not normalized:
            return set()
        consents = self.sudo().search(
            [
                ("email_normalized", "in", list(normalized)),
                ("state", "=", "granted"),
            ]
        )
        return set(consents.mapped("email_normalized"))

    @api.model
    def _has_consent(self, email):
        """Return whether ``email`` granted consent."""
        return bool(self._get_consented_emails([email]))

    @api.model
    def _set_consent(
        self,
        email,
        state,
        source="manual",
        source_details=False,
        mailing=None,
        note=False,
    ):
        """Record the recipient's choice, creating the record if needed."""
        if state not in dict(self._fields["state"].selection):
            raise ValueError(f"Invalid tracking consent state: {state}")
        email_normalized = tools.email_normalize(email, strict=False)
        if not email_normalized:
            raise ValidationError(
                _("Invalid email address: %(email)s", email=email or "")
            )
        consent = self._get_consent(email_normalized)
        vals = {
            "state": state,
            "source": source,
            "mailing_id": mailing.id if mailing else False,
        }
        if source_details:
            vals["source_details"] = source_details
        if note:
            vals["note"] = note
        if consent:
            consent.write(vals)
        else:
            try:
                with self.env.cr.savepoint():
                    consent = self.sudo().create(dict(vals, email=email_normalized))
            except IntegrityError:
                # Another request created the same consent in the meantime.
                consent = self._get_consent(email_normalized)
                if not consent:
                    raise
                consent.write(vals)
        return consent

    @api.model
    def _is_tracking_allowed(self, email):
        """Return whether tracking is allowed for ``email``.

        Tracking requires an explicit granted consent. The absence of a
        record always means that tracking is denied.
        """
        return self._has_consent(email)

    @api.model
    def _get_token(self, trace_id):
        """Return the HMAC token of a mailing trace for public pages."""
        return tools.hmac(self.env(su=True), TOKEN_SCOPE, trace_id)
