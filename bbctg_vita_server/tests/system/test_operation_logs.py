"""操作日志：模型日志名称登记、对象标签取值、日志列表筛选与详情的中文标签。"""

import json
import unittest

import modules.system.audit_middleware as audit_middleware
import modules.system.audit_session as audit_session
import modules.system.routes as system_routes
from db.session import Base
from models.immunology import SerumTiterTarget
from models.molecular_cell import MolecularLibraryOrder
from models.system import SysOperationLog, SysOperationLogItem, SysUser
from support import DbTestCase


def _response_target(data: dict) -> tuple:
    return audit_middleware._target_from_response(json.dumps({"data": data}).encode())


class LogLabelTests(unittest.TestCase):
    def test_every_audited_model_has_log_label(self):
        excluded = {"SysOperationLog", "SysOperationLogItem", "SysJobRunLog"}
        missing = sorted(
            mapper.class_.__name__
            for mapper in Base.registry.mappers
            if mapper.class_.__module__.startswith("models.")
            and mapper.class_.__name__ not in excluded
            and not getattr(mapper.class_, "__log_label__", None)
        )
        self.assertEqual(missing, [], "新模型要声明 __log_label__（操作日志里的对象类型中文名）")

    def test_declared_label_fields_exist_on_model(self):
        for mapper in Base.registry.mappers:
            declared = getattr(mapper.class_, "__audit_label__", ())
            columns = {attr.key for attr in mapper.column_attrs}
            with self.subTest(model=mapper.class_.__name__):
                self.assertLessEqual(set(declared), columns)

    def test_entity_label_prefers_declared_business_id(self):
        self.assertEqual(audit_session._entity_label(MolecularLibraryOrder(id=7, library_order_id="LIB-001")), "LIB-001")
        self.assertEqual(audit_session._entity_label(SerumTiterTarget(id=3, name="CD3", experiment_id="EXP-1")), "CD3")
        self.assertEqual(audit_session._entity_label(SysUser(id=1, username="u", display_name="张三")), "张三")

    def test_response_target_prefers_earliest_declared_business_id(self):
        self.assertEqual(_response_target({"id": 9, "library_order_id": "LIB-9"}), ("9", "LIB-9"))
        self.assertEqual(_response_target({"id": 5, "project_code": "PC-1", "discovery_id": "D-1"}), ("5", "PC-1"))
        self.assertEqual(_response_target({"id": 6, "name": "甲", "experiment_id": "E-1"}), ("6", "E-1"))


class OperationLogListTests(DbTestCase):
    tables = (SysOperationLog, SysOperationLogItem)

    def setUp(self):
        super().setUp()
        quiet_log = SysOperationLog(
            request_id="req-1",
            source="user",
            action="POST /api/molecular-cell/library-orders/files/list",
            operation_name="POST /api/molecular-cell/library-orders/files/list",
            operation_type="update",
            target_type="MolecularLibraryOrder",
            result="success",
            affected_count=1,
            detail={},
        )
        self.db.add_all([
            quiet_log,
            SysOperationLog(
                request_id="req-2",
                source="user",
                action="serum.project.edit",
                operation_name="编辑免疫项目",
                operation_type="update",
                target_type="project",
                result="success",
                affected_count=1,
                detail={},
            ),
        ])
        self.db.flush()
        self.db.add(SysOperationLogItem(
            log_id=quiet_log.id,
            entity_type="MolecularLibraryOrder",
            table_name="molecular_library_order",
            change_type="update",
            change_count=1,
        ))
        self.db.commit()
        self.log_id = quiet_log.id

    def test_list_filters_by_action_and_target_type_labels(self):
        response = system_routes.list_operation_logs(
            action="刷新质检", target_type=["文库工单"], source=None, result=None, operation_type=None, db=self.db
        )
        data = json.loads(json.dumps(response, default=str))["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["action_label"], "刷新质检核对")
        self.assertEqual(data["items"][0]["target_type_label"], "文库工单")
        self.assertIn("文库工单", data["target_type_options"])

    def test_detail_labels_log_and_items(self):
        detail = system_routes.get_operation_log_detail(self.log_id, db=self.db)["data"]
        self.assertEqual(detail["action_label"], "刷新质检核对")
        self.assertEqual(detail["target_type_label"], "文库工单")
        self.assertEqual(detail["items"][0]["entity_type_label"], "文库工单")
