"""发现合成与验证进度：状态机、权限认领、列表筛选与排队并发。"""

from datetime import datetime, timedelta
from unittest.mock import patch

from sqlalchemy import event, select, update

from core.errors import ConflictError, ForbiddenError
from models.discovery import DiscoverySynthesisOrder
from models.supernatant import SynthesisSupernatantWell
from models.target import Target
from modules.discovery.synthesis_progress import one_sync, service
from support import DbTestCase

TABLES = (Target, DiscoverySynthesisOrder, SynthesisSupernatantWell)
FIXED_NOW = datetime(2026, 11, 17, 10, 0, 0)


class SynthesisStatusMachineTests(DbTestCase):
    tables = TABLES

    def _completed_secreted_order(self):
        row = service.save(
            self.db,
            {
                "target_name": "IL-2",
                "target_type": "分泌型",
                "order_no": "CN2602120001585",
                "arrival_date": "2026-03-17",
                "affinity_date": "2026-03-26",
            },
            created_by="测试员",
        )
        self.assertEqual(row["flow_status"], "流式不适用")
        self.assertEqual(row["status"], "已完成")
        return row

    def test_create_and_auto_advance_through_arrival_and_assays(self):
        row = service.save(
            self.db,
            {
                "target_name": "B7-H4",
                "target_codes": ["20R015"],
                "mouse_strain": ["RNKO", "RN"],
                "synthesis_code": "20R015_RNBK01",
                "synthetic_count": "118",
                "synthetic_date": "2026-02-12",
            },
            created_by="测试员",
        )
        self.assertEqual(row["status"], "待下单")
        self.assertEqual(row["target_name"], "B7-H4")
        self.assertEqual(row["target_codes"], ["20R015"])
        self.assertEqual(row["mouse_strain"], "RN、RNKO")
        self.assertIsNone(row["owner"])
        self.assertEqual(row["synthetic_count"], 118)
        self.assertEqual(row["synthetic_date"], "2026-02-12")

        row = service.save(self.db, {"id": row["id"], "order_no": "CN2602120001585"})
        self.assertEqual(row["status"], "合成中")

        row = service.save(
            self.db,
            {"id": row["id"], "arrival_count": 113, "arrival_date": "2026-03-17"},
        )
        self.assertEqual(row["status"], "待检测")
        self.assertEqual(row["affinity_status"], "亲和力待检测")
        self.assertEqual(row["flow_status"], "流式待检测")

        row = service.save(
            self.db,
            {"id": row["id"], "affinity_status": "亲和力检测中"},
            created_by="张赞 Zan Zhang",
            scopes=frozenset({"affinity"}),
        )
        self.assertEqual(row["status"], "检测中")
        self.assertEqual(row["affinity_status"], "亲和力检测中")
        self.assertEqual(row["affinity_owner"], "张赞")

        row = service.save(
            self.db,
            {
                "id": row["id"],
                "affinity_date": "2026-03-25",
                "report_reason": "抗原重检",
                "selection_method": ["JX_P", "补挑"],
            },
        )
        self.assertEqual((row["selection_method"], row["is_rechoose"]), ("JX_P", "是"))
        self.assertEqual(row["status"], "待检测")
        self.assertEqual(row["affinity_status"], "亲和力待检测")
        self.assertEqual(row["affinity_owner"], "张赞")

        row = service.save(
            self.db,
            {"id": row["id"], "report_reason": None, "affinity_date": "2026-03-26"},
        )
        self.assertEqual(row["status"], "检测中")
        self.assertEqual(row["affinity_status"], "亲和力已完成")
        self.assertEqual(row["flow_status"], "流式待检测")
        self.assertIsNone(row["affinity_result"])

        row = service.save(self.db, {"id": row["id"], "flow_date": "2026-03-28"})
        self.assertEqual(row["flow_status"], "流式已完成")
        self.assertEqual(row["status"], "已完成")

    def test_manual_assay_completion_without_dates_keeps_completed(self):
        row = service.save(
            self.db,
            {"target_name": "CD6", "eng_requirement": "提高Tm"},
            created_by="兰维秋",
            scopes=frozenset({"pm"}),
        )
        manual = service.save(
            self.db,
            {"id": row["id"], "affinity_status": "亲和力已完成", "flow_status": "流式已完成"},
            created_by="兰维秋",
            scopes=frozenset({"affinity", "flow"}),
        )
        self.assertEqual(manual["status"], "已完成")
        manual = service.save(self.db, {"id": row["id"], "remark": "手工状态保持"})
        self.assertEqual(manual["status"], "已完成")

    def test_target_type_change_reopens_or_completes_order(self):
        row = self._completed_secreted_order()
        # 改成非分泌型后要补流式，已完成不能再保留
        row = service.save(self.db, {"id": row["id"], "target_type": "I型跨膜"})
        self.assertEqual(row["flow_status"], "流式待检测")
        self.assertEqual(row["status"], "检测中")
        self.assertIsNotNone(row["sort_order"])

        row = service.save(self.db, {"id": row["id"], "target_type": "分泌型"})
        self.assertEqual(row["flow_status"], "流式不适用")
        self.assertEqual(row["status"], "已完成")

        # 同值回写不算靶点类型变化，已完成保持
        row = service.save(self.db, {"id": row["id"], "target_type": "分泌型", "remark": "复核"})
        self.assertEqual(row["status"], "已完成")

    def test_assay_status_checks_use_values_from_same_payload(self):
        row = service.save(
            self.db,
            {"target_name": "B7-H4", "order_no": "CN1", "arrival_date": "2026-03-17", "report_reason": "抗原重检"},
            created_by="测试员",
        )
        with self.assertRaisesRegex(ValueError, "请先清除未出报告原因"):
            service.save(self.db, {"id": row["id"], "affinity_status": "亲和力检测中"}, created_by="张赞")

        row = service.save(
            self.db,
            {"id": row["id"], "report_reason": None, "affinity_status": "亲和力检测中"},
            created_by="张赞",
        )
        self.assertEqual(row["affinity_status"], "亲和力检测中")
        self.assertIsNone(row["affinity_owner"])

        with self.assertRaisesRegex(ValueError, "分泌型靶点不需要流式实验"):
            service.save(self.db, {"id": row["id"], "target_type": "分泌型", "flow_status": "流式待检测"})

    def test_multipass_skips_affinity_and_completes_when_flow_finishes(self):
        row = service.save(
            self.db,
            {
                "target_name": "CD20",
                "target_type": "多次穿膜",
                "order_no": "CN20",
                "arrival_date": "2026-03-17",
            },
        )
        self.assertEqual((row["affinity_status"], row["flow_status"], row["status"]), ("亲和力不适用", "流式待检测", "待检测"))
        with self.assertRaisesRegex(ValueError, "多次穿膜靶点不需要亲和力实验"):
            service.save(self.db, {"id": row["id"], "affinity_status": "亲和力待检测"})
        with self.assertRaisesRegex(ValueError, "亲和力不适用只用于多次穿膜靶点"):
            service.save(self.db, {"id": row["id"], "target_type": "I型跨膜", "affinity_status": "亲和力不适用"})

        # 还没到货时只填流式日期，停在检测中
        early = service.save(self.db, {"target_name": "CD22", "target_type": "多次穿膜", "order_no": "CN22"})
        early = service.save(self.db, {"id": early["id"], "flow_date": "2026-11-01"})
        self.assertEqual((early["status"], early["flow_status"], early["affinity_status"]), ("检测中", "流式已完成", "亲和力不适用"))
        early = service.save(self.db, {"id": early["id"], "arrival_date": "2026-10-30"})
        self.assertEqual(early["status"], "已完成")

        row = service.save(self.db, {"id": row["id"], "flow_status": "流式已完成"})
        self.assertEqual((row["flow_status"], row["affinity_status"], row["status"]), ("流式已完成", "亲和力不适用", "已完成"))

        # 改去其他类型要补亲和力；改回多次穿膜后流式已完成，整单再完成
        row = service.save(self.db, {"id": row["id"], "target_type": "I型跨膜"})
        self.assertEqual((row["affinity_status"], row["flow_status"], row["status"]), ("亲和力待检测", "流式已完成", "检测中"))
        row = service.save(self.db, {"id": row["id"], "target_type": "多次穿膜"})
        self.assertEqual((row["affinity_status"], row["status"]), ("亲和力不适用", "已完成"))

        row = service.save(self.db, {"id": row["id"], "status": "待检测"})
        self.assertEqual((row["affinity_status"], row["flow_status"], row["status"]), ("亲和力不适用", "流式待检测", "待检测"))

        # 已完成的分泌型改成多次穿膜后要做流式
        secreted = self._completed_secreted_order()
        secreted = service.save(self.db, {"id": secreted["id"], "target_type": "多次穿膜"})
        self.assertEqual((secreted["affinity_status"], secreted["flow_status"], secreted["status"]), ("亲和力不适用", "流式待检测", "待检测"))

    def test_manual_flow_skip_survives_cellular_type_change(self):
        rid = service.save(
            self.db,
            {"target_name": "CD9", "order_no": "CN9", "arrival_date": "2026-03-17", "target_type": "I型跨膜"},
        )["id"]
        # 细胞型之间换类型保留手动流式不适用，切去分泌型再切回才重新判断
        row = service.save(self.db, {"id": rid, "flow_status": "流式不适用"})
        self.assertEqual(row["flow_status"], "流式不适用")
        row = service.save(self.db, {"id": rid, "target_type": "II型跨膜"})
        self.assertEqual(row["flow_status"], "流式不适用")
        service.save(self.db, {"id": rid, "target_type": "分泌型"})
        row = service.save(self.db, {"id": rid, "target_type": "I型跨膜"})
        self.assertEqual(row["flow_status"], "流式待检测")

    def test_clearing_affinity_date_or_adding_reason_reverts_affinity_status(self):
        rid = service.save(
            self.db,
            {"target_name": "CD9", "order_no": "CN9", "arrival_date": "2026-03-17", "target_type": "I型跨膜"},
        )["id"]
        row = service.save(self.db, {"id": rid, "affinity_date": "2026-03-20"})
        self.assertEqual((row["affinity_status"], row["status"]), ("亲和力已完成", "检测中"))
        row = service.save(self.db, {"id": rid, "affinity_date": None})
        self.assertEqual((row["affinity_status"], row["status"]), ("亲和力待检测", "待检测"))

        service.save(self.db, {"id": rid, "affinity_date": "2026-03-21"})
        row = service.save(self.db, {"id": rid, "report_reason": "抗原重检"}, scopes=frozenset({"affinity"}))
        self.assertEqual(row["affinity_status"], "亲和力待检测")

    def test_manual_assay_stage_initializes_badges_and_resists_order_edits(self):
        rid = service.save(self.db, {"target_name": "CD1"})["id"]
        row = service.save(self.db, {"id": rid, "status": "待检测"})
        self.assertEqual((row["affinity_status"], row["flow_status"]), ("亲和力待检测", "流式待检测"))

        # 改订单号、One 回填订单号都不会退回合成阶段；清空到货日期才回去
        row = service.save(self.db, {"id": rid, "order_no": "CN100"})
        self.assertEqual(row["status"], "待检测")
        obj = self.db.get(DiscoverySynthesisOrder, rid)
        one_sync.apply_remote_snapshot_to_row(obj, {"order_no": "CN200"})
        self.assertEqual(obj.status, "待检测")
        row = service.save(self.db, {"id": rid, "arrival_date": None})
        self.assertEqual((row["status"], row["affinity_status"]), ("合成中", None))

        secreted = service.save(self.db, {"target_name": "IL2", "target_type": "分泌型"})["id"]
        row = service.save(self.db, {"id": secreted, "status": "检测中"})
        self.assertEqual((row["status"], row["flow_status"]), ("检测中", "流式不适用"))

    def test_reopening_completed_order_to_assaying_resets_both_assays(self):
        rid = service.save(self.db, {"target_name": "CD1"})["id"]
        service.save(self.db, {"id": rid, "status": "检测中"})
        service.save(self.db, {"id": rid, "affinity_status": "亲和力已完成"})
        row = service.save(self.db, {"id": rid, "flow_status": "流式已完成"})
        self.assertEqual(row["status"], "已完成")

        row = service.save(self.db, {"id": rid, "status": "检测中"})
        self.assertEqual((row["affinity_status"], row["flow_status"]), ("亲和力待检测", "流式待检测"))

    def test_pre_arrival_assay_data_undo_and_post_arrival_fallback(self):
        aff = frozenset({"affinity"})
        rid = service.save(self.db, {"target_name": "CD9", "order_no": "CN9", "target_type": "I型跨膜"})["id"]
        row = service.save(self.db, {"id": rid, "affinity_owner": "张赞"}, scopes=aff, created_by="张赞")
        self.assertEqual((row["status"], row["affinity_status"]), ("检测中", "亲和力检测中"))
        row = service.save(self.db, {"id": rid, "affinity_owner": None}, scopes=aff, created_by="张赞")
        self.assertEqual((row["status"], row["affinity_status"], row["flow_status"]), ("合成中", None, None))

        # 填日期会补上本人，删掉日期还剩人员，再删人员才退回合成中
        service.save(self.db, {"id": rid, "affinity_date": "2026-11-01"}, scopes=aff, created_by="张赞")
        row = service.save(self.db, {"id": rid, "affinity_date": None}, scopes=aff, created_by="张赞")
        self.assertEqual((row["status"], row["affinity_status"]), ("检测中", "亲和力检测中"))
        row = service.save(self.db, {"id": rid, "affinity_owner": None}, scopes=aff, created_by="张赞")
        self.assertEqual(row["status"], "合成中")

        # 已到货时清掉人员，检测中退回待检测
        service.save(self.db, {"id": rid, "arrival_date": "2026-11-02"})
        service.save(self.db, {"id": rid, "affinity_owner": "张赞"}, scopes=aff, created_by="张赞")
        row = service.save(self.db, {"id": rid, "affinity_owner": None}, scopes=aff, created_by="张赞")
        self.assertEqual((row["status"], row["affinity_status"]), ("待检测", "亲和力待检测"))

        # 内部转染手动推进的待检测不因删掉误填的日期退回
        internal = service.save(db=self.db, data={"target_name": "CD7", "supply_mode": "内部转染"})["id"]
        service.save(self.db, {"id": internal, "status": "待检测"})
        service.save(self.db, {"id": internal, "flow_date": "2026-11-03"})
        row = service.save(self.db, {"id": internal, "flow_date": None})
        self.assertEqual((row["status"], row["flow_status"]), ("待检测", "流式待检测"))

    def test_secreted_pre_arrival_assay_waits_for_arrival_to_complete(self):
        aff = frozenset({"affinity"})
        secreted = service.save(self.db, {"target_name": "IL2", "order_no": "CN2", "target_type": "分泌型"})["id"]
        row = service.save(self.db, {"id": secreted, "affinity_date": "2026-11-01"}, scopes=aff, created_by="张赞")
        self.assertEqual((row["status"], row["affinity_status"]), ("检测中", "亲和力已完成"))
        service.save(self.db, {"id": secreted, "affinity_date": None}, scopes=aff, created_by="张赞")
        row = service.save(self.db, {"id": secreted, "affinity_owner": None}, scopes=aff, created_by="张赞")
        self.assertEqual(row["status"], "合成中")

        service.save(self.db, {"id": secreted, "affinity_date": "2026-11-01"}, scopes=aff, created_by="张赞")
        row = service.save(self.db, {"id": secreted, "arrival_date": "2026-10-30"}, confirm_complete=True)
        self.assertEqual(row["status"], "已完成")

    def test_completion_requires_confirm(self):
        affinity = frozenset({"affinity"})
        rid = service.save(self.db, {"target_name": "CD8", "order_no": "CN3", "arrival_date": "2026-03-17"})["id"]
        service.save(self.db, {"id": rid, "flow_date": "2026-03-19"})
        payload = {"id": rid, "affinity_date": "2026-03-20"}
        with self.assertRaisesRegex(service.CompletionConfirmRequired, "CD8 · CN3.*完成后你将不能再改回"):
            service.save(self.db, dict(payload), scopes=affinity, confirm_complete=False)
        self.db.rollback()
        self.assertEqual(self.db.get(DiscoverySynthesisOrder, rid).status, "检测中")

        row = service.save(self.db, dict(payload), scopes=affinity)
        self.assertEqual(row["status"], "已完成")
        row = service.save(self.db, {"id": rid, "affinity_owner": "张赞"}, scopes=affinity, confirm_complete=False)
        self.assertEqual(row["status"], "已完成")

        # 手动选主状态已完成是明确操作，不再二次确认
        other = service.save(self.db, {"target_name": "CD10", "order_no": "CN4"})["id"]
        row = service.save(self.db, {"id": other, "status": "已完成"}, confirm_complete=False)
        self.assertEqual(row["status"], "已完成")

    def test_create_requires_fields(self):
        pm = frozenset({"pm"})
        base = {"order_kind": "改造", "supply_mode": "合成到货", "mouse_strain": "RM", "target_name": "CD6"}
        eng = {"eng_type": "Tm", "eng_method": "AI", "eng_parent_seq": "VH1", "eng_requirement": "提高Tm"}
        with self.assertRaisesRegex(ValueError, "订单性质、供应方式、小鼠品系、PM、靶点$"):
            service.save(self.db, {}, require_fields=True)
        self.db.rollback()
        with self.assertRaisesRegex(ValueError, "改造类型、改造方式、母本序列、改造要求$"):
            service.save(self.db, base, created_by="兰维秋", scopes=pm, require_fields=True)
        self.db.rollback()
        row = service.save(self.db, {**base, **eng}, created_by="兰维秋", scopes=pm, require_fields=True)
        self.assertEqual(row["pm"], "兰维秋")

    def test_engineering_order_normalizes_multi_values_and_fills_pm(self):
        row = service.save(
            self.db,
            {
                "order_kind": "改造",
                "priority": "加急",
                "target_name": "SLC3A2",
                "target_codes": ["20R389"],
                "order_no": "BAO0000575",
                "eng_type": ["Tm", "亲和力"],
                "eng_method": "NGS姐妹克隆 + AI",
                "eng_parent_seq": "Vh1$0-20R389_RNBK01AACCHS",
                "eng_requirement": "改造提高亲和力",
                "flow_note": "缺孔还未补",
            },
            created_by="王子豪 Zihao Wang",
        )
        self.assertEqual(row["target_name"], "SLC3A2")
        self.assertEqual(row["target_codes"], ["20R389"])
        self.assertEqual(row["status"], "合成中")
        self.assertEqual(row["priority"], "加急")
        self.assertEqual(row["eng_type"], "亲和力、Tm")
        self.assertEqual(row["eng_method"], "AI、NGS姐妹克隆")
        self.assertIsNone(row["owner"])
        self.assertEqual(row["pm"], "王子豪")


