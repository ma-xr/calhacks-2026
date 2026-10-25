# GTFS / 511 SF Bay Open Data (Muni, BART schedules and real-time)

## What it is
Static GTFS schedules (stops, routes, trips, stop_times, shapes) and GTFS-Realtime feeds (trip updates, vehicle positions, alerts). 511 combines feeds from about 30 Bay Area operators behind one API run by MTC.

## Publisher & URL
| Source | URL | Key needed? |
|---|---|---|
| 511 Open Data, transit | https://511.org/open-data/transit | Yes (free token) |
| Token request | https://511.org/open-data/token (name and email, accept T&C) | — |
| List operators | `http://api.511.org/transit/gtfsoperators?api_key=KEY` (gives operator IDs; Muni is usually `SF`, BART `BA`, unverified until you call it) | Yes |
| Static GTFS per operator | `http://api.511.org/transit/datafeeds?api_key=KEY&operator_id=SF` (optional `historic=YYYY-MM`) | Yes |
| GTFS-RT | `.../transit/tripupdates`, `.../vehiclepositions`, `.../servicealerts?api_key=KEY&agency=SF` (`agency=RG` returns the regional feed) | Yes |
| SIRI stop monitoring | `.../transit/StopMonitoring?api_key=KEY&agency=SF` | Yes |
| Muni direct GTFS | https://muni-gtfs.apps.sfmta.com/data/muni_gtfs-current.zip (linked from https://www.sfmta.com/reports/gtfs-transit-data after you accept the license) | No |
| BART direct GTFS | https://www.bart.gov/dev/schedules/google_transit.zip (HTTP 200 checked) ; https://www.bart.gov/schedules/developers/gtfs | No |
| BART real-time API docs | https://api.bart.gov | — |

## License / terms
| Source | Terms |
|---|---|
| 511 | 511 Open Data Terms & Conditions / Data Agreement: https://511.org/sites/default/files/pdfs/511_Data_Agreement_Final.pdf (a 2026 version is linked from the transit page). **Rate limit: 60 requests per 3600 s per token by default**. To raise it, email 511sfbaydeveloperresources@googlegroups.com |
| SFMTA | SFMTA Transit Data License Agreement: nonexclusive, limited, revocable, "as is", no sublicensing. Derivatives must carry the required notice. California law applies. |
| BART | Developer License Agreement https://www.bart.gov/dla. No registration needed. Credit or link back to BART. Logos and maps are reserved (an editable system map is CC-BY). |

Keep the 511 token in `.env` and never commit it. At 60 requests/hour, poll GTFS-RT about once a minute for one agency at most, or cache results.

## Fields we use
| File | Fields |
|---|---|
| stops.txt | `stop_id`, `stop_name`, `stop_lat`, `stop_lon`, `parent_station` (BART EM/MT/PL entrances) |
| routes.txt / trips.txt | `route_id`, `route_short_name`, `route_type`, `service_id`, `direction_id`, `shape_id` |
| stop_times.txt | `arrival_time`, `departure_time`, `stop_sequence` (headways) |
| shapes.txt | Route geometry for buses on Market, Mission, Howard and Folsom |
| GTFS-RT VehiclePositions | `vehicle.position`, `trip.trip_id`, `timestamp` (live bus and train positions for the demo) |

## How the model uses it
| Module | Use |
|---|---|
| Mode choice | Transit wait time (headway/2) and in-vehicle time for the transit option |
| Assignment | Bus vehicles as moving agents on the street graph. Portal release times follow train arrivals. |
| Validation | Scheduled vs observed (GTFS-RT) bus speeds. Compare with SFCTA CMP downtown bus speeds of 7.1 mph AM and 6.1 mph PM in 2025 (see `sfcta-sf-champ.md`). |

## Caveats
- Static GTFS is the plan. Real operations differ, so use GTFS-RT or CMP speeds to calibrate.
- Muni Metro subway and surface stops share `stop_name` text. Check `stop_id` and location.
- Feeds change at each service "sign-up" (about every 3–6 months per the DataSF Muni Stops note). Pin the feed version date.
- 511 operator IDs and feed versions can differ from the operators' direct feeds.

## Key numbers
- Rate limit of 60 requests/hour per token (511 transit page, above).
- Muni systemwide boardings in Aug 2026 were 83.6% of Aug 2019 (see `datasf.md`).
