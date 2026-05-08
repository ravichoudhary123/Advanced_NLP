"""Permission filtering primitives for enterprise search."""
from __future__ import annotations

from .models import ACL, Document, UserContext


class EntitlementService:
    """Fail-closed permission evaluator.

    This class models the mandatory post-filter that must run even when index
    pre-filtering is available. It is deliberately deterministic and auditable.
    """

    def can_read(self, user: UserContext, doc: Document) -> bool:
        if doc.tenant != user.tenant:
            return False
        return self._acl_allows(user, doc.acl)

    @staticmethod
    def _acl_allows(user: UserContext, acl: ACL) -> bool:
        if user.user_id in acl.deny_users:
            return False
        if acl.deny_groups.intersection(user.groups):
            return False
        if acl.public:
            return True
        if user.user_id in acl.allow_users:
            return True
        return bool(acl.allow_groups.intersection(user.groups))
