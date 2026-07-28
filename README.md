# London Pub Property Tracker

Live site: **https://chenjimeng01.github.io/pub-hunt-tracker/**

A tracker of pub / licensed premises for sale or to let across four target areas
for a pub-opening venture: **Marylebone** (W1U, W1H, W1G), **Fitzrovia** (W1T, W1W),
**Notting Hill** (W11, W2, W8) and **Primrose Hill** (NW1, NW3).
Both freehold and leasehold, no budget filter. Also tracks convertible Class E
units (restaurants/retail) — good pub sites often come to market as restaurants first.

The whole site is a single hand-maintained `index.html`. No build step.
Push to `main` and GitHub Pages redeploys automatically.

## Refresh procedure (automated, Mon & Thu)

A scheduled cloud agent refreshes the listings twice a week. The procedure:

1. **Search** the web for current listings in the four areas — pubs/bars first,
   then convertible Class E units; both for-sale and to-let. Priority sources:
   - Specialist pub agents (best stock, earliest): Christie & Co
     (`christie.com/pubs-for-sale/london`), Fleurets
     (`fleurets.com/properties/pubs-and-bars.html`), AG&G (`agg.uk.com`)
   - Portals: Rightmove commercial (`.../commercial-property-for-sale/<Area>/pubs.html`
     and `.../commercial-property-to-let/...`), Zoopla commercial hospitality,
     OnTheMarket commercial.

   **Agent-direct stock is the biggest blind spot** — specialist agents often
   market pubs only on their own sites, which block direct fetching (Savills
   returns 403). Sweep them via web search each run, one query per area, e.g.:
   `site:search.savills.com pub <area>` · `"pub" "<area>" for sale Savills OR
   Christie OR Fleurets OR "licensed leisure"` · `pub freehold <area> NW1/W1/W11
   for sale 2026`. When an agent page can't be fetched, find the same listing's
   portal mirror (Rightmove/Zoopla carry most Savills licensed-leisure stock) and
   verify + link THAT. Missing agent-only listings is how The Albert (Primrose
   Hill, £2.475m, on the market for months) was initially missed.

   **Distinguish investment sales from vacant possession.** A pub freehold sold
   with a sitting tenant on an FRI lease buys the income, not the keys — tag such
   cards "Pub (investment)" and state the lease/break terms in the description.

   For each candidate capture: name/address, area, postcode, sale vs let,
   freehold/leasehold if stated, price or annual rent, size/covers, a one-line
   description, and the **direct source URL**.

2. **VERIFY EVERY LISTING — the most important stage.** Search-engine snippets lag
   the market by weeks; never trust them. For EVERY candidate (new finds AND every
   card already on the tracker), fetch its detail-page URL this run and check:
   - HTTP 404/410, or a redirect to a search-results page → **dead, exclude/remove**
   - Page says "no longer on the market", "let agreed", "sold", "under offer" → **exclude/remove**
   - Only a page that renders the specific property with an asking price/rent and
     no removed/agreed marker counts as live.

   Card source links must be **direct detail pages only** (e.g.
   `zoopla.co.uk/.../details/NNNN/`, `rightmove.co.uk/properties/NNNN`) — NEVER a
   search-results URL. Every live card gets a dated verification line in `.specs`:
   `<span class="v-ok">✓ Listing verified live 30 Jul</span>` (update the date each
   run it re-verifies).

   Tip: Zoopla search pages render server-side — enumerate them for candidate
   detail URLs, then verify each detail page individually. An area with zero
   verified listings keeps its section with an honest `.empty-note` explaining
   what happened (see Fitzrovia).

3. **Dedupe** against the cards already in `index.html` (match on address + source).

4. **Edit `index.html`** — listing cards only. Do not touch the CSS, palette,
   typography, layout, Saved Searches section, or footer. Per card, match the
   existing markup exactly: `.card` with `data-area` / `data-status` attributes,
   `.card-tags` (`.tag` classes: `sale` / `let` / `freehold` / `leasehold` / `type`),
   `h3`, `.price`, `.desc`, `.specs`, `.src-link`.
   - Tag genuinely new listings by adding, as the first child of `.card-tags`:
     `<span class="tag" style="background:var(--accent);color:#fff">New</span>`
   - Remove the `New` tag from cards that carried it last run.
   - Drop listings that have clearly left the market.
   - Update the masthead "Last refreshed" date (`Thu 30 July 2026` format),
     the summary stat numbers, and each area section's `.count`.

   Every card also carries `data-pc="<postcode>"` on its `<article>` — always
   resolve the FULL postcode: if the listing doesn't publish one, extract the
   listing page's map coordinates (Zoopla embeds `"latitude"`/`"longitude"` in
   the page source) and reverse-geocode via
   `api.postcodes.io/postcodes?lon=<lng>&lat=<lat>` (free, no key). Full
   postcodes unlock property-level PropertyData checks (conservation, listed,
   planning, floor areas, £/sqft) instead of the district fallback and this button as the last
   child of `.card-foot`: `<button class="pd-btn" type="button">PropertyData check</button>`
   — it powers the on-demand PropertyData lookup (Supabase edge function
   `pubhunt-propertydata`; the page JS handles the rest, do not modify it).
   Each `.area-head` likewise keeps its `<button class="pd-btn pd-area-btn"
   type="button" data-pc="<district>">Area check</button>` (districts: Marylebone
   W1U, Fitzrovia W1T, Notting Hill W11, Primrose Hill NW1).

