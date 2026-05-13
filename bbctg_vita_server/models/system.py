from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class SysUser(Base):
    __tablename__ = "sys_user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="账号")
    display_name: Mapped[str | None] = mapped_column(String(128), comment="姓名")
    password_hash: Mapped[str | None] = mapped_column(String(255), comment="密码哈希")
    openid: Mapped[str | None] = mapped_column(String(100), unique=True, comment="云之家OpenID")
    job_no: Mapped[str | None] = mapped_column(String(32), comment="工号")
    department: Mapped[str | None] = mapped_column(String(128), comment="部门")
    group_name: Mapped[str | None] = mapped_column(String(128), comment="组别")
    position_title: Mapped[str | None] = mapped_column(String(128), comment="职位")
    gender: Mapped[str | None] = mapped_column(String(16), comment="性别")
    profile_signature: Mapped[str | None] = mapped_column(String(255), comment="个性名片语句")
    employment_status: Mapped[str] = mapped_column(String(32), default="active", comment="在职状态")
    email: Mapped[str | None] = mapped_column(String(128), comment="邮箱")
    mobile: Mapped[str | None] = mapped_column(String(32), comment="手机号")
    status: Mapped[str] = mapped_column(String(16), default="active", comment="用户状态")
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否超级管理员")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, comment="最后登录时间")
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.current_timestamp(), comment="创建时间")
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="更新时间",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "openid": self.openid,
            "job_no": self.job_no,
            "department": self.department,
            "group_name": self.group_name,
            "position_title": self.position_title,
            "gender": self.gender,
            "profile_signature": self.profile_signature,
            "employment_status": self.employment_status,
            "email": self.email,
            "mobile": self.mobile,
            "status": self.status,
            "is_superuser": self.is_superuser,
            "last_login_at": self.last_login_at,
        }


class SysRole(Base):
    __tablename__ = "sys_role"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="角色编码")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="角色名称")
    description: Mapped[str | None] = mapped_column(String(255), comment="角色描述")
    status: Mapped[str] = mapped_column(String(16), default="active", comment="角色状态")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序值")
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.current_timestamp(), comment="创建时间")
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="更新时间",
    )


class SysPermission(Base):
    __tablename__ = "sys_permission"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, comment="权限编码")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="权限名称")
    type: Mapped[str] = mapped_column(String(16), nullable=False, comment="权限类型")
    module: Mapped[str | None] = mapped_column(String(64), comment="所属模块编码")
    resource: Mapped[str | None] = mapped_column(String(64), comment="资源域")
    action: Mapped[str | None] = mapped_column(String(64), comment="动作")
    route_path: Mapped[str | None] = mapped_column(String(255), comment="前端路由路径")
    ui_key: Mapped[str | None] = mapped_column(String(128), comment="前端按钮或区域标识")
    parent_code: Mapped[str | None] = mapped_column(String(128), comment="上级权限编码")
    description: Mapped[str | None] = mapped_column(String(255), comment="权限描述")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序值")
    status: Mapped[str] = mapped_column(String(16), default="active", comment="权限状态")


class SysPermissionBundle(Base):
    __tablename__ = "sys_permission_bundle"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="权限包编码")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="权限包名称")
    module: Mapped[str] = mapped_column(String(64), nullable=False, comment="所属模块")
    description: Mapped[str | None] = mapped_column(String(255), comment="权限包描述")
    status: Mapped[str] = mapped_column(String(16), default="active", comment="权限包状态")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序值")
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.current_timestamp(), comment="创建时间")
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="更新时间",
    )


class SysPermissionBundleItem(Base):
    __tablename__ = "sys_permission_bundle_item"
    __table_args__ = (UniqueConstraint("bundle_code", "permission_code", name="uq_sys_permission_bundle_item"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    bundle_code: Mapped[str] = mapped_column(String(64), nullable=False, comment="权限包编码")
    permission_code: Mapped[str] = mapped_column(String(128), nullable=False, comment="权限编码")


class SysUserRole(Base):
    __tablename__ = "sys_user_role"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_sys_user_role"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="用户ID")
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="角色ID")


class SysRolePermissionBundle(Base):
    __tablename__ = "sys_role_permission_bundle"
    __table_args__ = (UniqueConstraint("role_id", "bundle_code", name="uq_sys_role_permission_bundle"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="角色ID")
    bundle_code: Mapped[str] = mapped_column(String(64), nullable=False, comment="权限包编码")


class SysUserPermissionOverride(Base):
    __tablename__ = "sys_user_permission_override"
    __table_args__ = (UniqueConstraint("user_id", "permission_code", name="uq_sys_user_permission_override"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="用户ID")
    permission_code: Mapped[str] = mapped_column(String(128), nullable=False, comment="权限编码")
    effect: Mapped[str] = mapped_column(String(8), nullable=False, comment="覆盖效果")
    reason: Mapped[str | None] = mapped_column(String(255), comment="覆盖原因")


class SysPermissionApi(Base):
    __tablename__ = "sys_permission_api"
    __table_args__ = (UniqueConstraint("permission_code", "method", "path_pattern", name="uq_sys_permission_api"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    permission_code: Mapped[str] = mapped_column(String(128), nullable=False, comment="权限编码")
    method: Mapped[str] = mapped_column(String(16), nullable=False, comment="HTTP方法")
    path_pattern: Mapped[str] = mapped_column(String(255), nullable=False, comment="接口路径模式")
    description: Mapped[str | None] = mapped_column(String(255), comment="接口说明")
    status: Mapped[str] = mapped_column(String(16), default="active", comment="状态")
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.current_timestamp(), comment="创建时间")


class SysOperationLog(Base):
    __tablename__ = "sys_operation_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    user_id: Mapped[int | None] = mapped_column(BigInteger, comment="操作用户ID")
    username: Mapped[str | None] = mapped_column(String(64), comment="操作账号")
    operator_name: Mapped[str | None] = mapped_column(String(128), comment="操作人姓名")
    action: Mapped[str] = mapped_column(String(128), nullable=False, comment="操作动作")
    operation_name: Mapped[str | None] = mapped_column(String(128), comment="操作名称")
    operation_type: Mapped[str | None] = mapped_column(String(32), comment="操作类型")
    target_type: Mapped[str | None] = mapped_column(String(64), comment="目标类型")
    target_id: Mapped[str | None] = mapped_column(String(128), comment="目标ID")
    target_label: Mapped[str | None] = mapped_column(String(255), comment="目标名称")
    result: Mapped[str] = mapped_column(String(16), default="success", comment="操作结果")
    detail: Mapped[object | None] = mapped_column(JSON, comment="操作详情")
    error_message: Mapped[str | None] = mapped_column(Text, comment="错误信息")
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.current_timestamp(), comment="操作时间")
