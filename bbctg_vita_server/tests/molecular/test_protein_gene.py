"""蛋白基因名接口：返回体解析和出错时整批不可用。"""

import unittest
from unittest.mock import MagicMock, patch

import requests

from core.config import get_settings
from integrations import protein_gene


def _response(status=200, body=None):
    response = MagicMock(status_code=status)
    response.json.return_value = body
    return response


def _body(heavy=(), light=(), genes=(), code=20000):
    return {
        "code": code,
        "data": {
            "beacon": {"heavy_chain_names": list(heavy), "light_chain_names": list(light), "matched": bool(heavy)},
            "ngs": {"gene_names": list(genes), "matched": bool(genes)},
            "protein_name": "x",
        },
    }


class ProteinGeneTests(unittest.TestCase):
    def setUp(self):
        settings = get_settings()
        for name, value in (("protein_gene_api_url", "http://gene.test/api"), ("protein_gene_api_key", "k")):
            patcher = patch.object(settings, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_uses_beacon_chains_and_reports_what_cannot_be_used(self):
        result = protein_gene._result
        self.assertEqual(
            result(_body(["Vh1.0-25R154_RMCWD03B04.1"], ["VhK.0-25R154_RMCWD03B04.1"])["data"]),
            ("Vh1.0-25R154_RMCWD03B04.1", "VhK.0-25R154_RMCWD03B04.1"),
        )
        self.assertEqual(result(_body(["VH1"])["data"]), ("VH1", None))
        self.assertIn("多条重链（VH1、VH2）", result(_body(["VH1", "VH2"], ["VK1"])["data"]))
        self.assertIn("多条轻链", result(_body(["VH1"], ["VK1", "VK2"])["data"]))
        self.assertIn("NGS 查到基因名 G1、G2", result(_body(genes=["G1", "G2"])["data"]))
        self.assertIsNone(result(_body()["data"]))

    def test_lookup_splits_found_and_issues_and_sends_key(self):
        bodies = {
            "P1": _response(body=_body(["VH1"], ["VK1"])),
            "P2": _response(body=_body()),
            "P3": _response(body=_body(genes=["G3"])),
        }
        with patch.object(
            protein_gene.requests, "get", side_effect=lambda url, params, headers, timeout: bodies[params["protein_name"]]
        ) as get:
            found, issues = protein_gene.lookup(["P1", "P2", "P3", "P1"])
        self.assertEqual(found, {"P1": ("VH1", "VK1")})
        self.assertEqual(list(issues), ["P3"])
        self.assertEqual(get.call_count, 3)
        self.assertEqual(get.call_args.kwargs["headers"], {"X-API-Key": "k"})

    def test_bad_key_error_code_or_network_makes_whole_batch_unavailable(self):
        bad_key = _response(status=401, body={"code": 401, "data": {}, "message": "接口密钥无效"})
        with patch.object(protein_gene.requests, "get", return_value=bad_key):
            with self.assertRaisesRegex(protein_gene.ProteinGeneUnavailable, "密钥无效"):
                protein_gene.lookup(["P1"])
        failed = _response(body={"code": 50000, "data": {}, "message": "数据库异常"})
        with patch.object(protein_gene.requests, "get", return_value=failed):
            with self.assertRaisesRegex(protein_gene.ProteinGeneUnavailable, "50000 数据库异常"):
                protein_gene.lookup(["P1"])
        with patch.object(protein_gene.requests, "get", side_effect=requests.ConnectionError()):
            with self.assertRaisesRegex(protein_gene.ProteinGeneUnavailable, "连不上"):
                protein_gene.lookup(["P1"])
        with patch.object(get_settings(), "protein_gene_api_key", ""):
            with self.assertRaisesRegex(protein_gene.ProteinGeneUnavailable, "没有配置"):
                protein_gene.lookup(["P1"])
        self.assertEqual(protein_gene.lookup([]), ({}, {}))
