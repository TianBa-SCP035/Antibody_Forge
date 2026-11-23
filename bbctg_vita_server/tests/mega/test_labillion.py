"""Labillion 响应解析、状态回调、状态同步与撤回删除。"""

import json
import unittest
from unittest.mock import MagicMock, patch

from requests import Response
from sqlalchemy import select

from integrations.labillion import LabillionError, _parse_labillion_response
from models.mega_automation import MegaFlowWorkOrder, MegaFlowWorkOrderDispatch
from models.system import SysOperationLog
from modules.mega_automation import labillion_sync, routes as mega_routes, service
from modules.mega_automation.callback import handle_labillion_status_push, normalize_labillion_status
from support import DbTestCase


def _response(payload):
    response = Response()
    response.status_code = 200
    response._content = json.dumps(payload).encode()
    return response


class _BrokenStatusEntry(dict):
    def get(self, key, default=None):
        raise RuntimeError("单条状态损坏")


class LabillionResponseTests(unittest.TestCase):
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


class LabillionStatusPushTests(DbTestCase):
    tables = (MegaFlowWorkOrder, MegaFlowWorkOrderDispatch)

    def _prepare(
        self,
        order_status,
        dispatch_status="pending",
        pause_state=None,
        error_message=None,
        dispatch_id="DSP1",
        order_num="ORD-1",
    ):
        order = MegaFlowWorkOrder(
            orderNum=order_num,
            orderType="TITER",
            priority="normal",
            status=order_status,
            error_message=error_message,
        )
        self.db.add(order)
        self.db.flush()
        dispatch = MegaFlowWorkOrderDispatch(
            dispatchId=dispatch_id,
            work_order_id=order.id,
            payload={"dispatchId": dispatch_id},
            payload_hash="0" * 64,
            content_hash_at_send="0" * 64,
            status=dispatch_status,
            pause_state=pause_state,
        )
        self.db.add(dispatch)
        self.db.commit()
        return order, dispatch

    def _push(self, dispatch_id, status):
        return handle_labillion_status_push(self.db, {"dispatchId": dispatch_id, "status": status})

    def test_aborted_callback_stays_open_until_running(self):
        order, dispatch = self._prepare("paused", dispatch_status="running", pause_state="paused")
        result = self._push(dispatch.dispatchId, "aborted")
        self.assertTrue(result["applied"])
        self.db.refresh(order)
        self.db.refresh(dispatch)
        self.assertEqual(order.status, "execution_failed")
        self.assertEqual(order.error_message, "设备执行中止")
        self.assertEqual(dispatch.status, "running")
        self.assertIsNone(dispatch.pause_state)

        result = self._push(dispatch.dispatchId, "running")
        self.assertTrue(result["applied"])
        self.db.refresh(order)
        self.db.refresh(dispatch)
        self.assertEqual(order.status, "running")
        self.assertIsNone(order.error_message)
        self.assertIsNone(dispatch.pause_state)

    def test_error_callback_can_still_finish(self):
        order, dispatch = self._prepare("running")
        result = self._push(dispatch.dispatchId, "Error")
        self.assertTrue(result["applied"])
        self.db.refresh(order)
        self.db.refresh(dispatch)
        self.assertEqual(order.status, "execution_error")
        self.assertEqual(order.error_message, "设备执行错误")
        self.assertEqual(dispatch.status, "running")

        result = self._push(dispatch.dispatchId, "Finished")
        self.assertTrue(result["applied"])
        self.db.refresh(order)
        self.db.refresh(dispatch)
        self.assertEqual(order.status, "completed")
        self.assertEqual(dispatch.status, "completed")
        self.assertIsNone(order.error_message)

    def test_withdrawn_order_ignores_later_callbacks(self):
        order, dispatch = self._prepare("paused", pause_state="withdrawn")
        for status in ("deleted", "running"):
            result = self._push(dispatch.dispatchId, status)
            self.assertFalse(result["applied"])
        self.db.refresh(order)
        self.db.refresh(dispatch)
        self.assertEqual(order.status, "paused")
        self.assertEqual(dispatch.status, "pending")
        self.assertEqual(dispatch.pause_state, "withdrawn")

    def test_deleted_callback_cancels_open_order(self):
        order, dispatch = self._prepare(
            "execution_failed",
            dispatch_status="running",
            error_message="设备执行中止",
        )
        result = self._push(dispatch.dispatchId, "deleted")
        self.assertTrue(result["applied"])
        self.db.refresh(order)
        self.db.refresh(dispatch)
        self.assertEqual(order.status, "cancelled")
        self.assertEqual(order.error_message, "操作台已删除工单")
        self.assertEqual(dispatch.status, "voided")
        self.assertIsNone(dispatch.pause_state)

    def test_repeat_status_callback_is_noop(self):
        order, dispatch = self._prepare(
            "execution_error",
            dispatch_status="running",
            error_message="设备执行错误",
        )
        result = self._push(dispatch.dispatchId, "error")
        self.assertFalse(result["applied"])
        self.db.refresh(order)
        self.db.refresh(dispatch)
        self.assertEqual(order.status, "execution_error")
        self.assertEqual(order.error_message, "设备执行错误")
        self.assertEqual(dispatch.status, "running")
        self.assertIsNone(dispatch.pause_state)

    def test_status_text_normalizes_known_aliases(self):
        cases = (
            ("Error", "error"),
            ("deleted", "deleted"),
            ("Aborted", "aborted"),
            ("unknown", ""),
        )
        for raw, expected in cases:
            with self.subTest(status=raw):
                self.assertEqual(normalize_labillion_status(raw), expected)

    def test_terminal_or_undispatched_order_ignores_status_push(self):
        cases = (
            ("completed", "order_terminal"),
            ("cancelled", "order_terminal"),
            ("draft", "order_not_dispatched"),
            ("validated", "order_not_dispatched"),
            ("failed", "order_not_dispatched"),
        )
        for status, reason in cases:
            with self.subTest(status=status):
                order, dispatch = self._prepare(status, dispatch_id=f"DSP-{status}", order_num=f"ORD-{status}")
                result = self._push(dispatch.dispatchId, "running")
                self.assertFalse(result["applied"])
                self.assertEqual(result["reason"], reason)
                self.db.refresh(order)
                self.db.refresh(dispatch)
                self.assertEqual(order.status, status)
                self.assertEqual(dispatch.status, "pending")


