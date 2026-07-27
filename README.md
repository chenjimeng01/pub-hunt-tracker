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

   For each candidate capture: name/address, area, postcode, sale vs let,
   freehold/leasehold if stated, price or annual rent, size/covers, a one-line
   description, and the **direct source URL**.

2. **Dedupe** against the cards already in `index.html` (match on address + source).

3. **Edit `index.html`** — listing cards only. Do not touch the CSS, palette,
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

4. **PropertyData enrichment — MARYLEBONE LISTINGS ONLY** (user instruction: do not
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

5. **Commit and push** to `main` with message `refresh: <date> — N listings, M new`.

### Hard rules

- Only **real listings actually found this run**, each with a real working source
  URL. Never invent a listing, address, price, or link.
- If an area turns up nothing new, keep its existing listings and just refresh the date.
- POA = price on application.
- Keep the four area sections even if one is empty (use the existing empty-state note).
