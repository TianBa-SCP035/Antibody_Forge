"""免疫工作台队列、筛选、权限范围与方案保存规则。"""

from core.errors import ConflictError, ForbiddenError
from models.immunology import (
    SerumImmMouse,
    SerumImmProject,
    SerumImmWorkbench,
)
from models.target import Target
from modules.auth.permissions import UserContext
from modules.immunology.serum import service as serum_service
from modules.immunology.serum.service import EXPERIMENT_RELATED_MODELS
from modules.immunology.workbench import routes as workbench_routes
import modules.immunology.workbench.service as workbench_service
from support import DbTestCase


class WorkbenchTestCase(DbTestCase):
    tables = (
        SerumImmProject,
        SerumImmWorkbench,
        *EXPERIMENT_RELATED_MODELS,
        Target,
    )

    def _sorts(self, *row_ids: int) -> list[int | None]:
        self.db.expire_all()
        return [self.db.get(SerumImmWorkbench, row_id).sort_order for row_id in row_ids]

    @staticmethod
    def _scheme_payload(detail: dict) -> dict:
        return {
            "id": detail["id"],
            "scheme_revision": detail["scheme_revision"],
            **{
                key: detail.get(key) or []
                for key in ("mouse_groups", "antigens", "steps", "titer_targets", "titer_pcs")
            },
        }


class ProjectQueueTests(WorkbenchTestCase):
    def test_project_terminal_transition_removes_and_rejoins_queue(self):
        first = workbench_service.save(self.db, {"target_name": "T1"})
        linked = SerumImmWorkbench(
            experiment_id="E1",
            plan_status=workbench_service.PLAN_STATUS_STARTED,
            sort_order=2,
        )
        project = SerumImmProject(experiment_id="E1", project_status="待二免")
        self.db.add_all([linked, project])
        self.db.commit()
        last = workbench_service.save(self.db, {"target_name": "T3"})

        serum_service.update_status(self.db, project.id, "结题")
        self.assertEqual(self._sorts(first["id"], linked.id, last["id"]), [1, None, 2])

        serum_service.update_status(self.db, project.id, "待二免")
        self.assertEqual(self._sorts(first["id"], linked.id, last["id"]), [1, 3, 2])


class HeaderFilterTests(WorkbenchTestCase):
    def setUp(self):
        super().setUp()
        self.db.add_all(
            [
                SerumImmWorkbench(
                    experiment_id="E1",
                    plan_status=workbench_service.PLAN_STATUS_STARTED,
                    owner="旧人",
                    reviewer="旧审",
                ),
                SerumImmProject(experiment_id="E1", owner="张三", reviewer="王五"),
                SerumImmWorkbench(experiment_id="E2", plan_status="草稿", owner="李四", reviewer="王五"),
                SerumImmWorkbench(experiment_id="E3", plan_status="草稿"),
            ]
        )
        self.db.commit()

    def test_started_rows_filter_and_list_by_project_values(self):
        by_reviewer = workbench_service.get_list(self.db, {"reviewer": "王五"})
        self.assertEqual({item["experiment_id"] for item in by_reviewer["items"]}, {"E1", "E2"})
        self.assertEqual(
            workbench_service.get_list(self.db, {"reviewer": "旧审"})["total"],
            0,
        )
        started = workbench_service.get_list(self.db, {"keyword": "E1"})["items"][0]
        self.assertEqual(started["reviewer"], "王五")

    def test_column_values_and_header_filters_use_displayed_owner(self):
        values = workbench_service.get_column_values(self.db, {"field": "owner"})["items"]
        self.assertEqual(
            sorted((item["value"], item["count"]) for item in values),
            [("", 1), ("张三", 1), ("李四", 1)],
        )
        filtered = workbench_service.get_list(
            self.db,
            {"field_filters": [{"field": "owner", "values": ["张三", ""]}]},
        )
        self.assertEqual(filtered["total"], 2)
        with self.assertRaises(ValueError):
            workbench_service.get_column_values(self.db, {"field": "target_name"})

    def test_stats_ignore_own_status_conditions(self):
        self.db.add(
            SerumImmWorkbench(
                experiment_id="E4",
                plan_status="已取消",
                owner="张三",
            )
        )
        self.db.commit()
        result = workbench_service.get_list(
            self.db,
            {
                "display_status": "草稿",
                "field_filters": [
                    {"field": "status", "values": ["草稿"]},
                    {"field": "owner", "values": ["张三"]},
                ],
            },
        )
        self.assertEqual(
            (
                result["stats"]["all"],
                result["stats"]["planned"],
                result["stats"]["ongoing"],
                result["stats"]["cancelled"],
            ),
            (2, 0, 1, 1),
        )


