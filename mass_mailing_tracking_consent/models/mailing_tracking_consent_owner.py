# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models, tools
from odoo.exceptions import AccessError
from odoo.osv import expression


class MailingTrackingConsentOwner(models.AbstractModel):
    """Add tracking consent information to models holding an email address."""

    _name = "mailing.tracking.consent.owner"
    _description = "Mailing Tracking Consent Owner"

    tracking_consent_id = fields.Many2one(
        "mailing.tracking.consent",
        compute="_compute_tracking_consent",
        string="Tracking Consent Record",
        groups="mass_mailing.group_mass_mailing_user",
    )
    tracking_consent = fields.Selection(
        selection=[("granted", "Granted"), ("refused", "Refused")],
        compute="_compute_tracking_consent",
        inverse="_inverse_tracking_consent",
        search="_search_tracking_consent",
        string="Consent to Email Tracking",
        groups="mass_mailing.group_mass_mailing_user",
        help="Consent to individual tracking of opens and clicks of mass "
        "mailings, stored per email address. Clearing the field does not "
        "delete the recorded choice; select Refused to withdraw it.",
    )

    @api.depends("email")
    def _compute_tracking_consent(self):
        consent_model = self.env["mailing.tracking.consent"].sudo()
        normalized = [
            (
                record,
                tools.email_normalize(record.email, strict=False)
                if record.email
                else False,
            )
            for record in self
        ]
        emails = [email for __record, email in normalized if email]
        consents = (
            consent_model.search([("email_normalized", "in", emails)])
            if emails
            else consent_model.browse()
        )
        consents_by_email = {consent.email_normalized: consent for consent in consents}
        empty = consent_model.browse()
        for record, email in normalized:
            consent = consents_by_email.get(email, empty) if email else empty
            record.tracking_consent_id = consent
            record.tracking_consent = consent.state if consent else False

    def _inverse_tracking_consent(self):
        if not self.env.user.has_group("mass_mailing.group_mass_mailing_user"):
            raise AccessError(
                _("You are not allowed to change email tracking consent.")
            )
        consent_model = self.env["mailing.tracking.consent"]
        for record in self.filtered("email"):
            if record.tracking_consent:
                consent_model._set_consent(
                    record.email,
                    record.tracking_consent,
                    source="manual",
                )

    def _search_tracking_consent(self, operator, value):
        if operator not in ("=", "!=", "in", "not in"):
            raise NotImplementedError(operator)
        consent_model = self.env["mailing.tracking.consent"].sudo()
        all_records = consent_model.search([])
        all_emails = all_records.mapped("email_normalized")
        all_states = [
            state for state, __label in consent_model._fields["state"].selection
        ]
        emails_by_state = {
            state: set(
                all_records.filtered(
                    lambda consent, state=state: consent.state == state
                ).mapped("email_normalized")
            )
            for state in all_states
        }
        values = value if isinstance(value, list | tuple | set) else [value]
        wanted_states = [state for state in values if state]
        want_empty = any(state is False for state in values)

        def _domain(emails, include_empty):
            terms = []
            if emails:
                terms.append([("email_normalized", "in", list(emails))])
            if include_empty:
                terms.append(
                    [
                        "|",
                        ("email_normalized", "=", False),
                        ("email_normalized", "not in", all_emails),
                    ]
                )
            return expression.OR(terms) if terms else [("id", "=", 0)]

        if operator in ("=", "in"):
            emails = set()
            for state in wanted_states:
                emails |= emails_by_state[state]
            return _domain(emails, want_empty)

        excluded_states = [state for state in all_states if state not in wanted_states]
        emails = set()
        for state in excluded_states:
            emails |= emails_by_state[state]
        return _domain(emails, not want_empty)

    def action_open_tracking_consent(self):
        self.ensure_one()
        consent = self.env["mailing.tracking.consent"]._get_consent(self.email)
        action = {
            "type": "ir.actions.act_window",
            "res_model": "mailing.tracking.consent",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }
        if consent:
            action["res_id"] = consent.id
        else:
            action["context"] = {
                "default_email": self.email,
                "default_source": "manual",
            }
        return action
