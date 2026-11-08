# Active trading pubs layer — plan & sizing

Goal: plot **trading pubs** in the four target areas on the map, in their own colour,
with a view of **how well each one trades**, so a listing can be judged against its
neighbours (competition, saturation, proven demand) and distressed operators show up as leads.

## What exists now (scaffold)

| Piece | Where | State |
|---|---|---|
| Pub dataset | `data/pubs.json` | 28 pubs seeded from `watchlist.json` (4 flagged `needs_review`: theatres/clubs) |
| Seeder | `scripts/seed_pubs.py` | Works, offline, idempotent |
| Enrichment + scoring | `scripts/enrich_pubs.py` | **Stubs only** — four sources + scorer raise `NotImplementedError` |
| Map layer | `index.html` | Orange diamond pins, "Show trading pubs" toggle, follows the Area filter, popup shows metrics when present |

Pubs reuse the listings' geocoding (postcodes.io, cached), so no coordinates to maintain.
Pins sit at postcode centre — good enough for ~1 pub per postcode; co-located pubs are fanned out.

## Data model (`data/pubs.json`)

`id, name, address, postcode, area, trading_status (trading|closed|unknown), needs_review,
source, operator{company_number, company_name, match_basis}, metrics{google, hygiene,
companies_house, rateable_value}, score{value 0-100, confidence, parts}, notes`.
A metric that was not fetched is `null` — never a guess.

## Reality check: "how successful"

A pub's turnover and profit are **not public**; small companies file filleted accounts with
no P&L. So "success" can only be a **proxy score**, shown with a confidence level:

| Signal | Source | Cost | What it tells you | Weakness |
|---|---|---|---|---|
| Rating × review count, price level, open/closed | Google Places API | Paid (~$20 per 1,000 lookups at last check; verify). Needs billing + key | Footfall/popularity, and whether it is still open | Popularity ≠ profit; name/address matching errors |
| Food hygiene rating + inspection date | FSA API | Free, no key | Operational standard; confirms it exists | Weak proxy for success |
| Rateable value | VOA business-rates open data | Free | Size/trade potential vs area median | Property size, not performance |
| Operator health: status, overdue filings, charges, net assets/cash, officer churn | Companies House API | Free key | Distress / stability. Strongest lead signal | Only where the operator company is matched; chains/managed houses hide the unit |
| Licence hours/capacity, variations, surrenders | Westminster / Camden / RBKC registers | Free, HTML scraping | Ambition, and exit leads | Three different systems; brittle |

Draft score: Google 50 · operator health 20 · rateable value vs area 20 · hygiene 10, with missing
parts dropped, weights rescaled, and `confidence` = share of weight available.

## Phases and size

Estimates are focused working days for one developer pairing with Claude; the scaffold above is Phase 0.

| # | Phase | Work | Size |
|---|---|---|---|
| 1 | **Discovery** | Pull all pub/bar premises in the target postcodes from the FSA register; drop theatres/clubs/restaurants; curate; dedupe. Expect a few hundred premises, ~150–250 real pubs (guess until queried) | 1–2 d |
| 2 | **Success v1** | Google Places + FSA hygiene fetchers, name/address matching with a confidence threshold, scorer, caching so refreshes are cheap | 2–3 d |
| 3 | **Operator & property** | Match pubs to operating companies (by hand/conservatively, as with the watchlist), Companies House health, VOA rateable values | 2–4 d |
| 4 | **UI** | Popup/side-panel detail, colour or size pins by score, filter by score, ranked table, score explainer, "nearby trading pubs" on each listing card | 2–3 d |
| 5 | **Automation & ops** | Run enrichment on the existing Mon/Thu agent or a Supabase function; keys in Vault; cost cap; README/agent instructions | 1–2 d |

- **MVP** (1 + 2 + light 4 + light 5): **~5–8 working days**.
- **Full build** (all phases): **~9–14 working days**.
- **Running cost:** roughly $10–30/month in Places lookups for a few hundred pubs refreshed monthly
  (to be confirmed against current pricing), plus the existing Supabase.
- **Ongoing effort:** ~1 hour/week curating new/closed pubs and operator matches.

## Decisions needed

1. **Google Places** — are you happy to create a Google Cloud billing account and key? It is the best single success signal.
2. **Scope** — all pubs, or only pubs within ~500 m of a current listing?
3. **Chains** — include chain/managed pubs (Nicholson's, Greene King…) or independents only? Chains are noisier to score.
4. **Storage** — `data/pubs.json` in the repo is fine up to ~1,000 pubs; move to Supabase if you want history/trends.

## Risks

- Matching a pub to the right Google/Companies House record is the main quality risk — wrong matches are worse than gaps (same rule as the watchlist).
- Google data terms limit caching/storing results; store only what the terms allow and refresh rather than archive.
- Score can mislead: a packed pub on a thin margin scores well. Always show confidence and the parts.
