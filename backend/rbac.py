"""
Role-based access control.

Four roles, each with a scope (which works it can see) and a set of capabilities
(what it can do to them). Both are enforced server-side: the scope filters every
list the API returns, and the capabilities gate every action endpoint. Hiding a
button in the browser is presentation, not access control, so the checks live
here and the interface follows them rather than the other way round.

The demo users below are fixed identities, not accounts — there is no password,
no session and no token. That is a deliberate limitation of a prototype whose
purpose is to demonstrate what role separation *does*, and it is stated plainly
in the interface. A deployment would put a real identity provider in front of
``current_user`` and change nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import Header, HTTPException

# --------------------------------------------------------------------------
# Capabilities
# --------------------------------------------------------------------------

#: Every action the system recognises. A role holds a subset of these.
CAPABILITIES = (
    "view.national",        # see the whole register
    "view.state",           # see works in the user's state
    "view.district",        # see works in the user's district
    "view.cases",           # see investigation cases in scope
    "case.create",          # open a case against a work
    "case.assign",          # assign or reassign a case
    "case.status",          # move a case through the workflow
    "case.verify",          # complete verification items, add remarks/evidence
    "case.escalate",        # escalate a case
    "case.close",           # close a case and record an outcome
    "admin.users",          # see the user register
    "admin.config",         # see system configuration
    "admin.audit",          # see the full audit trail across all cases
)


@dataclass(frozen=True)
class Role:
    name: str
    title: str
    summary: str
    capabilities: frozenset[str]
    #: How far the role can see. One of "national", "state", "district".
    scope: str
    #: What the role is expected to do with the system, shown on the switcher.
    responsibilities: tuple[str, ...] = ()


ROLES: dict[str, Role] = {
    "MINISTRY": Role(
        name="MINISTRY",
        title="Ministry / National",
        summary="National overview across every state and district. Monitors investigations; does not conduct them.",
        scope="national",
        capabilities=frozenset(
            {
                "view.national",
                "view.state",
                "view.district",
                "view.cases",
                "case.create",
                "case.assign",
                "case.escalate",
                "admin.audit",
            }
        ),
        responsibilities=(
            "National risk overview",
            "State and district monitoring",
            "High-risk works across the country",
            "Investigation monitoring",
        ),
    ),
    "STATE": Role(
        name="STATE",
        title="State Nodal Officer",
        summary="Works and cases within one state. Assigns cases to districts and tracks the state queue.",
        scope="state",
        capabilities=frozenset(
            {
                "view.state",
                "view.district",
                "view.cases",
                "case.create",
                "case.assign",
                "case.status",
                "case.escalate",
            }
        ),
        responsibilities=(
            "State-level works",
            "District monitoring within the state",
            "State investigation queue",
        ),
    ),
    "DISTRICT": Role(
        name="DISTRICT",
        title="District Authority",
        summary="Works in one district. Carries out the verification and records what was found.",
        scope="district",
        capabilities=frozenset(
            {
                "view.district",
                "view.cases",
                "case.create",
                "case.status",
                "case.verify",
                "case.escalate",
                "case.close",
            }
        ),
        responsibilities=(
            "District works",
            "District cases",
            "Verification of flagged signals",
            "Remarks, evidence and case updates",
        ),
    ),
    "ADMIN": Role(
        name="ADMIN",
        title="System Administrator",
        summary="User register, system configuration and the audit trail. No part in any determination.",
        scope="national",
        capabilities=frozenset(
            {
                "view.national",
                "view.state",
                "view.district",
                "view.cases",
                "admin.users",
                "admin.config",
                "admin.audit",
            }
        ),
        responsibilities=(
            "User management",
            "System configuration",
            "Audit logs",
        ),
    ),
}


@dataclass(frozen=True)
class User:
    username: str
    display_name: str
    designation: str
    role: str
    state: str | None = None
    district: str | None = None

    @property
    def role_def(self) -> Role:
        return ROLES[self.role]

    def can(self, capability: str) -> bool:
        return capability in self.role_def.capabilities

    def as_dict(self) -> dict[str, Any]:
        role = self.role_def
        return {
            "username": self.username,
            "display_name": self.display_name,
            "designation": self.designation,
            "role": self.role,
            "role_title": role.title,
            "role_summary": role.summary,
            "scope": role.scope,
            "state": self.state,
            "district": self.district,
            "capabilities": sorted(role.capabilities),
            "responsibilities": list(role.responsibilities),
            "scope_label": scope_label(self),
        }


#: Fixed demo identities. The state and district values are real values from the
#: synthetic register, so each role's view is genuinely narrower than the last
#: rather than being an empty screen.
DEMO_USERS: dict[str, User] = {
    "ministry.officer": User(
        username="ministry.officer",
        display_name="R. Menon",
        designation="Director, MPLADS Division",
        role="MINISTRY",
    ),
    "state.officer": User(
        username="state.officer",
        display_name="S. Rathore",
        designation="State Nodal Officer, Rajasthan",
        role="STATE",
        state="Rajasthan",
    ),
    "district.officer": User(
        username="district.officer",
        display_name="A. Sharma",
        designation="District Authority, Jaipur",
        role="DISTRICT",
        state="Rajasthan",
        district="Jaipur",
    ),
    "admin": User(
        username="admin",
        display_name="System Administrator",
        designation="Prototype administrator",
        role="ADMIN",
    ),
}

DEFAULT_USER = "ministry.officer"


def scope_label(user: User) -> str:
    """One line describing what this user can see, shown in the interface."""
    if user.role_def.scope == "national":
        return "All states and districts"
    if user.role_def.scope == "state":
        return f"{user.state} — all districts"
    return f"{user.district}, {user.state}"


# --------------------------------------------------------------------------
# Request plumbing
# --------------------------------------------------------------------------


def current_user(x_nirikshan_user: str | None = Header(default=None)) -> User:
    """Resolve the acting user from a request header.

    Falls back to the ministry view when no header is sent, so every existing
    call site keeps its national scope and nothing that worked before narrows
    unexpectedly.
    """
    if not x_nirikshan_user:
        return DEMO_USERS[DEFAULT_USER]
    user = DEMO_USERS.get(x_nirikshan_user.strip())
    if user is None:
        raise HTTPException(
            status_code=401,
            detail=(
                f"Unknown demonstration user '{x_nirikshan_user}'. "
                f"Available: {', '.join(sorted(DEMO_USERS))}."
            ),
        )
    return user


def require(user: User, capability: str) -> None:
    """Refuse an action the acting role does not hold."""
    if not user.can(capability):
        raise HTTPException(
            status_code=403,
            detail=(
                f"The {user.role_def.title} role cannot perform this action "
                f"({capability}). This action is restricted by role."
            ),
        )


def in_scope(user: User, *, state: str | None, district: str | None) -> bool:
    """Whether a work or case in this state/district is visible to this user."""
    scope = user.role_def.scope
    if scope == "national":
        return True
    if scope == "state":
        return state == user.state
    return district == user.district and (user.state is None or state == user.state)


def filter_rows(user: User, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Narrow a list of project dictionaries to what this user may see."""
    if user.role_def.scope == "national":
        return rows
    return [r for r in rows if in_scope(user, state=r.get("state"), district=r.get("district"))]


