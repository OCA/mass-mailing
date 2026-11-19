# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import BaseCase, tagged

from ..tools import tracking

BASE = "https://erp.example.com"


@tagged("post_install", "-at_install")
class TestTrackingTools(BaseCase):
    def test_host_variants(self):
        self.assertEqual(
            tracking.host_variants([BASE + "/"]),
            ["https://erp.example.com", "http://erp.example.com"],
        )

    def test_strip_open_pixels(self):
        body = (
            '<p>Hi</p><img src="https://erp.example.com/mail/track/12/abc/'
            'blank.gif"/><img src="https://erp.example.com/mail/tracking/'
            'open/db/5/tok/blank.gif" alt=""><img src="https://cdn.x/logo.png">'
        )
        result = tracking.strip_open_pixels(body)
        self.assertNotIn("blank.gif", result)
        self.assertIn("logo.png", result)

    def test_restore_links(self):
        hosts = tracking.host_variants([BASE])
        body = (
            '<a href="https://erp.example.com/r/aB3/m/42">a</a>'
            '<a href="http://erp.example.com/r/Zz9/m/42">b</a>'
            '<a href="https://reddit.com/r/python">c</a>'
        )
        self.assertEqual(tracking.find_short_codes(body, hosts), {"aB3", "Zz9"})
        result = tracking.restore_short_links(
            body, hosts, {"aB3": "https://shop.example.com/?a=1&b=2"}
        )
        self.assertIn('href="https://shop.example.com/?a=1&amp;b=2"', result)
        # unknown code: redirect kept, recipient id removed
        self.assertIn('href="http://erp.example.com/r/Zz9"', result)
        self.assertIn("https://reddit.com/r/python", result)
        self.assertNotIn("/m/42", result)

    def test_restore_does_not_strip_longer_trace_id(self):
        hosts = tracking.host_variants([BASE])
        body = (
            '<a href="https://erp.example.com/r/aB3/m/42">a</a>'
            '<a href="https://erp.example.com/r/aB3/m/420">b</a>'
        )
        result = tracking.restore_short_links(
            body, hosts, {"aB3": "https://shop.example.com/"}
        )
        self.assertNotIn('href="https://erp.example.com/r/aB3/m/42"', result)
        self.assertEqual(result.count('href="https://shop.example.com/"'), 2)
        self.assertNotIn("/m/42", result)

    def test_plain_text(self):
        hosts = tracking.host_variants([BASE])
        _html, text = tracking.remove_tracking(
            "",
            "Go [1] https://erp.example.com/r/aB3/m/42\n",
            hosts,
            {"aB3": "https://shop.example.com/?a=1&b=2"},
        )
        self.assertEqual(text, "Go [1] https://shop.example.com/?a=1&b=2\n")
