This module makes mass mailings comply with the Italian rules on tracking
pixels in email, from the point of view of the Odoo deployer.

Odoo 18 always adds a per-recipient tracking pixel to mass mailings and
tracks link clicks per recipient. It has no per-recipient switch, so a mailing
is either fully tracked or not sent. This is not compatible with the Italian
Data Protection Authority (Garante privacy) guidelines on tracking pixels in
email communications (Provvedimento n. 284 of 17 April 2026, published in the
Gazzetta Ufficiale n. 98 of 29 April 2026), which require prior, informed and
specific consent and allow the recipient to withdraw only the tracking
consent while continuing to receive the emails.

With this module:

- tracking is disabled by default; a pixel and tracked links are included
  only when the recipient granted a tracking consent;
- the recipient's choice is stored per email address, with date, source,
  originating mailing and an audit trail in the chatter;
- the consent is directly editable and searchable on mailing contacts and
  partners, so it can be used in mailing domains, filters and imports;
- every mailing has its own tracking policy: only consenting recipients
  (default), never, or always for communications covered by a legal
  exemption;
- every tracked or non-tracked mailing can contain a footer link to a public
  page where the recipient can give or withdraw the tracking consent, or
  unsubscribe from all emails;
- the footer link is protected by an opaque HMAC token; the email address is
  not included in the URL;
- when tracking is denied, the core pixel, the OCA ``mail_tracking`` pixel
  and the per-recipient click suffix are removed from both the HTML and the
  plain-text body, and the short links are replaced by their original
  destination URL;
- pixels already delivered stop recording openings after the consent is
  withdrawn, and tracked links stop recording clicks.

The module does not replace the privacy notice: the deployer must still
describe the tracking pixel, its purposes and the retention period in the
privacy policy, and must keep the unsubscribe link in the mailing footer.