class SynthesisScopePermissionTests(DbTestCase):
    tables = TABLES

    def _completed_secreted_order(self):
        return service.save(
            self.db,
            {
                "target_name": "IL-2",
                "target_type": "分泌型",
                "order_no": "CN2602120001585",
                "arrival_date": "2026-03-17",
                "affinity_date": "2026-03-26",
            },
            created_by="测试员",
        )

    def test_pm_create_autofills_pm_and_leaves_owner_empty(self):
        row = service.save(
            self.db,
            {"target_name": "CD6", "eng_requirement": "提高Tm"},
            created_by="兰维秋",
            scopes=frozenset({"pm"}),
        )
        self.assertEqual((row["pm"], row["owner"]), ("兰维秋", None))

    def test_assay_scopes_close_with_reason_and_post_complete_edits(self):
        both = frozenset({"affinity", "flow"})
        rid = service.save(self.db, {"target_name": "CD6", "order_no": "CN1", "arrival_date": "2026-03-17"})["id"]
        row = service.save(self.db, {"id": rid, "report_reason": "3个克隆以下"}, created_by="张赞")
        self.assertEqual((row["affinity_status"], row["status"]), ("亲和力待检测", "待检测"))

        with self.assertRaisesRegex(ValueError, "请先清除未出报告原因"):
            service.save(self.db, {"id": rid, "affinity_status": "亲和力已完成"}, scopes=frozenset({"affinity"}))
        with self.assertRaisesRegex(ValueError, "请先清除未出报告原因"):
            service.save(self.db, {"id": rid, "affinity_status": "亲和力检测中"}, created_by="张赞")

        # 双实验员可带原因结案，改原因文字不影响；流式标不适用后整单自动完成
        row = service.save(self.db, {"id": rid, "affinity_status": "亲和力已完成"}, scopes=both)
        self.assertEqual((row["affinity_status"], row["status"]), ("亲和力已完成", "检测中"))
        row = service.save(self.db, {"id": rid, "report_reason": "3个克隆以下（复核）"}, scopes=both)
        self.assertEqual(row["affinity_status"], "亲和力已完成")
        row = service.save(self.db, {"id": rid, "flow_status": "流式不适用"}, scopes=both)
        self.assertEqual((row["flow_status"], row["status"]), ("流式不适用", "已完成"))

        # 已完成后改日期、原因不回退；实验状态要先打回才能改
        row = service.save(self.db, {"id": rid, "arrival_date": "2026-03-18"})
        row = service.save(self.db, {"id": rid, "report_reason": "全阴"}, scopes=frozenset({"affinity"}))
        self.assertEqual((row["status"], row["affinity_status"]), ("已完成", "亲和力已完成"))
        with self.assertRaisesRegex(ValueError, "先打回待检测"):
            service.save(self.db, {"id": rid, "flow_status": "流式待检测"}, scopes=both)
        for scopes in (frozenset({"affinity"}), frozenset({"full"})):
            with self.subTest(scopes=scopes), self.assertRaisesRegex(ValueError, "先打回待检测"):
                service.save(self.db, {"id": rid, "affinity_status": "亲和力检测中"}, created_by="张赞", scopes=scopes)

    def test_assay_scopes_main_status_transitions_and_reopen(self):
        both = frozenset({"affinity", "flow"})
        msg = "实验员只能把已完成的工单打回待检测，或把工单改为已取消"
        rid = service.save(self.db, {"target_name": "CD6", "order_no": "CN1", "arrival_date": "2026-03-17"})["id"]

        with self.assertRaisesRegex(ForbiddenError, "不可修改该字段"):
            service.save(self.db, {"id": rid, "status": "已完成"}, scopes=frozenset({"affinity"}))
        with self.assertRaisesRegex(ForbiddenError, msg):
            service.save(self.db, {"id": rid, "status": "已完成"}, scopes=both)

        service.save(self.db, {"id": rid, "affinity_status": "亲和力已完成"}, scopes=both)
        service.save(self.db, {"id": rid, "flow_status": "流式不适用"}, scopes=both)
        with self.assertRaisesRegex(ForbiddenError, msg):
            service.save(self.db, {"id": rid, "status": "检测中"}, scopes=both)
        with self.assertRaises(ForbiddenError):
            service.save(self.db, {"id": rid, "status": "待检测"}, scopes=frozenset({"flow"}))

        row = service.save(self.db, {"id": rid, "status": "待检测"}, scopes=both)
        self.assertEqual((row["status"], row["affinity_status"], row["flow_status"]), ("待检测", "亲和力待检测", "流式不适用"))

        service.save(self.db, {"id": rid, "affinity_status": "亲和力检测中"}, created_by="张赞")
        reopened = service.save(self.db, {"id": rid, "flow_status": "流式已完成"})
        self.assertEqual(reopened["status"], "检测中")
        self.assertEqual(service.get_list(self.db, {"status": ["亲和力检测中", "流式已完成"]})["total"], 1)

        pending = service.save(self.db, {"target_name": "CD7", "order_no": "CN2"})
        with self.assertRaisesRegex(ForbiddenError, msg):
            service.save(self.db, {"id": pending["id"], "status": "已完成"}, scopes=both)

    def test_assay_staff_with_both_scopes_can_cancel_but_not_restore(self):
        both = frozenset({"affinity", "flow"})
        msg = "实验员只能把已完成的工单打回待检测，或把工单改为已取消"
        pending = service.save(self.db, {"target_name": "CD8", "order_no": "CN3"})
        assaying = service.save(self.db, {"target_name": "CD9", "order_no": "CN4", "arrival_date": "2026-03-17"})
        completed = self._completed_secreted_order()
        self.assertEqual(assaying["status"], "待检测")

        with self.assertRaisesRegex(ForbiddenError, "不可修改该字段"):
            service.save(self.db, {"id": pending["id"], "status": "已取消"}, scopes=frozenset({"affinity"}))

        for row in (pending, assaying, completed):
            saved = service.save(self.db, {"id": row["id"], "status": "已取消"}, scopes=both)
            self.assertEqual(saved["status"], "已取消")
            self.assertIsNone(saved["sort_order"])

        for status in ("待下单", "待检测", "已取消"):
            with self.subTest(status=status), self.assertRaisesRegex(ForbiddenError, msg):
                service.save(self.db, {"id": pending["id"], "status": status}, scopes=both)

    def test_claim_lifecycle_and_seven_day_return_window(self):
        pm = frozenset({"pm"})
        rid = service.save(self.db, {"target_name": "CD6", "pm": "兰维秋"})["id"]

        with self.assertRaisesRegex(ValueError, "尚未开放认领"):
            service.claim_order(self.db, rid, "张赞", scopes=pm)
        self.assertEqual(service.claim_order(self.db, rid, None)["owner"], "无人问津")

        with patch("modules.discovery.synthesis_progress.service.now_local", return_value=FIXED_NOW):
            self.assertEqual(service.claim_order(self.db, rid, "张赞", scopes=pm)["owner"], "张赞")
            with self.assertRaisesRegex(ValueError, "不可重复认领"):
                service.claim_order(self.db, rid, "兰维秋", scopes=pm)
            self.assertEqual(service.claim_order(self.db, rid, "张赞", scopes=pm)["owner"], "无人问津")
            service.claim_order(self.db, rid, "张赞", scopes=pm)

        with patch("modules.discovery.synthesis_progress.service.now_local", return_value=FIXED_NOW + timedelta(days=8)):
            with self.assertRaisesRegex(ValueError, "超过 7 天"):
                service.claim_order(self.db, rid, "张赞", scopes=pm)
            with self.assertRaisesRegex(ForbiddenError, "超过 7 天"):
                service.save(self.db, {"id": rid, "owner": "无人问津"}, created_by="张赞", scopes=pm)
            with self.assertRaisesRegex(ForbiddenError, "只能认领"):
                service.save(self.db, {"id": rid, "owner": "兰维秋"}, created_by="张赞", scopes=pm)
            with self.assertRaisesRegex(ValueError, "已由 张赞 负责"):
                service.claim_order(self.db, rid, None)

    def test_pm_claims_order_without_pm_or_owner_as_pm(self):
        pm = frozenset({"pm"})
        rid = service.save(self.db, {"target_name": "CD7"})["id"]

        saved = service.claim_order(self.db, rid, "张赞", scopes=pm)
        self.assertEqual(saved["pm"], "张赞")
        self.assertFalse(saved["owner"])
        service.save(self.db, {"id": rid, "remark": "x"}, created_by="张赞", scopes=pm)
        with self.assertRaisesRegex(ValueError, "尚未开放认领"):
            service.claim_order(self.db, rid, "兰维秋", scopes=pm)
        with self.assertRaisesRegex(ForbiddenError, "不可修改该字段"):
            service.save(self.db, {"id": rid, "pm": "兰维秋"}, created_by="张赞", scopes=pm)

    def test_pm_ownership_and_field_restrictions(self):
        pm = frozenset({"pm"})
        rid = service.save(self.db, {"target_name": "CD6", "pm": "兰维秋"})["id"]
        service.claim_order(self.db, rid, None)
        service.claim_order(self.db, rid, "张赞", scopes=pm)

        # 已认领的工单只归负责人，PM 本人也不能改或删
        with self.assertRaisesRegex(ForbiddenError, "只有负责人"):
            service.save(self.db, {"id": rid, "remark": "x"}, created_by="兰维秋", scopes=pm)
        with self.assertRaisesRegex(ForbiddenError, "只有负责人"):
            service.delete(self.db, rid, scopes=pm, actor_name="兰维秋")

        service.save(self.db, {"id": rid, "remark": "x"}, created_by="张赞", scopes=pm)
        for field in ("pm", "target_type", "experiment_id"):
            with self.subTest(field=field), self.assertRaisesRegex(ForbiddenError, "不可修改该字段"):
                service.save(self.db, {"id": rid, field: "x"}, created_by="张赞", scopes=pm)
        with self.assertRaisesRegex(ForbiddenError, "需通过认领"):
            service.save(self.db, {"target_name": "CD7", "owner": "兰维秋"}, created_by="兰维秋", scopes=pm)

        # 没有负责人时归 PM
        other = service.save(self.db, {"target_name": "CD7", "pm": "兰维秋"})["id"]
        with self.assertRaisesRegex(ForbiddenError, "只有本人是 PM"):
            service.save(self.db, {"id": other, "remark": "x"}, created_by="张赞", scopes=pm)
        service.save(self.db, {"id": other, "remark": "x"}, created_by="兰维秋", scopes=pm)

    def test_assay_scope_field_isolation_and_owner_autofill(self):
        rid = service.save(self.db, {"target_name": "CD6", "pm": "兰维秋"})["id"]
        with self.assertRaises(ForbiddenError):
            service.save(self.db, {"id": rid, "flow_note": "x"}, scopes=frozenset({"affinity"}))
        with self.assertRaises(ForbiddenError):
            service.save(self.db, {"id": rid, "affinity_result": "x"}, scopes=frozenset({"flow"}))

        affinity = frozenset({"affinity"})
        row = service.save(self.db, {"id": rid, "affinity_date": "2026-11-03"}, created_by="张赞 Zan", scopes=affinity)
        self.assertEqual(row["affinity_owner"], "张赞")
        row = service.save(self.db, {"id": rid, "affinity_date": "2026-11-04"}, created_by="兰维秋", scopes=affinity)
        self.assertEqual(row["affinity_owner"], "张赞")

    def test_affinity_owner_multi_autofill_and_options_filter(self):
        affinity = frozenset({"affinity"})
        rid = service.save(self.db, {"target_name": "CD8", "order_no": "CN8", "arrival_date": "2026-11-01"})["id"]
        row = service.save(self.db, {"id": rid, "affinity_owner": ["张赞", "黄志诚", "张赞"]})
        self.assertEqual(row["affinity_owner"], "张赞、黄志诚")

        row = service.save(self.db, {"id": rid, "affinity_status": "亲和力检测中"}, created_by="兰维秋", scopes=affinity)
        self.assertEqual(row["affinity_owner"], "张赞、黄志诚")
        row = service.save(self.db, {"id": rid, "affinity_status": "亲和力待检测"})
        self.assertEqual(row["affinity_owner"], "张赞、黄志诚")

        # 管理员改检测中不填本人，实验员在为空时填本人
        service.save(self.db, {"id": rid, "affinity_owner": None})
        row = service.save(self.db, {"id": rid, "affinity_status": "亲和力检测中"}, created_by="管理员")
        self.assertIsNone(row["affinity_owner"])
        service.save(self.db, {"id": rid, "affinity_status": "亲和力待检测"})
        row = service.save(self.db, {"id": rid, "affinity_status": "亲和力检测中"}, created_by="兰维秋", scopes=affinity)
        self.assertEqual(row["affinity_owner"], "兰维秋")

        self.assertEqual(service.get_options(self.db)["affinity_owners"], ["兰维秋"])
        values = service.get_column_values(self.db, {"field": "affinity_owner"})["items"]
        self.assertEqual([item["value"] for item in values], ["兰维秋"])
        service.save(self.db, {"id": rid, "affinity_owner": "张赞+黄志诚"})
        found = service.get_list(self.db, {"field_filters": [{"field": "affinity_owner", "values": ["黄志诚"]}]})
        self.assertEqual([item["id"] for item in found["items"]], [rid])

    def test_engineering_scope_create_edit_and_delete_permissions(self):
        eng = frozenset({"eng"})
        need = {"order_kind": "常规合成", "mouse_strain": "RM", "target_name": "CD6"}
        with self.assertRaisesRegex(ForbiddenError, "只能操作改造"):
            service.save(self.db, {**need, "supply_mode": "合成到货"}, created_by="李四 Li Si", scopes=eng, require_fields=True)
        self.db.rollback()

        row = service.save(self.db, {**need, "supply_mode": "内部转染"}, created_by="李四 Li Si", scopes=eng, require_fields=True)
        self.assertEqual((row["pm"], row["order_sender"], row["synthetic_corp"]), ("李四", "李四 Li Si", "内部"))
        rid = row["id"]

        saved = service.save(
            self.db, {"id": rid, "pm": "张赞", "arrival_date": "2026-11-03", "synthetic_corp": "擎科"}, scopes=eng
        )
        self.assertEqual((saved["pm"], saved["synthetic_corp"]), ("张赞", "擎科"))
        for field in ("owner", "flow_note", "affinity_result"):
            with self.subTest(field=field), self.assertRaisesRegex(ForbiddenError, "不可修改该字段"):
                service.save(self.db, {"id": rid, field: "x"}, created_by="李四", scopes=eng)
            self.db.rollback()
        with self.assertRaisesRegex(ForbiddenError, "只能操作改造"):
            service.save(self.db, {"id": rid, "supply_mode": "合成到货"}, created_by="李四", scopes=eng)
        self.db.rollback()

        normal = service.save(self.db, {"target_name": "CD7"})["id"]
        with self.assertRaisesRegex(ForbiddenError, "只能操作改造"):
            service.save(self.db, {"id": normal, "remark": "x"}, created_by="李四", scopes=eng)
        self.db.rollback()
        with self.assertRaisesRegex(ForbiddenError, "只能操作改造"):
            service.delete(self.db, normal, scopes=eng, actor_name="李四")
        self.db.rollback()

        service.save(self.db, {"id": rid, "status": "已取消"}, scopes=eng)
        service.delete(self.db, rid, scopes=eng, actor_name="李四")
        self.assertIsNone(self.db.get(DiscoverySynthesisOrder, rid))

    def test_engineering_corp_default_and_reclassify_with_pm_scope(self):
        eng = frozenset({"eng"})
        arrival = service.save(self.db, {"order_kind": "改造", "target_name": "CD8"}, created_by="李四", scopes=eng)
        self.assertEqual(arrival["synthetic_corp"], "内部")
        linked = self.db.get(DiscoverySynthesisOrder, arrival["id"])
        one_sync.apply_remote_snapshot_to_row(linked, {"order_no": "CN1", "synthetic_corp": "君跻"})
        self.assertEqual(linked.synthetic_corp, "君跻")

        saved = service.save(
            self.db, {"id": arrival["id"], "order_kind": "常规合成"}, created_by="李四", scopes=frozenset({"pm", "eng"})
        )
        self.assertEqual(saved["order_kind"], "常规合成")

    def test_corp_hidden_without_full_edit(self):
        drift = {"field": "synthetic_corp", "current": "擎科", "remote": "金斯瑞"}
        row = {"synthetic_corp": "擎科", "source_snapshot": {"synthetic_corp": "擎科"}, "drift_fields": [drift]}
        masked = service.mask_synthetic_corp({"items": [row, {"synthetic_corp": None}]})["items"]
        self.assertEqual(masked[0]["synthetic_corp"], "***")
        self.assertEqual(masked[0]["source_snapshot"]["synthetic_corp"], "***")
        self.assertEqual((masked[0]["drift_fields"][0]["current"], masked[0]["drift_fields"][0]["remote"]), ("***", "***"))
        self.assertIsNone(masked[1]["synthetic_corp"])

        rows = [
            {"order_kind": "常规合成", "supply_mode": "合成到货", "synthetic_corp": "擎科"},
            {"order_kind": "常规合成", "supply_mode": "改亚型", "synthetic_corp": "内部"},
        ]
        kept = service.mask_synthetic_corp(rows, keep_engineering_rows=True)
        self.assertEqual([item["synthetic_corp"] for item in kept], ["***", "内部"])

        query = service.without_corp_query({
            "synthetic_corp": "擎科",
            "sort_field": "synthetic_corp",
            "field_filters": [{"field": "synthetic_corp", "values": ["擎科"]}, {"field": "owner", "values": ["张赞"]}],
        })
        self.assertEqual(query, {"field_filters": [{"field": "owner", "values": ["张赞"]}]})


