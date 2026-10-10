import json
from unittest import TestCase

from requests import Response

from integrations.labillion import LabillionError, _parse_labillion_response


def _response(payload):
    response = Response()
    response.status_code = 200
    response._content = json.dumps(payload).encode()
    return response


class LabillionResponseTest(TestCase):
    def test_code_minus_one_uses_detail(self):
        payload = {
            "data": {
                "isSuccess": False,
                "detail": "订单类型不存在：TITER",
                "dispatchId": "DSP260806117433",
                "orderName": "25D254501-PTGIR-效价检测",
                "orderType": "TITER",
            },
            "code": -1,
            "message": "订单类型不存在",
        }
        with self.assertRaises(LabillionError) as raised:
            _parse_labillion_response(_response(payload))
        self.assertEqual(str(raised.exception), "订单类型不存在：TITER")

    def test_success_false_inside_data_is_failure(self):
        payload = {"code": 200, "message": "ok", "data": {"isSuccess": False, "detail": "二抗不支持"}}
        with self.assertRaises(LabillionError) as raised:
            _parse_labillion_response(_response(payload))
        self.assertEqual(str(raised.exception), "二抗不支持")

    def test_success_returns_data(self):
        self.assertEqual(_parse_labillion_response(_response({"code": 200, "data": "token"})), "token")