5. **PropertyData enrichment — MARYLEBONE LISTINGS ONLY** (user instruction: do not
   spend credits on other areas). Requires the API key in env var
   `PROPERTYDATA_API_KEY` (locally: `.env`, git-ignored — **NEVER commit the key**;
   if the env var is absent, skip this step entirely and leave existing vitals as-is).

   Base URL `https://api.propertydata.co.uk/<endpoint>?key=$KEY&postcode=...`
   Rate limit: **4 calls per 10 seconds** — sleep between calls. ~1 credit/call;
   trial account has 500 total, so enrich **new Marylebone listings only**, not
   re-checks of ones that already have a `.vitals` block.

   Per new Marylebone listing with a full postcode:
   - `/conservation-area` and `/listed-buildings` → verification rows
   - `/planning-applications` → one row only if something material is nearby
   - Skip `/valuation-commercial-sale` and `/valuation-commercial-rent` unless the
     listing states floor area (`property_type` + area params required) — never
     guess a floor area to force a valuation.

   Render results in a `<div class="vitals">` block inside the card, after `.specs`,
   before `.card-foot` — see The Harcourt card for the exact markup (`.v-src` dated
   header, `.v-row` rows, `.v-flag` for consent warnings). Keep the Marylebone
   `.area-vitals` strip's date current if you refresh area stats (crime,
   demographics, restaurants — district level; refresh at most monthly).
   Only report values the API actually returned — never invent figures.

6. **Licensing register sweep (best-effort).** Check the public premises-licence
   registers for new applications, transfers, variations, and surrenders at
   addresses in the target postcodes:
   - Westminster: `licensing.westminster.gov.uk` (current applications search)
   - Camden: `camden.gov.uk` licensing register / current licensing applications
   - RBKC: `rbkc.gov.uk` licensing register
   These are HTML pages on different systems — read them, extract anything at a
   pub/bar address in W1U/W1H/W1G/W1T/W1W/W11/W2/W8/NW1/NW3, and note it in the
   commit summary. A licence **surrender or transfer** at a pub address is a
   strong lead — flag it prominently. If a register is down or unsearchable,
   skip it and say so; do not guess.

7. **Commit and push** to `main` with message `refresh: <date> — N listings, M new`.

## Off-market signals architecture

The tracker page has a Signals section that loads live (cached 24h) from the
Supabase edge function `pubhunt-signals`:

- **`{action: "planning"}`** — queries PlanIt (free, no key) for planning
  applications within ~1km of each area centre, rolling 56-day window, filtered
  to pub/licensed-use relevance. Classes: `possible-exit` (pub + residential
  conversion terms — a freeholder heading for the door), `use-change` (change of
  use involving licensed/restaurant/Class E/sui generis), `activity` (other).
- **`{action: "companies"}`** — Companies House watch over `pubhunt_watchlist`
  (Supabase table; human-readable copy in `watchlist.json`, built from the FSA
  food-hygiene register's pub/bar premises in the four areas). Flags non-active
  status, overdue accounts/confirmation statements. Needs the **live** CH API
  key in Vault (`COMPANIES_HOUSE_API_KEY`, read via service-role-only RPC
  `pubhunt_get_ch_key`). Watchlist rows need `company_number` populated —
  match operators conservatively and curate by hand; wrong matches are worse
  than missing ones.

Both API keys live in Supabase Vault — **never in this public repo**.
The scheduled agent should mention notable new signals in its final summary.

### Hard rules

- Only **real listings actually found this run**, each with a real working source
  URL. Never invent a listing, address, price, or link.
- If an area turns up nothing new, keep its existing listings and just refresh the date.
- POA = price on application.
- Keep the four area sections even if one is empty (use the existing empty-state note).