class SynthesisOptionsAndListTests(DbTestCase):
    tables = TABLES

    def test_person_options_use_own_field_by_frequency(self):
        for pm, affinity_owner in (("兰维秋", "赵雨蕾"), ("安高", "黄志诚"), ("安高", "黄志诚")):
            service.save(self.db, {"target_name": "CD1", "pm": pm, "affinity_owner": affinity_owner})
        options = service.get_options(self.db)
        self.assertEqual(options["affinity_owners"], ["黄志诚", "赵雨蕾"])
        self.assertEqual(options["pms"], ["安高", "兰维秋"])
        self.assertEqual(options["owners"], ["无人问津"])

    def test_default_list_and_queue_sort_put_completed_out_of_queue(self):
        completed = service.save(
            self.db,
            {
                "target_name": "IL-2",
                "target_type": "分泌型",
                "order_no": "CN1",
                "arrival_date": "2026-03-17",
                "affinity_date": "2026-03-26",
            },
            created_by="测试员",
        )
        active = service.save(self.db, {"target_name": "SLC3A2", "order_no": "BAO1"}, created_by="测试员")

        default_list = service.get_list(self.db, {})["items"]
        self.assertEqual([item["id"] for item in default_list], [active["id"], completed["id"]])
        queue_list = service.get_list(self.db, {"sort_field": "sort_order"})["items"]
        self.assertEqual(queue_list[0]["id"], active["id"])
        self.assertEqual(queue_list[0]["sort_order"], 1)
        self.assertIsNone(queue_list[1]["sort_order"])

    def test_quick_filter_has_drift_matches_source_difference(self):
        service.save(self.db, {"target_name": "CD3", "order_no": "CN1", "flow_note": "有说明", "report_reason": "异常"})
        drifted = service.save(
            self.db,
            {
                "target_name": "CD4",
                "order_no": "CN2",
                "synthetic_count": 10,
                "synthetic_date": "2026-04-02",
                "arrival_count": 8,
                "arrival_date": "2026-04-17",
            },
        )
        self.db.get(DiscoverySynthesisOrder, drifted["id"]).source_snapshot = {
            "order_no": "GS2",
            "synthetic_count": 12,
            "synthetic_date": "2026-04-01",
            "arrival_count": 9,
            "arrival_date": "2026-04-15",
        }
        alias = service.save(self.db, {"target_name": "CD5", "order_no": "CN3", "synthetic_count": 5})
        self.db.get(DiscoverySynthesisOrder, alias["id"]).source_snapshot = {"order_no": "GS3", "synthetic_count": 5}
        empty_local = service.save(self.db, {"target_name": "CD6", "order_no": "CN4"})
        self.db.get(DiscoverySynthesisOrder, empty_local["id"]).source_snapshot = {
            "synthetic_count": 3,
            "arrival_date": "2026-05-01",
        }
        other = service.save(self.db, {"target_name": "CD8", "order_no": "BAO1", "is_rechoose": "否"})
        self.db.get(DiscoverySynthesisOrder, other["id"]).source_snapshot = {"is_rechoose": "是"}
        self.db.commit()

        data = service.get_list(self.db, {"quick_filter": "has_drift", "limit": 50})
        self.assertEqual({item["target_name"] for item in data["items"]}, {"CD4", "CD8"})
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["stats"]["has_drift"], 2)
        self.assertEqual(data["stats"]["all"], 5)


