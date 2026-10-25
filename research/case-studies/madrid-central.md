# Madrid Central low-emission / access-restricted zone (30 Nov 2018) → Madrid 360

## Context
Madrid repeatedly breached the EU annual NO2 limit (40 µg/m³). Madrid Central was a 472 ha zone covering the Centro district ([es.wikipedia, citing El Periódico 2018](https://es.wikipedia.org/wiki/Madrid_Central)). Only residents, their guests, zero/ECO-label vehicles, vehicles parking in garages, deliveries and transit could enter, enforced by cameras. It is an *access restriction*, not a pedestrianization, but it is the main European evidence on removing through-traffic from a dense historic core.

## Intervention
| Item | Detail | Source |
|---|---|---|
| Approval / start | Approved 29 Oct 2018; live 30 Nov 2018 (delayed one week at the CEOE's request to avoid Black Friday) | [en.wikipedia](https://en.wikipedia.org/wiki/Madrid_Central); [es.wikipedia](https://es.wikipedia.org/wiki/Madrid_Central) |
| Area | 472 ha | same |
| Fines | Warning period; fines enforced from spring 2019; fines moratorium attempted July 2019 by new council, overturned in court | [es.wikipedia](https://es.wikipedia.org/wiki/Madrid_Central) |
| Courts | TSJM annulled on procedural grounds 27 Jul 2020; Supreme Court made it final 11 May 2021; replaced by "Distrito Centro" ZBEDEP under Madrid 360 ordinance (Sept 2021) | same |
| Madrid 360 | Announced 30 Sep 2019; e.g. lets C-label vehicles with 2+ occupants in | same |

## Measured before/after
### NO2, computed by us from [Ayuntamiento de Madrid open data, "Calidad del aire. Datos diarios"](https://datos.madrid.es/dataset/201410-0-calidad-aire-diario/downloads) (annual mean of valid daily NO2 values, magnitude 8)
| Station | 2017 | 2018 (pre: zone live only in Dec) | 2019 (first full year) | 2023 | 2018→2019 |
|---|---|---|---|---|---|
| Plaza del Carmen (#35, inside zone) | 49.1 | 44.6 | **36.2** | NA | **−18.8%** |
| Plaza de España (#4, zone perimeter) | 49.4 | 42.9 | 39.9 | 28.1 | −7.0% |
| Mean of 23 other city stations | 41.3 | 36.2 | 34.5 | 27.4 | −4.7% |
| **Difference (inside − rest)** | | | | | **≈ −14 percentage points** |
Station names for codes 35 and 4 come from the municipal station list (Intérprete de ficheros: [PDF](https://datos.madrid.es/dataset/201410-0-calidad-aire-diario/resource/201410-63-calidad-aire-diario/download/201410-63-calidad-aire-diario.pdf)).

### Other reported results
| Metric | Value | Source / quality |
|---|---|---|
| NO2 reduction (T&E assessment) | −32% overall; −39% in Apr–Jun 2019 (fines enforced) vs same months 2010–18; only −10% in months without fines | Transport & Environment 2019 briefing via [Energy News, 12 Sep 2019](https://www.energynews.es/madrid-central-zona-de-bajas-emisiones-mas-efectiva/) |
| Vehicle NOx emissions in zone (modelled, UPM) | −38% (Dec 2018 – early 2019); CO2 −14.2% in zone; citywide NOx −9%, CO2 −2% | UPM study via [Público, 14 Mar 2019](https://www.publico.es/sociedad/madrid-central-madrid-central-reduce-emisiones-contaminantes-38-inicio.html) |
| Plaza del Carmen "contamination" early months | −9% (UPM, as reported by El País) | same |
| Traffic inside zone / on perimeter roads (Gran Vía, Alcalá, M-30) | City balances reported falls inside and no large rise on the perimeter (unverified; primary city traffic report not located) | — |
| Retail / card spending (e.g. BBVA data, Christmas 2018) | Press reports of higher card spending in the zone vs the previous Christmas (+8.6% figure in brief: unverified) | — |
| Peer-reviewed spending effect | Galdon-Sanchez et al., *J. European Economic Association* (2023): Madrid Central's effect on congestion, pollution and consumer spending (coefficients not verified here (unverified)) | not fetched |
| Protest in support (29 Jun 2019) | ~10,000 attendees (Government Delegation) | [es.wikipedia](https://es.wikipedia.org/wiki/Madrid_Central) |

## Caveats / confounds
- Our station comparison is a simple before/after against the city average (no weather or trend model). 2017 was a high-NO2 year, so use 2018→2019. Fleet renewal is lowering NO2 everywhere (city mean −34% from 2017 to 2023).
- T&E and UPM figures mix measured concentrations and modelled emissions over different windows. The enforcement effect (−39% with fines vs −10% without) is the most policy-relevant finding.
- Retail claims are mostly bank or press data releases. Treat them as indicative only until the JEEA paper's estimates are checked.
- Search budget ran out before Madrid traffic counts could be retrieved. Fill this gap before quoting traffic numbers.

## Sources
- Ayuntamiento de Madrid, air quality daily data (CSV, 2017–2023): https://datos.madrid.es/dataset/201410-0-calidad-aire-diario/downloads
- es.wikipedia, Madrid Central: https://es.wikipedia.org/wiki/Madrid_Central
- en.wikipedia, Madrid Central: https://en.wikipedia.org/wiki/Madrid_Central
- Energy News on T&E LEZ briefing (2019): https://www.energynews.es/madrid-central-zona-de-bajas-emisiones-mas-efectiva/
- Público on UPM emissions study (2019): https://www.publico.es/sociedad/madrid-central-madrid-central-reduce-emisiones-contaminantes-38-inicio.html

## What our model should reproduce
| Parameter / output | Target |
|---|---|
| Air quality inside the restricted zone | NO2 about −15% to −20% in year 1 relative to the city trend (measured −18.8% vs −4.7%), and up to −30–40% in enforced months (T&E). Perimeter about −7% (no measurable worsening at Pza España). |
| Enforcement | Effects shrink by ~3/4 without enforcement (−39% vs −10%). The sim's "access restriction" policy should have a compliance parameter. |
| `ped_street_retail_uplift` | No verified figure. Do not use Madrid for retail calibration until the JEEA estimate is checked. |
| Emissions vs concentrations | Zone vehicle NOx emissions −38% → concentration −19%. Use a ~0.5 pass-through from local traffic emissions to roadside NO2 when background is included. |
