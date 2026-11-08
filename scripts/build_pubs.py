#!/usr/bin/env python3
"""Build data/pubs.json: every pub/bar in the four target areas.

Sources (both free, no key):
  * FSA food-hygiene register  api.ratings.food.gov.uk  - premises, exact lat/lng,
    hygiene rating + inspection date. Business type 7843 = "Pub/bar/nightclub".
  * watchlist.json - hand-curated operator (Companies House) matches, kept as-is.

Idempotent: re-running refreshes name/address/coordinates/hygiene from the FSA and
keeps anything curated by hand (notes, operator, needs_review, metrics.google, score).
Premises the FSA no longer lists are left in place, not deleted - check them by hand.

    python3 scripts/build_pubs.py            # fetch from FSA + merge
    python3 scripts/build_pubs.py --offline  # only fold watchlist.json into pubs.json
"""
import argparse, json, re, sys, time, urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WATCHLIST = ROOT / "watchlist.json"
CHAINS = ROOT / "data" / "chains.json"
OUT = ROOT / "data" / "pubs.json"
FSA = "https://api.ratings.food.gov.uk/Establishments"
PUB_BAR_NIGHTCLUB = 7843

# Postcode districts that define each target area (see README).
AREA_OF_DISTRICT = {
    "W1U": "marylebone", "W1H": "marylebone", "W1G": "marylebone",
    "W1T": "fitzrovia", "W1W": "fitzrovia",
    "W11": "notting-hill", "W2": "notting-hill", "W8": "notting-hill",
    "NW1": "primrose-hill", "NW3": "primrose-hill",
}
# (lat, lng) search centres, 1 mile radius each; together they cover the districts above.
CENTRES = [
    (51.5205, -0.1527),  # Marylebone High St
    (51.5190, -0.1388),  # Fitzrovia
    (51.5094, -0.1967),  # Notting Hill
    (51.5154, -0.1755),  # Paddington / Bayswater (W2)
    (51.5010, -0.1930),  # Kensington (W8)
    (51.5390, -0.1606),  # Primrose Hill
    (51.5392, -0.1426),  # Camden Town (NW1)
    (51.5559, -0.1780),  # Hampstead (NW3)
    (51.5435, -0.1747),  # Swiss Cottage (NW3/NW8 edge)
    (51.5504, -0.1646),  # Belsize Park (NW3)
    (51.5172, -0.2100),  # Ladbroke Grove (W11)
    (51.5199, -0.1700),  # Edgware Road (W2/W1H)
    (51.5252, -0.1337),  # Euston (NW1)
    (51.5260, -0.1600),  # Regent's Park / Baker St (NW1)
]
RADIUS_MILES = 1

# The FSA bucket includes things that are not pubs; hold these back until confirmed.
NOT_A_PUB = re.compile(r"theatre|cinema|hotel|nightclub|night club|\bclub\b|restaurant|gallery|museum|casino", re.I)


def slug(*parts):
    return re.sub(r"[^a-z0-9]+", "-", " ".join(parts).lower()).strip("-")


def norm_name(s):
    s = re.sub(r"\b(the|ph|public house|pub|and|&)\b", " ", s.lower())
    return re.sub(r"[^a-z0-9]+", "", s)


def tidy(s):
    """FSA data is often ALL CAPS; title-case it (keeping apostrophes and & sane)."""
    s = s.strip()
    if not s.isupper():
        return s
    out = re.sub(r"[A-Za-z]+('[A-Za-z]+)?", lambda m: m.group(0).capitalize() if "'" not in m.group(0)
                 else m.group(0).split("'")[0].capitalize() + "'" + m.group(0).split("'")[1].lower(), s.lower())
    return re.sub(r"\b(Nw|Sw|Se|Ne|Wc|W|E|N)(\d{1,2}[A-Za-z]?)\b", lambda m: m.group(0).upper(), out)  # postcodes


def detect_chain(name, brands):
    for brand, pattern in brands.items():
        if re.search(pattern, name, re.I):
            return brand
    return None


def district(pc):
    return pc.upper().split()[0] if pc else ""


