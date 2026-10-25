"""City environments. Each is a ~1.9 x 1.9 km simulation box in its own local meter frame
(x east, z south, origin at the box center), plus a wider context ring that fades out.

SF keeps its original paths (data/processed/world.json etc.), which the engine reads.
Other cities write to data/processed/<id>/ and data/raw/<id>/.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CITIES = {
    "sf": {
        "name": "San Francisco", "area": "Financial District + SoMa",
        "center": (37.7887, -122.3987), "bbox": (37.7800, -122.4095, 37.7975, -122.3880),
        "districts": [["FINANCIAL DISTRICT", -150, -480], ["SOMA", -120, 420]],
    },
    "chicago": {
        "name": "Chicago", "area": "The Loop",
        # Chicago River / Marina City (north) to Van Buren (south), Canal St (west) to Millennium Park (east)
        "center": (41.8805, -87.6290), "bbox": (41.8718, -87.6404, 41.8893, -87.6176),
        "districts": [["THE LOOP", 0, 80], ["RIVER NORTH", -60, -880], ["GRANT PARK", 860, 420]],
        "landmarks": ["Willis Tower", "Chicago Board of Trade", "Art Institute of Chicago", "Marina City", "Aon Center",
                      "Chicago Theatre", "Rookery", "Union Station", "Trump International Hotel"],
        "lake": "Lake Michigan",
    },
    "nyc": {
        "name": "New York", "area": "Midtown Manhattan",
        # 34th St (Empire State, Penn Station) to ~55th St (Rockefeller Center); 8th Ave to Lexington Ave
        "center": (40.7540, -73.9840), "bbox": (40.7453, -73.9952, 40.7628, -73.9728),
        "districts": [["MIDTOWN", 0, 0], ["TIMES SQUARE", -180, -420], ["MURRAY HILL", 760, 520]],
        "landmarks": ["Empire State Building", "Chrysler Building", "Grand Central Terminal", "One Vanderbilt",
                      "30 Rockefeller Plaza", "Bank of America Tower", "The New York Times Building",
                      "New York Public Library", "Madison Square Garden"],
    },
}


def context_bbox(city, km=2.7):
    s, w, n, e = CITIES[city]["bbox"]
    import math
    lat = (s + n) / 2
    dlat = km / 110.54
    dlon = km / (111.32 * math.cos(math.radians(lat)))
    return (s - dlat, w - dlon, n + dlat, e + dlon)


def paths(city):
    if city == "sf":
        return {"raw": ROOT / "data/raw", "out": ROOT / "data/processed",
                "core": ROOT / "data/raw/osm_fidi_soma_2026-10-24.json", "context": ROOT / "data/raw/osm_context_2026-10-24.json",
                "coast": ROOT / "data/raw/osm_coast_2026-10-24.json", "parts": ROOT / "data/raw/osm_parts_2026-10-24.json"}
    raw = ROOT / "data/raw" / city
    return {"raw": raw, "out": ROOT / "data/processed" / city,
            "core": raw / "osm_core.json", "context": raw / "osm_context.json", "coast": raw / "osm_coast.json", "parts": raw / "osm_parts.json"}