class LabillionStatusSyncTests(DbTestCase):
    tables = (MegaFlowWorkOrder, MegaFlowWorkOrderDispatch)

    def _syncable(self, order_num, dispatch_id):
        order = MegaFlowWorkOrder(
            orderNum=order_num,
            orderType="TITER",
            priority="normal",
            status="sent",
            content_hash="a" * 64,
        )
        self.db.add(order)
        self.db.flush()
        dispatch = MegaFlowWorkOrderDispatch(
            dispatchId=dispatch_id,
            work_order_id=order.id,
            payload={"dispatchId": dispatch_id},
            payload_hash="b" * 64,
            content_hash_at_send="a" * 64,
            status="pending",
        )
        self.db.add(dispatch)
        self.db.commit()
        return order, dispatch

    def test_every_detail_sync_queries_labillion(self):
        order, dispatch = self._syncable("S1", "DSP-S1")
        calls = []

        def query(ids):
            calls.append(list(ids))
            status = "running" if len(calls) == 1 else "finished"
            return {dispatch.dispatchId: {"status": status}}

        with (
            patch("modules.mega_automation.labillion_sync.is_labillion_enabled", return_value=True),
            patch("modules.mega_automation.labillion_sync.query_order_statuses", side_effect=query),
        ):
            first = labillion_sync.sync_work_order_labillion_status(self.db, order.id)
            second = labillion_sync.sync_work_order_labillion_status(self.db, order.id)

        self.assertTrue(first["applied"])
        self.assertEqual(first["item"]["status"], "running")
        self.assertTrue(second["applied"])
        self.assertEqual(second["item"]["status"], "completed")
        self.assertEqual(second["item"]["dispatches"][0]["status"], "completed")
        self.assertEqual(calls, [[dispatch.dispatchId], [dispatch.dispatchId]])

    def test_batch_sync_keeps_other_orders_when_one_item_fails(self):
        good, good_dispatch = self._syncable("GOOD", "DSP-GOOD")
        bad, bad_dispatch = self._syncable("BAD", "DSP-BAD")

        def query(ids):
            result = {}
            for dispatch_id in ids:
                if dispatch_id == bad_dispatch.dispatchId:
                    # 非空才会进入逐条处理；读字段时失败，同批已提交的工单不能被它回滚
                    result[dispatch_id] = _BrokenStatusEntry(status="running")
                else:
                    result[dispatch_id] = {"status": "running"}
            return result

        with (
            patch("modules.mega_automation.labillion_sync.is_labillion_enabled", return_value=True),
            patch("modules.mega_automation.labillion_sync.query_order_statuses", side_effect=query),
        ):
            summary = labillion_sync.sync_non_terminal_work_orders(self.db)

        self.assertFalse(summary["skipped"])
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["applied"], 1)
        self.assertEqual(summary["failed"], 1)
        self.db.refresh(good)
        self.db.refresh(bad)
        self.db.refresh(good_dispatch)
        self.db.refresh(bad_dispatch)
        self.assertEqual(good.status, "running")
        self.assertEqual(good_dispatch.status, "running")
        self.assertEqual(bad.status, "sent")
        self.assertEqual(bad_dispatch.status, "pending")


