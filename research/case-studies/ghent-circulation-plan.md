# Ghent, Belgium: Circulation Plan (Circulatieplan), 3 April 2017

## Context
Ghent (~265,000 residents (unverified)) has had car-free streets since the 1970s–80s: Donkersteeg 1976, Langemunt 1982, Veldstraat 1984 ([nl.wikipedia, Circulatieplan Gent](https://nl.wikipedia.org/wiki/Circulatieplan_Gent), citing De Standaard). The 1997 mobility plan made ~25 ha of the centre car-free ([Tomorrow.city](https://tomorrow.city/how-the-city-of-pontevedra-became-a-pioneer-in-pedestrianizing-its-streets)). At a March 1998 hearing, 82% of traders said that plan would be a "deathblow" to the centre ([nl.wikipedia](https://nl.wikipedia.org/wiki/Circulatieplan_Gent), citing Het Nieuwsblad). Before 2017, counters showed **nearly 40% of motorised traffic in the centre was through-traffic** ([Stad Gent, Circulation plan](https://stad.gent/en/mobility-ghent/circulation-plan)).

## Intervention
| Item | Detail | Source |
|---|---|---|
| Date | Implemented over one weekend, live 3 April 2017 | [Stad Gent, Mobiliteitsplan](https://stad.gent/mobiliteitsplan); [nl.wikipedia](https://nl.wikipedia.org/wiki/Circulatieplan_Gent) |
| Design | Centre inside the R40 ring split into 6 sectors around an enlarged car-free core. Cars cannot drive directly between sectors and must go out via the R40 ring. Buses, emergency services, refuse trucks, permitted carers and bikes may pass through | [Stad Gent, Circulation plan](https://stad.gent/en/mobility-ghent/circulation-plan) |
| Scale | ~80 streets changed direction/flow; 14 locations permanently closed to most motor traffic; ~2,500 road signs changed | same; [en.wikipedia, Ghent](https://en.wikipedia.org/wiki/Ghent) |
| Enforcement | ANPR cameras; €55 fine | [Stad Gent](https://stad.gent/en/mobility-ghent/circulation-plan) |
| Companions | 2016 parking plan (tariff zones, park-and-ride, bike parking); Low-Emission Zone inside R40 from 1 Jan 2020 | [Stad Gent, Mobiliteitsplan](https://stad.gent/mobiliteitsplan) |
| Politics | Referendum petition fell 673 signatures short (2017) | [nl.wikipedia](https://nl.wikipedia.org/wiki/Circulatieplan_Gent), citing Het Nieuwsblad |

## Measured before/after
| Metric | Value | Source / status |
|---|---|---|
| Cycling share of trips | **22% (2012) → 34% (recent, year not stated)** | [Stad Gent, Cycling policy](https://stad.gent/en/mobility-ghent/cycling-policy) |
| Cycling infrastructure | 513 km total (+188 km since 2010); 32,467 public bike-parking spaces | same |
| City-reported qualitative outcomes | Fewer accidents, better air quality, less noise, fewer traffic jams, significant rise in cycling | [Stad Gent, Circulation plan](https://stad.gent/en/mobility-ghent/circulation-plan) (no figures on page) |
| Car traffic inside R40 / on R40 ring after 2017 | Commonly reported: large falls on former through-routes and a smaller rise on the R40 ring (unverified; city monitoring report not located) | — |
| Car mode share | Commonly cited as roughly halving between 2012 and 2019 (unverified) | — |
| Retail / footfall | No verified data located (unverified) | — |

**Data gap:** the city's 2018/2019 circulation-plan monitoring reports (*monitoringsrapport circulatieplan*) were not reachable. Old stad.gent URLs return 404 and the web search budget ran out. Treat Ghent as a *design* precedent (sector/filter plan) with one verified outcome (bike share +12 pp).

## Caveats / confounds
- The bike-share change spans 2012 to an unstated recent year and includes the 2016 parking plan, the 2020 LEZ, e-bike growth and COVID. It is not attributable to the circulation plan alone.
- Ghent's centre already had decades of pedestrianization, so 2017 was an incremental change on a car-light base.

## Sources
- Stad Gent, Circulation plan (EN): https://stad.gent/en/mobility-ghent/circulation-plan
- Stad Gent, Mobiliteitsplan (NL): https://stad.gent/mobiliteitsplan
- Stad Gent, Cycling policy (EN): https://stad.gent/en/mobility-ghent/cycling-policy
- nl.wikipedia, Circulatieplan Gent: https://nl.wikipedia.org/wiki/Circulatieplan_Gent
- en.wikipedia, Ghent (transport section): https://en.wikipedia.org/wiki/Ghent
- Tomorrow.city: https://tomorrow.city/how-the-city-of-pontevedra-became-a-pioneer-in-pedestrianizing-its-streets

## What our model should reproduce
| Parameter / output | Target |
|---|---|
| Through-traffic share | Before filtering, ~40% of CBD motor traffic was through-traffic. In a FiDi sim, the evaporable/divertible pool should be the through-traffic share (estimate it from OD data), not total volume. |
| Network design | Sector plan: every address stays reachable, but sector-to-sector trips must use the ring. This is the most transferable design for FiDi + SoMa (e.g. sectors bounded by Market / The Embarcadero / Bryant). The sim should support "filter" edits, not only full closures. |
| Mode shift | Bike share +12 pp over ~10 years (22% → 34%) with a sustained package. Ramp slowly. |
| `traffic_evaporation_median` | No verified Ghent figure. Use London LTN (≈50% inside cells) and Oslo (−28% area-wide) instead. |