class WorkbenchScopeTests(WorkbenchTestCase):
    def test_route_permissions_map_to_service_scopes(self):
        context = UserContext(
            id=1,
            username="tester",
            display_name="测试员",
            roles=[],
            permissions=[
                workbench_routes.WORKBENCH_DRAFT_EDIT_PERMISSION,
                workbench_routes.WORKBENCH_SUPPORT_EDIT_PERMISSION,
            ],
        )
        self.assertEqual(workbench_routes._edit_scopes(context), frozenset({"draft", "support"}))

    def test_draft_scope_rejects_protected_fields(self):
        created = workbench_service.save(self.db, {"target_name": "T1"})
        cases = {
            "plan_status": "筹备中",
            "reviewer": "审核员",
            "review_status": "已通过",
            "can_start": "是",
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                with self.assertRaises(ForbiddenError):
                    workbench_service.save(
                        self.db,
                        {"id": created["id"], field: value},
                        edit_scopes={"draft"},
                    )
                self.db.rollback()

    def test_draft_scope_rejects_non_draft_delete(self):
        created = workbench_service.save(
            self.db,
            {"target_name": "T1", "plan_status": "筹备中"},
            edit_scopes={"full"},
        )
        with self.assertRaises(ForbiddenError):
            workbench_service.delete(self.db, created["id"], edit_scopes={"draft"})

    def test_draft_scope_rejects_reorder(self):
        first = workbench_service.save(self.db, {"target_name": "T1"})
        second = workbench_service.save(self.db, {"target_name": "T2"})
        with self.assertRaises(ForbiddenError):
            workbench_service.reorder(
                self.db,
                first["id"],
                second["id"],
                edit_scopes={"draft"},
            )

    def test_support_scope_limits_edits_to_support_fields(self):
        created = workbench_service.save(self.db, {"target_name": "T1"})
        updated = workbench_service.save(
            self.db,
            {"id": created["id"], "mouse_room": "A101", "antigen_ready": "是"},
            edit_scopes={"support"},
        )
        self.assertEqual((updated["mouse_room"], updated["antigen_ready"]), ("A101", "是"))
        with self.assertRaises(ForbiddenError):
            workbench_service.save(
                self.db,
                {"id": created["id"], "remark": "越权修改"},
                edit_scopes={"support"},
            )

    def test_support_scope_rejects_create(self):
        with self.assertRaises(ForbiddenError):
            workbench_service.save(
                self.db,
                {"mouse_room": "A101"},
                edit_scopes={"support"},
            )

    def test_full_scope_allows_protected_fields(self):
        created = workbench_service.save(self.db, {"target_name": "T1"})
        updated = workbench_service.save(
            self.db,
            {
                "id": created["id"],
                "plan_status": "筹备中",
                "reviewer": "审核员",
                "review_status": "已通过",
                "can_start": "是",
            },
            edit_scopes={"full"},
        )
        self.assertEqual(
            (
                updated["plan_status"],
                updated["reviewer"],
                updated["review_status"],
                updated["can_start"],
            ),
            ("筹备中", "审核员", "已通过", "是"),
        )


class WorkbenchSchemeConflictTests(WorkbenchTestCase):
    def test_stale_scheme_revision_raises_conflict(self):
        created = workbench_service.save(self.db, {"target_name": "T1"})
        detail = workbench_service.get_detail(self.db, created["id"])
        row = self.db.get(SerumImmWorkbench, created["id"])
        row.remark = "并发修改"
        self.db.commit()

        with self.assertRaises(ConflictError):
            workbench_service.save_scheme(self.db, self._scheme_payload(detail))

    def test_foreign_child_row_cannot_be_modified_through_scheme(self):
        first = workbench_service.save(self.db, {"target_name": "T1"})
        second = workbench_service.save(self.db, {"target_name": "T2"})
        second_row = self.db.get(SerumImmWorkbench, second["id"])
        foreign_mouse = SerumImmMouse(
            experiment_id=second_row.experiment_id,
            group_id="G2",
            mouse_strain="C57",
        )
        self.db.add(foreign_mouse)
        self.db.commit()
        detail = workbench_service.get_detail(self.db, first["id"])
        payload = self._scheme_payload(detail)
        payload["mouse_groups"] = [
            {
                "id": foreign_mouse.id,
                "group_id": "G2",
                "mouse_strain": "DBA",
            }
        ]

        with self.assertRaises(ConflictError):
            workbench_service.save_scheme(self.db, payload)


class ImmunologyWorkbenchRulesTests(WorkbenchTestCase):
    def test_expected_compares_with_list_values(self):
        created = workbench_service.save(self.db, {"target_name": "T1"})
        row = self.db.get(SerumImmWorkbench, created["id"])
        row.mouse_strain = "旧表头"
        self.db.add(SerumImmMouse(experiment_id=row.experiment_id, group_id="G1", mouse_strain="BALB/c"))
        self.db.commit()
        listed = workbench_service.get_list(self.db, {})["items"][0]
        self.assertEqual(listed["mouse_strain"], "BALB/c")

        # 前端基线是列表展示值：品系显示方案分组，而不是工作台表头
        saved = workbench_service.save(
            self.db,
            {"id": row.id, "mouse_strain": "DBA", "_expected": {"mouse_strain": "BALB/c"}},
        )
        self.assertEqual(saved["mouse_strain"], "DBA")

        with self.assertRaises(ConflictError):
            workbench_service.save(
                self.db,
                {"id": row.id, "mouse_strain": "C57", "_expected": {"mouse_strain": "BALB/c"}},
            )
        self.db.rollback()

    def test_detail_reorder_and_scheme_save_show_group_strains(self):
        created = workbench_service.save(self.db, {"target_name": "T1"})
        row = self.db.get(SerumImmWorkbench, created["id"])
        row.mouse_strain = "旧表头"
        self.db.add_all([
            SerumImmMouse(experiment_id=row.experiment_id, group_id="G1", mouse_strain="BALB/c"),
            SerumImmMouse(experiment_id=row.experiment_id, group_id="G2", mouse_strain="C57"),
        ])
        self.db.commit()

        detail = workbench_service.get_detail(self.db, row.id)
        self.assertEqual(detail["mouse_strain"], "BALB/c、C57")
        reordered = workbench_service.reorder(self.db, row.id, row.id)["items"][0]
        self.assertEqual(reordered["mouse_strain"], "BALB/c、C57")
        saved = workbench_service.save_scheme(
            self.db,
            {
                "id": row.id,
                "scheme_revision": detail["scheme_revision"],
                **{key: detail.get(key) or [] for key in ("mouse_groups", "antigens", "steps", "titer_targets", "titer_pcs")},
            },
        )
        self.assertEqual(saved["mouse_strain"], "BALB/c、C57")

    def test_multi_options_round_trip_as_list(self):
        row = workbench_service.save(self.db, {"species_cross": ["猴", "人"], "immuno_method": "LNP，蛋白"})
        self.assertEqual(row["species_cross"], ["人", "猴"])
        self.assertEqual(row["immuno_method"], ["蛋白", "LNP"])
        self.assertEqual(self.db.get(SerumImmWorkbench, row["id"]).species_cross, "人,猴")

        saved = workbench_service.save(
            self.db,
            {"id": row["id"], "species_cross": [], "_expected": {"species_cross": ["人", "猴"]}},
        )
        self.assertEqual(saved["species_cross"], [])
        with self.assertRaises(ConflictError):
            workbench_service.save(self.db, {"id": row["id"], "remark": "冲突", "_expected": {"immuno_method": ["蛋白"]}})
        self.db.rollback()

    def test_invalid_immuno_method_is_rejected(self):
        row = workbench_service.save(self.db, {"immuno_method": ["蛋白"]})
        with self.assertRaisesRegex(ValueError, "免疫方式包含不允许的选项"):
            workbench_service.save(self.db, {"id": row["id"], "immuno_method": ["自由文本"]})
        self.db.rollback()
