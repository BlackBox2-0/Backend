from __future__ import annotations

import hashlib
import json
from typing import Any

from database import fetch_all


def _tx_hash(identifier: str, timestamp: str) -> str:
    digest = hashlib.sha256(f"{identifier}-{timestamp}".encode()).hexdigest()
    return f"bb-{digest[:8]}-{digest[8:12]}"


def get_transactions() -> list[dict[str, Any]]:
    enforcement_rows = fetch_all("enforcement_events", "timestamp DESC")
    override_rows = fetch_all("overrides", "created_at DESC")

    txs: list[dict[str, Any]] = []

    for row in enforcement_rows:
        payload: dict[str, Any] = {}
        if row.get("payload_json"):
            try:
                payload = json.loads(row["payload_json"])
            except Exception:
                pass

        txs.append({
            "tx_hash": _tx_hash(row["id"], row["timestamp"]),
            "type": "ENFORCEMENT",
            "actor": payload.get("user") or row.get("user") or "policy_engine",
            "event_id": row["id"],
            "decision": row["final_decision"],
            "reason": payload.get("final_decision_source") or "policy",
            "resource": row.get("resource") or payload.get("resource") or "",
            "timestamp": row["timestamp"],
            "confirmed": True,
        })

    for row in override_rows:
        txs.append({
            "tx_hash": _tx_hash(row["id"], row["created_at"]),
            "type": "OVERRIDE",
            "actor": row["actor"],
            "event_id": row["original_event_id"],
            "decision": row["new_decision"],
            "reason": row["reason"],
            "resource": "",
            "timestamp": row["created_at"],
            "confirmed": True,
        })

    txs.sort(key=lambda t: t["timestamp"], reverse=True)
    return txs
