#!/usr/bin/env python3
"""Enrich data/pubs.json with Google Places data (stage 2).

SCAFFOLD ONLY - not implemented, not run. Stage 1 (scripts/build_pubs.py) is free and
done; this stage adds rating / review count / closed-status per pub within a hard
monthly budget so it stays inside Google's free usage.

Design (see docs/active-pubs-plan.md):
  * Key from the environment (GOOGLE_PLACES_API_KEY; .env locally, never committed).
  * Find the place with a text search for the pub's name biased to its exact lat/lng
    (every pub already has coordinates) and require a close name + distance match;
    on any doubt leave metrics.google null. A wrong match is worse than a gap.
  * Save place_id on first match so later refreshes are a cheap details call, not a search.
  * Hard cap: --budget N lookups per run (default 900). Also set a daily quota cap in Google Cloud.
  * Skip pubs fetched within --max-age-days. Order by distance to a current listing first.
  * Store only what Google's terms allow (place_id, rating, review count, price level, status).

    python3 scripts/enrich_pubs.py --budget 900 --max-age-days 30
"""
import argparse, json, os
from pathlib import Path

PUBS = Path(__file__).resolve().parent.parent / "data" / "pubs.json"


def lookup_google(pub, api_key):
    """-> {"place_id", "rating", "reviews", "price_level", "status", "fetched"} or None."""
    raise NotImplementedError


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=900)
    ap.add_argument("--max-age-days", type=int, default=30)
    args = ap.parse_args()
    key = os.environ.get("GOOGLE_PLACES_API_KEY")
    if not key:
        raise SystemExit("GOOGLE_PLACES_API_KEY is not set")
    data = json.loads(PUBS.read_text())
    # TODO: select pubs (listing-proximity first, stale first), call lookup_google up to
    # args.budget times, write metrics.google, and set pub["score"] only once a
    # scoring rule is agreed (stage 2 shows rating + reviews, not an invented score).
    raise NotImplementedError


if __name__ == "__main__":
    main()
