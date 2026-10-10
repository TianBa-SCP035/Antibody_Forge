from modules.mega_automation.callback import apply_labillion_status, normalize_labillion_status


class _Row:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_aborted_stays_open_until_running():
    order = _Row(status="paused", error_message=None)
    dispatch = _Row(status="running", pause_state="paused")

    assert apply_labillion_status(order, dispatch, "aborted") is True
    assert order.status == "execution_failed"
    assert order.error_message == "设备执行中止"
    assert dispatch.status == "running"
    assert dispatch.pause_state is None

    assert apply_labillion_status(order, dispatch, "running") is True
    assert order.status == "running"
    assert order.error_message is None
    assert dispatch.pause_state is None


def test_error_can_finish():
    order = _Row(status="running", error_message=None)
    dispatch = _Row(status="pending", pause_state=None)

    assert apply_labillion_status(order, dispatch, "error") is True
    assert order.status == "execution_error"
    assert order.error_message == "设备执行错误"
    assert dispatch.status == "running"

    assert apply_labillion_status(order, dispatch, "finished") is True
    assert order.status == "completed"
    assert dispatch.status == "completed"
    assert order.error_message is None


def test_withdrawn_ignores_later_callbacks():
    order = _Row(status="paused", error_message=None)
    dispatch = _Row(status="pending", pause_state="withdrawn")

    assert apply_labillion_status(order, dispatch, "deleted") is False
    assert apply_labillion_status(order, dispatch, "running") is False
    assert order.status == "paused"
    assert dispatch.status == "pending"
    assert dispatch.pause_state == "withdrawn"


def test_deleted_cancels_open_order():
    order = _Row(status="execution_failed", error_message="设备执行中止")
    dispatch = _Row(status="running", pause_state=None)

    assert apply_labillion_status(order, dispatch, "deleted") is True
    assert order.status == "cancelled"
    assert order.error_message == "操作台已删除工单"
    assert dispatch.status == "voided"
    assert dispatch.pause_state is None


def test_repeat_status_is_noop():
    order = _Row(status="execution_error", error_message="设备执行错误")
    dispatch = _Row(status="running", pause_state=None)
    assert apply_labillion_status(order, dispatch, "error") is False


def test_status_aliases():
    assert normalize_labillion_status("Error") == "error"
    assert normalize_labillion_status("deleted") == "deleted"
    assert normalize_labillion_status("Aborted") == "aborted"
    assert normalize_labillion_status("unknown") == ""
