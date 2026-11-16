"""免疫项目的成员判断：负责人、审核人按用户名或姓名（含姓名第一段）匹配。"""

from models.immunology import SerumImmProject
from models.system import SysUser


def owner_aliases(user: SysUser) -> set[str]:
    aliases = {str(value).strip() for value in (user.username, user.display_name) if str(value or "").strip()}
    for value in list(aliases):
        aliases.add(value.split()[0])
    return aliases


def is_owner_name(user: SysUser, owner: str | None) -> bool:
    owner_name = str(owner or "").strip()
    return bool(owner_name and owner_name in owner_aliases(user))


def is_project_member(user: SysUser, project: SerumImmProject) -> bool:
    return is_owner_name(user, project.owner) or is_owner_name(user, project.reviewer)
