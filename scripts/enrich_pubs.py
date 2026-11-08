#!/usr/bin/env python3
"""Enrich data/pubs.json with trading-performance signals, then score each pub.

SCAFFOLD ONLY — the sources below are stubs; none is implemented or has been run.
Each source fills one key of pub["metrics"]; the scorer turns whatever is present
into pub["score"]. A source that has no key / no match must leave its metric null
(never guess), and the scorer must lower `confidence` rather than invent a value.

Keys come from the environment (locally .env, git-ignored; in CI/Supabase Vault).
NEVER commit a key to this public repo.

    python3 scripts/enrich_pubs.py --source hygiene          # one source
    python3 scripts/enrich_pubs.py --all --max-age-days 30   # everything stale
"""
import argparse, json, os
from pathlib import Path

PUBS = Path(__file__).resolve().parent.parent / "data" / "pubs.json"


def fetch_hygiene(pub):
    """FSA food-hygiene rating + last inspection date. Free, no key.
    api.ratings.food.gov.uk/Establishments (header x-api-version: 2).
    -> {"rating": 5, "inspected": "2025-03-04", "fhrsid": 123}"""
    raise NotImplementedError


def fetch_google(pub):
    """Google Places (New): rating, user_ratings_total, price_level, business_status.
    Needs GOOGLE_PLACES_API_KEY. Match on name + address; reject low-confidence matches.
    -> {"rating": 4.5, "reviews": 1203, "price_level": 2, "business_status": "OPERATIONAL"}"""
    raise NotImplementedError


def fetch_companies_house(pub):
    """Operator company health. Needs COMPANIES_HOUSE_API_KEY. Only for pubs with
    pub["operator"] set (matched by hand). Accounts for small companies rarely
    include turnover, so record: status, accounts overdue, charges, latest net
    assets/cash if filed, officer changes in the last 12 months.
    -> {"status": "active", "accounts_overdue": False, "charges": 1, "net_assets": 84000}"""
    raise NotImplementedError


def fetch_rateable_value(pub):
    """VOA business rates list (open data): rateable value as a size/trade proxy.
    -> {"rateable_value": 62000, "description": "Public House and Premises"}"""
    raise NotImplementedError


SOURCES = {
    "hygiene": fetch_hygiene,
    "google": fetch_google,
    "companies_house": fetch_companies_house,
    "rateable_value": fetch_rateable_value,
}


def score(pub):
    """Transparent 0-100 'trading strength' from whatever metrics exist.
    Proxy only — true turnover/profit is not public for most pubs.
    Draft weights: Google rating x review volume 50, operator health 20,
    rateable value vs area median 20, hygiene 10. Missing parts are dropped and
    the remaining weights rescaled; confidence = share of weight that was available.
    -> {"value": 72, "confidence": "med", "parts": {...}}"""
    raise NotImplementedError


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=SOURCES)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--max-age-days", type=int, default=30)
    args = ap.parse_args()
    data = json.loads(PUBS.read_text())
    wanted = list(SOURCES) if args.all else [args.source] if args.source else []
    for pub in data["pubs"]:
        for name in wanted:
            pub["metrics"][name] = SOURCES[name](pub)  # TODO: skip if fresher than --max-age-days
        if wanted:
            pub["score"] = score(pub)
    PUBS.write_text(json.dumps(data, indent=1) + "\n")


if __name__ == "__main__":
    main()
