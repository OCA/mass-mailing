After installing the module, no tracking pixel or per-recipient tracked link
is added to a mass mailing unless the recipient granted a tracking consent.

Record the consents in *Email Marketing > Configuration > Tracking Consents*,
or import them with the usual import tool. Each record has an email address
and a state:

- *Granted*: tracking is allowed;
- *Refused*: tracking is disabled, but the recipient keeps receiving the
  mailings.

The *Consent to Email Tracking* field is also available on mailing contacts
and partners. It is editable and searchable, so it can be used in mailing
domains, filters and imports. The *Manage*/*Open Consent Record* button opens
the related record with its audit trail.

Each mailing has a *Tracking Privacy* tab:

- *Only recipients who gave consent* (default): the pixel and the
  personalised links are added only for email addresses with a recorded
  consent;
- *Never*: no recipient is tracked individually;
- *Always (exemptions only)*: every recipient is tracked. Use it only for
  communications covered by a legal exemption of the Garante guidelines,
  after assessing the legal basis.

The tab also has an *Add Tracking Preferences Link* option. When the policy is
*Only recipients who gave consent*, the footer link is added to tracked and
non-tracked mailings, so a recipient who has not chosen yet can opt in.

In *Email Marketing > Configuration > Settings* you can set the default
tracking policy and the default footer option for new mailings.

The public page is protected by an opaque HMAC token, without the email
address in the URL. A recipient reaches it from the footer of a mailing.
There, the recipient can stop tracking only, allow tracking again, or
unsubscribe from all emails. The choice is stored and logged, together with
the originating mailing. The token is bound to the mailing trace and does not
expire: links in old emails keep working as long as the trace is kept, and
stop working when the trace is purged. A forwarded email can be used to change
the recipient's choice, so keep the trace and the consent audit as evidence.

The module deliberately provides no global switch to bypass consent. If a
mailing falls under one of the legal exemptions, select the *Always
(exemptions only)* policy on that mailing or use Odoo's regular email
templates, which do not add a tracking pixel. The module does not assess the
legal basis of a specific mailing: that remains the controller's decision.
