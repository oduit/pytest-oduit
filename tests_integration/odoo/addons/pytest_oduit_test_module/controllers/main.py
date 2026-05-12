from odoo import http


class PytestOduitTestController(http.Controller):
    @http.route("/pytest-oduit/test", auth="user", type="http")
    def test(self):
        return "Hello World"
