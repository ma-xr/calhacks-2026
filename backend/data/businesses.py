"""Google Maps places via Apify compass/crawler-google-places -> data/backend/businesses.json

Usage:
  python businesses.py --test   # one small run (<=10 places), cached under data/cache/apify/test_*
  python businesses.py --full   # one consolidated run for the whole bbox (capped), cached under data/cache/apify/full_*
  python businesses.py          # build output from cache only (prefers full, else test)

Never deletes or modifies Apify resources; only starts runs and reads their own datasets.
Pricing (FREE tier, checked via API 2026-10-24): place-scraped $0.004 + place-details-scraped $0.002
(required for popular times via scrapePlaceDetailPage) => ~$0.006/place. No filters (they cost extra).
"""
import difflib
import json
import math
import re
import sys
import time

import common as c

ACTOR = "compass~crawler-google-places"
API = "https://api.apify.com/v2"
PRICE_PER_PLACE = 0.006

POLY = {"type": "Polygon", "coordinates": [[[c.W, c.N], [c.E, c.N], [c.E, c.S], [c.W, c.S], [c.W, c.N]]]}

FULL_SEARCHES = {  # term -> maxCrawledPlacesPerSearch
    "restaurant": 250,
    "coffee shop": 150,
    "fast food": 120,
    "bar": 120,
    "store": 180,
    "grocery store": 60,
}
FULL_CAP_USD = 8.0


def run_input(searches, per_search):
    return {
        "searchStringsArray": searches,
        "customGeolocation": POLY,
        "maxCrawledPlacesPerSearch": per_search,
        "language": "en",
        "scrapePlaceDetailPage": True,  # needed for popularTimesHistogram
        "skipClosedPlaces": False,
        "maxReviews": 0,
        "maxImages": 0,
        "maxQuestions": 0,
        "scrapeContacts": False,
        "includeWebResults": False,
        "scrapeDirectories": False,
        "scrapeTableReservationProvider": False,
    }


def apify(method, path, **kw):
    env = c.load_env()
    with c.http_client(headers={"Authorization": f"Bearer {env['APIFY_TOKEN']}"}, timeout=300) as cl:
        r = cl.request(method, API + path, **kw)
        r.raise_for_status()
        return r.json()


def run_actor(tag, inputs, cap_usd):
    """Start ONE run (unless a run record for this tag is cached), wait, download dataset to cache."""
    rec_p = c.cache_path("apify", f"{tag}_run.json")
    items_p = c.cache_path("apify", f"{tag}_items.json")
    if items_p.exists():
        print("cached:", items_p)
        return json.loads(items_p.read_text())
    if rec_p.exists():
        run = json.loads(rec_p.read_text())
        print("reusing existing run", run["id"])
    else:
        # one run per input; for the full run we pass all search terms at once with per-term caps
        run = apify("POST", f"/acts/{ACTOR}/runs", params={"maxTotalChargeUsd": cap_usd}, json=inputs)["data"]
        rec_p.write_text(json.dumps(run))
        c.write_params(rec_p, {"actor": ACTOR, "input": inputs, "maxTotalChargeUsd": cap_usd})
        c.log_usage("apify", f"start run {run['id']} ({tag}) cap ${cap_usd}", f"<= ${cap_usd} (estimate logged separately)")
    while True:
        st = apify("GET", f"/actor-runs/{run['id']}")["data"]
        if st["status"] in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break
        print("status", st["status"], st.get("stats", {}).get("runTimeSecs"), "usage", st.get("usageTotalUsd"))
        time.sleep(20)
    rec_p.write_text(json.dumps(st))
    items = []
    off = 0
    while True:
        env = c.load_env()
        with c.http_client(headers={"Authorization": f"Bearer {env['APIFY_TOKEN']}"}, timeout=300) as cl:
            r = cl.get(f"{API}/datasets/{st['defaultDatasetId']}/items", params={"offset": off, "limit": 1000, "clean": 1})
            r.raise_for_status()
            b = r.json()
        items += b
        if len(b) < 1000:
            break
        off += 1000
    items_p.write_text(json.dumps(items))
    c.write_params(items_p, {"dataset": st["defaultDatasetId"], "run": st["id"], "status": st["status"]})
    c.log_usage("apify", f"run {st['id']} ({tag}) {st['status']}, {len(items)} items, dataset {st['defaultDatasetId']}",
                f"actual ${st.get('usageTotalUsd')}")
    return items


