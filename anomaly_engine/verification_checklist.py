"""
Verification checklists.

A risk signal on its own tells an officer that something needs looking at. It
does not tell them *what to look at*. This module turns each detected signal
into the concrete checks that would confirm or dismiss it.

Two rules shape everything here:

* Items are generated from the signals that were **actually detected** on a
  record. A work with no duplicate signal never gets duplicate checks, and a
  work with no signals gets no checklist at all. Nothing is shown for show.
* Each item carries the recorded figures the officer will be reconciling, taken
  from the anomaly's own evidence. The checklist is therefore a reading of the
  record, not a generic form.

Completing every item does not establish that a work is sound, and leaving them
incomplete does not establish that it is not. The checklist records what was
verified; the determination stays with the authorised officer.
"""

from __future__ import annotations

from typing import Any

#: The checks for each detector family, in the order an officer would work
#: through them. ``key`` is stable and is what gets persisted against a case,
#: so these strings must not be renamed casually once cases exist.
CHECKLIST_TEMPLATES: dict[str, list[dict[str, str]]] = {
    "COST_ANOMALY": [
        {
            "key": "cost.sanctioned_amount",
            "label": "Verify the sanctioned amount",
            "hint": "Confirm the sanctioned figure on the record against the sanction order.",
        },
        {
            "key": "cost.expenditure",
            "label": "Verify the reported expenditure",
            "hint": "Confirm the expenditure booked against the work in the accounts.",
        },
        {
            "key": "cost.revised_estimate",
            "label": "Check whether a revised estimate exists",
            "hint": "A sanctioned revision can account for the difference entirely.",
        },
        {
            "key": "cost.approval",
            "label": "Verify the approval for the revision or excess",
            "hint": "Identify the authority that approved the excess and on what date.",
        },
        {
            "key": "cost.payment_evidence",
            "label": "Review the payment evidence",
            "hint": "Reconcile the recorded payment instalments with the expenditure figure.",
        },
    ],
    "PROGRESS_MISMATCH": [
        {
            "key": "progress.physical",
            "label": "Verify the physical progress",
            "hint": "Confirm the reported physical completion against site measurement.",
        },
        {
            "key": "progress.reconcile",
            "label": "Reconcile financial against physical progress",
            "hint": "Establish what the funds drawn ahead of physical work were applied to.",
        },
        {
            "key": "progress.evidence",
            "label": "Review the progress evidence",
            "hint": "Inspect measurement books, site photographs or the inspection report.",
        },
    ],
    "DELAY_RISK": [
        {
            "key": "delay.timeline",
            "label": "Review the expected against the actual timeline",
            "hint": "Confirm the sanctioned completion date and any approved extension.",
        },
        {
            "key": "delay.latest_progress",
            "label": "Check the latest progress position",
            "hint": "Establish whether the recorded progress is current.",
        },
        {
            "key": "delay.reason",
            "label": "Record the reason for the delay",
            "hint": "Land, clearance, contractor, weather or funds — record which, with a reference.",
        },
    ],
    "POTENTIAL_DUPLICATE": [
        {
            "key": "duplicate.descriptions",
            "label": "Compare the project descriptions",
            "hint": "Read both descriptions side by side and note where they differ.",
        },
        {
            "key": "duplicate.locations",
            "label": "Compare the project locations",
            "hint": "Confirm whether the two works are at the same site or at distinct sites.",
        },
        {
            "key": "duplicate.work_type",
            "label": "Compare the asset or work type",
            "hint": "Confirm whether the same asset is being created twice.",
        },
        {
            "key": "duplicate.independence",
            "label": "Verify whether the works are actually independent",
            "hint": "Adjacent phases of one scheme and two separate works look alike in the data.",
        },
        {
            "key": "duplicate.separate_sanction",
            "label": "Verify the separate sanction for each work",
            "hint": "Confirm each work carries its own sanction order and its own allocation.",
        },
    ],
    "DATA_QUALITY": [
        {
            "key": "quality.missing_fields",
            "label": "Review the missing fields",
            "hint": "Obtain the values absent from the record and have them entered.",
        },
        {
            "key": "quality.inconsistent_values",
            "label": "Verify the inconsistent values",
            "hint": "Reconcile figures that cannot all be correct at the same time.",
        },
        {
            "key": "quality.dates",
            "label": "Verify the dates and supporting records",
            "hint": "Check the sequence of recommendation, sanction, start and completion dates.",
        },
    ],
}


#: Per-item context drawn from the anomaly itself, so an item reads as a check
#: against this record rather than a line from a standard form. The value is the
#: anomaly field whose text is worth repeating under the item.
_ITEM_CONTEXT: dict[str, str] = {
    "cost.sanctioned_amount": "expected_value",
    "cost.expenditure": "actual_value",
    "cost.revised_estimate": "difference",
    "progress.physical": "actual_value",
    "progress.reconcile": "difference",
    "delay.timeline": "expected_value",
    "delay.latest_progress": "actual_value",
    "duplicate.descriptions": "actual_value",
    "duplicate.locations": "difference",
    "quality.missing_fields": "actual_value",
    "quality.inconsistent_values": "difference",
}


def checklist_for_anomaly(anomaly: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the checklist items for one detected signal."""
    code = anomaly.get("type")
    template = CHECKLIST_TEMPLATES.get(code, [])
    if not template:
        return []

    items = []
    for entry in template:
        context_field = _ITEM_CONTEXT.get(entry["key"])
        recorded = anomaly.get(context_field) if context_field else None
        items.append(
            {
                "key": entry["key"],
                "signal_type": code,
                "signal_title": anomaly.get("title", code),
                "label": entry["label"],
                "hint": entry["hint"],
                # What the record currently says about this item, so the officer
                # is reconciling against a figure rather than from memory.
                "recorded": recorded if isinstance(recorded, str) else None,
            }
        )
    return items


def build_checklist(anomalies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every verification item raised by the signals detected on one work.

    Returns an empty list when nothing was detected — a clean record does not
    get a checklist, because there is nothing on it to verify.
    """
    items: list[dict[str, Any]] = []
    for anomaly in sorted(anomalies, key=lambda a: a.get("contribution", 0), reverse=True):
        items.extend(checklist_for_anomaly(anomaly))
    return items


def checklist_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Counts for a progress indicator, grouped by the signal that raised each item."""
    total = len(items)
    completed = sum(1 for i in items if i.get("completed"))
    by_signal: dict[str, dict[str, Any]] = {}
    for item in items:
        code = item.get("signal_type", "UNKNOWN")
        bucket = by_signal.setdefault(
            code,
            {"signal_type": code, "signal_title": item.get("signal_title", code), "total": 0, "completed": 0},
        )
        bucket["total"] += 1
        if item.get("completed"):
            bucket["completed"] += 1

    return {
        "total": total,
        "completed": completed,
        "pending": total - completed,
        "percent_complete": round(100.0 * completed / total, 1) if total else 0.0,
        "by_signal": list(by_signal.values()),
    }


#: Shown wherever a checklist is displayed, so a completed list is never read as
#: a clearance.
CHECKLIST_NOTE = (
    "These verification steps are generated from the signals detected on this "
    "record. Completing them documents what was checked; it is not a finding "
    "and does not by itself clear or implicate the work."
)
