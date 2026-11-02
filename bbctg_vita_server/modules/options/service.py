"""跨模块共用的下拉选项：靶点库搜索、在职人员搜索。"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.system import SysUser
from models.target import Target
from modules.atlas import service as atlas_service
from utils.filter_values import like_literal

DEFAULT_TARGET_LIMIT = 20
MAX_TARGET_LIMIT = 50
DEFAULT_USER_LIMIT = 30
# 在职人员规模有限；表格粘贴校验需要整份名单
MAX_USER_LIMIT = 5000


def _target_option_dict(
    snum: str,
    name: str,
    structural_properties: str | None = None,
    structure_feature: str | None = None,
) -> dict[str, Any]:
    return {
        "snum": snum,
        "name": name,
        "structural_properties": structural_properties,
        "structure_feature": structure_feature,
    }


def get_target_options(
    db: Session,
    keyword: str,
    limit: int = DEFAULT_TARGET_LIMIT,
    codes: list[str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    selected_codes = list(
        dict.fromkeys(str(code).strip() for code in (codes or []) if str(code).strip())
    )
    selected_items: list[dict[str, Any]] = []
    if selected_codes:
        targets_by_code = {
            target.snum: target
            for target in db.scalars(select(Target).where(Target.snum.in_(selected_codes)))
        }
        selected_items = [
            _target_option_dict(
                code,
                targets_by_code[code].name,
                targets_by_code[code].structural_properties,
                targets_by_code[code].structure_feature,
            )
            for code in selected_codes
            if code in targets_by_code
        ]

    result = atlas_service.get_target_list(
        db,
        {
            "page": 1,
            "limit": min(max(int(limit or DEFAULT_TARGET_LIMIT), 1), MAX_TARGET_LIMIT),
            "keyword": str(keyword or "").strip(),
        },
        include_stats=False,
    )
    seen = set(selected_codes)
    search_items = [
        _target_option_dict(
            item["snum"],
            item["name"],
            item.get("structural_properties"),
            item.get("structure_feature"),
        )
        for item in result["items"]
        if item["snum"] not in seen
    ]
    return {"items": [*selected_items, *search_items]}


def get_user_options(
    db: Session,
    keyword: str = "",
    limit: int = DEFAULT_USER_LIMIT,
) -> list[str]:
    stmt = (
        select(SysUser.display_name)
        .where(
            SysUser.status == "active",
            SysUser.employment_status == "active",
            SysUser.display_name.is_not(None),
            SysUser.display_name != "",
        )
        .distinct()
        .order_by(SysUser.display_name)
    )
    text = str(keyword or "").strip()
    if text:
        stmt = stmt.where(SysUser.display_name.like(f"%{like_literal(text)}%", escape="\\"))
    return [
        value
        for value in db.scalars(
            stmt.limit(min(max(int(limit or DEFAULT_USER_LIMIT), 1), MAX_USER_LIMIT))
        ).all()
        if value
    ]
