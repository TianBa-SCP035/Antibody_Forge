from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from integrations.labillion import LabillionError
from modules.mega_automation.service import _labillion_withdraw_pause


class _Db:
    def __init__(self):
        self.events = []

    def commit(self):
        self.events.append("commit")

    def rollback(self):
        self.events.append("rollback")


class WithdrawLockTest(TestCase):
    def test_delete_runs_after_withdraw_is_committed(self):
        db = _Db()
        order = SimpleNamespace(id=60, status="sent", error_message="旧错误")
        current = SimpleNamespace(status="pending", pause_state=None, dispatchId="DSP261012967278")

        def delete_orders(ids):
            db.events.append(("delete", list(ids), order.status, current.pause_state))

        with patch("modules.mega_automation.service.delete_orders", delete_orders):
            _labillion_withdraw_pause(db, order, current)

        self.assertEqual(
            db.events,
            ["commit", ("delete", ["DSP261012967278"], "paused", "withdrawn")],
        )
        self.assertEqual(order.status, "paused")
        self.assertIsNone(order.error_message)

    def test_failed_delete_restores_sent_pending(self):
        db = _Db()
        order = SimpleNamespace(id=60, status="sent", error_message=None)
        current = SimpleNamespace(status="pending", pause_state=None, dispatchId="DSP261012967278")

        def delete_orders(_ids):
            db.events.append("delete")
            raise LabillionError("连接 Labillion 服务超时")

        def restore(_db, order_id, dispatch_id):
            db.events.append(("restore", order_id, dispatch_id))

        with (
            patch("modules.mega_automation.service.delete_orders", delete_orders),
            patch("modules.mega_automation.service._restore_sent_after_failed_withdraw", restore),
        ):
            with self.assertRaises(ValueError) as caught:
                _labillion_withdraw_pause(db, order, current)

        self.assertIn("连接 Labillion 服务超时", str(caught.exception))
        self.assertEqual(db.events, ["commit", "delete", ("restore", 60, "DSP261012967278")])
        self.assertEqual(order.status, "paused")
        self.assertEqual(current.pause_state, "withdrawn")
