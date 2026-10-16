from odoo import fields, models


class MailingContact(models.Model):
    _name = "mailing.contact"
    _inherit = ["mailing.contact"]

    mobile = fields.Char(tracking=True)
