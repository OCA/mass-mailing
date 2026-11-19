# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class MailingContact(models.Model):
    _name = "mailing.contact"
    _inherit = ["mailing.contact", "mailing.tracking.consent.owner"]
