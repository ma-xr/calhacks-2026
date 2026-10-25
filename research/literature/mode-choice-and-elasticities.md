# Mode Choice and Travel-Demand Elasticities

This file sets how agents trade off car vs BART/Muni vs walk, and how strongly demand responds to time, cost, and parking. Coefficients below come straight from the Bay Area's production models: MTC Travel Model One and SFCTA's ActivitySim implementation. We read the model files ourselves.

Status legend: **verified** = read in primary file or text. **secondary** = abstract or reputable summary. **(unverified)** = not confirmed.

---

## 1. Key findings

### 1.1 Logit basics

- **Multinomial logit (MNL):** P(i) = exp(V_i) / Σ_j exp(V_j), with V_i = ASC_i + β_ivt·IVT_i + β_ovt·OVT_i + β_cost·Cost_i + …
  - The ratio β_cost/β_ivt gives value of time (VOT).
  - The ratio β_ovt/β_ivt gives the walk/wait weighting.
- **Nested logit:** correlated alternatives (e.g. transit sub-modes) share a nest with coefficient 0 < λ ≤ 1. A lower λ means more substitution within the nest.
- TM1 uses nest coefficients **0.72** (upper level) and **0.35** (lower level) (verified, [TM1 `ModeChoice.xls`, Work sheet](https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/model/ModeChoice.xls)).
- SFCTA ActivitySim uses **0.5** for all nests ([`tour_mode_choice_coefficients.csv`](https://github.com/sfcta/activitysim-sfcta/blob/main/configs/resident/tour_mode_choice_coefficients.csv)).
- Textbook reference: Koppelman & Bhat (2006), *A Self-Instructing Course in Mode Choice Modeling: Multinomial and Nested Logit Models* (FTA) — https://www.caee.utexas.edu/prof/bhat/COURSES/LM_Draft_060131Final-060630.pdf

### 1.2 MTC Travel Model One (TM1) tour mode choice: verified from the UEC workbook

Source: [`model-files/model/ModeChoice.xls`](https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/model/ModeChoice.xls), master branch. Last saved Feb 2025. We parsed it directly.

**In-vehicle time coefficient `c_ivt` (utils/min) by tour purpose**

| Purpose | c_ivt |
|---|---|
| **Work** | **−0.0134** |
| University, School | −0.0224 |
| Escort, Shopping, EatOut, OthMaint, Social, OthDiscr | −0.0175 |
| Work-based (at-work subtour) | −0.0188 |

**Other time weights, as multiples of c_ivt (the same for all purposes)**

| Term | Multiplier | Implied (work) |
|---|---|---|
| Walk time, short (≤ `walkThresh` = **1.5 mi**) | **2.0×** | −0.0268/min |
| Walk time, long (>1.5 mi) | 10.0× | −0.134/min |
| Bike time, short (≤ 6 mi) / long | 4.0× / 20.0× | |
| Initial wait, short (≤ `waitThresh` = **10 min**) | **2.0×** | |
| Initial wait, long (>10 min) | 1.0× | |
| Walk access / egress / auxiliary (transfer walk) | **2.0×** each | |
| Drive-access time | 2.0× | |
| Transfer wait | 2.0× | |
| Transfer penalty, walk-transit (per transfer) | 30× (≈30 IVT-min) | |
| Transfer penalty, drive-transit | 40× | |
| In-vehicle time on light rail / heavy rail (BART) / commuter rail / ferry | 0.90× / **0.80×** / 0.70× / 0.80× | Rail IVT is perceived as less onerous than bus IVT |

**Cost and value of time**

- **Cost coefficient:** `c_cost = (0.60 × c_ivt) / valueOfTime`. Cost is in **cents** and VOT in **$/hr**; the 0.6 factor converts 60 min/hr ÷ 100 ¢/$.
- **VOT per person:** drawn from a **lognormal** distribution by household income. Means, in **2000 $/hr** ([`mtcTourBased.properties`](https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/runtime/mtcTourBased.properties)):

| Income group | Mean VOT (2000 $/hr) |
|---|---|
| Low | 6.01 |
| Mid | 8.81 |
| High | 10.44 |
| Very high | 12.86 |

  Draws are truncated to $1–$50/hr.
- **Highway assignment VOT:** **$15.00/hr** (2000 $). Trucks: $30/hr ([`hwyParam.block`](https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/scripts/block/hwyParam.block)).
- **Auto operating cost:** 18.29 ¢/mile (2000 ¢) in the mode-choice UEC.
- **Shared-ride cost sharing:** SR2 divides parking cost by `costShareSr2` and SR3+ by `costShareSr3`. The assignment-side values are 1.75 and 2.50.

**Parking in TM1**

- Daily parking cost = `hourlyParkingCost` (zonal field `PRKCST`) × `tourDuration`.
- It applies only if the worker lacks free or subsidized parking. A separate `FreeParkingEligibility.xls` model decides that.
- CBD parking zones are listed in [`CBDParkingZones.csv`](https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/model/CBDParkingZones.csv).

**Alternative-specific constants (work tours, individual)**

These are **calibrated constants**, not portable behavioural parameters; they absorb everything unobserved.

| Mode | Zero-auto HH | Auto-deficient HH | Auto-sufficient HH |
|---|---|---|---|
| Walk | +6.27 | +3.14 | −0.22 |
| Walk-to-transit | +7.25 | +1.43 | −2.08 |
| Drive-to-transit | 0 | +0.53 | −2.52 |

  Transit sub-mode constants: heavy rail **+0.98**, commuter rail +1.89, express bus −0.31.

### 1.3 SFCTA ActivitySim (SF-CHAMP successor): verified from config files

Source: [`sfcta/activitysim-sfcta` `configs/resident/tour_mode_choice_coefficients.csv`](https://github.com/sfcta/activitysim-sfcta/blob/main/configs/resident/tour_mode_choice_coefficients.csv), main branch, last pushed 2024-09.

**Caveat:** the repo README still describes the SANDAG ABM3 example it was forked from. These coefficients may be inherited from SANDAG rather than re-estimated for SF. Their SF calibration status is **(unverified)**.

| Coefficient (work) | Value | Ratio to IVT |
|---|---|---|
| `coef_ivt_work` | **−0.016** /min | 1.0 |
| `coef_walktime_work` | −0.0424 /min | **2.65×** |
| `coef_wait_work` (initial wait) | −0.024 /min | **1.5×** |
| `coef_xwait_work` (transfer wait) | −0.032 /min | 2.0× |
| `coef_xwalk_work` (transfer walk) | −0.040 /min | 2.5× |
| `coef_acctime_work` (drive access) | −0.032 /min | 2.0× |
| `coef_income_work` | −0.625 | see below |

- **Cost sensitivity is income-scaled** ([preprocessor](https://github.com/sfcta/activitysim-sfcta/blob/main/configs/resident/tour_mode_choice_annotate_choosers_preprocessor.csv)): `c_cost = coef_income / max(income, 1000)^θ`, with θ = **0.6 for work** and 0.5 otherwise. Costs and fares are in cents.
- **Implied work VOT** (our arithmetic: VOT = c_ivt / c_cost):
  - HH income $100k → **≈ $15.4/hr**
  - HH income $200k → **≈ $23.3/hr**
  - The dollar-year basis is **(unverified)**.
- Other constants ([`constants.yaml`](https://github.com/sfcta/activitysim-sfcta/blob/main/configs/common/constants.yaml)): `walkSpeed` = **3.0 mph** (1.34 m/s), `walkThresh` = 1.5 mi, `bikeSpeed` = 7.8 mph, `driveSpeed` = 25 mph, `costPerMile` = 18.29.
- **Original SF-CHAMP (2002) documentation:** coefficients are in zipped development reports on [SFCTA SF-CHAMP Modeling](https://www.sfcta.org/sf-champ-modeling). We did not open them, so SF-CHAMP 6/7 calibration-report coefficients are **(unverified)**.

### 1.4 Value of time: federal guidance

| Item | Value | Source |
|---|---|---|
| USDOT local personal travel VTTS (2015 $) | **$13.60/person-hr** | USDOT 2016 VOT guidance / BCA Resource Guide ([BCA Resource Guide 2016](https://www.transportation.gov/sites/dot.gov/files/docs/BCA%20Resource%20Guide%20-%20November%202016.pdf)), secondary |
| Walk, wait, and transfer time, personal (2015 $) | **$27.20/hr** (= **2×** in-vehicle) | same, secondary |
| USDOT local personal, escalated to **2024 $** | **$21.80/person-hr** | [Caltrans Cal-B/C vs Federal comparison matrix 2026](https://dot.ca.gov/-/media/dot-media/programs/transportation-planning/documents/division-transportation-planning/transportation-economics/cal-bc-federal-comparison-of-value-matrix-2026-a11y.pdf) (verified, PDF text) |
| Cal-B/C automobile/personal | $16.45/hr | same |
| Rule | "for wait times, the value should be doubled" | same |
| Basis | Local personal VTTS = 50% of median hourly household income; walk/wait = 100% | [USDOT 2016 guidance](https://www.transportation.gov/sites/dot.gov/files/docs/Revised%20Departmental%20Guidance%20on%20Valuation%20of%20Travel%20Time%20in%20Economic%20Analysis%20-%20September%202016.pdf). The percentages are **(unverified this session; the PDF returned 403)**, but they are consistent with the 2× ratio above |

**Model-implied VOT ratios.** In both Bay Area models, out-of-vehicle time (walk, wait) is weighted **1.5–2.65×** in-vehicle time. This matches the federal **2×** rule.

### 1.5 Elasticities

**Car travel w.r.t. travel time**

| Elasticity | Short run | Long run | Source |
|---|---|---|---|
| Traffic volume w.r.t. travel time (UK, induced traffic) | **−0.5** | **up to −1.0** | [Goodwin 1996](https://trid.trb.org/View/458127) (secondary) |
| Car trips w.r.t. travel time, all purposes (Europe) | −0.60 | −0.29 | de Jong & Gunn (2001), via [Litman, VTPI *Understanding Transport Demands and Elasticities* (Aug 2026), Table 8](https://www.vtpi.org/elasticities.pdf) (verified) |
| Car-km w.r.t. travel time, all purposes | −0.20 | −0.74 | same |
| US urban auto demand w.r.t. in-vehicle time | **−0.22** | — | Small & Winston (1999), via [VTPI Table 10](https://www.vtpi.org/elasticities.pdf) |
| US urban auto demand w.r.t. price | −0.47 | — | same |
| Urban bus / rail w.r.t. in-vehicle time | −0.60 / −0.60 | — | same |

**Fuel price** (Goodwin, Dargay & Hanly 2004, *Transport Reviews* 24(3):275–292, [IDEAS](https://ideas.repec.org/a/taf/transr/v24y2003i3p275-292.html); values via [VTPI Table 9](https://www.vtpi.org/elasticities.pdf), verified)

| Dependent variable | Short run | Long run |
|---|---|---|
| Vehicle-km, total | **−0.10** (range −0.05 to −0.17, n=3) | **−0.29** (−0.10 to −0.63, n=3) |
| Fuel consumption, total | −0.25 (n=46) | −0.64 (n=51) |
| Vehicle stock | −0.08 | −0.25 |

**Income** (same review): +10% real income gives traffic about +2% within a year and about +5% long run.

**Parking price**

| Measure | Value | Source |
|---|---|---|
| Vehicle trips w.r.t. parking price (review range) | **−0.1 to −0.3** | [VTPI 2026, "Parking Price"](https://www.vtpi.org/elasticities.pdf) (verified) |
| Parking fees vs other out-of-pocket costs | Parking has **1.5–2.0×** the effect per dollar | USEPA 1998, via VTPI |
| Car trips to preferred CBD parking w.r.t. its price | **−0.541** | Hensher & King 2001, via VTPI |
| Cross-elasticity: public transit w.r.t. CBD parking price | +0.291 | same |
| Cross-elasticity: forgo CBD trip | +0.469 | same |
| Portland CBD commuters: free parking → $6/day | Drive-alone 62% → 46%; transit 22% → 50% | Hess 2001, via VTPI |
| Vancouver: $9 parking + $0 toll | Auto commute share 83% → 49% | Washbrook et al. 2006, via VTPI |
| **SFpark**: on-street occupancy w.r.t. meter price | **−0.4** average, varying strongly by time and location | Pierce & Shoup 2013, *JAPA* 79(1):67–81 ([PDF](https://www.shoupdogg.com/wp-content/uploads/sites/10/2017/06/Getting-the-Prices-Right-An-Evaluation-of-Pricing-Parking-by-Demand-in-San-Francisco.pdf); [UCLA brief](https://www.lewis.ucla.edu/wp-content/uploads/sites/17/2018/09/Pricing-Parking-by-Demand_-Assessing-Price-Adjustments-in-the-SFpark-Program.pdf)), secondary |

SFpark's −0.4 is a **parking-occupancy** elasticity at a block level. It is **not** a mode-choice elasticity; much of the response is spatial (parking a block away).

**Transit fares** (VTPI [*Transit Price Elasticities*, June 2025](https://www.vtpi.org/tranelas.pdf), verified)

| Measure | Value |
|---|---|
| Bus fare, large US cities (>1M population), all hours | **−0.36** (APTA / Pham & Linsalata 1991) |
| Bus fare, peak | −0.18 |
| Bus fare, off-peak | −0.39 |
| Simpson–Curtin rule | 3% fare increase → 1% ridership loss (≈ −0.33); described as "too simplistic and outdated" |
| Australian standard values, bus / rail fare | −0.29 / −0.35 (Luk & Hepburn 1993, via [VTPI elasticities Table 7](https://www.vtpi.org/elasticities.pdf)) |

### 1.6 Downtown SF mode share (context for calibration)

- **Adult weekday trips to/from/within Downtown SF, all purposes** ([SFCTA Downtown Travel Study, Executive Summary, May 2025](https://www.sfcta.org/sites/default/files/2025-05/Downtown_Travel_Study_FINAL_Report_2025-05-22_Executive_Summary.pdf), verified from PDF text):

| Mode | 2019 | 2023 |
|---|---|---|
| Automobile | **24.5%** | **36.9%** |
| Transit | **27.9%** | **20.9%** |
| Walk/bike | **43.4%** | **39.7%** |
| Taxi/TNC | 4.2% | 2.5% |

  - Total trips fell 1.64M → 0.89M (−46%). Work trips fell −66%.
  - Downtown workers telecommuting 2+ days/week rose from 13.7% to 62.8%.
  - *Our pairing of chart labels to years was checked by both columns summing to 100%.*
- **Work-trip-only shares to Downtown** are in the full report (Fig. 3-9). They were **not retrieved**, so they are **(unverified)**.
- **Citywide all-trip shares, fall 2019:** drive alone 31%, carpool 17%, transit 22%, walk 22%, TNC 5% ([SFMTA Travel Decisions Survey](https://sfmta.com/media/20810/download), secondary).

---

## 2. How our model uses it

| Parameter key | Adopted value | Range | Basis |
|---|---|---|---|
| `vot_personal_usd_per_hr` | **21.80** (2024 $) | 15–35; draw per agent from lognormal by income, following TM1 | USDOT via [Caltrans 2026 matrix](https://dot.ca.gov/-/media/dot-media/programs/transportation-planning/documents/division-transportation-planning/transportation-economics/cal-bc-federal-comparison-of-value-matrix-2026-a11y.pdf); TM1 income dispersion ([properties](https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/runtime/mtcTourBased.properties)) |
| `walk_wait_time_multiplier` | **2.0** | 1.5–2.65 | TM1 walk/wait 2.0× ([ModeChoice.xls](https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/model/ModeChoice.xls)); SFCTA 1.5× wait, 2.65× walk ([coefficients](https://github.com/sfcta/activitysim-sfcta/blob/main/configs/resident/tour_mode_choice_coefficients.csv)); USDOT 2× |
| `car_trip_time_elasticity` | **−0.5** | −0.2 to −1.0 | [Goodwin 1996](https://trid.trb.org/View/458127); de Jong & Gunn via [VTPI](https://www.vtpi.org/elasticities.pdf) |
| `daily_parking_cost_fidi_usd` | **22** (commuter early bird) | 22–40 (12-hr max); $8/hr transient | SFMTA Golden Gateway Garage, 250 Clay St (FiDi): early bird $22, 12-hr max $40, 24-hr max $46, $8/hr daytime ([SFMTA garage page](https://www.sfmta.com/index%2Ephp/garages-lots/golden-gateway-garage); secondary, undated). Private-garage averages are (unverified). TM1 treats parking as hourly × duration |
| `downtown_sf_worker_mode_share` | Calibration target (all purposes, 2023): auto 0.37 / transit 0.21 / walk-bike 0.40 / TNC 0.025. Use the 2019 vector for a pre-pandemic scenario | — | [SFCTA 2025](https://www.sfcta.org/sites/default/files/2025-05/Downtown_Travel_Study_FINAL_Report_2025-05-22_Executive_Summary.pdf). The work-only split is (unverified) |

**Recommended utility form for agents (work commute)**, per minute and per dollar:

```
V_car     = ASC_car  + b_ivt*IVT_car  + b_ivt*2.0*walk_egress + b_cost*(op_cost + parking)
V_transit = ASC_tr   + b_ivt*k_mode*IVT_tr + b_ivt*2.0*(walk_acc + walk_egr + wait) + b_ivt*30*n_xfer + b_cost*fare
V_walk    = ASC_walk + b_ivt*2.0*walk_time            (walk_time beyond 1.5 mi weighted 10x, per TM1)

b_ivt  = -0.0134/min    (TM1 work)
k_mode = 0.8 for BART, 1.0 for Muni bus, 0.9 for Muni Metro (light rail)
b_cost = 60 * b_ivt / VOT     per dollar   (VOT drawn per agent)
```

The ASCs must be **re-calibrated** so that baseline shares match the SFCTA downtown shares above. TM1's ASCs are regional and segmented by auto sufficiency.

**Sanity check (our arithmetic).** Raise FiDi parking by $5/day. With TM1-like coefficients and VOT ≈ $20/hr:

- b_cost = 60 × (−0.0134) / 20 ≈ −0.040 per $, so the utility drop is ≈ **0.20 utils**.
- MNL own-elasticity = (1 − P_car) · b_cost · price. At P_car = 0.3 and a $25/day base price, that is ≈ 0.7 × 0.040 × 25 ≈ **−0.7**, i.e. about **−14%** car commuters for +$5.

That is **more elastic** than VTPI's general vehicle-trip range (**−0.1 to −0.3**). It sits near CBD-specific evidence: Hensher & King **−0.54**, and Hess's Portland case, where $6/day cut drive-alone share by about a quarter. Nesting and free-parking eligibility (many commuters never see the price) damp this in practice. **Calibration target:** an effective parking elasticity of car commute trips of about **−0.3 to −0.5**, reached by giving a share of workers employer-paid parking. That share is (unverified).

---

## 3. Limitations

- **TM1 coefficients are not estimated on FiDi data.** The ASCs absorb regional effects, and TM1 is calibrated to a 2000 survey and later validation years. **We use the coefficient ratios, not the constants.**
- **The SFCTA ActivitySim fork may carry SANDAG coefficients.** Treat it as a second opinion, not SF-specific truth.
- **Dollar-year mismatch.** TM1 uses 2000 $, USDOT 2015 $ / 2024 $. Deflate consistently, or use ratios.
- **Elasticities are context-specific and mostly short-run.** Transit fare elasticities in VTPI are mainly short-run US 1980s data; Litman notes they likely understate long-run response ([tranelas.pdf](https://www.vtpi.org/tranelas.pdf)).
- **Post-pandemic shifts.** Telework (63% of downtown workers 2+ days/week) and the auto-share rebound mean 2019-calibrated models over-predict transit ([SFCTA 2025](https://www.sfcta.org/sites/default/files/2025-05/Downtown_Travel_Study_FINAL_Report_2025-05-22_Executive_Summary.pdf)).
- **Free-parking eligibility** is a huge driver of car commuting. TM1 models it explicitly; we should keep a share of workers with employer-paid parking. That share is **(unverified for FiDi)**.

---

## 4. Sources

1. MTC Travel Model One, `ModeChoice.xls` (tour mode choice UEC). https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/model/ModeChoice.xls
2. MTC TM1, `mtcTourBased.properties` (VOT distributions). https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/runtime/mtcTourBased.properties
3. MTC TM1, `hwyParam.block` (assignment VOT). https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/scripts/block/hwyParam.block
4. SFCTA ActivitySim, tour mode choice coefficients / preprocessor / constants. https://github.com/sfcta/activitysim-sfcta/tree/main/configs
5. SFCTA SF-CHAMP Modeling page. https://www.sfcta.org/sf-champ-modeling
6. Koppelman & Bhat (2006), FTA mode choice course. https://www.caee.utexas.edu/prof/bhat/COURSES/LM_Draft_060131Final-060630.pdf
7. Caltrans, Cal-B/C vs Federal Comparison of Values Matrix (2026). https://dot.ca.gov/-/media/dot-media/programs/transportation-planning/documents/division-transportation-planning/transportation-economics/cal-bc-federal-comparison-of-value-matrix-2026-a11y.pdf
8. USDOT (2016), Revised Departmental Guidance on Valuation of Travel Time. https://www.transportation.gov/sites/dot.gov/files/docs/Revised%20Departmental%20Guidance%20on%20Valuation%20of%20Travel%20Time%20in%20Economic%20Analysis%20-%20September%202016.pdf
9. Litman, T. (2026), *Understanding Transport Demands and Elasticities*, VTPI. https://www.vtpi.org/elasticities.pdf
10. Litman, T. (2025), *Transit Price Elasticities and Cross-Elasticities*, VTPI. https://www.vtpi.org/tranelas.pdf
11. Goodwin, Dargay & Hanly (2004), *Transport Reviews* 24(3). https://ideas.repec.org/a/taf/transr/v24y2003i3p275-292.html
12. Goodwin (1996), *Transportation* 23. https://trid.trb.org/View/458127
13. Pierce & Shoup (2013), Getting the Prices Right, *JAPA* 79(1). https://www.shoupdogg.com/wp-content/uploads/sites/10/2017/06/Getting-the-Prices-Right-An-Evaluation-of-Pricing-Parking-by-Demand-in-San-Francisco.pdf
14. SFCTA (2025), Downtown Travel Study, Executive Summary. https://www.sfcta.org/sites/default/files/2025-05/Downtown_Travel_Study_FINAL_Report_2025-05-22_Executive_Summary.pdf
15. SFMTA, Travel Decisions / Mode Share Survey 2019. https://sfmta.com/media/20810/download
