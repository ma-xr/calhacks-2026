# Case Study: JFK Promenade (car-free JFK Drive), Golden Gate Park, 2020 → permanent 2022

**Relevance to our sim:** This is a clean case of removing a mostly cut-through road. It shows (a) large walk/bike gains, (b) a measurable *net loss* of total users once cars are excluded, (c) small to negative travel-time effects on alternative routes, and (d) access/equity trade-offs (museums, disability access). It is outside our bbox, so use it for parameter ranges, not geography.

---

## 1. Context

| Metric (pre-closure) | Value | Source |
|---|---|---|
| Share of weekday JFK traffic that was cut-through (no park destination) | **75%** | [SFMTA/RPD GGP Access & Safety Program deck, Sep 2021](https://www.sfmta.com/media/28467/download?inline) |
| Vehicles/day crossing JFK east of Nancy Pelosi Dr (typical weekday, fall 2019) | ~8,700 | [SFMTA Golden Gate Park Traffic Study, Feb 2022](https://sfmta.com/media/30549/download) |
| Vehicles/day on 8th Ave between Fulton and JFK (fall 2019) | ~12,500 | same |
| Ped/bike injury collisions in GGP, 5 years pre-COVID | >100 total. 38 on the current car-free alignment, 26 at its entries, 42 elsewhere | [SFMTA deck, Sep 2021](https://www.sfmta.com/media/28467/download?inline) |
| Historic closures | Sundays since 1967; "Healthy Saturdays" since 2007 | same |

## 2. Intervention

| Date | Event | Source |
|---|---|---|
| Apr 27, 2020 | RPD closes JFK Dr and several other park roads to cars as a COVID measure (exact segments and length: see [RPD Current Route Details](https://sfrecpark.org/1575/Current-Route-Details); unverified here) | [RPD/SFMTA Annual Report FY24](https://sfrecpark.org/DocumentCenter/View/28988/Golden-Gate-Park-Annual-Access-and-Safety-Report-FY24) |
| Apr 26, 2022 | Board of Supervisors passes Ordinance 74-22 (effective Jun 7, 2022) making it permanent and adding an access program (shuttle, ADA blue zones, garage pricing) | same |
| Nov 8, 2022 | **Prop J** (keep car-free) passes; **Prop I** (reopen JFK and the Great Highway) fails. Prop N transfers the Music Concourse garage to RPD | same. Vote shares (unofficial, advocacy-reported): J **61.97% yes**, I **64.11% no** per [SF Bicycle Coalition](https://sfbike.org/news/big-successes-for-biking-from-2022-midterms/). Verify against certified SF Dept of Elections results (unverified) |
| Program scope | "3 miles of roadways closed to private vehicles" | [FY24 report, Attachment A](https://sfrecpark.org/DocumentCenter/View/28988/Golden-Gate-Park-Annual-Access-and-Safety-Report-FY24) |

## 3. Measured before/after

### 3a. Treated street: users by mode (SFCTA, JFK between Kezar Dr and Tea Garden Dr, weekly averages)

Source: [SFCTA presentation to BOS, Apr 26, 2022](https://sfcta.org/sites/default/files/2022-04/SFCTA-BOS_Board_GGP-JFKTripAnalysisKezarandTeaGardenPRESENTATION_2022-04-26.pdf)

| Period | Ped & bike | Auto users | Total |
|---|---|---|---|
| Mar 2019–Feb 2020 (pre) | 50,532 | 21,484 | 72,016 |
| Mar 2020–Feb 2021 | 94,461 | 1,805 | 96,266 |
| Mar 2021–Feb 2022 | 65,843 | 0 | 65,843 |
| **Change, pre → yr 2** | **+30%** | −100% | **−9%** |

SFMTA's version of the same CityDash.ai dataset ([SFMTA project update, Apr 2022](https://www.sfmta.com/project-updates/april-2022-update-new-hearing-date-and-new-robust-data)):

| Metric | Value |
|---|---|
| Walking on JFK, 2019 → 2021 | **+29%** |
| Biking on JFK, 2019 → 2021 | **+76%** |
| Weekly walkers + bikers: pre (Mar19–Feb20) / yr 1 / yr 2 | 48,639 / 90,958 / 62,261 |
| Earlier claim | "almost 7 million" walking/biking/rolling trips since Apr 2020, a "36% daily increase in park visits" ([SFMTA deck, Sep 2021](https://www.sfmta.com/media/28467/download?inline)) |
| Visitation by supervisorial district / equity zones | "No meaningful change" pre vs post ([SFMTA, Apr 2022](https://www.sfmta.com/project-updates/april-2022-update-new-hearing-date-and-new-robust-data); [FY24 report](https://sfrecpark.org/DocumentCenter/View/28988/Golden-Gate-Park-Annual-Access-and-Safety-Report-FY24)) |

### 3b. Surrounding network: traffic and travel time ([SFMTA GGP Traffic Study, Feb 2022](https://sfmta.com/media/30549/download))

| Metric | Fall 2019 → Fall 2021 |
|---|---|
| Weekday volumes on major streets near, within or crossing GGP | **−8% to −39%** (e.g., labelled segments −8%, −11%, −13%, −14%, −16%, −17%, −18%, −24%, −39%, −42%) |
| Median auto travel time, top-10 E-W O-D pairs that used JFK | decreased for **9 of 10** pairs |
| Median auto travel time, N-S cross-park pairs (Richmond ↔ Inner Sunset) | decreased for 3 of 4 pairs (−0.5 to −4.5 min; one +1.5 min) |
| Spare capacity on Lincoln Way and Fulton St at peak | could carry **20–40% more** traffic than observed in fall 2021 |
| Natural experiment, winter 2019, Saturday (JFK open) vs Sunday (JFK closed), 10am–4pm | −45 s to +72 s depending on O-D pair (Inner Richmond→Inner Sunset +20 s; Richmond→Bayview −45 s; Panhandle→Outer Richmond +72 s; Inner→Outer Richmond −5 s; Inner→Outer Sunset +27 s) |

### 3c. Safety

| Metric | Value | Source |
|---|---|---|
| Injury collisions on car-free JFK since Apr 2020 (as of Sep 2021) | **0** | [SFMTA deck, Sep 2021](https://www.sfmta.com/media/28467/download?inline) |
| FY24 (Jul 2023–Jun 2024) reported collisions in car-free area | **0**. 28 in GGP overall: 23 on roads with traffic, 4 on JFK adjacent to the Promenade | [FY24 report](https://sfrecpark.org/DocumentCenter/View/28988/Golden-Gate-Park-Annual-Access-and-Safety-Report-FY24) |
| FY25 | 1 reported collision in car-free area; 23 on GGP roads with traffic | [RPD FY25 annual report](https://sfrecpark.org/DocumentCenter/View/28987/JFK-Promenade-Annual-Report-FY25) (via search snippet) |
| Caveat | SFPD-reported crashes undercount injuries compared with SF General ER data | [FY24 report](https://sfrecpark.org/DocumentCenter/View/28988/Golden-Gate-Park-Annual-Access-and-Safety-Report-FY24) |

### 3d. Destinations: the "museum access" debate (attendance)

Source: [FY24 report](https://sfrecpark.org/DocumentCenter/View/28988/Golden-Gate-Park-Annual-Access-and-Safety-Report-FY24)

| Institution | FY19 | FY23 | FY24 | FY24 vs FY19 |
|---|---|---|---|---|
| Cal Academy | 1,334,559 | 1,184,450 | 1,226,452 | −8% |
| de Young | 1,120,025 | 1,066,221 | 859,000 | −23% |
| Conservatory of Flowers | 168,830 | 147,175 | 138,660 | −18% |
| Japanese Tea Garden | 534,068 | 551,134 | 545,573 | +2% |
| Botanical Garden | 424,143 | 507,437 | 523,419 | +23% |
| Music Concourse garage transient revenue (index) | — | — | — | **+15%** vs FY19 |

- Cal Academy visitor survey: "parking inconvenience" was 27% in FY19 and **30%** in FY24.
- Citywide confounds (Controller, Jul 2024): hotel occupancy −20%, Muni ridership −35%, BART SF exits −65% vs 2019.
- Shuttle: >49,000 riders in FY24.
- Public support: RPD survey found 70% in favour of keeping JFK car-free ([RPD Outreach & Analysis](https://sfrecpark.org/1579/Outreach-and-Analysis)). An independent SF Standard poll found lower support and showed seniors leaning toward reopening ([SF Standard, Oct 2022](https://sfstandard.com/2022/10/13/is-jfk-promenade-here-to-stay-many-support-car-free-road-but-polling-says-it-could-still-go-either-way/)).

### 3e. Retail / air quality

There is no retail on the corridor. No air-quality measurement was found (none / unverified).

## 4. Caveats / confounds

1. **COVID.** The closure began during shelter-in-place. Year-1 counts (+87%) are a pandemic recreation spike. Use the year-2 numbers (+28–30%).
2. Fall 2019 → fall 2021 network-wide traffic fell for COVID and remote-work reasons. The −8% to −39% volumes and faster travel times are **not** attributable to the closure. The clean natural experiment is the 2019 Saturday vs Sunday comparison (±72 s).
3. Counts come from location-based-services (LBS, CityDash.ai) and infrared sensors that can't distinguish mode ([FY24 report](https://sfrecpark.org/DocumentCenter/View/28988/Golden-Gate-Park-Annual-Access-and-Safety-Report-FY24)).
4. The "+76% biking" and "+29% walking" figures (SFMTA) and the "+30% ped & bike" figure (SFCTA) come from the same vendor data but different aggregations.

## 5. Sources

- SFMTA/RPD Golden Gate Park Access & Safety Program deck (Sep 2021): https://www.sfmta.com/media/28467/download?inline
- SFMTA Golden Gate Park Traffic Study (Feb 2022): https://sfmta.com/media/30549/download
- SFCTA, Trip Analysis of JFK Drive between Kezar and Tea Garden (Apr 26, 2022): https://sfcta.org/sites/default/files/2022-04/SFCTA-BOS_Board_GGP-JFKTripAnalysisKezarandTeaGardenPRESENTATION_2022-04-26.pdf
- SFMTA April 2022 update: https://www.sfmta.com/project-updates/april-2022-update-new-hearing-date-and-new-robust-data
- RPD/SFMTA Annual Report FY24 (Sep 6, 2024): https://sfrecpark.org/DocumentCenter/View/28988/Golden-Gate-Park-Annual-Access-and-Safety-Report-FY24
- RPD/SFMTA Annual Report FY25: https://sfrecpark.org/DocumentCenter/View/28987/JFK-Promenade-Annual-Report-FY25
- RPD Outreach and Analysis: https://sfrecpark.org/1579/Outreach-and-Analysis
- SF Bicycle Coalition, 2022 results: https://sfbike.org/news/big-successes-for-biking-from-2022-midterms/
- SF Standard poll (Oct 2022): https://sfstandard.com/2022/10/13/is-jfk-promenade-here-to-stay-many-support-car-free-road-but-polling-says-it-could-still-go-either-way/

## 6. What our model should reproduce

| Target | Value | Notes |
|---|---|---|
| `ped_footfall_uplift` (car-free recreational street, steady state) | **+28% to +30%** walk + bike on the treated street; walking alone +29% | Use year 2, not the COVID year 1 |
| Cycling uplift on a fully car-free street | **+76%** (upper bound for a street that becomes a car-free spine) | Compare Market +25% (buses remain) |
| Total person-throughput on treated street | **−9%** (cars gone, more peds/bikes) | Model should *not* assume ped gains fully replace lost car users |
| `traffic_evaporation_median` sanity check | Removing ~8,700 veh/day of 75%-cut-through traffic produced **no measurable travel-time penalty**: ±72 s on alternative O-D pairs (2019 Sat/Sun test). Parallel arterials (Fulton, Lincoln) had 20–40% spare capacity | Evaporation is plausible when parallels have slack. Our FiDi grid has less slack at peak |
| Injury collisions on treated segment | → ~0 | Drop to near zero once motor vehicles are removed |
| Destination access | Car-dependent destinations can lose 0–23% of visitors (de Young −23%, Cal Academy −8% vs FY19) while other destinations rise (Botanical Garden +23%) | COVID-confounded. Model a small negative access effect for car-oriented venues, not a large one |
