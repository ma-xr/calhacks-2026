# Health and External-Cost Valuation: Literature Synthesis

Scope: how we value extra walking (WHO HEAT), avoided driving (crashes, CO2, air pollution), and the inputs behind those values (mortality rate, VSL, carbon cost).
Convention: inline links for every number. "(unverified)" means no primary or reliable secondary source was reached. "(derived)" means our arithmetic.

---

## 1. Key findings

### 1.1 WHO HEAT physical-activity module (primary source: 2017 methods guide)

[Kahlmeier et al., *HEAT for walking and for cycling: Methods and user guide* (WHO Europe, 2017)](https://www.rsu.lv/sites/default/files/book_download/heat.pdf), Table 1 and §3.9:

| Mode | Age range | Relative risk (all-cause mortality) | Reference volume | Benefit cap |
|---|---|---|---|---|
| **Walking** | **20–74** | **0.89** (95% CI 0.83–0.96) | **168 min/week** at 4.8 km/h | **30%** risk reduction (reached at **460 min/week**) |
| Cycling | 20–64 | 0.90 (CI 0.87–0.94) | 100 min/week at 14 km/h | 45% (reached at 447 min/week) |

- **Formula:** risk reduction = (1 − RR) × (local volume ÷ reference volume), capped. The dose-response is **linear**, so baseline activity is not needed. Deaths prevented = reduction × population mortality rate × population.
- **Time lag:** benefits build **20% per year to full effect after 5 years**.
- The RRs come from a 2013–14 meta-analysis of 14 walking and 7 cycling cohort studies.
- HEAT is designed for **habitual** population-level behaviour, not individuals or one-off events.
- (derived) **+30 min/week walking gives −1.96% mortality risk; +60 min/week gives −3.9%.**
- Note: the brief's "0.886 per 11.25 MET-h/week" is **not** the HEAT parameterisation. HEAT expresses dose in minutes/week at a fixed speed, and the actual value is 0.89 at 168 min.
- HEAT tool versions after 2017 (5.x) may refine these; the [Frontiers 2023 10-year review](https://doaj.org/article/7180524431314be7b5ad70b2a4ce740c) gives context. A "2023 methods update" with different RR or cap values is **unverified**. We use the 2017 primary table.

### 1.2 Baseline mortality, US ages 20–74

2023 age-specific death rates per 100k from [NCHS Data Brief 521, *Mortality in the US, 2023*](https://www.cdc.gov/nchs/products/databriefs/db521.htm):

| Age group | Deaths per 100k |
|---|---|
| 15–24 | 76.8 |
| 25–34 | 148.1 |
| 35–44 | 237.3 |
| 45–54 | 411.8 |
| 55–64 | 899.6 |
| 65–74 | 1,809.6 |

- Totals: 3.09M deaths; age-adjusted rate 750.5.
- (derived) The population-weighted crude rate for ages 20–74 is **~590 per 100k (0.0059/yr)**.
  - This uses the 15–24 rate for 20–24, which understates slightly.
  - The population weights are approximate 2023 Census age counts from memory (21.9, 45.5, 44.0, 40.6, 42.0 and 34.0M), so they are **unverified**.
  - Replace this with a CDC WONDER query for ages 20–74, preferably for San Francisco County. SF's age-adjusted mortality is likely below the US figure (unverified).

### 1.3 Value of a Statistical Life (USDOT)

| Base year | VSL | Source |
|---|---|---|
| 2022 | $12.5M | [USDOT VSL guidance page](https://www.transportation.gov/office-policy/transportation-policy/revised-departmental-guidance-on-valuation-of-a-statistical-life-in-economic-analysis) (table, via search summary) |
| 2023 | $13.2M | same; [USCG/DHS 2023 memo](https://www.dco.uscg.mil/Portals/9/CG-5R/VSL%202023%202May23%20FINAL%20for%20DIST.pdf) |
| 2024 | $13.7M | same; [USCG 2024 memo](https://dco.uscg.mil/Portals/9/VSL%202024%209May24%20FINAL%20for%20DIST.pdf) |
| **2025** | **$14.2M** | [USDOT VSL guidance page](https://www.transportation.gov/office-policy/transportation-policy/revised-departmental-guidance-on-valuation-of-a-statistical-life-in-economic-analysis); [USDOT Economic Values](https://www.transportation.gov/regulations/economic-values-used-in-analysis) |

USDOT updates the VSL annually for prices and real income using its 2013 methodology ([2021 transmittal memo](https://www.dco.uscg.mil/Portals/9/USDOT%20VSL%20Update%202021%20-%20Transmittal%20Memo.pdf)). We could not fetch the USDOT pages directly (HTTP 403); the values come from search excerpts of those pages.

### 1.4 Crash costs

**USDOT BCA Guidance 2025 Update II, KABCO values (2023$)**, as reproduced in an [NCDOT BCA technical memo](https://connect.ncdot.gov/resources/LBIP2026-I95US301/Documents/BCA%20Technical%20Memorandum.pdf) that cites the [USDOT guidance PDF](https://www.transportation.gov/sites/dot.gov/files/2024-11/Benefit%20Cost%20Analysis%20Guidance%202025%20Update%20%28Final%29.pdf):

| Severity | $ per person (2023$) |
|---|---|
| K (killed) | **$13,200,000** |
| A (incapacitating) | **$1,254,700** |
| B (non-incapacitating) | **$246,900** |
| C (possible injury) | **$118,000** |
| O (no injury) | **$5,300** |
| U (injured, severity unknown) | $229,800 |
| PDO crash (per crash) | $9,500 |
| Injury crash (per crash) | $329,500 |
| Fatal crash (per crash) | $14,806,000 |

**National totals.**
- NHTSA 2023: **40,901 deaths** and **1.26 deaths per 100M VMT**. [NHTSA 2023 overview](https://crashstats.nhtsa.dot.gov/Api/Public/Publication/813705); [NHTSA](https://www.nhtsa.gov/node/138971)
- Blincoe et al. 2023 (NHTSA, 2019 data): **$340B economic cost**, about **$1.4T total societal harm** including quality of life, from 36,500 deaths and 4.5M injuries. [NHTSA press release](https://www.nhtsa.gov/press-releases/traffic-crashes-cost-america-billions-2019); [DOT HS 813 403](https://crashstats.nhtsa.dot.gov/Api/Public/ViewPublication/813403.pdf)

**Per-VMT crash cost (derived).**
- Fatalities only: 1.26e-8 × $13.2M = **$0.17/VMT**.
- All severities: Blincoe's ~$1.4T ÷ ~3.2–3.3T VMT (US VMT figure unverified) = **~$0.43/VMT**.
- A per-mile figure from VTPI/Litman was not retrieved.

### 1.5 CO2 and carbon cost

- **EPA: 400 g CO2 per mile** for a typical gasoline passenger vehicle (22.2 mpg; 8,887 g CO2/gal). Older EPA versions said 404 g. [EPA](https://www.epa.gov/greenvehicles/greenhouse-gas-emissions-typical-passenger-vehicle)
- **EPA 2023 SC-GHG report:** SC-CO2 for 2020 emissions is **$190/t (2% discount rate, 2020$)**. Range: **$120 at 2.5%** to **$340 at 1.5%**. About $240 in 2026$. [RFF primer](https://www.rff.org/publications/reports/adopting-the-social-cost-of-carbon-for-state-benefit-cost-analysis-a-primer-for-practitioners/); [costofcarbon.org table](https://costofcarbon.org/epa-values-for-the-social-cost-of-greenhouse-gases)
- **Policy status:** **E.O. 14154 (Jan 20, 2025)** disbanded the federal IWG and withdrew its SC-GHG guidance, so federal agencies no longer use these values ([CRS IF12916](https://www.everycrsreport.com/reports/IF12916.html); [AIP](https://www.aip.org/fyi/trump-reverses-climate-policies-on-first-day-in-office)). EPA's own 2023 estimates remain the best available science-based figure, and several states use them (RFF). We present carbon value as a separately labelled line.

### 1.6 Air-pollution damage costs

- **USDOT BCA 2025 Update II (2023$, per metric ton, emissions in 2030–2053):** **NOx $20,900; SOx $56,800**. PM2.5 is printed as "$1,04,100" in the NCDOT memo, so the exact value is unclear (unverified; likely about $1.04M). [NCDOT memo](https://connect.ncdot.gov/resources/LBIP2026-I95US301/Documents/BCA%20Technical%20Memorandum.pdf)
- **EPA sector benefit-per-ton, 2025, internal combustion engines:** direct PM2.5 **$167,000**, SO2 $38,800, NOx $10,800. [EPA BenMAP](https://www.epa.gov/benmap/sector-based-pm25-benefit-ton-estimates)
- **A $/VMT air-pollution figure (VTPI/Litman, EPA) was not retrieved, so it is unverified.** Converting would need fleet g/mi emission factors (e.g. EPA MOVES) that we did not source.

### 1.7 Integrated health impact assessments (validation anchors)

- **Barcelona superblocks** (Mueller et al. 2020, *Environment International*, doi 10.1016/j.envint.2019.105132). Implementing **503 superblocks** could prevent about **667 premature deaths/yr** (95% CI 235–1,098):
  - NO2: 291
  - noise: 163
  - heat: 117
  - green space: 60
  - **physical activity: 36**
  - The plan adds about 200 days of life expectancy and is worth **about €1.7B/yr**.
  - [UAB record](https://ddd.uab.cat/record/284134); [ACU research bank](https://acuresearchbank.acu.edu.au/items/40dad34b-5ebf-406b-a836-a29433e5284f); [ISGlobal](https://2020.isglobal.org/an-award-winning-study-on-a-life-saving-plan/)
  - **Takeaway: in a dense city, avoided pollution, noise and heat can exceed the physical-activity benefit.**
- **Woodcock et al. 2009, *Lancet*** (ITHIM, London 2030). Increased active travel plus less driving saves **7,332 DALYs per million population per year**, versus **160** for low-emission vehicles alone and **7,439** combined. The gain is mostly from fewer ischaemic heart disease deaths. [Oxford ORA](https://ora.ox.ac.uk/objects/uuid:d51885a7-b4ca-4513-985c-be6345861f0d); [LSHTM](https://researchonline.lshtm.ac.uk/4468)

---

## 2. How our model uses it

| Parameter key | Recommended value (range) | Basis |
|---|---|---|
| `heat_walk_rr` | **0.89** (CI 0.83–0.96) | HEAT 2017 Table 1 |
| `heat_walk_ref_min_per_week` | **168** | HEAT 2017 (at 4.8 km/h) |
| `heat_walk_rr_cap` | **0.30** max risk reduction (≈460 min/wk) | HEAT 2017 |
| `us_crude_mortality_20_74` | **0.0059/yr** (range 0.0050–0.0065) | Derived from NCHS 2023 age-specific rates with approximate population weights. Replace with a WONDER pull. |
| `vsl_usd` | **$14.2M** (2025 base; $13.7M for a 2024 base) | USDOT |
| `crash_cost_usd_per_vmt` | **$0.20** (range $0.17 fatal-only to $0.43 all-severity) | Derived from NHTSA 2023 rate × USDOT K value, and Blincoe societal harm ÷ VMT |
| `co2_kg_per_vmt` | **0.400** | EPA |
| `scc_usd_per_tonne` | **$190** (2020$; range $120–$340; ≈$240 in 2026$) | EPA 2023 SC-GHG (federally withdrawn 2025; shown as a separate line) |

**Walking health value per agent per year:**
- Value = ΔRiskReduction × `us_crude_mortality_20_74` × `vsl_usd`, for agents aged 20–74.
- ΔRiskReduction = min(0.30, 0.11 × Δmin_week / 168).
- Example (derived): +30 min/week gives 0.0196 × 0.0059 × $14.2M ≈ **$1,640/person/yr** at full effect.
- We ramp benefits 20% per year in multi-year views (HEAT lag). The single-year "City Value" uses the steady state and is labelled as such.

**Avoided-driving value:**
- Value = ΔVMT × (`crash_cost_usd_per_vmt` + `co2_kg_per_vmt` / 1000 × `scc_usd_per_tonne` + an air-pollution term).
- (derived) The CO2 term is 0.4 kg × $190/t = **$0.076/VMT**.
- The air-pollution term is left as an unverified placeholder until we source per-mile emission factors.

**Validation.** Superblocks and ITHIM show physical activity is a minority of total health benefit in dense cities. If our walking term dominates the City Value, we flag it in the UI.

## 3. Limitations

- **HEAT is European and population-level.** Its RR comes mostly from leisure and commute walking cohorts. Applying it to individual agents is a convenience, not its intended use.
- **Substitution.** HEAT assumes new walking adds to total activity. Agents who swap gym time for walking get overstated benefits.
- **Mortality rate.** US-wide and derived. SF and FiDi commuters are likely healthier and higher-income, which would lower the benefit.
- **VSL is US-federal.** HEAT's own guidance recommends a local VSL. The USDOT value is the appropriate US choice.
- **Crash risk to new pedestrians** (HEAT has an injury module) is not modelled. Pedestrianised streets reduce exposure, but walking elsewhere may raise it.
- **Carbon value is policy-contested** in the US since E.O. 14154.
- Not retrieved: a HEAT 5.x (2023) parameter table, the full USDOT 2025 BCA PDF (HTTP 403), VTPI per-mile costs, and a CDC WONDER 20–74 crude rate. The web-search budget ran out before population weights could be sourced.

## 4. Sources

- WHO HEAT methods guide 2017 (Kahlmeier et al.): https://www.rsu.lv/sites/default/files/book_download/heat.pdf
- HEAT 10-year review (Frontiers 2023): https://doaj.org/article/7180524431314be7b5ad70b2a4ce740c
- NCHS Data Brief 521: https://www.cdc.gov/nchs/products/databriefs/db521.htm
- USDOT VSL guidance: https://www.transportation.gov/office-policy/transportation-policy/revised-departmental-guidance-on-valuation-of-a-statistical-life-in-economic-analysis ; https://www.transportation.gov/regulations/economic-values-used-in-analysis
- USCG VSL memos: https://dco.uscg.mil/Portals/9/VSL%202024%209May24%20FINAL%20for%20DIST.pdf ; https://www.dco.uscg.mil/Portals/9/CG-5R/VSL%202023%202May23%20FINAL%20for%20DIST.pdf
- USDOT BCA Guidance 2025: https://www.transportation.gov/sites/dot.gov/files/2024-11/Benefit%20Cost%20Analysis%20Guidance%202025%20Update%20%28Final%29.pdf (values via NCDOT memo: https://connect.ncdot.gov/resources/LBIP2026-I95US301/Documents/BCA%20Technical%20Memorandum.pdf)
- NHTSA 2023 overview: https://crashstats.nhtsa.dot.gov/Api/Public/Publication/813705
- Blincoe et al. 2023: https://crashstats.nhtsa.dot.gov/Api/Public/ViewPublication/813403.pdf ; https://www.nhtsa.gov/press-releases/traffic-crashes-cost-america-billions-2019
- EPA typical vehicle emissions: https://www.epa.gov/greenvehicles/greenhouse-gas-emissions-typical-passenger-vehicle
- EPA SC-GHG (via RFF, costofcarbon.org): https://www.rff.org/publications/reports/adopting-the-social-cost-of-carbon-for-state-benefit-cost-analysis-a-primer-for-practitioners/ ; https://costofcarbon.org/epa-values-for-the-social-cost-of-greenhouse-gases
- E.O. 14154 / CRS: https://www.everycrsreport.com/reports/IF12916.html
- EPA BenMAP benefit-per-ton: https://www.epa.gov/benmap/sector-based-pm25-benefit-ton-estimates
- Mueller et al. 2020: https://ddd.uab.cat/record/284134
- Woodcock et al. 2009: https://ora.ox.ac.uk/objects/uuid:d51885a7-b4ca-4513-985c-be6345861f0d