class LabillionWithdrawTests(DbTestCase):
    tables = (MegaFlowWorkOrder, MegaFlowWorkOrderDispatch)

    def _sent_order(self, error_message=None):
        order = MegaFlowWorkOrder(
            orderNum="ORD-1",
            orderName="检测",
            orderType="TITER",
            priority="normal",
            status="sent",
            error_message=error_message,
            content_hash="a" * 64,
        )
        self.db.add(order)
        self.db.flush()
        dispatch = MegaFlowWorkOrderDispatch(
            dispatchId="DSP261012967278",
            work_order_id=order.id,
            payload={"dispatchId": "DSP261012967278"},
            payload_hash="b" * 64,
            content_hash_at_send="a" * 64,
            status="pending",
        )
        self.db.add(dispatch)
        self.db.commit()
        return order, dispatch

    def test_withdraw_commits_pause_before_labillion_delete(self):
        order, dispatch = self._sent_order(error_message="旧错误")
        seen = {}

        def delete_orders(ids):
            # 删除请求会同步回调；回调读到已撤回状态的前提是事务已经结束
            self.assertFalse(self.db.in_transaction())
            self.assertEqual(list(ids), [dispatch.dispatchId])
            self.db.expire_all()
            fresh_order = self.db.get(MegaFlowWorkOrder, order.id)
            fresh_dispatch = self.db.get(MegaFlowWorkOrderDispatch, dispatch.id)
            seen["status"] = fresh_order.status
            seen["error"] = fresh_order.error_message
            seen["pause"] = fresh_dispatch.pause_state
            seen["dispatch_status"] = fresh_dispatch.status

        with patch("modules.mega_automation.service.delete_orders", delete_orders):
            detail = service.pause_work_order(self.db, order.id)

        self.assertEqual(
            seen,
            {"status": "paused", "error": None, "pause": "withdrawn", "dispatch_status": "pending"},
        )
        self.assertEqual(detail["status"], "paused")
        self.assertIsNone(detail["error_message"])
        self.assertEqual(detail["display_status"], "withdrawn")
        self.assertEqual(detail["dispatches"][0]["status"], "pending")
        self.assertEqual(detail["dispatches"][0]["pause_state"], "withdrawn")

    def test_failed_labillion_delete_restores_sent_pending(self):
        order, dispatch = self._sent_order()
        seen = {}

        def delete_orders(ids):
            self.assertFalse(self.db.in_transaction())
            self.assertEqual(list(ids), [dispatch.dispatchId])
            self.db.expire_all()
            seen["during"] = self.db.get(MegaFlowWorkOrder, order.id).status
            raise LabillionError("连接 Labillion 服务超时")

        with patch("modules.mega_automation.service.delete_orders", delete_orders):
            with self.assertRaises(ValueError) as caught:
                service.pause_work_order(self.db, order.id)

        self.assertEqual(str(caught.exception), "Labillion 订单删除失败：连接 Labillion 服务超时")
        self.assertEqual(seen["during"], "paused")
        self.db.expire_all()
        fresh_order = self.db.get(MegaFlowWorkOrder, order.id)
        fresh_dispatch = self.db.get(MegaFlowWorkOrderDispatch, dispatch.id)
        self.assertEqual(fresh_order.status, "sent")
        self.assertIsNone(fresh_order.error_message)
        self.assertEqual(fresh_dispatch.status, "pending")
        self.assertIsNone(fresh_dispatch.pause_state)

class LabillionCallbackAuditTests(DbTestCase):
    tables = (SysOperationLog,)

    def test_labillion_failure_is_audited_but_still_acknowledged(self):
        with self.Session() as db:
            with (
                patch.object(
                    mega_routes.callback,
                    "handle_labillion_status_push",
                    side_effect=RuntimeError("internal failure"),
                ),
                patch.object(mega_routes.logger, "exception"),
            ):
                response = mega_routes.labillion_status_callback(
                    {"dispatchId": "dispatch-1", "payload": "secret"},
                    db,
                )
            log = db.scalar(
                select(SysOperationLog).where(
                    SysOperationLog.action == "mega.labillion.callback"
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.body)["data"]["reason"], "internal_error")
            self.assertEqual(log.result, "failed")
            self.assertEqual(log.target_id, "dispatch-1")
            self.assertNotIn("secret", str(log.detail))

    def test_labillion_noop_uses_canonical_audit_identity(self):
        result = {
            "applied": False,
            "reason": "dispatch_terminal",
            "dispatchId": "dispatch-2",
        }
        with self.Session() as db:
            with patch.object(
                mega_routes.callback,
                "handle_labillion_status_push",
                return_value=result,
            ):
                response = mega_routes.labillion_status_callback(
                    {"dispatchId": "dispatch-2"},
                    db,
                )
            log = db.scalar(
                select(SysOperationLog).where(
                    SysOperationLog.action
                    == mega_routes.LABILLION_CALLBACK_AUDIT_ACTION.code
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.body)["data"], {"applied": False, "reason": "dispatch_terminal"})
            self.assertEqual(log.target_id, "dispatch-2")
            self.assertEqual(log.detail["change_summary"], "dispatch_terminal")

    def test_labillion_non_object_body_is_failed_audit_with_200_ack(self):
        db = MagicMock()
        with (
            patch.object(
                mega_routes.callback,
                "handle_labillion_status_push",
            ) as callback_handler,
            patch.object(mega_routes, "write_operation_log") as write_log,
            patch.object(mega_routes.logger, "exception"),
        ):
            response = mega_routes.labillion_status_callback(["invalid"], db)
        callback_handler.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(write_log.call_args.kwargs["result"], "failed")
