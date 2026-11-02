from unittest import TestCase
from unittest.mock import MagicMock, patch

import requests
from fastapi import HTTPException

from modules.auth.service import login_with_yunzhijia_ticket


class YunzhijiaLoginTest(TestCase):
    def test_empty_context_is_unauthorized(self):
        client = MagicMock()
        client.acquire_user_context.return_value = {"success": False, "data": None}
        with patch("modules.auth.service.YunzhijiaClient", return_value=client):
            with self.assertRaises(HTTPException) as raised:
                login_with_yunzhijia_ticket(MagicMock(), "used-ticket")
        self.assertEqual(raised.exception.status_code, 401)
        self.assertIn("openid", raised.exception.detail)

    def test_upstream_error_is_unauthorized(self):
        client = MagicMock()
        client.acquire_user_context.side_effect = requests.Timeout("slow")
        with patch("modules.auth.service.YunzhijiaClient", return_value=client):
            with self.assertRaises(HTTPException) as raised:
                login_with_yunzhijia_ticket(MagicMock(), "ticket")
        self.assertEqual(raised.exception.status_code, 401)
