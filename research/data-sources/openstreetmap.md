# OpenStreetMap (OSM)

## What it is
A crowd-sourced global map database (nodes, ways, relations with free-form tags). We pull the road graph, building outlines, POIs (amenity/shop), and rail/transit features for the study bbox via the Overpass API.

## Publisher & URL
| Item | Value |
|---|---|
| Publisher | OpenStreetMap Foundation / contributors |
| Main site | https://www.openstreetmap.org |
| Query API we use | Overpass API, public instance `overpass-api.de` (our raw file header: "Overpass API 0.7.62.11") |
| Overpass docs | https://dev.overpass-api.de/overpass-doc/en/ |
| Bulk alternative | Geofabrik extracts, https://download.geofabrik.de/north-america/us/california.html |

## License / terms
| Item | Value | Source |
|---|---|---|
| Data license | Open Database License (ODbL) | https://www.openstreetmap.org/copyright |
| Attribution | Must credit OpenStreetMap and say the data is under ODbL. Usual wording: "© OpenStreetMap contributors", linked to /copyright | same |
| Share-alike | If you alter or build on the data, you can only distribute the result under ODbL. Rendered maps and images are "produced works" and only need attribution (see the ODbL text) | same; https://opendatacommons.org/licenses/odbl/ |
| Overpass fair use | About 10,000 requests/day and under about 1 GB/day on the public instance | https://dev.overpass-api.de/overpass-doc/en/preface/commons.html |

**Implication for us:** `data/processed/world.json` mixes OSM geometry with other data. If we publish that file, the OSM-derived layers must stay ODbL. The UI needs a visible "© OpenStreetMap contributors" credit.

## Fields we use
| Element | Tags | Use |
|---|---|---|
| ways `highway=*` | `highway`, `name`, `oneway`, `lanes`, `maxspeed`, `sidewalk`, `cycleway*`, `busway` | Road and walk network, link capacity and free-flow speed |
| ways `building=*` | `building`, `building:levels`, `height`, `name`, `addr:*` | 3D massing (fallback when DataSF footprints are missing) |
| nodes/ways `amenity`, `shop`, `office`, `leisure`, `tourism` | `name`, `opening_hours`, `cuisine`, `indoor_seating` | Retail and social destinations, joined to Apify/Google places |
| `railway=*`, `public_transport=*` | `station`, `subway_entrance`, `platform` | BART/Muni portal locations (GTFS stays authoritative) |

Our snapshot (`data/raw/osm_fidi_soma_2026-10-24.json`, OSM base 2026-10-24T19:08Z, bbox s,w,n,e = 37.7800, -122.4095, 37.7975, -122.3880) has 5,376 elements (4,064 ways, 1,312 nodes). Tag counts: building 2,175, highway 1,852, amenity 723, shop 644, railway 47, public_transport 13. These are counted from our local file.

## How the model uses it
| Module | Use |
|---|---|
| Assignment | Directed street graph for car, walk and bike routing. Gateways are road ends at the bbox edge (`scripts/build_world.py`) |
| Land use / retail | POI layer, cross-checked against DataSF Registered Business Locations and Apify places |
| Social | Third places such as bars, cafes and parks |
| Rendering | Building massing (prefer DataSF heights) |

## Caveats
- Tags are incomplete and uneven. `lanes`, `maxspeed`, `building:levels` and `opening_hours` are often missing, so we need defaults.
- The bbox north edge (37.7975) takes in part of Chinatown and Jackson Square.
- The data changes all the time. Pin the snapshot timestamp (above) for reproducibility.
- OSM has no traffic volumes or signal timing.

## Key numbers
- See the element counts above (from our local file, not a published statistic).