CAT_RULES = [  # (our category, substrings of the primary google category, checked in order)
    ("grocery", ["grocery", "supermarket", "hypermarket", "convenience store", "market", "liquor store", "deli"]),
    ("cafe", ["coffee", "cafe", "café", "espresso", "tea house", "bakery", "juice", "bubble tea", "donut", "dessert",
              "ice cream", "cha chaan teng"]),
    ("fast_food", ["fast food", "hamburger", "sandwich", "takeout", "takeaway", "burrito", "taco", "food court",
                   "chicken restaurant", "hot dog", "salad shop", "poke"]),
    ("restaurant", ["restaurant", "bistro", "diner", "steak", "sushi", "brunch", "eatery", "bar & grill", "grill"]),
    ("bar", ["bar", "pub", "brewery", "brewpub", "lounge", "night club", "wine bar", "beer garden", "beer hall",
             "cocktail", "tavern", "saloon"]),
    ("shop", ["store", "shop", "boutique", "pharmacy", "drugstore", "outlet", "mall", "salon", "florist", "optician",
              "jeweler", "gallery", "dealer", "bookstore", "retail", "wholesaler"]),
]


def categorize(cats):
    cats_l = [x.lower() for x in cats if x]
    if not cats_l:
        return "other"
    prim = cats_l[0]
    for cat, keys in CAT_RULES:
        if any(k in prim for k in keys):
            if cat == "bar" and ("barber" in prim or "storage" in prim):
                continue
            return cat
    return "other"


def price_level(p):
    if not p:
        return None
    s = str(p)
    if re.fullmatch(r"\$+", s.strip()):
        return min(len(s.strip()), 4)
    nums = [float(x) for x in re.findall(r"\d+", s)]
    if not nums:
        return None
    mid = sum(nums[:2]) / len(nums[:2])
    if "+" in s and len(nums) == 1:
        mid = nums[0] * 1.2
    return 1 if mid < 15 else 2 if mid < 30 else 3 if mid < 60 else 4


DAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]


def popular(h):
    if not h:
        return None
    out = {}
    for d in DAYS:
        arr = [0] * 24
        for e in h.get(d) or []:
            hr = e.get("hour")
            if hr is not None and 0 <= hr < 24:
                arr[hr] = int(e.get("occupancyPercent") or 0)
        out[d] = arr
    return out if any(sum(v) for v in out.values()) else None


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).strip()