class SynthesisHeaderFilterTests(DbTestCase):
    tables = TABLES
    ROWS = [
        dict(status="待下单", owner="甲", target_name="PD-L1", target_codes=["20R001"],
             mouse_strain="RN、RNKO", synthesis_code="S001", synthetic_count=10,
             synthetic_date="2026-01-05", remark="首批", target_color="red"),
        dict(status="合成中", owner="乙", target_name="CD274", target_codes=["20R001"],
             mouse_strain="RN", synthesis_code="S002", synthetic_count=50,
             synthetic_date="2026-02-10", remark=None),
        dict(status="已完成", owner=None, target_name="HER2", target_codes=["20R002"],
             mouse_strain="RNKO", synthesis_code="S003", synthetic_count=None,
             synthetic_date=None, remark="补做 100%"),
        dict(status="合成中", owner="甲", target_name="PD-L1&HER2", target_codes=["20R001", "20R002"],
             mouse_strain=None, synthesis_code="S004", synthetic_count=80,
             synthetic_date="2026-03-01", remark=""),
    ]

    def setUp(self):
        super().setUp()
        for index, row in enumerate(self.ROWS, start=1):
            self.db.add(DiscoverySynthesisOrder(
                synthesis_order_id=f"SO{index:03d}",
                order_kind="常规",
                supply_mode="自合成",
                **row,
            ))
        self.db.commit()

    def codes(self, *field_filters, **extra):
        data = {"limit": 50, "field_filters": list(field_filters), **extra}
        return sorted(item["synthesis_code"] for item in service.get_list(self.db, data)["items"])

    def values(self, field, **extra):
        return service.get_column_values(self.db, {"field": field, **extra})

    def test_values_and_exclude_handle_blank(self):
        self.assertEqual(self.codes({"field": "owner", "values": ["甲"]}), ["S001", "S004"])
        self.assertEqual(self.codes({"field": "owner", "values": ["乙", ""]}), ["S002", "S003"])
        self.assertEqual(self.codes({"field": "owner", "exclude": ["甲"]}), ["S002", "S003"])
        self.assertEqual(self.codes({"field": "owner", "exclude": ["甲", ""]}), ["S002"])
        self.assertEqual(self.codes({"field": "remark", "exclude": [""]}), ["S001", "S003"])

    def test_conditions(self):
        self.assertEqual(self.codes({"field": "remark", "condition": {"op": "contains", "value": "100%"}}), ["S003"])
        self.assertEqual(
            self.codes({"field": "remark", "condition": {"op": "not_contains", "value": "首"}}),
            ["S002", "S003", "S004"],
        )
        self.assertEqual(self.codes({"field": "synthetic_count", "condition": {"op": "gte", "value": "50"}}), ["S002", "S004"])
        self.assertEqual(
            self.codes({"field": "synthetic_date", "condition": {"op": "between", "value": "2026-02-01", "value2": "2026-03-31"}}),
            ["S002", "S004"],
        )
        self.assertEqual(self.codes({"field": "synthetic_date", "condition": {"op": "blank"}}), ["S003"])
        self.assertEqual(
            self.codes({"field": "eng_result", "condition": {"op": "blank"}}),
            ["S001", "S002", "S003", "S004"],
        )
        self.assertEqual(
            self.codes({"field": "synthetic_date", "condition": {"op": "between", "value": "2026/2/1", "value2": "2026.3.31"}}),
            ["S002", "S004"],
        )
        for bad_filter in (
            {"field": "synthetic_date", "condition": {"op": "gte", "value": "2026-13-01"}},
            {"field": "synthetic_date", "condition": {"op": "gte", "value": "01/01/2026"}},
            {"field": "sort_order", "values": ["1"]},
        ):
            with self.subTest(bad_filter=bad_filter), self.assertRaises(ValueError):
                self.codes(bad_filter)

    def test_mouse_strain_csv_filter_and_values(self):
        self.assertEqual(self.codes({"field": "mouse_strain", "values": ["RN"]}), ["S001", "S002"])
        self.assertEqual(self.codes({"field": "mouse_strain", "exclude": ["RN"]}), ["S003", "S004"])
        strains = self.values("mouse_strain")["items"]
        self.assertEqual({item["value"]: item["count"] for item in strains}, {"RN": 2, "RNKO": 2, "": 1})

    def test_target_name_aliases_and_color_filter(self):
        self.assertEqual(self.codes({"field": "target_name", "values": ["PD-L1"]}), ["S001", "S002", "S004"])
        self.assertEqual(self.codes({"field": "target_name", "exclude": ["HER2"]}), ["S001", "S002"])
        targets = self.values("target_name")["items"]

        def group_count(name):
            hits = [item for item in targets if name in (item["value"], *item["aliases"])]
            self.assertEqual(len(hits), 1, name)
            return hits[0]["count"]

        self.assertEqual(group_count("PD-L1"), 3)
        self.assertEqual(group_count("CD274"), 3)
        self.assertEqual(group_count("HER2"), 2)
        self.assertEqual(group_count("PD-L1&HER2"), 1)

        searched = self.values("target_name", value_keyword="cd274")["items"]
        self.assertEqual(len(searched), 1)
        self.assertIn("PD-L1", (searched[0]["value"], *searched[0]["aliases"]))
        self.assertEqual(self.codes({"field": "target_name", "values": [searched[0]["value"]]}), ["S001", "S002", "S004"])
        self.assertEqual(self.codes({"field": "target_name", "colors": ["red"]}), ["S001"])

    def test_target_codes_json_filter_and_values(self):
        self.assertEqual(self.codes({"field": "target_codes", "values": ["20R002"]}), ["S003", "S004"])
        self.assertEqual(self.codes({"field": "target_codes", "exclude": ["20R001"]}), ["S003"])
        listed = self.values("target_codes")["items"]
        self.assertEqual({item["value"]: item["count"] for item in listed}, {"20R001": 3, "20R002": 2})

    def test_sender_affinity_owner_and_rechoose_filters(self):
        self.db.execute(
            update(DiscoverySynthesisOrder)
            .where(DiscoverySynthesisOrder.synthesis_code == "S001")
            .values(order_sender="任鸿滨", affinity_owner="张三、李四")
        )
        self.db.execute(
            update(DiscoverySynthesisOrder)
            .where(DiscoverySynthesisOrder.synthesis_code == "S002")
            .values(is_rechoose="是")
        )
        self.db.commit()
        self.assertEqual(self.codes({"field": "order_sender", "values": ["任鸿滨"]}), ["S001"])
        self.assertEqual(self.codes(order_sender="任鸿滨"), ["S001"])
        self.assertEqual(self.codes(affinity_owner=["李四"]), ["S001"])
        self.assertEqual(self.codes(is_rechoose="是"), ["S002"])
        self.assertEqual(self.values("order_sender")["items"], [{"value": "任鸿滨", "count": 1}, {"value": "", "count": 3}])

    def test_status_header_includes_assay_sub_statuses(self):
        for code, status, affinity, flow in (
            ("S005", "检测中", "亲和力已完成", "流式待检测"),
            ("S006", "待检测", "亲和力待检测", "流式待检测"),
            ("S007", "已完成", "亲和力已完成", "流式已完成"),
        ):
            self.db.add(DiscoverySynthesisOrder(
                synthesis_order_id=f"SO{code}", order_kind="常规", supply_mode="自合成",
                synthesis_code=code, status=status, affinity_status=affinity, flow_status=flow,
            ))
        self.db.commit()

        listed = [(item["value"], item["count"]) for item in self.values("status")["items"]]
        self.assertEqual(listed, [
            ("待下单", 1), ("合成中", 2), ("待检测", 1), ("检测中", 1), ("已完成", 2),
            ("亲和力待检测", 1), ("亲和力已完成", 1), ("流式待检测", 2),
        ])
        # 已完成行的子状态不计入，也不被子状态筛中
        self.assertEqual(self.codes({"field": "status", "values": ["亲和力已完成"]}), ["S005"])
        self.assertEqual(self.codes({"field": "status", "values": ["亲和力已完成", "流式待检测"]}), ["S005"])
        self.assertEqual(self.codes({"field": "status", "values": ["待下单", "流式待检测"]}), ["S001", "S005", "S006"])
        self.assertEqual(
            self.codes({"field": "status", "exclude": ["流式待检测"]}),
            ["S001", "S002", "S003", "S004", "S007"],
        )
        self.assertEqual(self.codes(status="亲和力待检测"), ["S006"])

        # 组合项两项都要满足，多个组合之间取或；状态列取值不列组合，子弹窗的取值才列
        self.assertEqual(self.codes(status="亲和力已完成且流式待检测"), ["S005"])
        self.assertEqual(self.codes(status=["亲和力已完成且流式待检测", "亲和力待检测且流式待检测"]), ["S005", "S006"])
        self.assertEqual(self.codes(status=["亲和力已完成且流式已完成", "待下单"]), ["S001"])
        breakdown = self.values("status_breakdown", field_filters=[{"field": "status", "values": ["合成中"]}])
        self.assertEqual([(item["value"], item["count"]) for item in breakdown["items"]], [
            *listed, ("亲和力待检测且流式待检测", 1), ("亲和力已完成且流式待检测", 1),
        ])

    def test_value_list_ignores_own_header_filter_and_keeps_others(self):
        own = {"field": "owner", "values": ["甲"]}
        listed = self.values("owner", field_filters=[own])["items"]
        self.assertEqual({item["value"] for item in listed}, {"甲", "乙", ""})
        other = {"field": "status", "values": ["合成中"]}
        listed = self.values("owner", field_filters=[other])["items"]
        self.assertEqual({item["value"]: item["count"] for item in listed}, {"甲": 1, "乙": 1})

    def test_value_orders_and_truncation(self):
        recent = self.values("synthesis_code", value_order="recent", value_limit=2)
        self.assertEqual([item["value"] for item in recent["items"]], ["S004", "S003"])
        self.assertTrue(recent["truncated"])
        dates = self.values("synthetic_date", value_order="value_desc")["items"]
        self.assertEqual(dates[0]["value"], "2026-03-01")
        self.assertEqual(dates[-1], {"value": "", "count": 1})
        statuses = [item["value"] for item in self.values("status")["items"]]
        self.assertEqual(statuses, ["待下单", "合成中", "已完成"])

    def test_header_sort_uses_business_order_and_blanks_last(self):
        rows = service.get_list(self.db, {"limit": 50, "sort_field": "status", "sort_dir": "desc"})["items"]
        self.assertEqual([row["status"] for row in rows], ["已完成", "合成中", "合成中", "待下单"])
        rows = service.get_list(self.db, {"limit": 50, "sort_field": "owner", "sort_dir": "asc"})["items"]
        self.assertEqual([row["owner"] for row in rows], ["乙", "甲", "甲", None])
        rows = service.get_list(self.db, {"limit": 50, "sort_field": "owner", "sort_dir": "desc"})["items"]
        self.assertEqual([row["owner"] for row in rows], ["甲", "甲", "乙", None])

    def test_stats_and_export_follow_header_filters(self):
        header = [{"field": "status", "exclude": ["合成中"]}]
        data = service.get_list(self.db, {"limit": 50, "field_filters": header})
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["stats"]["all"], 2)
        self.assertEqual(data["stats"]["synthesizing"], 0)
        with patch.object(service, "build_list_workbook", side_effect=lambda **kw: kw) as built:
            service.export_list_workbook(self.db, {
                "field_filters": header, "sort_field": "synthesis_code", "sort_dir": "desc",
            })
        rows = built.call_args.kwargs["rows"]
        code_at = [h for h, _ in service.EXPORT_COLUMNS].index("送测转码")
        self.assertEqual([row[code_at] for row in rows], ["S003", "S001"])

    def test_value_search_keeps_list_keyword_and_text_search(self):
        found = self.values("remark", value_keyword="补做", value_order="recent")["items"]
        self.assertEqual(found, [{"value": "补做 100%", "count": 1}])
        listed = self.values("owner", keyword="S00")["items"]
        self.assertEqual({item["value"]: item["count"] for item in listed}, {"甲": 2, "乙": 1, "": 1})
        listed = self.values("owner", keyword="PD-L1", value_keyword="甲")["items"]
        self.assertEqual(listed, [{"value": "甲", "count": 2}])


