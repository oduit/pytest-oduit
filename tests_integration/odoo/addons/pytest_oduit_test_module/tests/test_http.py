try:
    from odoo.addons.base.tests.common import HttpCaseWithUserDemo as HttpCase
except ImportError:
    from odoo.tests.common import HttpCase


class TestModuleHttp(HttpCase):
    def test_pytest_oduit_endpoint(self):
        self.authenticate("demo", "demo")
        result = self.url_open("/pytest-oduit/test", allow_redirects=False)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.text, "Hello World")