def fetch_json(url):
    req = urllib.request.Request(url, headers={"x-api-version": "2", "accept": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            if attempt == 2:
                raise
            print(f"  retry after {e}", file=sys.stderr)
            time.sleep(2 * (attempt + 1))


def fetch_fsa():
    found = {}
    for lat, lng in CENTRES:
        page = 1
        while True:
            q = (f"?businessTypeId={PUB_BAR_NIGHTCLUB}&latitude={lat}&longitude={lng}"
                 f"&maxDistanceLimit={RADIUS_MILES}&sortOptionKey=distance&pageSize=500&pageNumber={page}")
            d = fetch_json(FSA + q)
            for e in d["establishments"]:
                found[e["FHRSID"]] = e
            if page >= d["meta"]["totalPages"]:
                break
            page += 1
        print(f"  centre {lat},{lng}: {len(found)} unique so far", file=sys.stderr)
    return found.values()


def from_fsa(e):
    pc = (e.get("PostCode") or "").strip().upper()
    geo = e.get("geocode") or {}
    try:
        lat, lng = float(geo["latitude"]), float(geo["longitude"])
    except (KeyError, TypeError, ValueError):
        lat = lng = None
    addr = tidy(", ".join(p for p in (e.get(f"AddressLine{i}") for i in range(1, 5)) if p))
    rating = e.get("RatingValue")
    return {
        "id": f"fsa-{e['FHRSID']}",
        "fhrsid": e["FHRSID"],
        "name": tidy(e["BusinessName"]),
        "address": addr,
        "postcode": pc,
        "area": AREA_OF_DISTRICT.get(district(pc)),
        "lat": lat, "lng": lng,
        "hygiene": {"rating": int(rating) if rating and rating.isdigit() else None,
                    "inspected": (e.get("RatingDate") or "")[:10] or None},
    }


BRANDS = json.loads(CHAINS.read_text())["brands"]


def blank(base):
    base.setdefault("trading_status", "trading")        # trading | closed | unknown
    base.setdefault("needs_review", bool(NOT_A_PUB.search(base["name"])))
    base.setdefault("source", "fsa")
    # Chain brand if recognisable from the name, else null (= treated as independent).
    # Set by hand for pub-company pubs with individual names; a brand already set is kept.
    if not base.get("chain"):
        base["chain"] = detect_chain(base["name"], BRANDS)
    base.setdefault("lat", None)
    base.setdefault("lng", None)
    base.setdefault("operator", None)
    base.setdefault("metrics", {})
    # Slots later stages fill. null = not fetched yet; never guess.
    base["metrics"].setdefault("google", None)          # {"place_id","rating","reviews","price_level","status","fetched"}
    base["metrics"].setdefault("osm", None)             # {"osm_id","opening_hours","real_ale","food","outdoor_seating"}
    base.setdefault("score", None)
    base.setdefault("notes", "")
    return base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    pubs = {}
    if OUT.exists():
        for p in json.loads(OUT.read_text())["pubs"]:
            if p.get("source") == "fsa-watchlist":
                continue        # derived from watchlist.json below; rebuilt every run
            # drop slots from the earlier scaffold schema
            for k in ("companies_house", "rateable_value"):
                p.get("metrics", {}).pop(k, None)
            pubs[p["id"]] = p

    if not args.offline:
        print("Fetching FSA pubs...", file=sys.stderr)
        for e in fetch_fsa():
            f = from_fsa(e)
            if not f["area"]:       # outside the target postcode districts
                continue
            hygiene = f.pop("hygiene")
            cur = pubs.setdefault(f["id"], blank(dict(f)))
            for k in ("name", "address", "postcode", "area", "lat", "lng", "fhrsid"):
                cur[k] = f[k]
            cur["metrics"]["hygiene"] = hygiene

        # The register often holds an old and a new registration for one premises
        # (operator change). Keep the most recently inspected.
        newest = {}
        for p in pubs.values():
            if p["source"] != "fsa":
                continue
            k = (p["postcode"], norm_name(p["name"]))
            h = (p["metrics"].get("hygiene") or {}).get("inspected") or ""
            if k not in newest or h > newest[k][0]:
                newest[k] = (h, p["id"])
        for p in list(pubs.values()):
            k = (p["postcode"], norm_name(p["name"]))
            if p["source"] == "fsa" and newest[k][1] != p["id"] and not p.get("notes"):
                del pubs[p["id"]]

    # Fold in watchlist operator matches; attach to the FSA record where one matches.
    by_key = {}
    for p in pubs.values():
        by_key.setdefault((p["postcode"], norm_name(p["name"])), p)
    for w in json.loads(WATCHLIST.read_text()):
        key = (w["postcode"].upper(), norm_name(w["pub_name"]))
        target = by_key.get(key)
        if target is None:      # not (yet) on the FSA list: keep as a watchlist-only record
            target = blank({"id": slug(w["pub_name"], w["postcode"]), "name": w["pub_name"],
                            "address": w["address"], "postcode": w["postcode"].upper(),
                            "area": w["area"], "lat": None, "lng": None, "source": "fsa-watchlist"})
            if target["id"] in pubs:
                target = pubs[target["id"]]
            else:
                pubs[target["id"]] = target
            by_key[key] = target
        if w.get("company_number") and not target.get("operator"):
            target["operator"] = {"company_number": w["company_number"],
                                  "company_name": w.get("company_name"),
                                  "match_basis": w.get("match_basis")}

    out = sorted((blank(p) for p in pubs.values()), key=lambda p: (p["area"] or "", p["name"].lower()))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"schema_version": 2, "generated": date.today().isoformat(), "pubs": out}, indent=1) + "\n")
    by_area = {}
    for p in out:
        by_area[p["area"]] = by_area.get(p["area"], 0) + 1
    print(f"{len(out)} premises -> {OUT.relative_to(ROOT)}  {by_area}; "
          f"{sum(p['needs_review'] for p in out)} need review; "
          f"{sum(bool(p['chain']) for p in out)} chain", file=sys.stderr)


if __name__ == "__main__":
    main()
