"""Dump real API responses to JSON fixtures for the frontend render test.

The frontend cannot reach a live server in this sandbox, so the render smoke
test stubs ``fetch`` with these files. They are captured from the actual FastAPI
application rather than hand-written, so the shapes the components are tested
against are the shapes they will really receive.

Run:  .venv/bin/python -m tools.dump_fixtures
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import quote, urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import SessionLocal  # noqa: E402
from backend.main import app  # noqa: E402
from backend.models import CaseEvent, InvestigationCase, VerificationItem  # noqa: E402
from tools.asgi_client import Client  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "frontend" / "src" / "__fixtures__"

HERO = "MPLAD-2026-024"
CLEAN = "MPLAD-2026-001"

#: Two works on file and a peer in the same district, so the profile page is
#: exercised with a real signal mix rather than a single row. The comma and the
#: space are deliberate: this name is also the encoding case that the agency
#: route got wrong once already.
AGENCY = "Zilla Parishad, Nagpur"

#: The demonstration identity each capture acts as. The district officer holds
#: every verification capability, so the case payloads come out with the full
#: set of actions available rather than a subset.
DISTRICT_USER = "district.officer"

# (path, params) pairs covering every request the frontend makes, including the
# variants the Projects page issues as the user filters.
REQUESTS: list[tuple[str, dict]] = [
    ("/api/health", {}),
    ("/api/dashboard/stats", {}),
    ("/api/investigation-queue", {}),
    ("/api/agencies", {}),
    ("/api/methodology", {}),
    ("/api/projects", {"risk_level": "ALL", "sort": "risk_desc"}),
    ("/api/projects", {"risk_level": "CRITICAL", "sort": "risk_desc"}),
    ("/api/projects", {"risk_level": "HIGH", "sort": "risk_desc"}),
    ("/api/projects", {"search": "Rampur", "risk_level": "ALL", "sort": "risk_desc"}),
    ("/api/projects", {"search": "zzzznotathing", "risk_level": "ALL", "sort": "risk_desc"}),
    (f"/api/projects/{HERO}", {}),
    (f"/api/projects/{CLEAN}", {}),
    (f"/api/projects/{HERO}/analyze", {}),
    (f"/api/projects/{CLEAN}/analyze", {}),
    ("/api/projects/MPLAD-2026-017", {}),  # the deliberately malformed record
    ("/api/projects/MPLAD-2026-017/analyze", {}),
    # --- role, case workflow and derived intelligence
    ("/api/roles", {}),
    ("/api/me", {}),
    ("/api/cases", {}),
    ("/api/audit", {}),
    ("/api/compliance", {}),
    ("/api/trends", {}),
    ("/api/watchlist", {}),
    (f"/api/projects/{HERO}/network", {}),
    (f"/api/projects/{CLEAN}/network", {}),
    # The project page asks for relationships on every record it shows, so the
    # malformed one is captured too: it is the case with no coordinates.
    ("/api/projects/MPLAD-2026-017/network", {}),
    (f"/api/projects/{HERO}/what-if", {}),
    # Percent-encoded to match what encodeURIComponent sends from the browser,
    # so the recorded key is the key the stub will look up.
    (f"/api/agencies/{quote(AGENCY, safe='')}", {}),
]


def key_for(path: str, params: dict) -> str:
    return path + (f"?{urlencode(sorted(params.items()))}" if params else "")


def seed_case(client: Client) -> str:
    """Open a case on the hero work and part-complete it, for the case fixtures.

    The shipped database carries no case activity — inventing officer work in a
    demonstration dataset would be dishonest, and the demo is better for opening
    the case live. But the case detail page still has to be render-tested, so a
    case is created here, captured, and removed again by :func:`clear_cases`.
    """
    headers = {"X-Nirikshan-User": DISTRICT_USER}
    created = client.post("/api/cases", json={"project_id": HERO}, headers=headers)
    if created.status != 201:
        print(f"  WARN could not open a case: {created.status} {created.json()}")
        return ""

    case_id = created.json()["case_id"]

    # Tick the first item so the fixture exercises a part-complete checklist and
    # the status transition that the first verification entry triggers.
    items = created.json().get("checklist") or []
    if items:
        client.patch(
            f"/api/cases/{case_id}/checklist/{items[0]['key']}",
            json={
                "completed": True,
                "remark": "Sanction order located on file and the figure matches the register.",
                "evidence_ref": "SO/JPR/2026/0241",
            },
            headers=headers,
        )
    client.post(
        f"/api/cases/{case_id}/remarks",
        json={"remark": "Site visit scheduled with the junior engineer.", "reference": None},
        headers=headers,
    )
    return case_id


def clear_cases() -> None:
    """Remove every case row, so the committed database ships clean."""
    db = SessionLocal()
    try:
        db.query(VerificationItem).delete()
        db.query(CaseEvent).delete()
        db.query(InvestigationCase).delete()
        db.commit()
    finally:
        db.close()


def main() -> int:
    client = Client(app)
    client.startup()

    clear_cases()
    case_id = seed_case(client)

    requests = list(REQUESTS)
    if case_id:
        requests.append((f"/api/cases/{case_id}", {}))

    OUT.mkdir(parents=True, exist_ok=True)
    fixtures: dict[str, object] = {}

    for path, params in requests:
        response = client.get(path, params=params or None)
        if response.status != 200:
            print(f"  WARN {path} -> {response.status}")
        fixtures[key_for(path, params)] = response.json()

    clear_cases()

    target = OUT / "api.json"
    target.write_text(json.dumps(fixtures, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(fixtures)} fixtures to {target.relative_to(Path.cwd())}")
    if case_id:
        print(f"Captured case {case_id}; case rows cleared so the database ships clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