class SynthesisQueueTests(DbTestCase):
    tables = TABLES

    def _sorts(self, *row_ids: int) -> list[int | None]:
        self.db.expire_all()
        return [self.db.get(DiscoverySynthesisOrder, rid).sort_order for rid in row_ids]

    def test_queue_placement_priority_reorder_terminal_and_delete(self):
        r1 = service.save(self.db, {"target_name": "T1"}, created_by="测试员")
        r2 = service.save(self.db, {"target_name": "T2"}, created_by="测试员")
        r3 = service.save(self.db, {"target_name": "T3", "priority": "加急"}, created_by="测试员")
        self.assertEqual(self._sorts(r1["id"], r2["id"], r3["id"]), [2, 3, 1])

        service.save(self.db, {"id": r2["id"], "priority": "加急"})
        self.assertEqual(self._sorts(r1["id"], r2["id"], r3["id"]), [3, 2, 1])
        service.save(self.db, {"id": r3["id"], "priority": "正常"})
        self.assertEqual(self._sorts(r1["id"], r2["id"], r3["id"]), [3, 1, 2])

        service.reorder(self.db, r1["id"], r3["id"])
        self.assertEqual(self._sorts(r2["id"], r1["id"], r3["id"]), [1, 2, 3])
        same = service.reorder(self.db, r1["id"], r1["id"])
        self.assertEqual([item["id"] for item in same["items"]], [r1["id"]])

        r4 = service.save(self.db, {"target_name": "T4", "sort_order": 2}, created_by="测试员")
        self.assertEqual(self._sorts(r2["id"], r4["id"], r1["id"], r3["id"]), [1, 2, 3, 4])

        service.save(self.db, {"id": r4["id"], "status": "已取消"})
        self.assertEqual(self._sorts(r2["id"], r4["id"], r1["id"], r3["id"]), [1, None, 2, 3])
        with self.assertRaisesRegex(ValueError, "终态记录不参与排序"):
            service.reorder(self.db, r4["id"], r1["id"])

        service.delete(self.db, r1["id"])
        self.assertEqual(self._sorts(r2["id"], r3["id"]), [1, 2])

    def test_queue_shift_update_count_stays_constant_as_rows_grow(self):
        def measure(count: int) -> int:
            with self.Session() as db:
                ids = [service.save(db, {"target_name": f"T{i}"}, created_by="测试员")["id"] for i in range(count)]
                updates = 0

                def capture(_conn, _cursor, statement, _parameters, _context, _executemany):
                    nonlocal updates
                    if statement.lstrip().upper().startswith("UPDATE DISCOVERY_SYNTHESIS_ORDER"):
                        updates += 1

                event.listen(self.engine, "before_cursor_execute", capture)
                try:
                    service.save(db, {"id": ids[0], "status": "已取消"})
                finally:
                    event.remove(self.engine, "before_cursor_execute", capture)
                orders = dict(db.execute(select(DiscoverySynthesisOrder.id, DiscoverySynthesisOrder.sort_order)).all())
                self.assertEqual([orders[i] for i in ids], [None, *range(1, count)])
                return updates

        small_updates = measure(4)
        self.db.execute(DiscoverySynthesisOrder.__table__.delete())
        self.db.commit()
        large_updates = measure(40)
        self.assertEqual(small_updates, large_updates)
        self.assertLessEqual(large_updates, 2)

    def test_terminal_rows_leave_queue_in_same_transaction(self):
        def add_row(code, sort_order):
            row = DiscoverySynthesisOrder(
                synthesis_order_id=code,
                status=service.STATUS_WAIT_ORDER,
                order_kind=service.ORDER_KIND_NORMAL,
                supply_mode=service.SUPPLY_MODE_ARRIVAL,
                priority="正常",
                sort_order=sort_order,
            )
            self.db.add(row)
            return row

        first, done, last = add_row("S1", 1), add_row("S2", 2), add_row("S3", 3)
        self.db.commit()

        done.status = service.STATUS_COMPLETED
        service.settle_queue_after_sync(self.db)
        self.db.commit()
        self.assertEqual((first.sort_order, done.sort_order, last.sort_order), (1, None, 2))

    def test_expected_conflict_detection_single_and_batch(self):
        r1 = service.save(
            self.db,
            {"target_name": "CD3", "synthetic_corp": "金斯瑞", "synthetic_count": 10},
            created_by="测试员",
        )
        r2 = service.save(self.db, {"target_name": "CD4", "remark": "初版"}, created_by="测试员")

        with self.assertRaises(ConflictError):
            service.save_batch(
                self.db,
                {
                    "items": [
                        {"id": r1["id"], "remark": "不应写入", "_expected": {"target_name": "CD3"}},
                        {"id": r2["id"], "remark": "新版", "_expected": {"remark": "过期"}},
                    ]
                },
            )
        self.db.rollback()
        self.assertIsNone(self.db.get(DiscoverySynthesisOrder, r1["id"]).remark)

        updated = service.save_batch(
            self.db,
            {
                "items": [
                    {
                        "id": r1["id"],
                        "remark": "已改",
                        "_expected": {
                            "target_name": "CD3",
                            "synthetic_count": 10.0,
                            "remark": "",
                            "sort_order": 999,
                            "synthesis_order_id": "IGNORED",
                        },
                    }
                ]
            },
        )
        self.assertEqual(updated["items"][0]["remark"], "已改")

        # 非全权限用户基线里的脱敏 *** 合成公司不应触发误冲突
        aff_updated = service.save(
            self.db,
            {
                "id": r1["id"],
                "affinity_result": "正常",
                "_expected": {"synthetic_corp": "***", "remark": "已改"},
            },
            scopes=frozenset({"affinity"}),
        )
        self.assertEqual(aff_updated["affinity_result"], "正常")

        with self.assertRaises(ConflictError):
            service.save(self.db, {"id": r1["id"], "remark": "冲突", "_expected": {"remark": "过期"}})
        self.db.rollback()
        plain = service.save(self.db, {"id": r1["id"], "remark": "无基线覆盖"})
        self.assertEqual(plain["remark"], "无基线覆盖")

    def test_list_rows_round_trip_as_expected(self):
        service.save(
            self.db,
            {
                "target_name": "CD3",
                "mouse_strain": ["RN", "RNKO"],
                "synthetic_count": 10,
                "synthetic_date": "2026/1/5",
                "remark": "第一行\n第二行",
            },
            created_by="测试员",
        )
        service.save(self.db, {"target_name": "CD4"}, created_by="测试员")
        items = service.get_list(self.db, {})["items"]
        for item in items:
            saved = service.save(self.db, {"id": item["id"], "remark": "单条", "_expected": dict(item)})
            self.assertEqual(saved["remark"], "单条")
        items = service.get_list(self.db, {})["items"]
        saved = service.save_batch(
            self.db,
            {"items": [{"id": item["id"], "remark": "批量", "_expected": dict(item)} for item in items]},
        )
        self.assertEqual([row["remark"] for row in saved["items"]], ["批量", "批量"])


