# Active trading pubs layer — plan & sizing

Goal: plot **trading pubs** in the four target areas on the map, in their own colour,
with a view of **how well each one trades**, so a listing can be judged against its
neighbours (competition, saturation, proven demand) and distressed operators show up as leads.

## Status

**Stage 1 — free discovery: built.** `scripts/build_pubs.py` pulls every pub/bar in the four areas
from the FSA food-hygiene register (free, no key), de-duplicates old/new registrations, keeps the
operator matches from `watchlist.json`, and writes `data/pubs.json`: **167 premises** (Marylebone 13,
Fitzrovia 24, Notting Hill 48, Primrose Hill 82), each with **exact coordinates**, hygiene rating and
inspection date. 10 are flagged `needs_review` (theatres, clubs…) and held off the map, so **157 plot**.
Re-run any time; hand edits (notes, operator, `needs_review`) survive.

**Stage 2 — Google rating + review count: not built.** `scripts/enrich_pubs.py` is a documented
skeleton (budget cap, match rules, caching). Needs a Google Cloud key (card on file, hard quota cap).

**Map:** orange diamond pins, "Show trading pubs" toggle, follows the Area filter, popup shows
hygiene (and Google rating/reviews once present).

**Not done:** OpenStreetMap tags (opening hours, real ale, food, outdoor seating). The Overpass API
connection was reset from this environment even with the host allowed. Slot `metrics.osm` is reserved;
try again from another environment or a scheduled job.

## Limits to know

- The FSA register lists *premises that serve food/drink*, not a licence list: it can include a
  closed pub for a while and miss a very new one. `trading_status` is therefore unverified until Google
  reports "closed".
- 2 watchlist premises (Bourne & Hollingsworth, Bull & Bush) are not in the FSA pub/bar bucket; they stay
  as postcode-centre pins.
- Hygiene rating says nothing about how busy a pub is; that is what stage 2 adds.

## Data model (`data/pubs.json`, schema 2)

`id, fhrsid, name, address, postcode, area, lat, lng, trading_status (trading|closed|unknown),
needs_review, source, operator{company_number, company_name, match_basis}, metrics{hygiene{rating,
inspected}, google{place_id, rating, reviews, price_level, status, fetched}, osm{…}}, score, notes`.
A metric that was not fetched is `null` — never a guess.

## Stage 2 plan (Google, under the free allowance)

- Match each pub by name near its known lat/lng; accept only close name + distance matches.
- Save `place_id` once, so refreshes are a cheap details call.
- Hard budget of ~900 lookups/month in the script **and** a daily quota cap in Google Cloud.
- Priority: pubs nearest a current listing, then oldest data.
- Show rating + review count as-is (review count ≈ how busy); add a derived score only if still wanted.
- Then: "competition within 300 m" on each listing card (count, average rating, busiest pub).

## Not planned (judged not worth it)

Company-by-company Companies House matching, VOA rateable values and licensing-register scraping.
Use Companies House by hand for individual shortlisted pubs instead.

## Decisions needed

1. Google Cloud account + key with a hard quota cap (stage 2).
2. ~~Chains~~ — decided: independents only. `data/chains.json` flags obvious brands by name; pub-company pubs with individual names (Fuller's, Young's, Greene King) need flagging by hand via `chain` in pubs.json.
