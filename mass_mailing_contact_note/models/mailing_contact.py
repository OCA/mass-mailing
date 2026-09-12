from odoo import fields, models


class MailingContact(models.Model):
    _name = "mailing.contact"
    _inherit = ["mailing.contact"]

    note = fields.Text(tracking=True)
