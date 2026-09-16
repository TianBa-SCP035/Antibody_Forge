from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
import uuid


@dataclass(frozen=True)
class AuditAction:
    code: str
    name: str
    operation_type: str | None = None
    resource: str | None = None


@dataclass
class AuditContext:
    request_id: str
    source: str
    method: str
    path: str
    actions: tuple[AuditAction, ...] = ()
    user_id: int | None = None
    username: str | None = None
    operator_name: str | None = None
    ip_address: str | None = None
    fallback_action: str | None = None
    fallback_name: str | None = None
    suppress_noop: bool = False
    committed_results: set[str] = field(default_factory=set)

    @property
    def explicitly_audited(self) -> bool:
        return bool(self.actions) and not self.suppress_noop

    def record_committed_result(self, result: str) -> None:
        self.committed_results.add("failed" if result == "failed" else "success")

    def has_committed_result(self, result: str) -> bool:
        if result == "failed":
            return "failed" in self.committed_results
        return bool(self.committed_results)

    def select_action(self, change_type: str) -> AuditAction:
        preferred = {
            "create": {"create"},
            "delete": {"delete"},
            "update": {"edit", "edit_all", "manage", "update"},
        }.get(change_type, set())
        for action in self.actions:
            if action.operation_type in preferred:
                return action
        if self.actions:
            return self.actions[0]
        code = self.fallback_action or f"{self.method} {self.path}"
        return AuditAction(
            code=code[:128],
            name=(self.fallback_name or code)[:128],
            operation_type=change_type,
        )


_AUDIT_CONTEXT: ContextVar[AuditContext | None] = ContextVar("audit_context", default=None)


def get_audit_context() -> AuditContext | None:
    return _AUDIT_CONTEXT.get()


def set_audit_context(context: AuditContext) -> Token:
    return _AUDIT_CONTEXT.set(context)


def reset_audit_context(token: Token) -> None:
    _AUDIT_CONTEXT.reset(token)


def bind_audit_actor(user) -> None:
    """Enrich the request context from the normal auth dependency.

    This reuses the user lookup every protected endpoint already performs and
    avoids a second audit-only query.
    """
    context = get_audit_context()
    if context is None:
        return
    context.user_id = getattr(user, "id", None)
    context.username = getattr(user, "username", None)
    context.operator_name = getattr(user, "display_name", None)
    if context.source == "system":
        context.source = "user"


@contextmanager
def audit_scope(
    action: str,
    operation_name: str,
    *,
    source: str = "system",
    operation_type: str = "update",
):
    context = AuditContext(
        request_id=uuid.uuid4().hex,
        source=source,
        method=source.upper(),
        path=action,
        fallback_action=action,
        fallback_name=operation_name,
        actions=(
            AuditAction(
                code=action,
                name=operation_name,
                operation_type=operation_type,
            ),
        ),
    )
    token = set_audit_context(context)
    try:
        yield context
    finally:
        reset_audit_context(token)
