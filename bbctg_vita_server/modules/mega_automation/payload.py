from __future__ import annotations

from typing import Any

from models.mega_automation import MegaFlowWorkOrder

from modules.mega_automation.content import get_order_content, safe_list

def build_dispatch_payload(order: MegaFlowWorkOrder, dispatch_id: str) -> dict[str, Any]:
    content = get_order_content(order)
    return {
        "dispatch_id": dispatch_id,
        "order_no": order.order_no,
        "order_name": order.order_name or "",
        "data_type": order.data_type,
        "priority": order.priority or "normal",
        "pc_infos": safe_list(content.get("pc_infos")),
        "sample_plates": safe_list(content.get("sample_plates")),
        "cell_plates": safe_list(content.get("cell_plates")),
    }
