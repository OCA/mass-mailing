# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Mass Mailing Tracking Consent",
    "summary": "Send mass mailings without tracking pixels unless the "
    "recipient consented",
    "version": "18.0.1.0.0",
    "category": "Marketing/Email Marketing",
    "website": "https://github.com/OCA/mass-mailing",
    "author": "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "development_status": "Alpha",
    "depends": ["mass_mailing"],
    "data": [
        "security/ir.model.access.csv",
        "templates/tracking_consent_templates.xml",
        "views/mailing_tracking_consent_views.xml",
        "views/mailing_mailing_views.xml",
        "views/mailing_contact_views.xml",
        "views/res_partner_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "images": ["static/description/icon.png"],
}
