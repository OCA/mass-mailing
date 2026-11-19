# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
"""Helpers that remove per-recipient tracking from outgoing email bodies.

Two mechanisms are handled:

* open tracking: the 1x1 GIF added by ``mass_mailing``
  (``/mail/track/<mail_id>/<token>/blank.gif``) and the pixel added by the
  OCA ``mail_tracking`` module (``/mail/tracking/open/...``);
* click tracking: links shortened by ``link_tracker``
  (``<base_url>/r/<code>``) with the recipient trace suffix
  (``/m/<trace_id>``) added by ``mass_mailing``. They are replaced by the
  original destination URL.

The module is kept free of Odoo imports so that it can be unit tested in
isolation and reused by other modules.
"""

import html
import re

PIXEL_RE = re.compile(
    r"<img\b[^>]*?\bsrc\s*=\s*([\"'])[^\"']*?/mail/track(?:ing/open)?/"
    r"[^\"']*?\1[^>]*>",
    re.IGNORECASE,
)


def host_variants(urls):
    """Return base URLs without trailing slash, in http and https forms."""
    hosts = set()
    for url in urls:
        if not url:
            continue
        url = url.strip().rstrip("/")
        hosts.add(url)
        if url.startswith("https://"):
            hosts.add("http://" + url[len("https://") :])
        elif url.startswith("http://"):
            hosts.add("https://" + url[len("http://") :])
    return sorted(hosts, key=len, reverse=True)


def short_link_re(hosts):
    """Return a regex matching short links of ``hosts`` with optional trace."""
    hosts = [host for host in hosts if host]
    if not hosts:
        return None
    alternatives = "|".join(
        re.escape(host) for host in sorted(hosts, key=len, reverse=True)
    )
    return re.compile(
        rf"(?P<short>(?:{alternatives})/r/(?P<code>[A-Za-z0-9]+))"
        r"(?P<trace>/m/\d+)?(?![A-Za-z0-9/])"
    )


def strip_open_pixels(body):
    """Remove the core and ``mail_tracking`` open pixels from HTML."""
    if not body:
        return body
    return PIXEL_RE.sub("", body)


def find_short_codes(text, hosts):
    """Return the short-link codes found in ``text`` for ``hosts``."""
    regex = short_link_re(hosts)
    if not text or regex is None:
        return set()
    return {match.group("code") for match in regex.finditer(text)}


def restore_short_links(text, hosts, code_to_url, escape_html=True):
    """Replace tracked short links by their original destination URL.

    When the code is unknown, keep the short link but remove the
    per-recipient ``/m/<trace_id>`` suffix.
    """
    regex = short_link_re(hosts)
    if not text or regex is None:
        return text

    def _replace(match):
        url = code_to_url.get(match.group("code"))
        if not url:
            return match.group("short")
        return html.escape(url, quote=True) if escape_html else url

    return regex.sub(_replace, text)


def remove_tracking(body_html, body_text, hosts, code_to_url):
    """Return ``(body_html, body_text)`` without per-recipient tracking."""
    if body_html:
        body_html = strip_open_pixels(body_html)
        body_html = restore_short_links(body_html, hosts, code_to_url, escape_html=True)
    if body_text:
        body_text = restore_short_links(
            body_text, hosts, code_to_url, escape_html=False
        )
    return body_html, body_text
