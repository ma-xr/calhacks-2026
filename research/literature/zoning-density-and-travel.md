# Zoning, Density and Travel: Built-Environment Elasticities and Floor-Area Conversions

When a user rezones a block (e.g. office → mixed residential/retail) or changes FAR, the sim must:

1. Convert floor area to **jobs and residents**.
2. Let the new land-use mix change **trip generation, destination choice (Huff), and mode**.

This file gives the empirical elasticities and the conversion factors for both steps. It also covers pedestrian movement parameters (walking speed and detour factor).

Status legend: **verified** = read in primary text. **secondary** = abstract or reputable summary. **(unverified)** = not confirmed.

---

## 1. Key findings

### 1.1 Ewing & Cervero (2010), "Travel and the Built Environment: A Meta-Analysis", *JAPA* 76(3):265–294

Verified from the full text ([PDF](http://www.cedeus.cl/wp-content/uploads/2013/09/EwingCervero.pdf); [TRID](https://trid.trb.org/view/980894)). The meta-analysis covers 50+ studies and reports weighted-average elasticities.

**Table 3 — VMT**

| D-variable | Measure | n studies | Elasticity |
|---|---|---|---|
| Density | Household/population density | 9 | **−0.04** |
| Density | Job density | 6 | 0.00 |
| Diversity | Land-use mix (entropy) | 10 | **−0.09** |
| Diversity | Jobs–housing balance | 4 | −0.02 |
| Design | Intersection/street density | 6 | **−0.12** |
| Design | % 4-way intersections | 3 | −0.12 |
| Destination accessibility | Job accessibility by auto | 5 | **−0.20** |
| Destination accessibility | Job accessibility by transit | 3 | −0.05 |
| Destination accessibility | Distance to downtown | 3 | **−0.22** |
| Distance to transit | Distance to nearest transit stop | 6 | **−0.05** |

**Table 4 — Walking**

| D-variable | Measure | n studies | Elasticity |
|---|---|---|---|
| Density | Household/population density | 10 | 0.07 |
| Density | Job density | 6 | 0.04 |
| Density | Commercial FAR | 3 | 0.07 |
| Diversity | Land-use mix (entropy) | 8 | **0.15** |
| Diversity | Jobs–housing balance | 4 | **0.19** |
| Diversity | Distance to a store | 5 | **0.25** |
| Design | Intersection/street density | 7 | **0.39** |
| Design | % 4-way intersections | 5 | −0.06 |
| Destination accessibility | Jobs within one mile | 3 | 0.15 |
| Distance to transit | Distance to nearest transit stop | 3 | 0.15 |

**Table 5 — Transit use**

| D-variable | Measure | n studies | Elasticity |
|---|---|---|---|
| Density | Household/population density | 10 | 0.07 |
| Density | Job density | 6 | 0.01 |
| Diversity | Land-use mix (entropy) | 6 | 0.12 |
| Design | Intersection/street density | 4 | 0.23 |
| Design | % 4-way intersections | 5 | **0.29** |
| Distance to transit | Distance to nearest transit stop | 3 | **0.29** |

- **Sign convention:** distance-type variables are sign-reversed, so a positive value means more walking or transit with *better* access (closer store or stop).
- **Correction to the brief:** walking w.r.t. jobs–housing balance is **0.19**, not 0.15. The 0.15 value belongs to land-use mix and jobs within one mile.
- The authors call these "**ballpark estimates**". Most samples have **3–10 studies**, and few control for self-selection. No elasticity exceeds |0.39|, "but the combined effect of several such variables on travel could be quite large" ([PDF](http://www.cedeus.cl/wp-content/uploads/2013/09/EwingCervero.pdf)).

### 1.2 Critique: Stevens (2017), "Does Compact Development Make People Drive Less?", *JAPA* 83(1):7–18

[IDEAS](https://ideas.repec.org/a/taf/rjpaxx/v83y2017i1p7-18.html); [APA summary](https://planning.org/knowledgebase/resource/9182225). Secondary sources only.

- Meta-regression of **37 studies (1996–2015)**. Compact-development features have a significant but **small** negative effect on driving. Stevens concludes they "do not appear to have much influence on driving" ([Nelson commentary](https://ppms.trec.pdx.edu/media/project_files/Nelson_-_Compact_Development_Reduces_VMT.pdf)).
- **Rebuttal:** Ewing & Cervero (2017, *JAPA*) argue his conclusions overreach. Ewing frames a –0.22 elasticity as meaningful: a doubling (100% increase) would mean about 22% less driving ([Planning, Jan 2017](https://planning.org/planning/2017/jan/research/)). Stevens' own per-variable point estimates are **(unverified)**.
- **Takeaway:** the built environment has real but modest effects. Several D's moving together (as in a downtown infill) compound.

### 1.3 Floor area per job (employment density)

**San Francisco Planning standard factors** (verified, [SF Planning 2020 Jobs-Housing Fit Report, Table 3](https://sfplanning.org/sites/default/files/resources/2021-11/Jobs-Housing_Fit_Report_2020.pdf))

| Land use | Square feet per job |
|---|---|
| **Office** | **240** |
| **Retail** | **350** |
| Cultural/institutional/educational | 350 |
| **Visitor (hotel)** | **440** |
| Medical | 350 |
| PDR (production, distribution, repair) | 570 |

**Other benchmarks**

| Source | Value | Note |
|---|---|---|
| Central SoMa Plan ordinance (2018) | **~220 gsf per worker** (blended non-residential) | 8.5M gsf → about 40,000 jobs ([ordinance](https://default.sfplanning.org/Citywide/Central_Corridor/central_soma_planning_code_admin_code_ordinance-041018.pdf)) (secondary) |
| US EIA CBECS 2018, Table B16 — office buildings, median | **609 sq ft/worker** | National stock, incl. suburban ([EIA B16](https://www.eia.gov/consumption/commercial/data/2018/bc/pdf/b16.pdf)) (secondary) |
| CBECS — admin/professional office, median | 625 | same |
| CBECS — bank/financial office, median | 714 | same |
| CBECS — all commercial buildings, median | 1,167 | same |

**Why SF Planning's 240 and CBECS's 609 differ:**

- CBECS medians are national, building-level, and dominated by small and suburban offices.
- Downtown towers pack workers far more densely.
- Post-pandemic, *occupied* desks per sq ft are lower still: downtown office attendance is 40–45% of pre-pandemic ([SFCTA 2025](https://www.sfcta.org/sites/default/files/2025-05/Downtown_Travel_Study_FINAL_Report_2025-05-22_Executive_Summary.pdf)).
- The "150–250 sqft/job post-pandemic office" norm in the brief, and the NRDC/Ehrenhalt figures, are **(unverified)**.

### 1.4 Households and residents

| Measure | Value | Source |
|---|---|---|
| **SF persons per household, ACS 2019–2023** | **2.24** (US: 2.54) | [Census QuickFacts](https://census.gov/quickfacts/fact/table/sanfranciscocitycalifornia,US/PST045219) (secondary) |
| SF households, 2019–2023 | 362,650 | same |
| SF population change 2019→2023 | −8% (Bay Area −3%) | [SFCTA 2025](https://www.sfcta.org/sites/default/files/2025-05/Downtown_Travel_Study_FINAL_Report_2025-05-22_Executive_Summary.pdf) |
| SF worker households per 100,000 sq ft (all AMI groups) | Office 241.7; Retail 156.3; Visitor 73.0 | Keyser Marston 2019 nexus, via [SF Planning JHF Report Table 4](https://sfplanning.org/sites/default/files/resources/2021-11/Jobs-Housing_Fit_Report_2020.pdf). The sums are our arithmetic over the AMI rows |

### 1.5 Pedestrian movement parameters

| Measure | Value | Source |
|---|---|---|
| Walk speed in SFCTA's model | **3.0 mph = 1.34 m/s** | [SFCTA ActivitySim `constants.yaml`](https://github.com/sfcta/activitysim-sfcta/blob/main/configs/common/constants.yaml) (verified) |
| Knoblauch et al. 1996, 15th-percentile walking speed | **1.25 m/s** (ages 14–64); **0.97 m/s** (65+) | *TRR* 1538:27–38 ([TRID](https://trid.trb.org/View/469376); [FHWA summary](https://www.fhwa.dot.gov/publications/research/safety/pedbike/98107/section2.cfm)) (secondary). Design values recommended: 1.22 / 0.91 m/s |
| MUTCD 2009 §4E.06, pedestrian clearance | **3.5 ft/s (1.07 m/s)**; up to 4 ft/s with extended push-button; 3 ft/s check | [MUTCD Ch. 4E](https://mutcd.fhwa.dot.gov/htm/2009/part4/part4e.htm) (verified) |
| MATSim default teleported walk | **3.0 km/h (0.83 m/s)** × beeline factor **1.3** | [MATSim `RoutingConfigGroup.java`](https://github.com/matsim-org/matsim-libs/blob/main/matsim/src/main/java/org/matsim/core/config/groups/RoutingConfigGroup.java) (verified). Deliberately conservative |
| **San Francisco walk-network circuity** (network ÷ straight-line distance) | **1.210** | Boeing (2019), Table 1, 40 US cities ([arXiv:1708.00836](https://arxiv.org/pdf/1708.00836)) (verified) |
| SF drive-network circuity | **1.308** | same. SF has the 2nd-largest drive-vs-walk gap (+46%), from one-way streets and hills |
| Other cities' walk circuity | Manhattan 1.142; Chicago 1.178 | same |

---

## 2. How our model uses it

| Parameter key | Adopted value | Range | Basis |
|---|---|---|---|
| `office_sqft_per_job` | **240** | 220 (Central SoMa blend) – 609 (CBECS national median) | [SF Planning JHF 2020](https://sfplanning.org/sites/default/files/resources/2021-11/Jobs-Housing_Fit_Report_2020.pdf) |
| `retail_sqft_per_job` | **350** | 350–500 (upper end unverified) | same |
| `hotel_sqft_per_job` | **440** | — | same ("Visitor") |
| `sf_persons_per_household` | **2.24** | 1.8–2.3 for downtown new-build (unverified) | [Census QuickFacts](https://census.gov/quickfacts/fact/table/sanfranciscocitycalifornia,US/PST045219) |
| `walking_speed_m_s` | **1.34** | 1.07 (MUTCD design) – 1.25 (15th percentile, young) | [SFCTA constants](https://github.com/sfcta/activitysim-sfcta/blob/main/configs/common/constants.yaml); [Knoblauch 1996](https://trid.trb.org/View/469376) |
| `walk_detour_factor` | **1.21** | 1.14–1.30 (1.3 = MATSim default) | [Boeing 2019](https://arxiv.org/pdf/1708.00836) |

Notes:
- **Walking speed.** Our agents walk on the graph, so the detour is already explicit. Use straight-line distance × `walk_detour_factor` only for teleported or estimated walks (e.g. station egress).
- **Detour factor.** FiDi's regular grid plus Market St's diagonal is probably at or below the citywide 1.21. That is our judgment, not a sourced figure.

**Rezoning → agents (conversion recipe)**

```
GFA_total          = FAR * lot_area_sqft
GFA_use            = GFA_total * share_use                        (office / retail / hotel / residential)
jobs_use           = GFA_use * (1 - vacancy_use) / sqft_per_job_use
dwelling_units     = GFA_res * residential_efficiency / avg_unit_gsf
residents          = dwelling_units * (1 - res_vacancy) * sf_persons_per_household
```

- Inputs from this file: `sqft_per_job_use` (240 / 350 / 440) and `sf_persons_per_household` (2.24).
- `vacancy_use`, `residential_efficiency` (~0.8), `avg_unit_gsf` (~900–1,000 for new SF multifamily), and `res_vacancy` are **(unverified)** placeholders. Expose them as parameters.
- **Post-pandemic option:** multiply office jobs by an attendance factor of 0.40–0.45 for the "agents present on a given weekday" count ([SFCTA 2025](https://www.sfcta.org/sites/default/files/2025-05/Downtown_Travel_Study_FINAL_Report_2025-05-22_Executive_Summary.pdf)).

**Rezoning → travel response (validation, not hard-coding)**

Behaviour should emerge from Huff destination choice and the mode logit. Ewing & Cervero give the order of magnitude to check against:

| Plan change | Expected direction and size |
|---|---|
| Adding residential to an office block | Raises local land-use mix → resident VMT elasticity ≈ **−0.09**; walking w.r.t. mix **+0.15** |
| Retail within walking distance of homes | Walking w.r.t. distance to store **+0.25** |
| Pedestrianizing or adding mid-block paths | Raises effective intersection density → walking **+0.39**, transit **+0.23**, VMT **−0.12** |

**Worked check (our arithmetic):** a plan that raises the land-use entropy of a 10-block area by 20% should change resident walking trips by about **+3%** (0.15 × 20%) and VMT by about **−2%**. Results 10× larger signal an over-sensitive Huff or mode model.

---

## 3. Limitations

- **Cross-sectional, small samples, little control for self-selection.** Ewing & Cervero's tables mix studies with and without self-selection controls (often 0–1 per cell). Stevens (2017) argues the true effects are smaller.
- **Elasticities are for residents' travel** (household VMT and walking), mostly suburban-to-urban US gradients. FiDi is already at the extreme end, so marginal effects may be nonlinear: small at very high density, or larger for walking.
- **Employment densities change.** Hybrid work weakens the link between floor area and on-site workers. SF Planning's 240 sf/job reflects jobs *assigned* to a building, not daily occupancy.
- **CBECS is national.** It is not appropriate as a downtown SF value except as an upper bound.
- **Household size varies by unit type and neighbourhood.** Downtown new-build studios and 1-BRs likely sit below the citywide 2.24 (unverified).
- **Walking speed varies with age, grade, and crowding.** SF hills (8%+ grades) slow pedestrians, though our study area is mostly flat. Crowding at Montgomery/Embarcadero station exits at peak is not captured.

---

## 4. Sources

1. Ewing, R., Cervero, R. (2010). Travel and the Built Environment: A Meta-Analysis. *JAPA* 76(3):265–294. http://www.cedeus.cl/wp-content/uploads/2013/09/EwingCervero.pdf · https://trid.trb.org/view/980894
2. Stevens, M. (2017). Does Compact Development Make People Drive Less? *JAPA* 83(1):7–18. https://ideas.repec.org/a/taf/rjpaxx/v83y2017i1p7-18.html
3. Ewing (2017), *Planning* research column. https://planning.org/planning/2017/jan/research/
4. Nelson, A.C., commentary on Stevens. https://ppms.trec.pdx.edu/media/project_files/Nelson_-_Compact_Development_Reduces_VMT.pdf
5. SF Planning (2021), 2020 Jobs-Housing Fit Report (employment density factors; KMA 2019 nexus factors). https://sfplanning.org/sites/default/files/resources/2021-11/Jobs-Housing_Fit_Report_2020.pdf
6. SF Central SoMa Plan ordinance (2018). https://default.sfplanning.org/Citywide/Central_Corridor/central_soma_planning_code_admin_code_ordinance-041018.pdf
7. US EIA, CBECS 2018, Table B16. https://www.eia.gov/consumption/commercial/data/2018/bc/pdf/b16.pdf
8. US Census QuickFacts, San Francisco city. https://census.gov/quickfacts/fact/table/sanfranciscocitycalifornia,US/PST045219
9. SFCTA (2025), Downtown Travel Study, Executive Summary. https://www.sfcta.org/sites/default/files/2025-05/Downtown_Travel_Study_FINAL_Report_2025-05-22_Executive_Summary.pdf
10. Knoblauch, Pietrucha, Nitzburg (1996). Field Studies of Pedestrian Walking Speed and Start-Up Time. *TRR* 1538. https://trid.trb.org/View/469376
11. FHWA MUTCD 2009, Chapter 4E. https://mutcd.fhwa.dot.gov/htm/2009/part4/part4e.htm
12. Boeing, G. (2019). The Morphology and Circuity of Walkable and Drivable Street Networks. https://arxiv.org/pdf/1708.00836
13. MATSim `RoutingConfigGroup.java`. https://github.com/matsim-org/matsim-libs/blob/main/matsim/src/main/java/org/matsim/core/config/groups/RoutingConfigGroup.java
14. SFCTA ActivitySim `constants.yaml`. https://github.com/sfcta/activitysim-sfcta/blob/main/configs/common/constants.yaml
