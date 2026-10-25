"""Loads the data pipeline outputs in data/backend/ (written by backend/data/*). Every loader returns
None when its file is missing, and the engine falls back to documented parameters."""
import json

from .config import DATA_BACKEND


def _load(name):
    p = DATA_BACKEND / name
    try:
        return json.loads(p.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


class Inputs:
    def __init__(self):
        self.lodes = _load("lodes.json")
        self.acs = _load("acs.json")
        self.landuse = _load("landuse.json")
        self.businesses = _load("businesses.json")
        self.traffic_counts = _load("traffic_counts.json")
        self.transit = _load("transit.json")

    def status(self):
        return {k: getattr(self, k) is not None for k in ("lodes", "acs", "landuse", "businesses", "traffic_counts", "transit")}

    # Normalized accessors (tolerant to small schema variations from the pipeline).
    def landuse_by_building(self):
        if not self.landuse:
            return None
        rows = self.landuse.get("buildings") or self.landuse.get("items") or []
        out = {}
        for r in rows:
            bid = r.get("building_id")
            if bid is not None:
                out[int(bid)] = r
        return out or None

    def businesses_by_poi(self):
        if not self.businesses:
            return None
        rows = self.businesses.get("places") or self.businesses.get("items") or self.businesses.get("businesses") or []
        out = {}
        for r in rows:
            pid = r.get("matched_poi_id")
            if pid is None or r.get("closed"):
                continue
            # Keep the best-reviewed match per POI.
            if pid not in out or (r.get("reviews") or 0) > (out[pid].get("reviews") or 0):
                out[int(pid)] = r
        return out or None

    def home_region_share(self):
        # Prefer the version without homes >150 km away (HQ-reporting artifacts, not daily commuters).
        for k in ("home_region_share_excl_far", "home_region_share"):
            if self.lodes and isinstance(self.lodes.get(k), dict):
                return self.lodes[k]
        return None

    def residents_total(self):
        t = (self.acs or {}).get("tracts_summary") or {}
        return float(t["population"]) if t.get("population") else None

    def persons_per_household(self):
        t = (self.acs or {}).get("tracts_summary") or {}
        return float(t["persons_per_household"]) if t.get("persons_per_household") else None

    def home_region_share_by_earnings(self):
        if self.lodes and isinstance(self.lodes.get("home_region_share_by_earnings"), dict):
            return self.lodes["home_region_share_by_earnings"]
        return None

    def earnings_share(self):
        if not self.lodes or not isinstance(self.lodes.get("jobs_by_earnings"), dict):
            return None
        j = self.lodes["jobs_by_earnings"]
        tot = sum(j.get(k, 0) for k in ("SE01", "SE02", "SE03")) or 1
        return {"low": j.get("SE01", 0) / tot, "mid": j.get("SE02", 0) / tot, "high": j.get("SE03", 0) / tot}

    def jobs_total(self):
        if self.lodes and self.lodes.get("jobs_total"):
            return float(self.lodes["jobs_total"])
        return None

    def office_job_share(self):
        """Share of LODES jobs in office-type sectors (info, finance, real estate, professional, management, admin)."""
        if not self.lodes or not isinstance(self.lodes.get("jobs_by_sector"), dict):
            return None
        s = self.lodes["jobs_by_sector"]
        def val(k):
            v = s.get(k)
            return v.get("jobs", 0) if isinstance(v, dict) else (v or 0)
        tot = sum(val(k) for k in s) or 1
        return sum(val(k) for k in ("CNS09", "CNS10", "CNS11", "CNS12", "CNS13", "CNS14")) / tot
