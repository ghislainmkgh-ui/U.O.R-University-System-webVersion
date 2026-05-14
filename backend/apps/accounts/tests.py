from django.test import SimpleTestCase


class BackendSmokeTests(SimpleTestCase):
    """Fast checks for public routes and auth protection."""

    def assert_json(self, response, status_code, *, success=None, code=None):
        self.assertEqual(response.status_code, status_code)
        payload = response.json()
        if success is not None:
            self.assertEqual(payload.get("success"), success)
        if code is not None:
            self.assertEqual(payload.get("code"), code)
        return payload

    def test_health_endpoint_is_public(self):
        response = self.client.get("/api/health/")
        payload = self.assert_json(response, 200, success=True)
        self.assertEqual(payload["data"]["status"], "healthy")

    def test_partner_health_endpoint_is_public(self):
        response = self.client.get("/api/v1/health/")
        payload = self.assert_json(response, 200, success=True)
        self.assertEqual(payload["data"]["service"], "U.O.R Transfer API")

    def test_login_rejects_missing_credentials(self):
        response = self.client.post("/api/auth/login/", data={}, content_type="application/json")
        self.assert_json(response, 400, success=False, code="missing_credentials")

    def test_login_rejects_wrong_method(self):
        response = self.client.get("/api/auth/login/")
        self.assert_json(response, 405, success=False, code="method_not_allowed")

    def test_me_requires_token(self):
        response = self.client.get("/api/auth/me/")
        self.assert_json(response, 401, success=False, code="auth_required")

    def test_admin_routes_require_token(self):
        protected_routes = [
            "/api/dashboard/summary/",
            "/api/students/",
            "/api/finance/overview/",
            "/api/access/logs/",
            "/api/transfers/pending/",
            "/api/notifications/status/",
            "/api/reports/summary/",
            "/api/academics/students/1/summary/",
            "/api/academics/students/1/records/",
            "/api/academics/students/1/documents/",
        ]
        for route in protected_routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assert_json(response, 401, success=False, code="auth_required")

    def test_access_code_routes_validate_payload_before_database_work(self):
        routes = ["/api/access/validate-code/", "/validate_code/", "/verify_code/"]
        for route in routes:
            with self.subTest(route=route):
                response = self.client.post(route, data={}, content_type="application/json")
                self.assert_json(response, 400, success=False, code="missing_code")

    def test_partner_transfer_routes_require_partner_token(self):
        routes = ["/api/v1/transfer/receive/", "/api/v1/transfer/send/"]
        for route in routes:
            with self.subTest(route=route):
                response = self.client.post(route, data={}, content_type="application/json")
                self.assert_json(response, 401, success=False, code="missing_api_token")

    def test_partner_token_rejects_missing_credentials(self):
        response = self.client.post("/api/v1/auth/token/", data={}, content_type="application/json")
        self.assert_json(response, 400, success=False, code="missing_partner_credentials")