def main(mode="build"):
    if mode == "test":
        items = run_actor("test", run_input(["coffee shop"], 8), 0.5)
        print(json.dumps(items[:1], indent=1)[:4000])
        return
    if mode == "full":
        searches = list(FULL_SEARCHES)
        est_n = 150 * len(searches)
        c.log_usage("apify", f"ESTIMATE full run: <= {est_n} places x ${PRICE_PER_PLACE} (place $0.004 + details $0.002, FREE tier) = <= ${est_n * PRICE_PER_PLACE:.2f}; hard cap maxTotalChargeUsd=${FULL_CAP_USD}", f"est <= ${est_n * PRICE_PER_PLACE:.2f}")
        # the actor takes a single maxCrawledPlacesPerSearch for all terms: 6 terms x 150 = 900 max places
        inp = run_input(searches, 150)
        run_actor("full", inp, FULL_CAP_USD)
        mode = "build"

    full_p = c.cache_path("apify", "full_items.json")
    test_p = c.cache_path("apify", "test_items.json")
    src = full_p if full_p.exists() else test_p
    items = json.loads(src.read_text())
    world = c.load_world()
    bb = world["bbox"]
    x0, x1, z0, z1 = bb["x0"], bb["x1"], bb["z0"], bb["z1"]
    fpois = [p for p in world["pois"] if p["c"] in ("cafe", "restaurant", "fast_food", "bar", "shop")
             and x0 - 40 < p["x"] < x1 + 40 and z0 - 40 < p["z"] < z1 + 40]

    seen = set()
    out = []
    for it in items:
        pid = it.get("placeId")
        loc = it.get("location") or {}
        if not pid or pid in seen or loc.get("lat") is None:
            continue
        lat, lng = loc["lat"], loc["lng"]
        if not c.in_bbox(lat, lng):
            continue
        seen.add(pid)
        x, z = c.to_xz(lat, lng)
        cats = it.get("categories") or ([it.get("categoryName")] if it.get("categoryName") else [])
        cat = categorize([it.get("categoryName")] + cats if it.get("categoryName") else cats)
        # match to world POI
        best, bscore = None, 0.0
        nm = norm(it.get("title"))
        for i, p in enumerate(fpois):
            d = math.hypot(p["x"] - x, p["z"] - z)
            if d > 35:
                continue
            r = difflib.SequenceMatcher(None, nm, norm(p["n"])).ratio()
            if r >= 0.6 and r - d / 1000 > bscore:
                best, bscore = i, r - d / 1000
        out.append({
            "place_id": pid,
            "name": it.get("title"),
            "category": cat,
            "google_categories": cats,
            "x": round(x, 1), "z": round(z, 1), "lat": lat, "lng": lng,
            "address": it.get("address"),
            "rating": it.get("totalScore"),
            "reviews": it.get("reviewsCount"),
            "price_level": price_level(it.get("price")),
            "price_raw": it.get("price"),
            "popular_times": popular(it.get("popularTimesHistogram")),
            "opening_hours": it.get("openingHours"),
            "closed": bool(it.get("permanentlyClosed") or it.get("temporarilyClosed")),
            "permanently_closed": bool(it.get("permanentlyClosed")),
            "temporarily_closed": bool(it.get("temporarilyClosed")),
            "search_term": it.get("searchString"),
            "matched_poi_id": best,
        })

    from collections import Counter
    cnt = Counter(o["category"] for o in out)
    prof = {}
    for cat in sorted(cnt):
        acc = [0.0] * 24
        n = 0
        for o in out:
            if o["category"] != cat or not o["popular_times"]:
                continue
            days = [o["popular_times"][d] for d in DAYS[:5]]
            tot = sum(sum(dd) for dd in days)
            if not tot:
                continue
            for h in range(24):
                acc[h] += sum(dd[h] for dd in days) / tot
            n += 1
        prof[cat] = {"n": n, "weekday_profile": [round(a / n, 5) for a in acc] if n else None}
    meta = {
        "sources": [f"https://apify.com/compass/crawler-google-places (Google Maps), raw: {src.relative_to(c.ROOT)}"],
        "fetched_at": json.loads(src.with_name(src.name + ".params.json").read_text()).get("fetched_at")
        if src.with_name(src.name + ".params.json").exists() else None,
        "notes": [
            "Search: customGeolocation polygon = sim bbox; terms " + ", ".join(FULL_SEARCHES) + "; scrapePlaceDetailPage=true for popular times.",
            "category: mapped from the primary Google category (first match wins: grocery, cafe, bar, fast_food, restaurant, shop; else other).",
            "price_level: '$'..'$$$$' -> 1..4; range strings like '$10-20' -> by midpoint (<15:1, <30:2, <60:3, else 4).",
            "popular_times: Google 'Popular times' relative occupancy 0-100 per hour, keyed Mo..Su, 24 ints (hour index = local hour).",
            "matched_poi_id: index into the filtered world POI list [p for p in world['pois'] if p['c'] in (cafe,restaurant,fast_food,bar,shop) and inside bbox+-40m], matched by distance <= 35 m and difflib ratio >= 0.6 on normalized names.",
            "weekday_profile: per category, mean over places of (Mon-Fri summed hourly occupancy / its total), sum = 1.",
        ],
        "caveats": [
            "Google Maps search results are not a census; per-term result caps mean some places are missing.",
            "Popular times are relative (each place's own peak = 100), not absolute visitor counts; often missing for small places.",
            "Data is scraped content from Google Maps; use only for this simulation.",
        ],
        "count_by_category": dict(cnt),
        "n_places": len(out),
        "n_with_popular_times": sum(1 for o in out if o["popular_times"]),
        "share_with_popular_times": round(sum(1 for o in out if o["popular_times"]) / max(len(out), 1), 4),
        "n_matched_poi": sum(1 for o in out if o["matched_poi_id"] is not None),
        "n_filtered_world_pois": len(fpois),
        "avg_weekday_profile_by_category": prof,
    }
    c.write_out("businesses.json", {"meta": meta, "places": out})
    print(json.dumps({k: meta[k] for k in ("count_by_category", "n_places", "n_with_popular_times", "n_matched_poi")}))


if __name__ == "__main__":
    main("test" if "--test" in sys.argv else "full" if "--full" in sys.argv else "build")
