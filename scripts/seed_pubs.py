#!/usr/bin/env python3
"""Seed data/pubs.json from watchlist.json (the FSA-register pub/bar premises).

Idempotent: re-running keeps anything already in data/pubs.json (metrics, notes,
manual edits) and only adds premises it hasn't seen. Offline, no API keys.

    python3 scripts/seed_pubs.py
"""
import json, re, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WATCHLIST = ROOT / "watchlist.json"
OUT = ROOT / "data" / "pubs.json"

# FSA's "pub/bar" bucket includes venues that merely hold a bar.
NOT_A_PUB = re.compile(r"theatre|cinema|hotel|club\b|restaurant|gallery|museum", re.I)


def slug(*parts):
    return re.sub(r"[^a-z0-9]+", "-", " ".join(parts).lower()).strip("-")


def new_pub(w):
    operator = None
    if w.get("company_number"):
        operator = {
            "company_number": w["company_number"],
            "company_name": w.get("company_name"),
            "match_basis": w.get("match_basis"),
        }
    return {
        "id": slug(w["pub_name"], w["postcode"]),
        "name": w["pub_name"],
        "address": w["address"],
        "postcode": w["postcode"],
        "area": w["area"],
        "trading_status": "trading",          # trading | closed | unknown
        "needs_review": bool(NOT_A_PUB.search(w["pub_name"])),  # confirm it is really a pub
        "source": "fsa-watchlist",
        "operator": operator,
        # Filled by scripts/enrich_pubs.py. null = not fetched yet.
        "metrics": {"google": None, "hygiene": None, "companies_house": None, "rateable_value": None},
        "score": None,                         # {"value": 0-100, "confidence": "low|med|high", "parts": {...}}
        "notes": "",
    }


def main():
    existing = {}
    if OUT.exists():
        existing = {p["id"]: p for p in json.loads(OUT.read_text())["pubs"]}
    added = 0
    for w in json.loads(WATCHLIST.read_text()):
        p = new_pub(w)
        if p["id"] not in existing:
            existing[p["id"]] = p
            added += 1
    pubs = sorted(existing.values(), key=lambda p: (p["area"], p["name"].lower()))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"schema_version": 1, "generated": date.today().isoformat(), "pubs": pubs}, indent=1) + "\n")
    print(f"{len(pubs)} pubs in {OUT.relative_to(ROOT)} ({added} new)", file=sys.stderr)


if __name__ == "__main__":
    main()
