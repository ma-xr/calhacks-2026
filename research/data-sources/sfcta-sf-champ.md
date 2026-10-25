# SFCTA: SF-CHAMP, Downtown Travel Study, CMP congestion monitoring; plus the SFMTA Travel Decision Survey

## 1. SF-CHAMP (San Francisco Chained Activity Modeling Process)
| Item | Value |
|---|---|
| What | SFCTA's activity-based, tour-based regional travel model for SF land-use and transport forecasting |
| URL | https://www.sfcta.org/sf-champ-modeling |
| Data access | No public download of model code or outputs. Requests go to the **Model & Data Service Bureau**, data@sfcta.org (https://www.sfcta.org/model-data-service-bureau). Include your purpose and project. SFCTA says it is open to sharing with research projects, but turnaround isn't guaranteed. |
| Public outputs | "Vehicle Miles Traveled estimates from SF-CHAMP 2012" (office/residential/retail, 2012 and 2040) on DataSF/data.gov: https://catalog.data.gov/dataset/vehicle-miles-traveled-estimates-from-sf-champ-2012 |
| Code | SFCTA GitHub: https://github.com/sfcta (CountDracula count DB, network tools). The SF-CHAMP core is not confirmed public. |
| License | Not stated (unverified). Assume each request comes with its own agreement. |
| Base year / TAZ count | Not on the public page (unverified) |

**How we use it:** to benchmark our OD and mode split against SF-CHAMP if SFCTA provides TAZ-level outputs. Otherwise we use the published study numbers below.

## 2. Downtown Travel Study (SFCTA, final May 2025)
- **URL:** https://www.sfcta.org/sites/default/files/2025-05/Downtown_Travel_Study_FINAL_Report_2025-05-22_Executive_Summary.pdf (full report: `.../Downtown_Travel_Study_FINAL_Report_2025-05-22.pdf`)
- **Data:** household travel diary surveys of Bay Area residents run jointly by SFCTA, MTC and VTA. It compares 2019 with 2023. It also uses Census, INRIX and transit-agency data.

| Finding (typical adult weekday trips to/from/within Downtown) | 2019 | 2023 |
|---|---|---|
| Change in Downtown trips, within Downtown Core | — | **−46%** |
| … to/from rest of SF | — | −25% |
| … to/from rest of Bay Area | — | −25% |
| Work trips | — | −66% (largest % drop). Non-work purposes account for 69% of the total drop |
| Mode share: walk/bike | 43.4% | 39.7% |
| Mode share: automobile | 24.5% | 36.9% |
| Mode share: transit | 27.9% | 20.9% |
| Mode share: taxi/TNC | 4.2% | 2.5% |
| Downtown workers telecommuting 2+ days/week | 13.7% | 62.8% |
| SF residents telecommuting | 7% | 24% |
| Downtown residents receiving deliveries per weekday | 26% | 40% |
| Transit trips Downtown↔rest of SF | — | down >50%. Drive trips down only 4% |
| Downtown I-80 car trips: intra-SF / to-from SF / pass-through | 11% / 82% / 7% | 13% / 72% / 15% |
| Downtown BART stations, % of 2019 ridership (2024) | — | 36% weekday, 54% weekend |
| Muni weekday ridership, % of 2019 (2024) | — | >70% |
| Bay Bridge / Golden Gate volumes vs pre-pandemic | — | −9% / −16% |

## 3. Congestion Management Program (CMP) monitoring
- **What:** a biennial state-mandated report that measures LOS and speeds on the CMP network (freeways plus major arterials). Speeds come from INRIX, collected in April–May. AM peak is 7–9 a.m. and PM peak is 4:30–6:30 p.m.
- **Report:** https://www.sfcta.org/reports/congestion-management-program-2025 (final PDF 2025-12-16)
- **Interactive map:** https://congestion.sfcta.org
- **CSV for the table below:** https://www.sfcta.org/sites/default/files/2025-12/SFCTA_CMP2025_Fig4-3_CMP_Arterial_Average_Speeds_Citywide_and_in_the_Downtown_Core.csv
- **License:** not stated (unverified). Cite SFCTA.

### CMP arterial average speeds (mph)
| Year | Citywide AM | Citywide PM | **Downtown core AM** | **Downtown core PM** |
|---|---|---|---|---|
| 2017 | 14.05 | 12.83 | 11.05 | 9.38 |
| 2019 | 13.33 | 12.20 | **10.44** | **9.12** |
| 2021 | 17.69 | 16.66 | 14.27 | 13.48 |
| 2023* | 15.54 | 13.95 | 12.17 | 10.76 |
| 2024 | 16.75 | 15.66 | 13.51 | 12.46 |
| **2025** | 16.11 | 14.67 | **12.89** | **11.55** |

\*SFCTA flags an INRIX data anomaly in fall 2023 and compares 2025 with 2024 instead (CAC memo, https://www.sfcta.org/sites/default/files/2025-11/SFCTA_CAC_Item11_CongestionManagementProgramMEMO_2025-11-19.pdf).

| Other 2025 CMP numbers | Value | Source |
|---|---|---|
| Downtown core arterial change, 2024→2025 | −6% AM, −7% PM | CAC memo |
| CMP network arterial speeds (Table 4-1) | AM 16.8 → 16.1; PM 15.7 → 14.7 mph (2024 → 2025) | CMP 2025 report page |
| Freeway speeds | AM 33.9 → 32.7; PM 25.1 → 23.9 mph | CMP 2025 report page |
| Downtown arterial LOS (PM 2025) | "nearly uniformly LOS D" | CAC memo |
| Muni bus speeds, citywide | 9.0 mph AM, 8.1 mph PM | CAC memo |
| Muni bus speeds, downtown | 7.1 mph AM; PM 6.4 (2023) → 6.1 (2025) | CMP 2025 report page |
| Auto-to-transit speed ratio | 1.8 (AM and PM) | CAC memo |
| Arterial buffer time index | AM 22%, PM 20% | SFCTA board memo |
| Bike counts 2023→2025 | +42% AM, +36% PM; pedestrians +0% AM, +8% PM | CAC memo |

**How we use it:** free-flow and congested link speeds for assignment calibration. The downtown PM target is about 11.5 mph for cars and about 6.1 mph for buses (2025). A pre-pandemic scenario uses about 9.1 mph.

## 4. SFMTA Travel Decision Survey
| Item | Value |
|---|---|
| What | SFMTA telephone mode-share survey of Bay Area residents (2019: n=801, adults 18+). Annual 2012–2017, then biennial. |
| Data | DataSF `qmdj-wtj2` (https://data.sf.gov/d/qmdj-wtj2). The full XLSX is linked from the dataset (http://bit.ly/SFMTATravelSurvey2019) |
| Blog / results | https://www.sfmta.com/blog/sfmta-travel-decision-survey-2019 |
| 2019 headline | Sustainable mode share (all trips, SF) **47%**, down from 54% in 2017 (TNC now counted as non-sustainable). Target: 80% by 2030 |
| Later editions | The 2021, 2023 and 2025 surveys were not found online (unverified whether they were run or published) |
| Fields | Per-trip mode columns (`da`, `do`, `crshre`, `tnc`, `taxi`, `trans`, `bike`, `walk`, `scoot`...), purposes (`work`, `shop`, `soc`...) |

## Caveats
- Downtown Travel Study comparisons are 2019 vs 2023 diaries, so they predate later return-to-office gains (Kastle SF was 47.2% in Oct 2026).
- The study's "Downtown" boundary is wider than our bbox (it is mapped in the report; check the exact polygon there).
- CMP speeds are segment-length averages from INRIX probe data and include signal delay. They only cover April–May.