def scoped_context(context: dict[str, Any], user: User) -> dict[str, Any]:
    """The analysis context with its record list narrowed to the user's area.

    Duplicate detection is corpus-level, so the analysis itself always runs over
    every work — narrowing the corpus would change the scores, and a district
    officer must see the same score for a work as the ministry does. Only the
    lists a view iterates over are narrowed; ``analyses`` is left whole so a
    lookup by id still works for anything the caller has already authorised.
    """
    if user.role_def.scope == "national":
        return context

    allowed = {
        r["project_id"]
        for r in context["records"]
        if in_scope(user, state=r.get("state"), district=r.get("district"))
    }
    return {
        **context,
        "records": [r for r in context["records"] if r["project_id"] in allowed],
        "rows": [r for r in context["rows"] if r.project_id in allowed],
    }


def assert_visible(user: User, *, state: str | None, district: str | None, what: str) -> None:
    """Refuse to serve a single record outside the user's scope."""
    if not in_scope(user, state=state, district=district):
        raise HTTPException(
            status_code=403,
            detail=(
                f"{what} is outside your area of responsibility "
                f"({scope_label(user)}). Access is restricted by role."
            ),
        )


#: Shown next to the role switcher. The prototype must not be mistaken for an
#: authenticated system.
AUTH_NOTICE = (
    "Demonstration identities only. This prototype has no password, session or "
    "token — the role is selected, not authenticated. Role scope and permissions "
    "are enforced by the API; a deployment would place a real identity provider "
    "in front of the same checks."
)
