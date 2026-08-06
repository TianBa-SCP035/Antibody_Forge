from __future__ import annotations

from typing import Any

from integrations.labillion import build_reply_address
from models.mega_automation import MegaFlowWorkOrder

from modules.mega_automation.content import get_order_content, safe_list

def build_dispatch_payload(order: MegaFlowWorkOrder, dispatchId: str) -> dict[str, Any]:
    content = get_order_content(order)
    return {
        "dispatchId": dispatchId,
        "orderNum": order.orderNum,
        "orderName": order.orderName or "",
        "orderType": order.orderType,
        "priority": order.priority or "normal",
        "orderDetail": {
            "pc_infos": safe_list(content.get("pc_infos")),
            "sample_plates": safe_list(content.get("sample_plates")),
            "cell_plates": safe_list(content.get("cell_plates")),
        },
        "replyAddress": build_reply_address(),
    }