class CancelledVisibilityTests(DbTestCase):
    tables = TABLES

    def test_cancelled_orders_stay_hidden_without_full_or_both_assay_scopes(self):
        open_row = service.save(self.db, {"target_name": "OPEN"}, created_by="测试员")
        cancelled = service.save(self.db, {"target_name": "GONE"}, created_by="测试员")
        service.save(self.db, {"id": cancelled["id"], "status": "已取消"})

        hidden = service.get_list(self.db, {}, include_cancelled=False)
        self.assertEqual([item["target_name"] for item in hidden["items"]], ["OPEN"])
        self.assertEqual(hidden["stats"]["all"], 1)
        self.assertEqual(hidden["stats"]["cancelled"], 0)
        self.assertEqual(hidden["total"], 1)

        shown = service.get_list(self.db, {})
        self.assertCountEqual([item["target_name"] for item in shown["items"]], ["OPEN", "GONE"])
        self.assertEqual(shown["stats"]["cancelled"], 1)

        self.assertTrue(service.sees_cancelled(frozenset({"full"})))
        self.assertTrue(service.sees_cancelled(frozenset({"affinity", "flow"})))
        self.assertFalse(service.sees_cancelled(frozenset({"affinity"})))
        self.assertFalse(service.sees_cancelled(frozenset({"flow", "pm"})))
        self.assertFalse(service.sees_cancelled(frozenset()))
        self.assertEqual(open_row["target_name"], "OPEN")
