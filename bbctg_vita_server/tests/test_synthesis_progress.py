from datetime import timedelta
import json
import unittest
from unittest.mock import patch

from sqlalchemy import event, select, update

from models.discovery import DiscoverySynthesisOrder
from models.target import Target
from modules.discovery.synthesis_progress import one_sync, service
from support import DbTestCase
from utils.clock import now_local
from utils.workbench_queue import lock_queue


class SynthesisProgressServiceTests(DbTestCase):
    tables = (Target, DiscoverySynthesisOrder)

    def _completed_secreted_order(self, db):
        row = service.save(
            db,
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

    def test_target_type_change_reopens_or_completes_order(self):
        with self.Session() as db:
            row = self._completed_secreted_order(db)
            # 改成非分泌型后要补流式，已完成不能再保留
            row = service.save(db, {"id": row["id"], "target_type": "I型跨膜"})
            self.assertEqual(row["flow_status"], "流式待检测")
            self.assertEqual(row["status"], "检测中")
            self.assertIsNotNone(row["sort_order"])

            row = service.save(db, {"id": row["id"], "target_type": "分泌型"})
            self.assertEqual(row["flow_status"], "流式不适用")
            self.assertEqual(row["status"], "已完成")

            # 同值回写不算靶点类型变化，已完成保持
            row = service.save(db, {"id": row["id"], "target_type": "分泌型", "remark": "复核"})
            self.assertEqual(row["status"], "已完成")

    def test_assay_status_checks_use_values_from_same_payload(self):
        with self.Session() as db:
            row = service.save(
                db,
                {"target_name": "B7-H4", "order_no": "CN1", "arrival_date": "2026-03-17", "report_reason": "抗原重检"},
                created_by="测试员",
            )
            with self.assertRaisesRegex(ValueError, "请先清除未出报告原因"):
                service.save(db, {"id": row["id"], "affinity_status": "亲和力检测中"}, created_by="张赞")

            row = service.save(
                db,
                {"id": row["id"], "report_reason": None, "affinity_status": "亲和力检测中"},
                created_by="张赞",
            )
            self.assertEqual(row["affinity_status"], "亲和力检测中")
            self.assertIsNone(row["affinity_owner"])

            with self.assertRaisesRegex(ValueError, "分泌型靶点不需要流式实验"):
                service.save(db, {"id": row["id"], "target_type": "分泌型", "flow_status": "流式待检测"})

    def test_close_with_reason_and_rollback(self):
        both = frozenset({"affinity", "flow"})
        msg = "实验员只能把已完成的工单打回待检测"
        with self.Session() as db:
            row = service.save(db, {"target_name": "CD6", "order_no": "CN1", "arrival_date": "2026-03-17"})
            rid = row["id"]
            row = service.save(db, {"id": rid, "report_reason": "3个克隆以下"}, created_by="张赞")
            self.assertEqual((row["affinity_status"], row["status"]), ("亲和力待检测", "待检测"))
            # 单项实验员不能改主状态，有原因时也不能把亲和力标为已完成
            with self.assertRaisesRegex(PermissionError, "不可修改该字段"):
                service.save(db, {"id": rid, "status": "已完成"}, scopes=frozenset({"affinity"}))
            with self.assertRaisesRegex(ValueError, "请先清除未出报告原因"):
                service.save(db, {"id": rid, "affinity_status": "亲和力已完成"}, scopes=frozenset({"affinity"}))
            with self.assertRaisesRegex(ValueError, "请先清除未出报告原因"):
                service.save(db, {"id": rid, "affinity_status": "亲和力检测中"}, created_by="张赞")
            # 双权限实验员也不能直接把未完成的工单改成已完成
            with self.assertRaisesRegex(PermissionError, msg):
                service.save(db, {"id": rid, "status": "已完成"}, scopes=both)
            # 带原因结案，改原因文字不影响；流式不做标不适用后整单自动完成
            row = service.save(db, {"id": rid, "affinity_status": "亲和力已完成"}, scopes=both)
            self.assertEqual((row["affinity_status"], row["status"]), ("亲和力已完成", "检测中"))
            row = service.save(db, {"id": rid, "report_reason": "3个克隆以下（复核）"}, scopes=both)
            self.assertEqual(row["affinity_status"], "亲和力已完成")
            row = service.save(db, {"id": rid, "flow_status": "流式不适用"}, scopes=both)
            self.assertEqual((row["flow_status"], row["status"]), ("流式不适用", "已完成"))
            # 已完成后改日期、原因不回退；实验状态要先打回才能改
            row = service.save(db, {"id": rid, "arrival_date": "2026-03-18"})
            row = service.save(db, {"id": rid, "report_reason": "全阴"}, scopes=frozenset({"affinity"}))
            self.assertEqual((row["status"], row["affinity_status"]), ("已完成", "亲和力已完成"))
            with self.assertRaisesRegex(ValueError, "先打回待检测"):
                service.save(db, {"id": rid, "flow_status": "流式待检测"}, scopes=both)
            for status in ("检测中", "已取消"):
                with self.assertRaisesRegex(PermissionError, msg):
                    service.save(db, {"id": rid, "status": status}, scopes=both)
            # 打回待检测：两项实验一并回到待检测，流式不适用保留
            row = service.save(db, {"id": rid, "status": "待检测"}, scopes=both)
            self.assertEqual((row["status"], row["affinity_status"], row["flow_status"]), ("待检测", "亲和力待检测", "流式不适用"))
            pending = service.save(db, {"target_name": "CD7", "order_no": "CN2"})
            with self.assertRaisesRegex(PermissionError, msg):
                service.save(db, {"id": pending["id"], "status": "已完成"}, scopes=both)

    def test_manual_flow_skip_and_affinity_date_clear(self):
        with self.Session() as db:
            rid = service.save(
                db, {"target_name": "CD9", "order_no": "CN9", "arrival_date": "2026-03-17", "target_type": "I型跨膜"}
            )["id"]
            # 细胞型也能手动标流式不适用；细胞型之间换类型不影响，分泌型改回细胞型才重新判断
            row = service.save(db, {"id": rid, "flow_status": "流式不适用"})
            self.assertEqual(row["flow_status"], "流式不适用")
            row = service.save(db, {"id": rid, "target_type": "II型跨膜"})
            self.assertEqual(row["flow_status"], "流式不适用")
            service.save(db, {"id": rid, "target_type": "分泌型"})
            row = service.save(db, {"id": rid, "target_type": "I型跨膜"})
            self.assertEqual(row["flow_status"], "流式待检测")
            # 清掉亲和力日期，亲和力已完成随之回退
            row = service.save(db, {"id": rid, "affinity_date": "2026-03-20"})
            self.assertEqual((row["affinity_status"], row["status"]), ("亲和力已完成", "检测中"))
            row = service.save(db, {"id": rid, "affinity_date": None})
            self.assertEqual((row["affinity_status"], row["status"]), ("亲和力待检测", "待检测"))
            # 已完成后新填未出原因 = 报告卡住，回到待检测；单项实验员不能借此结案
            service.save(db, {"id": rid, "affinity_date": "2026-03-21"})
            row = service.save(db, {"id": rid, "report_reason": "抗原重检"}, scopes=frozenset({"affinity"}))
            self.assertEqual(row["affinity_status"], "亲和力待检测")

    def test_manual_assay_stage_starts_badges(self):
        with self.Session() as db:
            rid = service.save(db, {"target_name": "CD1"})["id"]
            row = service.save(db, {"id": rid, "status": "待检测"})
            self.assertEqual((row["affinity_status"], row["flow_status"]), ("亲和力待检测", "流式待检测"))
            # 改订单号、One 回填订单号都不会退回合成阶段；清空到货日期才回去
            row = service.save(db, {"id": rid, "order_no": "CN100"})
            self.assertEqual(row["status"], "待检测")
            obj = db.get(DiscoverySynthesisOrder, rid)
            one_sync.apply_remote_snapshot_to_row(obj, {"order_no": "CN200"})
            self.assertEqual(obj.status, "待检测")
            row = service.save(db, {"id": rid, "arrival_date": None})
            self.assertEqual((row["status"], row["affinity_status"]), ("合成中", None))
            secreted = service.save(db, {"target_name": "IL2", "target_type": "分泌型"})["id"]
            row = service.save(db, {"id": secreted, "status": "检测中"})
            self.assertEqual((row["status"], row["flow_status"]), ("检测中", "流式不适用"))
            # 全部编辑把已完成改回检测中也算打回，两项实验回到待测
            service.save(db, {"id": rid, "status": "检测中"})
            service.save(db, {"id": rid, "affinity_status": "亲和力已完成"})
            row = service.save(db, {"id": rid, "flow_status": "流式已完成"})
            self.assertEqual(row["status"], "已完成")
            row = service.save(db, {"id": rid, "status": "检测中"})
            self.assertEqual((row["affinity_status"], row["flow_status"]), ("亲和力待检测", "流式待检测"))

    def test_assay_data_entered_before_arrival_can_be_undone(self):
        aff = frozenset({"affinity"})
        with self.Session() as db:
            rid = service.save(db, {"target_name": "CD9", "order_no": "CN9", "target_type": "I型跨膜"})["id"]
            row = service.save(db, {"id": rid, "affinity_owner": "张赞"}, scopes=aff, created_by="张赞")
            self.assertEqual((row["status"], row["affinity_status"]), ("检测中", "亲和力检测中"))
            row = service.save(db, {"id": rid, "affinity_owner": None}, scopes=aff, created_by="张赞")
            self.assertEqual((row["status"], row["affinity_status"], row["flow_status"]), ("合成中", None, None))
            # 填日期会补上本人，删掉日期还剩人员，再删人员才退回合成中
            service.save(db, {"id": rid, "affinity_date": "2026-11-01"}, scopes=aff, created_by="张赞")
            row = service.save(db, {"id": rid, "affinity_date": None}, scopes=aff, created_by="张赞")
            self.assertEqual((row["status"], row["affinity_status"]), ("检测中", "亲和力检测中"))
            row = service.save(db, {"id": rid, "affinity_owner": None}, scopes=aff, created_by="张赞")
            self.assertEqual(row["status"], "合成中")
            # 已到货时清掉人员，检测中退回待检测
            service.save(db, {"id": rid, "arrival_date": "2026-11-02"})
            service.save(db, {"id": rid, "affinity_owner": "张赞"}, scopes=aff, created_by="张赞")
            row = service.save(db, {"id": rid, "affinity_owner": None}, scopes=aff, created_by="张赞")
            self.assertEqual((row["status"], row["affinity_status"]), ("待检测", "亲和力待检测"))
            # 内部转染手动推进的待检测不因删掉误填的日期退回
            internal = service.save(db, {"target_name": "CD7", "supply_mode": "内部转染"})["id"]
            service.save(db, {"id": internal, "status": "待检测"})
            service.save(db, {"id": internal, "flow_date": "2026-11-03"})
            row = service.save(db, {"id": internal, "flow_date": None})
            self.assertEqual((row["status"], row["flow_status"]), ("待检测", "流式待检测"))
            # 分泌型没到货填了亲和力日期不自动完成，删掉还能退；补上到货日期才完成
            secreted = service.save(db, {"target_name": "IL2", "order_no": "CN2", "target_type": "分泌型"})["id"]
            row = service.save(db, {"id": secreted, "affinity_date": "2026-11-01"}, scopes=aff, created_by="张赞")
            self.assertEqual((row["status"], row["affinity_status"]), ("检测中", "亲和力已完成"))
            service.save(db, {"id": secreted, "affinity_date": None}, scopes=aff, created_by="张赞")
            row = service.save(db, {"id": secreted, "affinity_owner": None}, scopes=aff, created_by="张赞")
            self.assertEqual(row["status"], "合成中")
            service.save(db, {"id": secreted, "affinity_date": "2026-11-01"}, scopes=aff, created_by="张赞")
            row = service.save(db, {"id": secreted, "arrival_date": "2026-10-30"}, confirm_complete=True)
            self.assertEqual(row["status"], "已完成")

    def test_person_options_use_own_field_by_frequency(self):
        with self.Session() as db:
            for pm, affinity_owner in (("兰维秋", "赵雨蕾"), ("安高", "黄志诚"), ("安高", "黄志诚")):
                service.save(db, {"target_name": "CD1", "pm": pm, "affinity_owner": affinity_owner})
            options = service.get_options(db)
            self.assertEqual(options["affinity_owners"], ["黄志诚", "赵雨蕾"])
            self.assertEqual(options["pms"], ["安高", "兰维秋"])
            self.assertEqual(options["owners"], ["无人问津"])

    def test_completion_requires_confirm(self):
        affinity = frozenset({"affinity"})
        with self.Session() as db:
            rid = service.save(db, {"target_name": "CD8", "order_no": "CN3", "arrival_date": "2026-03-17"})["id"]
            service.save(db, {"id": rid, "flow_date": "2026-03-19"})
            payload = {"id": rid, "affinity_date": "2026-03-20"}
            with self.assertRaisesRegex(service.CompletionConfirmRequired, "CD8 · CN3.*完成后你将不能再改回"):
                service.save(db, dict(payload), scopes=affinity, confirm_complete=False)
            db.rollback()
            self.assertEqual(db.get(DiscoverySynthesisOrder, rid).status, "检测中")
            row = service.save(db, dict(payload), scopes=affinity)
            self.assertEqual(row["status"], "已完成")
            row = service.save(db, {"id": rid, "affinity_owner": "张赞"}, scopes=affinity, confirm_complete=False)
            self.assertEqual(row["status"], "已完成")
            # 手动选主状态已完成是明确操作，不再二次确认
            other = service.save(db, {"target_name": "CD10", "order_no": "CN4"})["id"]
            row = service.save(db, {"id": other, "status": "已完成"}, confirm_complete=False)
            self.assertEqual(row["status"], "已完成")

    def test_status_machine_and_save_workflow(self):
        with self.Session() as db:
            # 1. Create without order_no -> status is 待下单, owner is None before affinity
            row1 = service.save(
                db,
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
            self.assertEqual(row1["status"], "待下单")
            self.assertEqual(row1["target_name"], "B7-H4")
            self.assertEqual(row1["target_codes"], ["20R015"])
            self.assertEqual(row1["mouse_strain"], "RN、RNKO")
            self.assertIsNone(row1["owner"])
            self.assertEqual(row1["synthetic_count"], 118)
            self.assertEqual(row1["synthetic_date"], "2026-02-12")

            # 2. Fill order_no -> auto advances to 合成中
            row1 = service.save(db, {"id": row1["id"], "order_no": "CN2602120001585"})
            self.assertEqual(row1["status"], "合成中")

            # 3. Fill arrival_count / arrival_date -> auto advances to 待检测
            row1 = service.save(
                db,
                {"id": row1["id"], "arrival_count": 113, "arrival_date": "2026-03-17"},
            )
            self.assertEqual(row1["status"], "待检测")
            self.assertEqual(row1["affinity_status"], "亲和力待检测")
            self.assertEqual(row1["flow_status"], "流式待检测")

            # 4. Switching affinity to testing claims it; report_reason forces affinity back to waiting while keeping owner
            row1 = service.save(
                db,
                {"id": row1["id"], "affinity_status": "亲和力检测中"},
                created_by="张赞 Zan Zhang",
                scopes=frozenset({"affinity"}),
            )
            self.assertEqual(row1["status"], "检测中")
            self.assertEqual(row1["affinity_status"], "亲和力检测中")
            self.assertEqual(row1["affinity_owner"], "张赞")

            row1 = service.save(
                db,
                {
                    "id": row1["id"],
                    "affinity_date": "2026-03-25",
                    "report_reason": "抗原重检",
                    "selection_method": ["JX_P", "补挑"],
                },
            )
            self.assertEqual((row1["selection_method"], row1["is_rechoose"]), ("JX_P", "是"))
            self.assertEqual(row1["status"], "待检测")
            self.assertEqual(row1["affinity_status"], "亲和力待检测")
            self.assertEqual(row1["affinity_owner"], "张赞")

            # Clearing report_reason with affinity_date completes affinity; flow remains parallel until flow_date is set
            row1 = service.save(
                db,
                {"id": row1["id"], "report_reason": None, "affinity_date": "2026-03-26"},
            )
            self.assertEqual(row1["status"], "检测中")
            self.assertEqual(row1["affinity_status"], "亲和力已完成")
            self.assertEqual(row1["flow_status"], "流式待检测")
            self.assertIsNone(row1["affinity_result"])

            row1 = service.save(db, {"id": row1["id"], "flow_date": "2026-03-28"})
            self.assertEqual(row1["flow_status"], "流式已完成")
            self.assertEqual(row1["status"], "已完成")

            # 5. Engineering order with multi-value eng_type & eng_method joined with '、',
            #    and auto-fills pm (not owner) from created_by
            row2 = service.save(
                db,
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
            self.assertEqual(row2["target_name"], "SLC3A2")
            self.assertEqual(row2["target_codes"], ["20R389"])
            self.assertEqual(row2["status"], "合成中")
            self.assertEqual(row2["priority"], "加急")
            self.assertEqual(row2["eng_type"], "亲和力、Tm")
            self.assertEqual(row2["eng_method"], "AI、NGS姐妹克隆")
            self.assertIsNone(row2["owner"])
            self.assertEqual(row2["pm"], "王子豪")

            # 6. Default list order is id desc; completed row1 has left the active queue.
            default_list = service.get_list(db, {})["items"]
            self.assertEqual(default_list[0]["id"], row2["id"])
            queue_list = service.get_list(db, {"sort_field": "sort_order"})["items"]
            self.assertEqual(queue_list[0]["id"], row2["id"])
            self.assertEqual(queue_list[0]["sort_order"], 1)
            self.assertIsNone(queue_list[1]["sort_order"])

            # 7. PM 新建：pm 自动填本人，负责人留空
            pm_created = service.save(
                db,
                {"target_name": "CD6", "eng_requirement": "提高Tm"},
                created_by="兰维秋",
                scopes=frozenset({"pm"}),
            )
            self.assertEqual((pm_created["pm"], pm_created["owner"]), ("兰维秋", None))

            # 整单已完成后改实验状态要先打回，全部编辑也一样；单项实验员不能打回
            for scopes in (frozenset({"affinity"}), frozenset({"full"})):
                with self.assertRaisesRegex(ValueError, "先打回待检测"):
                    service.save(
                        db, {"id": row1["id"], "affinity_status": "亲和力检测中"}, created_by="张赞", scopes=scopes
                    )
            with self.assertRaises(PermissionError):
                service.save(db, {"id": row1["id"], "status": "待检测"}, scopes=frozenset({"flow"}))
            reopened = service.save(db, {"id": row1["id"], "status": "待检测"})
            self.assertEqual(
                (reopened["status"], reopened["affinity_status"], reopened["flow_status"]),
                ("待检测", "亲和力待检测", "流式待检测"),
            )
            service.save(db, {"id": row1["id"], "affinity_status": "亲和力检测中"}, created_by="张赞")
            reopened = service.save(db, {"id": row1["id"], "flow_status": "流式已完成"})
            self.assertEqual(reopened["status"], "检测中")
            self.assertEqual(
                service.get_list(db, {"status": ["亲和力检测中", "流式已完成"]})["total"],
                1,
            )

            # 两项实验手动标完成（不填日期）也整单完成，之后改备注保持已完成
            manual = service.save(
                db,
                {"id": pm_created["id"], "affinity_status": "亲和力已完成", "flow_status": "流式已完成"},
                created_by="兰维秋",
                scopes=frozenset({"affinity", "flow"}),
            )
            self.assertEqual(manual["status"], "已完成")
            manual = service.save(db, {"id": pm_created["id"], "remark": "手工状态保持"})
            self.assertEqual(manual["status"], "已完成")

    def test_claim_and_scope_rules(self):
        pm = frozenset({"pm"})
        with self.Session() as db:
            rid = service.save(db, {"target_name": "CD6", "pm": "兰维秋"})["id"]
            # 空负责人不能认领；全部编辑在空与无人问津间切换
            with self.assertRaisesRegex(ValueError, "尚未开放认领"):
                service.claim_order(db, rid, "张赞", scopes=pm)
            self.assertEqual(service.claim_order(db, rid, None)["owner"], "无人问津")
            # PM 认领后他人不能再认领，7 天内可退回
            self.assertEqual(service.claim_order(db, rid, "张赞", scopes=pm)["owner"], "张赞")
            with self.assertRaisesRegex(ValueError, "不可重复认领"):
                service.claim_order(db, rid, "兰维秋", scopes=pm)
            self.assertEqual(service.claim_order(db, rid, "张赞", scopes=pm)["owner"], "无人问津")
            # 超过 7 天不能退回，也不能转给别人
            service.claim_order(db, rid, "张赞", scopes=pm)
            db.get(DiscoverySynthesisOrder, rid).owner_claimed_at = now_local() - timedelta(days=8)
            with self.assertRaisesRegex(ValueError, "超过 7 天"):
                service.claim_order(db, rid, "张赞", scopes=pm)
            with self.assertRaisesRegex(PermissionError, "超过 7 天"):
                service.save(db, {"id": rid, "owner": "无人问津"}, created_by="张赞", scopes=pm)
            with self.assertRaisesRegex(PermissionError, "只能认领"):
                service.save(db, {"id": rid, "owner": "兰维秋"}, created_by="张赞", scopes=pm)
            with self.assertRaisesRegex(ValueError, "已由 张赞 负责"):
                service.claim_order(db, rid, None)
            # 已认领的工单只归负责人，PM 本人也不能改；PM 字段、靶点类型 PM 都不能改
            with self.assertRaisesRegex(PermissionError, "只有负责人"):
                service.save(db, {"id": rid, "remark": "x"}, created_by="兰维秋", scopes=pm)
            with self.assertRaisesRegex(PermissionError, "只有负责人"):
                service.delete(db, rid, scopes=pm, actor_name="兰维秋")
            service.save(db, {"id": rid, "remark": "x"}, created_by="张赞", scopes=pm)
            for field in ("pm", "target_type", "experiment_id"):
                with self.assertRaisesRegex(PermissionError, "不可修改该字段"):
                    service.save(db, {"id": rid, field: "x"}, created_by="张赞", scopes=pm)
            with self.assertRaisesRegex(PermissionError, "需通过认领"):
                service.save(db, {"target_name": "CD7", "owner": "兰维秋"}, created_by="兰维秋", scopes=pm)
            # 没有负责人时归 PM
            other = service.save(db, {"target_name": "CD7", "pm": "兰维秋"})["id"]
            with self.assertRaisesRegex(PermissionError, "只有本人是 PM"):
                service.save(db, {"id": other, "remark": "x"}, created_by="张赞", scopes=pm)
            service.save(db, {"id": other, "remark": "x"}, created_by="兰维秋", scopes=pm)
            # 实验员权限按亲和力 / 流式拆分
            with self.assertRaises(PermissionError):
                service.save(db, {"id": rid, "flow_note": "x"}, scopes=frozenset({"affinity"}))
            with self.assertRaises(PermissionError):
                service.save(db, {"id": rid, "affinity_result": "x"}, scopes=frozenset({"flow"}))
            # 亲和力实验员填日期时，空的亲和力人员自动填本人，已有人员不覆盖
            affinity = frozenset({"affinity"})
            row = service.save(db, {"id": other, "affinity_date": "2026-11-03"}, created_by="张赞 Zan", scopes=affinity)
            self.assertEqual(row["affinity_owner"], "张赞")
            row = service.save(db, {"id": other, "affinity_date": "2026-11-04"}, created_by="兰维秋", scopes=affinity)
            self.assertEqual(row["affinity_owner"], "张赞")

    def test_affinity_owner_multi_and_autofill(self):
        affinity = frozenset({"affinity"})
        with self.Session() as db:
            rid = service.save(db, {"target_name": "CD8", "order_no": "CN8", "arrival_date": "2026-11-01"})["id"]
            row = service.save(db, {"id": rid, "affinity_owner": ["张赞", "黄志诚", "张赞"]})
            self.assertEqual(row["affinity_owner"], "张赞、黄志诚")
            # 已有人员时实验员改检测中不追加本人
            row = service.save(db, {"id": rid, "affinity_status": "亲和力检测中"}, created_by="兰维秋", scopes=affinity)
            self.assertEqual(row["affinity_owner"], "张赞、黄志诚")
            # 打回待检测保留人员
            row = service.save(db, {"id": rid, "affinity_status": "亲和力待检测"})
            self.assertEqual(row["affinity_owner"], "张赞、黄志诚")
            # 管理员改检测中不填本人，实验员在为空时填本人
            service.save(db, {"id": rid, "affinity_owner": None})
            row = service.save(db, {"id": rid, "affinity_status": "亲和力检测中"}, created_by="管理员")
            self.assertIsNone(row["affinity_owner"])
            service.save(db, {"id": rid, "affinity_status": "亲和力待检测"})
            row = service.save(db, {"id": rid, "affinity_status": "亲和力检测中"}, created_by="兰维秋", scopes=affinity)
            self.assertEqual(row["affinity_owner"], "兰维秋")

            options = service.get_options(db)
            self.assertEqual(options["affinity_owners"], ["兰维秋"])
            values = service.get_column_values(db, {"field": "affinity_owner"})["items"]
            self.assertEqual([item["value"] for item in values], ["兰维秋"])
            service.save(db, {"id": rid, "affinity_owner": "张赞+黄志诚"})
            found = service.get_list(db, {"field_filters": [{"field": "affinity_owner", "values": ["黄志诚"]}]})
            self.assertEqual([item["id"] for item in found["items"]], [rid])

    def test_create_requires_fields(self):
        pm = frozenset({"pm"})
        base = {"order_kind": "改造", "supply_mode": "合成到货", "mouse_strain": "RM", "target_name": "CD6"}
        eng = {"eng_type": "Tm", "eng_method": "AI", "eng_parent_seq": "VH1", "eng_requirement": "提高Tm"}
        with self.Session() as db:
            with self.assertRaisesRegex(ValueError, "订单性质、供应方式、小鼠品系、PM、靶点$"):
                service.save(db, {}, require_fields=True)
            db.rollback()
            with self.assertRaisesRegex(ValueError, "改造类型、改造方式、母本序列、改造要求$"):
                service.save(db, base, created_by="兰维秋", scopes=pm, require_fields=True)
            db.rollback()
            row = service.save(db, {**base, **eng}, created_by="兰维秋", scopes=pm, require_fields=True)
            self.assertEqual(row["pm"], "兰维秋")

    def test_engineering_experimenter_rules(self):
        eng = frozenset({"eng"})
        need = {"order_kind": "常规合成", "mouse_strain": "RM", "target_name": "CD6"}
        with self.Session() as db:
            with self.assertRaisesRegex(PermissionError, "只能操作改造"):
                service.save(db, {**need, "supply_mode": "合成到货"}, created_by="李四 Li Si", scopes=eng, require_fields=True)
            db.rollback()
            row = service.save(
                db, {**need, "supply_mode": "内部转染"}, created_by="李四 Li Si", scopes=eng, require_fields=True
            )
            self.assertEqual((row["pm"], row["order_sender"], row["synthetic_corp"]), ("李四", "李四 Li Si", "内部"))
            rid = row["id"]
            saved = service.save(
                db, {"id": rid, "pm": "张赞", "arrival_date": "2026-11-03", "synthetic_corp": "擎科"}, scopes=eng
            )
            self.assertEqual((saved["pm"], saved["synthetic_corp"]), ("张赞", "擎科"))
            for field in ("owner", "flow_note", "affinity_result"):
                with self.assertRaisesRegex(PermissionError, "不可修改该字段"):
                    service.save(db, {"id": rid, field: "x"}, created_by="李四", scopes=eng)
                db.rollback()
            with self.assertRaisesRegex(PermissionError, "只能操作改造"):
                service.save(db, {"id": rid, "supply_mode": "合成到货"}, created_by="李四", scopes=eng)
            db.rollback()
            normal = service.save(db, {"target_name": "CD7"})["id"]
            with self.assertRaisesRegex(PermissionError, "只能操作改造"):
                service.save(db, {"id": normal, "remark": "x"}, created_by="李四", scopes=eng)
            db.rollback()
            with self.assertRaisesRegex(PermissionError, "只能操作改造"):
                service.delete(db, normal, scopes=eng, actor_name="李四")
            db.rollback()
            service.save(db, {"id": rid, "status": "已取消"}, scopes=eng)
            service.delete(db, rid, scopes=eng, actor_name="李四")
            self.assertIsNone(db.get(DiscoverySynthesisOrder, rid))
            # 改造类新建默认内部，关联 One 后按 One 的合成公司走；兼有 PM 权限时负责人可把本人工单改回常规
            arrival = service.save(db, {"order_kind": "改造", "target_name": "CD8"}, created_by="李四", scopes=eng)
            self.assertEqual(arrival["synthetic_corp"], "内部")
            linked = db.get(DiscoverySynthesisOrder, arrival["id"])
            one_sync.apply_remote_snapshot_to_row(linked, {"order_no": "CN1", "synthetic_corp": "君跻"})
            self.assertEqual(linked.synthetic_corp, "君跻")
            both = frozenset({"pm", "eng"})
            saved = service.save(db, {"id": arrival["id"], "order_kind": "常规合成"}, created_by="李四", scopes=both)
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

    def test_one_batch_and_target_parsing(self):
        self.assertTrue(one_sync.is_manual_batch("23R037_RM_C_W_M1_20261102_20clones_20261103_to君跻_M.xlsx"))
        self.assertTrue(one_sync.is_manual_batch(None, "23R037_RM_C_W_M12_20261102"))
        self.assertFalse(one_sync.is_manual_batch("20R430_RM_C_W_S1_20261102_20clones_20261103_to君跻_M.xlsx"))
        self.assertFalse(one_sync.is_manual_batch("CD6_M1_20clones.xlsx"))
        self.assertEqual(one_sync.parse_one_target("[20R147]MCSP"), (["20R147"], "MCSP"))
        self.assertEqual(one_sync.parse_one_target("FN1", "21R009_RL_B_K_S1", None), (["21R009"], "FN1"))
        self.assertEqual(one_sync.parse_one_target("FN1", "FN1_RL_B_K_S1"), ([], "FN1"))

    def test_sync_from_one_creates_new_orders(self):
        def snap(sid, refstr, **extra):
            return {
                "source_one_type": "ngs",
                "source_one_id": sid,
                "refstr": refstr,
                "order_no": None,
                "synthetic_corp": "君跻",
                "synthetic_count": 20,
                "synthetic_date": "2026-11-03",
                "arrival_count": None,
                "arrival_date": None,
                "order_sender": "陶俊先 Junxian Tao",
                **extra,
            }

        file_a = "20R430_RM_C_W_S1_20261102_20clones_20261103_to君跻_M.xlsx"
        file_b = "21R001_RM_C_W_S2_20261102_10clones_20261103_to君跻_M.xlsx"
        new_a = snap(
            201, file_a, order_no="CN001", batch_label="20R430_RM_C_W_S1_20261102",
            synthesis_code="20R430_RMCWS1", task_target="[20R430]PD-L1",
        )
        new_b = snap(202, file_b, synthesis_code="21R001_RMCWS2", task_target="[21R001]XYZ")
        manual = snap(203, "23R037_RM_C_W_M1_20261102_20clones_20261103_to君跻_M.xlsx", order_no="CN003")
        known_order = snap(204, "x_20clones.xlsx", order_no="CN999")
        remote = [new_a, new_b, manual, known_order]

        def fake_fetch(_one_db, condition, params, *_args):
            if "created" in condition:
                return list(remote)
            return [item for item in remote if item["refstr"] in params["refs"]]

        def run_sync(db):
            with patch("modules.discovery.synthesis_progress.one_sync.open_one_db") as mock_open, patch(
                "modules.discovery.synthesis_progress.one_sync.fetch_remote_snapshots_by_ids", return_value={}
            ), patch(
                "modules.discovery.synthesis_progress.one_sync._query_candidates_for_rows", return_value=[]
            ), patch("modules.discovery.synthesis_progress.one_sync._fetch_snapshots", side_effect=fake_fetch):
                mock_open.return_value.__enter__.return_value = object()
                return service.sync_from_one(db)

        with self.Session() as db:
            service.save(
                db,
                {
                    "target_name": "PD-L1",
                    "batch_label": "20R430_RM_C_W_S1_20261102",
                    "synthesis_code": "20R430_RMCWS1",
                    "priority": "加急",
                    "owner": "张三",
                    "pm": "李四",
                    "project_code": "P001",
                    "mouse_strain": "RMB/C",
                },
                created_by="tester",
            )
            service.save(db, {"target_name": "OLD", "order_no": "cn999"}, created_by="tester")

            res = run_sync(db)
            self.assertEqual(res["created"], 2)
            rows = {row.source_one_id: row for row in db.query(DiscoverySynthesisOrder).all() if row.source_one_id}
            self.assertEqual(set(rows), {201, 202})

            row_a = rows[201]
            self.assertEqual(row_a.created_by, "One同步")
            self.assertEqual(row_a.status, "合成中")
            self.assertEqual(row_a.order_no, "CN001")
            self.assertEqual(row_a.order_sender, "陶俊先 Junxian Tao")
            self.assertEqual((row_a.owner, row_a.pm, row_a.project_code, row_a.priority), (None, "李四", "P001", "加急"))
            self.assertEqual((row_a.target_codes, row_a.target_name), (["20R430"], "PD-L1"))

            row_b = rows[202]
            self.assertEqual(row_b.status, "待下单")
            self.assertEqual(row_b.target_codes, ["21R001"])
            self.assertEqual(row_b.mouse_strain, "RMB/C")

            with self.assertRaisesRegex(ValueError, "已关联 One 订单"):
                service.delete(db, row_a.id)

            # 同文件另一条后来才下单：改绑已建的待下单行，不再新建
            remote.append(snap(205, file_b, order_no="CN005", synthesis_code="21R001_RMCWS2"))
            res = run_sync(db)
            self.assertEqual(res["created"], 0)
            db.refresh(row_b)
            self.assertEqual((row_b.source_one_id, row_b.order_no, row_b.status), (205, "CN005", "合成中"))
            self.assertEqual(db.query(DiscoverySynthesisOrder).count(), 4)

    def test_sync_from_one_and_drift_adoption(self):
        fake_snap = {
            "source_one_type": "ngs",
            "source_one_id": 101,
            "synthesis_code": "20R282_RNBK01",
            "order_no": "CN2602120001585",
            "synthetic_corp": "君跻",
            "synthetic_count": 118,
            "synthetic_date": "2026-02-12",
            "arrival_count": None,
            "arrival_date": None,
            "order_sender": "陶俊先 Junxian Tao",
            "order_state": "进行中",
        }
        with self.Session() as db:
            created = service.save(
                db,
                {
                    "target_name": "CD6",
                    "batch_label": "CD6_RN_B_K_01_20260208_1",
                    "synthesis_code": "20R282_RNBK01",
                },
                created_by="tester",
            )
            row_id = created["id"]
            self.assertEqual(created["status"], "待下单")

            with patch(
                "modules.discovery.synthesis_progress.one_sync.open_one_db"
            ) as mock_open, patch(
                "modules.discovery.synthesis_progress.one_sync.fetch_remote_snapshots_by_ids",
                return_value={},
            ), patch(
                "modules.discovery.synthesis_progress.one_sync._query_candidates_for_rows",
                return_value=[fake_snap],
            ):
                mock_open.return_value.__enter__.return_value = object()
                sync_res = service.sync_from_one(db)
                self.assertEqual(sync_res["linked"], 1)

            items = service.get_list(db, {})["items"]
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["status"], "合成中")
            self.assertEqual(items[0]["order_no"], "CN2602120001585")
            self.assertEqual(items[0]["batch_label"], "CD6_RN_B_K_01_20260208_1")
            self.assertEqual(items[0]["order_sender"], "陶俊先 Junxian Tao")
            self.assertFalse(items[0]["has_drift"])

            updated_remote = {
                ("ngs", 101): {
                    **fake_snap,
                    "order_sender": "任鸿滨 Hongbin Ren",
                    "synthetic_count": 120,
                    "arrival_count": 115,
                    "arrival_date": "2026-03-17",
                }
            }
            with patch(
                "modules.discovery.synthesis_progress.one_sync.open_one_db"
            ) as mock_open2, patch(
                "modules.discovery.synthesis_progress.one_sync.fetch_remote_snapshots_by_ids",
                return_value=updated_remote,
            ):
                mock_open2.return_value.__enter__.return_value = object()
                check_res = service.check_remote_for_local_rows(db, [row_id])
                self.assertTrue(check_res["remote_available"])
                patched = check_res["updated_items"][0]
                self.assertEqual(patched["arrival_count"], 115)
                self.assertEqual(patched["arrival_date"], "2026-03-17")
                self.assertEqual(patched["status"], "待检测")
                self.assertEqual(patched["synthetic_count"], 118)
                self.assertEqual(patched["order_sender"], "任鸿滨 Hongbin Ren")
                self.assertTrue(patched["has_drift"])
                self.assertEqual(patched["drift_fields"][0]["field"], "synthetic_count")
                self.assertEqual(patched["drift_fields"][0]["remote"], "120")

            adopted = service.adopt_source(db, row_id, ["synthetic_count"])
            self.assertEqual(adopted["synthetic_count"], 120)
            self.assertFalse(adopted["has_drift"])
            manual_sender = service.save(db, {"id": row_id, "order_sender": "手填"})
            self.assertEqual(manual_sender["order_sender"], "任鸿滨 Hongbin Ren")
            for label in ("CD6_RN_B_K_01_20260208_1（补挑）", "CD6_RN_B_K_01_20260208_1"):
                relabeled = service.save(db, {"id": row_id, "batch_label": label})
                self.assertEqual(
                    (relabeled["source_one_id"], relabeled["order_no"], relabeled["order_sender"]),
                    (101, "CN2602120001585", "任鸿滨 Hongbin Ren"),
                )

            # A no-op background remote check must not overwrite a manually chosen main status.
            service.save(db, {"id": row_id, "status": "已完成"})
            with patch(
                "modules.discovery.synthesis_progress.one_sync.open_one_db"
            ) as mock_open_same, patch(
                "modules.discovery.synthesis_progress.one_sync.fetch_remote_snapshots_by_ids",
                return_value=updated_remote,
            ):
                mock_open_same.return_value.__enter__.return_value = object()
                service.check_remote_for_local_rows(db, [row_id])
            self.assertEqual(service.get_list(db, {})["items"][0]["status"], "已完成")

            # Duplicate entry check: creating a second row with the same batch_label/order_no
            # when One DB has no other untaken record returns duplicates info
            dup_row = service.save(
                db,
                {
                    "target_name": "CD6",
                    "batch_label": "CD6_RN_B_K_01_20260208_1",
                    "order_no": "CN2602120001585",
                },
                created_by="tester",
            )
            with patch(
                "modules.discovery.synthesis_progress.one_sync.open_one_db"
            ) as mock_open3, patch(
                "modules.discovery.synthesis_progress.one_sync._query_candidates_for_rows",
                return_value=[fake_snap],
            ):
                mock_open3.return_value.__enter__.return_value = object()
                dup_check = service.check_remote_for_local_rows(db, [dup_row["id"]])
                self.assertEqual(dup_check["linked"], 0)
                dup_info = dup_check["duplicates"].get(str(dup_row["id"]), {})
                self.assertIn("CN2602120001585", dup_info.get("batch_label", []))
                self.assertIn("CD6_RN_B_K_01_20260208_1", dup_info.get("order_no", []))

            # Candidate switching check: when a synthesis_code has a second untaken order in One DB,
            # candidates list includes it, and switching order_no replaces auto-filled values cleanly
            second_snap = {
                "source_one_type": "ngs",
                "source_one_id": 102,
                "synthesis_code": "20R282_RNBK01",
                "batch_label": "CD6_RN_B_K_01_20260208_2",
                "order_no": "BAO0000888",
                "synthetic_corp": "擎科",
                "synthetic_count": 66,
                "synthetic_date": "2026-03-01",
                "arrival_count": None,
                "arrival_date": None,
                "order_state": "进行中",
                "task_projectid": "CD6_RN_B_K_01_20260208_2",
            }
            with patch(
                "modules.discovery.synthesis_progress.one_sync.open_one_db"
            ) as mock_open4, patch(
                "modules.discovery.synthesis_progress.one_sync.fetch_remote_snapshots_by_ids",
                return_value=updated_remote,
            ), patch(
                "modules.discovery.synthesis_progress.one_sync._query_candidates_for_rows",
                return_value=[fake_snap, second_snap],
            ):
                mock_open4.return_value.__enter__.return_value = object()
                cand_res = service.check_remote_for_local_rows(db, [row_id])
                cands = cand_res["candidates"].get(str(row_id), [])
                self.assertEqual(len(cands), 1)
                self.assertEqual(cands[0]["order_no"], "BAO0000888")

                # User switches row_id to BAO0000888 -> auto-filled synthetic_corp/date update to second_snap
                service.save(db, {"id": row_id, "order_no": "BAO0000888"})
                switched_res = service.check_remote_for_local_rows(db, [row_id])
                switched_item = switched_res["updated_items"][0]
                self.assertEqual(switched_item["source_one_id"], 102)
                self.assertEqual(switched_item["synthetic_corp"], "擎科")
                self.assertEqual(switched_item["synthetic_date"], "2026-03-01")
                self.assertIsNone(switched_item["order_sender"])

    def test_internal_supply_rows_link_only_by_order_or_batch(self):
        remote = {
            "source_one_type": "ngs",
            "source_one_id": 301,
            "synthesis_code": "20R383_RNBK01",
            "order_no": "BAO0000310",
            "synthetic_count": 192,
            "synthetic_date": "2026-03-26",
            "task_projectid": "FCGR2A_RN_B_K_01_20251115",
        }

        def check(db, row_id):
            with patch("modules.discovery.synthesis_progress.one_sync.open_one_db") as mock_open, patch(
                "modules.discovery.synthesis_progress.one_sync.fetch_remote_snapshots_by_ids", return_value={}
            ), patch(
                "modules.discovery.synthesis_progress.one_sync._query_candidates_for_rows", return_value=[remote]
            ):
                mock_open.return_value.__enter__.return_value = object()
                return service.check_remote_for_local_rows(db, [row_id])

        with self.Session() as db:
            subtype = service.save(
                db,
                {"target_name": "FCGR2A", "supply_mode": "改亚型", "synthesis_code": "20R383_RNBK01",
                 "batch_label": "FCGR2A_RNBK01", "synthetic_count": 564},
            )
            self.assertEqual(check(db, subtype["id"])["linked"], 0)
            service.save(db, {"id": subtype["id"], "batch_label": "FCGR2A_RN_B_K_01_20251115"})
            self.assertEqual(check(db, subtype["id"])["linked"], 1)

    def test_remote_snapshot_keeps_uploader_as_order_sender(self):
        snap = one_sync.build_remote_snapshot("beacon", {"id": 7, "uploader": "任鸿滨 Hongbin Ren"})
        self.assertEqual(snap["order_sender"], "任鸿滨 Hongbin Ren")
        self.assertIsNone(one_sync.build_remote_snapshot("ngs", {"id": 8})["order_sender"])
        picked = one_sync.build_remote_snapshot("ngs", {"id": 9, "selectmethod": "补挑,D_JX", "isrechooseorder": "false"})
        self.assertEqual((picked["selection_method"], picked["is_rechoose"]), ("D_JX", "是"))
        self.assertEqual(one_sync.build_remote_snapshot("ngs", {"id": 10, "isrechooseorder": "false"})["is_rechoose"], "否")

    def test_queue_shift_is_one_bulk_update(self):
        with self.Session() as db:
            ids = [service.save(db, {"target_name": f"T{i}"}, created_by="测试员")["id"] for i in range(4)]
            statements = []

            def capture(_conn, _cursor, statement, parameters, _context, executemany):
                if statement.lstrip().upper().startswith("UPDATE DISCOVERY_SYNTHESIS_ORDER"):
                    statements.append(len(parameters) if executemany else 1)

            event.listen(self.engine, "before_cursor_execute", capture)
            try:
                service.save(db, {"id": ids[0], "status": "已取消"})
            finally:
                event.remove(self.engine, "before_cursor_execute", capture)
            # 出队行自己一条，后面三行顺移合成一条
            self.assertEqual(statements, [1, 1])
        with self.Session() as db:
            orders = dict(db.execute(select(DiscoverySynthesisOrder.id, DiscoverySynthesisOrder.sort_order)).all())
        self.assertEqual([orders[i] for i in ids], [None, 1, 2, 3])

    def test_lock_queue_renews_snapshot_only_before_writes(self):
        with self.Session() as db:
            rid = service.save(db, {"target_name": "T1"}, created_by="测试员")["id"]
            commits = []
            event.listen(db, "after_commit", commits.append)
            # 只读过（如登录校验）就先提交，加锁后的读取不再用等锁前的快照
            db.get(DiscoverySynthesisOrder, rid)
            lock_queue(db, DiscoverySynthesisOrder)
            self.assertEqual(len(commits), 1)
            # 已有未提交的改动、flush 过或批量 UPDATE 过都不能提前提交
            db.get(DiscoverySynthesisOrder, rid).remark = "未提交"
            lock_queue(db, DiscoverySynthesisOrder)
            db.flush()
            lock_queue(db, DiscoverySynthesisOrder)
            db.rollback()
            db.execute(update(DiscoverySynthesisOrder).values(remark="批量"))
            lock_queue(db, DiscoverySynthesisOrder)
            db.rollback()
            self.assertEqual(len(commits), 1)
            self.assertIsNone(db.get(DiscoverySynthesisOrder, rid).remark)


class SynthesisHeaderFilterTests(DbTestCase):
    tables = (Target, DiscoverySynthesisOrder)
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
        with self.Session() as db:
            for index, row in enumerate(self.ROWS, start=1):
                db.add(DiscoverySynthesisOrder(
                    synthesis_order_id=f"SO{index:03d}",
                    order_kind="常规",
                    supply_mode="自合成",
                    **row,
                ))
            db.commit()

    def codes(self, *field_filters, **extra):
        with self.Session() as db:
            data = {"limit": 50, "field_filters": list(field_filters), **extra}
            return sorted(item["synthesis_code"] for item in service.get_list(db, data)["items"])

    def values(self, field, **extra):
        with self.Session() as db:
            return service.get_column_values(db, {"field": field, **extra})

    def test_values_and_exclude_handle_blank(self):
        self.assertEqual(self.codes({"field": "owner", "values": ["甲"]}), ["S001", "S004"])
        self.assertEqual(self.codes({"field": "owner", "values": ["乙", ""]}), ["S002", "S003"])
        self.assertEqual(self.codes({"field": "owner", "exclude": ["甲"]}), ["S002", "S003"])
        self.assertEqual(self.codes({"field": "owner", "exclude": ["甲", ""]}), ["S002"])
        self.assertEqual(self.codes({"field": "remark", "exclude": [""]}), ["S001", "S003"])

    def test_conditions(self):
        self.assertEqual(
            self.codes({"field": "remark", "condition": {"op": "contains", "value": "100%"}}),
            ["S003"],
        )
        self.assertEqual(
            self.codes({"field": "remark", "condition": {"op": "not_contains", "value": "首"}}),
            ["S002", "S003", "S004"],
        )
        self.assertEqual(
            self.codes({"field": "synthetic_count", "condition": {"op": "gte", "value": "50"}}),
            ["S002", "S004"],
        )
        self.assertEqual(
            self.codes({"field": "synthetic_date", "condition": {
                "op": "between", "value": "2026-02-01", "value2": "2026-03-31"}}),
            ["S002", "S004"],
        )
        self.assertEqual(
            self.codes({"field": "synthetic_date", "condition": {"op": "blank"}}),
            ["S003"],
        )
        self.assertEqual(
            self.codes({"field": "synthetic_date", "condition": {
                "op": "between", "value": "2026/2/1", "value2": "2026.3.31"}}),
            ["S002", "S004"],
        )
        with self.assertRaises(ValueError):
            self.codes({"field": "synthetic_date", "condition": {"op": "gte", "value": "2026-13-01"}})
        with self.assertRaises(ValueError):
            self.codes({"field": "synthetic_date", "condition": {"op": "gte", "value": "01/01/2026"}})
        with self.assertRaises(ValueError):
            self.codes({"field": "sort_order", "values": ["1"]})

    def test_multi_value_columns(self):
        self.assertEqual(self.codes({"field": "mouse_strain", "values": ["RN"]}), ["S001", "S002"])
        self.assertEqual(self.codes({"field": "mouse_strain", "exclude": ["RN"]}), ["S003", "S004"])
        strains = self.values("mouse_strain")["items"]
        self.assertEqual(
            {item["value"]: item["count"] for item in strains},
            {"RN": 2, "RNKO": 2, "": 1},
        )
        self.assertEqual(
            self.codes({"field": "target_name", "values": ["PD-L1"]}),
            ["S001", "S002", "S004"],
        )
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
        self.assertEqual(
            self.codes({"field": "target_name", "values": [searched[0]["value"]]}),
            ["S001", "S002", "S004"],
        )
        self.assertEqual(
            self.codes({"field": "target_name", "colors": ["red"]}),
            ["S001"],
        )

    def test_target_codes_and_order_sender_columns(self):
        raw = self.db.connection().connection.dbapi_connection
        raw.create_function("json_length", 1, lambda value: len(json.loads(value or "[]")))
        raw.create_function(
            "json_overlaps", 2, lambda left, right: bool(set(json.loads(left or "[]")) & set(json.loads(right or "[]")))
        )
        self.assertEqual(self.codes({"field": "target_codes", "values": ["20R002"]}), ["S003", "S004"])
        self.assertEqual(self.codes({"field": "target_codes", "exclude": ["20R001"]}), ["S003"])
        listed = self.values("target_codes")["items"]
        self.assertEqual({item["value"]: item["count"] for item in listed}, {"20R001": 3, "20R002": 2})
        with self.Session() as db:
            db.execute(update(DiscoverySynthesisOrder).where(DiscoverySynthesisOrder.synthesis_code == "S001")
                       .values(order_sender="任鸿滨", affinity_owner="张三、李四"))
            db.execute(update(DiscoverySynthesisOrder).where(DiscoverySynthesisOrder.synthesis_code == "S002")
                       .values(is_rechoose="是"))
            db.commit()
        self.assertEqual(self.codes({"field": "order_sender", "values": ["任鸿滨"]}), ["S001"])
        self.assertEqual(self.codes(order_sender="任鸿滨"), ["S001"])
        self.assertEqual(self.codes(affinity_owner=["李四"]), ["S001"])
        self.assertEqual(self.codes(is_rechoose="是"), ["S002"])
        self.assertEqual(self.values("order_sender")["items"], [{"value": "任鸿滨", "count": 1}, {"value": "", "count": 3}])

    def test_status_header_includes_assay_sub_statuses(self):
        with self.Session() as db:
            for code, status, affinity, flow in (
                ("S005", "检测中", "亲和力已完成", "流式待检测"),
                ("S006", "待检测", "亲和力待检测", "流式待检测"),
                ("S007", "已完成", "亲和力已完成", "流式已完成"),
            ):
                db.add(DiscoverySynthesisOrder(
                    synthesis_order_id=f"SO{code}", order_kind="常规", supply_mode="自合成",
                    synthesis_code=code, status=status, affinity_status=affinity, flow_status=flow,
                ))
            db.commit()
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
        with self.Session() as db:
            rows = service.get_list(db, {"limit": 50, "sort_field": "status", "sort_dir": "desc"})["items"]
            self.assertEqual([row["status"] for row in rows], ["已完成", "合成中", "合成中", "待下单"])
            rows = service.get_list(db, {"limit": 50, "sort_field": "owner", "sort_dir": "asc"})["items"]
            self.assertEqual([row["owner"] for row in rows], ["乙", "甲", "甲", None])
            rows = service.get_list(db, {"limit": 50, "sort_field": "owner", "sort_dir": "desc"})["items"]
            self.assertEqual([row["owner"] for row in rows], ["甲", "甲", "乙", None])

    def test_stats_and_export_follow_header_filters(self):
        header = [{"field": "status", "exclude": ["合成中"]}]
        with self.Session() as db:
            data = service.get_list(db, {"limit": 50, "field_filters": header})
            self.assertEqual(data["total"], 2)
            self.assertEqual(data["stats"]["all"], 2)
            self.assertEqual(data["stats"]["synthesizing"], 0)
            with patch.object(service, "build_list_workbook", side_effect=lambda **kw: kw) as built:
                service.export_list_workbook(db, {
                    "field_filters": header, "sort_field": "synthesis_code", "sort_dir": "desc",
                })
            rows = built.call_args.kwargs["rows"]
            code_at = [h for h, _ in service.EXPORT_COLUMNS].index("送测转码")
            self.assertEqual([row[code_at] for row in rows], ["S003", "S001"])

    def test_search_mode_text_columns(self):
        found = self.values("remark", value_keyword="补做", value_order="recent")["items"]
        self.assertEqual(found, [{"value": "补做 100%", "count": 1}])

    def test_value_search_keeps_list_keyword(self):
        listed = self.values("owner", keyword="S00")["items"]
        self.assertEqual({item["value"]: item["count"] for item in listed}, {"甲": 2, "乙": 1, "": 1})
        listed = self.values("owner", keyword="PD-L1", value_keyword="甲")["items"]
        self.assertEqual(listed, [{"value": "甲", "count": 2}])
        self.assertEqual(
            self.codes({"field": "eng_result", "condition": {"op": "blank"}}),
            ["S001", "S002", "S003", "S004"],
        )


if __name__ == "__main__":
    unittest.main()
