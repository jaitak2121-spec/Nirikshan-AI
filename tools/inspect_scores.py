"""Scratch: seed the database and print the risk distribution the engine produces."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from anomaly_engine import analyze_corpus  # noqa: E402
from backend.data.seed_data import PROJECTS  # noqa: E402

AS_OF = date(2026, 9, 2)

results = analyze_corpus(PROJECTS, as_of=AS_OF)

rows = []
for pid, res in results.items():
    codes = [a["type"] for a in res["anomalies"]]
    rows.append((res["risk_score"], pid, res["risk_level"], codes))

rows.sort(reverse=True)

print(f"{'SCORE':>6}  {'PROJECT':<16} {'LEVEL':<9} SIGNALS")
print("-" * 100)
for score, pid, level, codes in rows:
    print(f"{score:>6.1f}  {pid:<16} {level:<9} {', '.join(codes) or '-'}")

from collections import Counter  # noqa: E402

print()
print("Distribution:", dict(Counter(r[2] for r in rows)))

hero = results["MPLAD-2026-024"]
print()
print("=" * 100)
print("HERO  MPLAD-2026-024")
print("=" * 100)
print("score:", hero["risk_score"], hero["risk_level"])
for b in hero["risk"]["breakdown"]:
    print(f"  {b['type']:<22} max={b['max_weight']:<6} factor={b['severity_factor']:.3f} -> {b['points']:.2f}")
print("raw_total:", hero["risk"]["raw_total"], "clamped:", hero["risk"]["was_clamped"])
print()
for a in hero["anomalies"]:
    print(f"[{a['severity']}] {a['title']}")
    print("   ", a["headline"])
    for e in a["evidence"]:
        print(f"      - {e['label']}: {e['value']}")
print()
print("RECOMMENDATION:", hero["recommendation"]["priority"], "|", hero["recommendation"]["headline"])
for step in hero["recommendation"]["checklist"]:
    print("   [ ]", step)
print()
print("SIMILAR:", [(s["project_id"], round(s["similarity"], 3), s.get("distance_km")) for s in hero["similar_projects"]])
print()
print("VALIDATION ISSUES:")
for i in hero["validation"]["issues"]:
    print(f"  [{i['severity']}] {i['field']}: {i['reason']}")
