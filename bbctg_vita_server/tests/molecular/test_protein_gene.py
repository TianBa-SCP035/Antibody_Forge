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


def _item(name, heavy=(), light=(), genes=()):
    return {
        "input_protein_name": name,
        "protein_name": name,
        "beacon": {"heavy_chain_names": list(heavy), "light_chain_names": list(light), "matched": bool(heavy)},
        "ngs": {"gene_names": list(genes), "matched": bool(genes)},
    }


def _body(heavy=(), light=(), genes=(), code=20000, protein="x"):
    return {"code": code, "data": _item(protein, heavy, light, genes)}


def _batch(*items, code=20000):
    return {"code": code, "data": {"items": list(items)}}


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
        self.assertIn("没有和这个蛋白名称对上", result(_body(genes=["G1", "G2"])["data"]))
        self.assertIsNone(result(_body()["data"]))
        heavy_only = "20R062_RNBK01AAAYP5"
        self.assertEqual(
            result(_body(genes=[f"Vh1$0-{heavy_only}"], protein=heavy_only)["data"]),
            (f"Vh1$0-{heavy_only}", None),
        )
        combined = "20R891_RLBKS1AAAD4B_h1.0"
        combined_gene = "Vh1.0VKB-20R891_RLBKS1AAAD4B"
        self.assertEqual(
            result(_body(genes=[combined_gene, "Vh1.0VKB-20R891_OTHER"], protein=combined)["data"]),
            (combined_gene, None),
        )
        many = result(_body(
            genes=[f"Vh1$0-{heavy_only}", f"Vh1.0-{heavy_only}"],
            protein=heavy_only,
        )["data"])
        self.assertIn("多条基因名", many)
        self.assertNotIn("OTHER", many)

    def test_lookup_posts_names_and_matches_input_protein_name(self):
        body = _batch(
            _item("p3", genes=["G3"]),
            _item("P1", ["VH1"], ["VK1"]),
            _item("P2"),
        )
        with patch.object(protein_gene.requests, "post", return_value=_response(body=body)) as post:
            found, issues = protein_gene.lookup(["P1", "P2", "P3", "P1"])
        self.assertEqual(found, {"P1": ("VH1", "VK1")})
        self.assertEqual(list(issues), ["P3"])
        self.assertNotIn("P2", found)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args.args[0], "http://gene.test/api")
        self.assertEqual(post.call_args.kwargs["json"], {"protein_names": ["P1", "P2", "P3"]})
        self.assertEqual(post.call_args.kwargs["headers"], {"X-API-Key": "k"})

    def test_lookup_splits_batches_of_500(self):
        with patch.object(protein_gene, "BATCH_SIZE", 2), patch.object(
            protein_gene.requests, "post", return_value=_response(body=_batch())
        ) as post:
            protein_gene.lookup(["A", "B", "C"])
        self.assertEqual(
            [call.kwargs["json"]["protein_names"] for call in post.call_args_list],
            [["A", "B"], ["C"]],
        )

    def test_bad_key_error_code_or_network_makes_whole_batch_unavailable(self):
        bad_key = _response(status=401, body={"code": 401, "data": {}, "message": "接口密钥无效"})
        with patch.object(protein_gene.requests, "post", return_value=bad_key):
            with self.assertRaisesRegex(protein_gene.ProteinGeneUnavailable, "密钥无效"):
                protein_gene.lookup(["P1"])
        failed = _response(body={"code": 50000, "data": {}, "message": "数据库异常"})
        with patch.object(protein_gene.requests, "post", return_value=failed):
            with self.assertRaisesRegex(protein_gene.ProteinGeneUnavailable, "50000 数据库异常"):
                protein_gene.lookup(["P1"])
        with patch.object(protein_gene.requests, "post", side_effect=requests.ConnectionError()):
            with self.assertRaisesRegex(protein_gene.ProteinGeneUnavailable, "连不上"):
                protein_gene.lookup(["P1"])
        with patch.object(protein_gene.requests, "post", return_value=_response(body={"code": 20000, "data": {}})):
            with self.assertRaisesRegex(protein_gene.ProteinGeneUnavailable, "格式不对"):
                protein_gene.lookup(["P1"])
        with patch.object(get_settings(), "protein_gene_api_key", ""):
            with self.assertRaisesRegex(protein_gene.ProteinGeneUnavailable, "没有配置"):
                protein_gene.lookup(["P1"])
        self.assertEqual(protein_gene.lookup([]), ({}, {}))
