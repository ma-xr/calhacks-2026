"""BART ridership -> data/backend/transit.json

Sources (cached in data/cache/bart/):
  Ridership_<YYYYMM>.xlsx            monthly OD matrices (Average Weekday sheet: rows = entry, cols = exit)
  date-hour-soo-dest-<YEAR>.csv.gz   hourly OD (date, hour, origin, destination, trips); one year file
                                     (BART publishes per-year files only; we use the same calendar month
                                     of the previous year for the hourly profile)
"""
import csv
import datetime as dt
import gzip
import sys
from collections import defaultdict

import common as c

REPORT_MONTH = "202609"
REPORT_URL = f"https://www.bart.gov/sites/default/files/2026-10/Ridership_{REPORT_MONTH}.xlsx"
HOURLY_YEAR = 2025
HOURLY_MONTH = 9
HOURLY_URL = f"https://afcweb.bart.gov/ridership/origin-destination/date-hour-soo-dest-{HOURLY_YEAR}.csv.gz"
STATIONS = {"Embarcadero": ("EM", "EMBR"), "Montgomery Street": ("MT", "MONT"), "Powell Street": ("PL", "POWL")}


def report(offline):
    import openpyxl
    p = c.cache_path("bart", f"Ridership_{REPORT_MONTH}.xlsx")
    if not p.exists():
        if offline:
            raise RuntimeError("report not cached")
        c.download(REPORT_URL, p, "bart.gov")
    wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
    out = {}
    for sheet, key in (("Average Weekday", "weekday"), ("Average Saturday", "saturday"), ("Average Sunday", "sunday")):
        rows = list(wb[sheet].iter_rows(values_only=True))
        hi = next(i for i, r in enumerate(rows) if r[0] == "Exit Station Two-Letter Code")
        hdr = rows[hi]
        body = [r for r in rows[hi + 1:] if r[0] and r[0] != "Grand Total"]
        col = {h: j for j, h in enumerate(hdr) if h}
        for name, (code, _) in STATIONS.items():
            j = col[code]
            exits = sum(float(r[j] or 0) for r in body)
            row = next(r for r in body if r[0] == code)
            entries = sum(float(v or 0) for v in row[1:len(hdr) - 1] if isinstance(v, (int, float)))
            # top origins for exits at this station
            top = sorted(((r[0], float(r[j] or 0)) for r in body), key=lambda t: -t[1])[:10]
            d = out.setdefault(name, {})
            d[f"{key}_exits"] = round(exits)
            d[f"{key}_entries"] = round(entries)
            if key == "weekday":
                d["weekday_top_origins_of_exits"] = [{"station": s, "trips": round(v)} for s, v in top]
    return out


def hourly(offline):
    p = c.cache_path("bart", f"date-hour-soo-dest-{HOURLY_YEAR}.csv.gz")
    if not p.exists():
        if offline:
            raise RuntimeError("hourly not cached")
        c.download(HOURLY_URL, p, "afcweb.bart.gov")
    codes = {v[1]: k for k, v in STATIONS.items()}
    ex = {k: [0] * 24 for k in STATIONS}
    en = {k: [0] * 24 for k in STATIONS}
    days = set()
    with gzip.open(p, "rt") as f:
        for r in csv.reader(f):
            d = r[0]
            if int(d[5:7]) != HOURLY_MONTH:
                continue
            day = dt.date.fromisoformat(d)
            if day.weekday() >= 5:
                continue
            days.add(day)
            h = int(r[1])
            n = int(r[4])
            if r[3] in codes:
                ex[codes[r[3]]][h] += n
            if r[2] in codes:
                en[codes[r[2]]][h] += n
    # drop holidays (Labor Day) by excluding days whose total is < 60% of median? keep simple: list them
    return ex, en, sorted(days)


def main(offline=False):
    rep = report(offline)
    ex, en, days = hourly(offline)
    nd = len(days)
    stations = {}
    for k in STATIONS:
        te, tn = sum(ex[k]), sum(en[k])
        stations[k] = dict(rep[k])
        stations[k]["code"] = STATIONS[k][0]
        stations[k]["hourly_share"] = [round(v / te, 5) for v in ex[k]]
        stations[k]["hourly_share_entries"] = [round(v / tn, 5) for v in en[k]]
        stations[k]["hourly_profile_weekday_exits_avg"] = round(te / nd)
        stations[k]["hourly_profile_weekday_entries_avg"] = round(tn / nd)
    out = {
        "meta": {
            "sources": [REPORT_URL, HOURLY_URL],
            "fetched_at": c.now_iso(),
            "report_month": f"{REPORT_MONTH[:4]}-{REPORT_MONTH[4:]}",
            "hourly_profile_period": f"{HOURLY_YEAR}-{HOURLY_MONTH:02d} weekdays ({nd} days, incl. Labor Day)",
            "notes": [
                "weekday_exits/entries: BART monthly ridership report, 'Average Weekday' OD matrix (column sum = exits, row sum = entries).",
                "hourly_share: share of weekday exits by hour 0-23 at that station from BART hourly OD data (hour = hour the trip started at origin; BART trips are short so this approximates exit hour within ~0.5h).",
                "BART publishes hourly OD only as whole-year files; the 2026 file was empty at fetch time, so Sep 2025 is used for the hourly shape while daily volumes come from Sep 2026.",
            ],
            "caveats": [
                "Hour bin is the origin-entry hour, so exits are shifted early by the in-vehicle time (~10-40 min for East Bay origins).",
                "Hour 0 contains trips after midnight up to close (~00:00-01:00).",
            ],
        },
        "stations": stations,
    }
    c.write_out("transit.json", out)
    return out


if __name__ == "__main__":
    o = main(offline="--offline" in sys.argv)
    for k, v in o["stations"].items():
        print(k, v["weekday_exits"], v["weekday_entries"], [round(x * 100, 1) for x in v["hourly_share"]])
