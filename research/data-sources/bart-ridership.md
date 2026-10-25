# BART Ridership (station exits and origin-destination matrices)

## What it is
Fare-gate (Clipper) entry and exit counts for Bay Area Rapid Transit. Our bbox has four stations:
- **EM** Embarcadero
- **MT** Montgomery
- **PL** Powell (west edge)
- **CC** Civic Center (just outside, for context)

## Publisher & URL
| Product | URL | Format / coverage |
|---|---|---|
| Ridership reports hub | https://www.bart.gov/about/reports/ridership | — |
| Monthly OD matrix (avg weekday/Sat/Sun + total) | e.g. Sep 2026: https://www.bart.gov/sites/default/files/2026-10/Ridership_202609.xlsx ; archives `ridership_OD_2025.zip`, 2001+ | XLSX. Four tabs; **columns = origin (entry), rows = destination (exit)**. Posted by about the 5th of the next month |
| Hourly OD by station pair | https://afcweb.bart.gov/ridership/origin-destination/ (`date-hour-soo-dest-YYYY.csv.gz`; 2026 file present) | CSV: date, hour, origin, destination, exits |
| Daily station exits | https://afcweb.bart.gov/ridership/DSE/ ; DataSF mirror `m2xz-p7ja` (https://data.sf.gov/d/m2xz-p7ja, 1998-01-01 → 2025-07-31) | XLS / Socrata |
| Station code key | https://www.bart.gov/sites/default/files/docs/station-names.xls | — |

## License / terms
- BART's ridership page says the data is under a "Creative Commons Attribution License", linking to https://opendefinition.org/licenses/cc-by/. The version isn't stated, so credit BART.
- The DataSF mirror is listed as CC0 1.0.

## Fields we use
- Monthly OD "Average Weekday" tab: exits per destination row (EM, MT, PL) and entries per origin column.
- Hourly OD: exits at EM/MT/PL by hour and origin, which gives the AM arrival profile and the origin catchment.

## How the model uses it
| Module | Use |
|---|---|
| Population / mode choice | Rail-arrival agents spawn at portals. Origin-station mix (East Bay vs SF vs Peninsula) comes from the OD matrix. |
| Assignment | Hourly exits set the release schedule at station portals. |
| Validation | Simulated BART boardings and alightings at EM/MT/PL vs observed weekday averages. |

## Caveats
- Exits ≠ unique people. Return trips are counted, and transfers inside the system are not.
- Counts are by station, not by portal. Assign them to portals by street geometry (our assumption).
- Fare evasion is uncounted. BART has installed new fare gates (2023–2025, unverified), which can create an artificial jump in counts.
- DataSF `day_of_week` codes: `w` = weekday, `sa`, `su`, `hol`/`Hol` = holidays (we filtered on `w`).

## Key numbers: average weekday exits
Pre-pandemic and annual values are computed by us from DataSF `m2xz-p7ja` with `day_of_week='w'`. Sep 2026 values come from BART `Ridership_202609.xlsx`, "Average Weekday" tab.

| Period | Embarcadero | Montgomery | Powell | Civic Center | System total |
|---|---|---|---|---|---|
| 2019 (annual weekday avg) | 48,594 | 45,460 | 25,470 | 22,938 | 408,531 |
| Sep 2019 (20 weekdays) | 50,787 | 46,263 | 25,288 | 24,079 | 426,758 |
| 2021 | 6,062 | 5,903 | 5,811 | 4,584 | 78,541 |
| 2023 | 15,876 | 13,270 | 10,704 | 8,289 | 156,015 |
| 2024 | 16,746 | 13,755 | 10,729 | 8,646 | 164,261 |
| 2025 Jan–Jul | 18,616 | 14,987 | 10,961 | 9,466 | 167,174 |
| **Sep 2026 (BART OD file)** | **23,619** | **18,908** | **13,573** | **11,929** | **223,280** (trips) |
| Sep 2026 as % of Sep 2019 | 46.5% | 40.9% | 53.7% | 49.5% | 52.3% |

- Sep 2026 average weekday *entries*: EM 20,648; MT 17,217; PL 14,474; CC 13,154 (same file). So EM and MT have more exits than entries, which is what you expect at net inbound job centres.
- BART says 2025 averaged 180,649 weekday trips, and 2024 averaged 165,502 (https://www.bart.gov/about/reports/ridership).
- SFCTA Downtown Travel Study: downtown BART stations recovered to "36% of 2019 ridership by 2024 for weekdays and 54% for weekends" (https://www.sfcta.org/sites/default/files/2025-05/Downtown_Travel_Study_FINAL_Report_2025-05-22_Executive_Summary.pdf).

Note: the totals differ slightly by source. The DataSF "total" is exits. BART's "trips" figure counts the same trips but may handle holidays differently.
