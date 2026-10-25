# Congestion Modeling: Link Performance, Capacity, Free-Flow Speed, Equilibrium and Replanning

This file sets how link travel time responds to volume (volume-delay function, VDF), what capacity and free-flow speed downtown SF links should have, and why we reach equilibrium through MATSim-style replanning "settle days".

Status legend: **verified** = read in primary file or text. **secondary** = abstract or reputable summary. **(unverified)** = not confirmed.

---

## 1. Key findings

### 1.1 BPR function and alternatives

**BPR (Bureau of Public Roads, 1964, *Traffic Assignment Manual*):**

  t = t₀ · [1 + α · (V/C)^β], with the classic **α = 0.15, β = 4**.

- **Capacity caveat:** the 0.15/4 values were fitted with **"practical capacity"**, which is roughly 80% of true capacity. Using them with true (HCM) capacity underestimates congestion. The fix is to scale capacity by about 0.8, or to raise α (Boyles, Lownes & Unnikrishnan, *Transportation Network Analysis* Vol. I, [arXiv:2502.05182](https://arxiv.org/pdf/2502.05182)) (secondary).
- **Range used in practice:** β values from **2 to 12** appear in applied models, citing Spiess (1990) ([ANPET paper](https://anpet.emnuvens.com.br/anpet/article/download/936/569/4593)) (secondary). One Brazilian bridge calibration found α = 0.21, β = 3.82 (same source).
- **Conical VDF** (Spiess 1990, *Transportation Science* 24(2):153–158, [IDEAS](https://ideas.repec.org/a/inm/ortrsc/v24y1990i2p153-158.html)):
  - Designed to fix BPR drawbacks: it underestimates delay at low V/C, explodes numerically at high β, and gives no positive slope near zero flow.
  - Form: t = t₀·[2 + √(a²(1−x)² + b²) − a(1−x) − b], with b = (2a−1)/(2a−2) and x = V/C.
  - It matches a BPR of exponent a at x = 1 (secondary).

**MTC Travel Model One (TM1) VDFs (verified, [`SpeedFlowCurve.block`](https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/scripts/block/SpeedFlowCurve.block)):**

| Facility (FT) | Function |
|---|---|
| Freeway-to-freeway (1), freeway (2), managed freeway (8), special facility (9) | **"BPR variation"**: TC = T₀·(1 + 0.20·((V/C)/0.75)^6). In standard BPR terms this is **α ≈ 1.12, β = 6** (our algebra: 0.20/0.75⁶), so it is far steeper than 0.15/4 |
| Expressway (3), collector (4), ramp (5), **major arterial (7)**, toll plaza (10) | **Akcelik curve**: TC = 60·[L/FFS + 0.25·((x−1) + √((x−1)² + 16·J·x·L²))]. The delay parameter J is derived from a per-capclass "critical speed" ([`FreeFlowSpeed.block`](https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/scripts/block/FreeFlowSpeed.block)) |
| Centroid connectors (6) | Fixed time |

- Critical speeds for downtown arterials: **7.06 mph** for regional-core arterials (capclass 07) and **9.42 mph** for CBD arterials (capclass 17) ([`FreeFlowSpeed.block`](https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/scripts/block/FreeFlowSpeed.block)).
- **Answer to "what does MTC TM1 use?":** BPR-like α≈1.12/β=6 on freeways, and **Akcelik (not BPR) on urban arterials and collectors**.
- The claim that some MPOs use "α 0.8–1.0, β 5–10 for arterials" is **(unverified)**. The nearest verified data point is TM1's freeway curve above.

### 1.2 Capacity

**HCM signalized capacity**

- Base saturation flow **s₀ = 1,900 pc/h/ln**. The base case is a 12-ft lane with no heavy vehicles, flat grade, no parking, no buses, and no turns.
- Lane-group capacity is **c = s · g/C**.
- **Default g/C** (through movements): **0.45 for arterials, 0.40 for collectors** ([FHWA HPMS Field Manual, Appendix N](https://www.fhwa.dot.gov/ohim/hpmsmanl/appn5.cfm), verified).
- Implied unadjusted arterial capacity ≈ **1,900 × 0.45 ≈ 855 vph/lane**; collector ≈ **760**. These are our arithmetic.
- Local calibration studies report sat flows as low as 1,200–1,800 ([INDOT summary](https://secure.in.gov/indot/files/Sources-of-Information-on-Capacity.pdf); [WVU thesis](https://researchrepository.wvu.edu/etd/1626)) (secondary).

**TM1 per-lane hourly capacity and free-flow speed** (verified, [`SpeedCapacity_1hour.block`](https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/scripts/block/SpeedCapacity_1hour.block))

- CAPCLASS = 10·AT + FT ([MTC network lookup tables](https://github.com/BayAreaMetro/modeling-website/wiki/MasterNetworkLookupTables)).
- Area type **AT 0 = "Regional core"** applies to density index > 300; **AT 1 = CBD** to 100–300. FiDi and upper SoMa are AT 0 or 1.

| Facility | AT 0 Regional core: cap (vphpl) / FFS (mph) | AT 1 CBD: cap / FFS | AT 2 Urban business: cap / FFS |
|---|---|---|---|
| Freeway (2) | 2,050 / 55 | 2,050 / 55 | 2,100 / 60 |
| Expressway (3) | 1,450 / 40 | 1,450 / 40 | 1,600 / 45 |
| **Major arterial (7)** | **900 / 20** | **950 / 25** | 1,000 / 30 |
| **Collector (4)** | **600 / 10** | **650 / 15** | 700 / 20 |
| Freeway ramp (5) | 1,450 / 30 | 1,500 / 30 | 1,550 / 35 |
| Fwy-fwy connector (1) | 1,850 / 40 | 1,850 / 40 | 1,950 / 45 |

- TM1 multiplies hourly capacity by period length ("capfac" = 3–8 hours) ([`HwyAssign.job`](https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/scripts/assign/HwyAssign.job)).
- **Cross-check:** TM1's 900–950 vphpl for downtown arterials agrees with HCM s₀ × g/C ≈ 855 vphpl.
- **SF DTA (SFCTA/Dynameq, 2012):** calibrators added a **pedestrian-friction reduction** to turning saturation flows, applied only in AT 0–1. Their reason: in downtown, "turning vehicles must wait for a herd of pedestrians". Response times of 1.0–1.25 s were tested ([SF DTA Final Calibration & Validation Report](https://www.sfcta.org/sites/default/files/2019-03/SFDTAFinalCalibrationandValidationReport.pdf), verified).

### 1.3 Free-flow speed and legal limits in SF

- **California prima facie limit:** 25 mph in business and residence districts (CVC §22352, [leginfo](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=VEH&sectionNum=22352)). Not re-fetched this session.
- **AB 43 (2021):** lets SF set **20 mph** on business-activity districts, safety corridors, and High Injury Network streets. Phase 1 took effect Jan 2022 ([SFMTA blog](https://www.sfmta.com/blog/new-law-brings-safer-speed-limits-san-francisco)). We did not find a list naming FiDi streets, so FiDi-specific 20 mph segments are **(unverified)**.
- **SFMTA evaluation:** the reductions "had little effect on vehicle speeds", because most drivers were already at or below the limit ([SFMTA evaluation](https://www.sfmta.com/media/35591/download)) (secondary).
- **TM1 coded FFS for downtown arterials:** 20 mph (core) and 25 mph (CBD); collectors 10–15 mph (see the table above). These already embed signal and stop delay at free flow.
- **SF DTA calibration:** lowered FFS on locals and collectors to account for stop-sign acceleration and deceleration ([SF DTA report](https://www.sfcta.org/sites/default/files/2019-03/SFDTAFinalCalibrationandValidationReport.pdf)).

### 1.4 Equilibrium concepts

- **Wardrop's first principle (user equilibrium, 1952):** no traveller can lower their own cost by switching route; all used routes have equal, minimal cost (Wardrop, *Proc. ICE* Part II 1(3):325–378). Standard textbook statement in Sheffi (1985), *Urban Transportation Networks* (MIT, free PDF: http://web.mit.edu/sheffi/www/selectedMedia/sheffi_urban_trans_networks.pdf; link not re-checked).
- **TM1 static UE convergence:** relative gap **0.0005** (up to 1,000 iterations) in most periods, and **0.003** (100 iterations) in others ([`HwyAssign.job`](https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/scripts/assign/HwyAssign.job)).
- **Method of successive averages (MSA):** flows (or scores) are averaged with step 1/n over iterations. This guarantees convergence for stochastic or simulation-based loading (Sheffi 1985). MATSim recommends MSA score averaging once innovation is switched off ([MATSim book, §4.5.3](https://doi.org/10.5334/baw)).
- **Dynamic traffic assignment (DTA):** time-dependent loading with queue spillback (e.g. Dynameq's triangular fundamental diagram: FFS, saturation flow, jam density, backward wave speed). SF built one for downtown ([SF DTA report](https://www.sfcta.org/sites/default/files/2019-03/SFDTAFinalCalibrationandValidationReport.pdf)).

### 1.5 MATSim co-evolutionary replanning

Horni, Nagel & Axhausen (eds.) 2016, *The Multi-Agent Transport Simulation MATSim*, Ubiquity Press, open access, [doi:10.5334/baw](https://doi.org/10.5334/baw). Verified from the book text.

| Element | Value or behaviour |
|---|---|
| Loop | Plan selection → mobsim (network loading) → scoring → replanning, repeated over iterations |
| Innovation share | "A certain share of the agents (often **10%**)" clone and mutate a plan each iteration (Ch. 1). The tutorial config has **10% ReRoute**, 90% select an existing plan (Ch. 4) |
| Plan memory | `maxAgentPlanMemorySize` = **5** in the example. The worst plan is dropped |
| Selection | `ChangeExpBeta` / `SelectExpBeta` = MNL over remembered plans, scale `BrainExpBeta` (recommend **1.0**). `BestScore` "tends to get stuck"; avoid it alone |
| Convergence | Switch off innovation late (`fractionOfIterationsToDisableInnovation`), combined with **MSA score averaging** |
| Default scoring (Charypar–Nagel) | β_perf = **+6 utils/h**, β_trav = **−6 utils/h**, β_late = **−18 utils/h**, β_money = 1. The guide: set β_perf to the car travel-time prefactor of your mode-choice model if you have one |
| Example practice | Melbourne MATSim: 200 iterations, innovation disabled for the final 20% ([AToM, arXiv:2112.12071](https://arxiv.org/pdf/2112.12071)) |

---

## 2. How our model uses it

| Parameter key | Adopted value | Range for sensitivity | Basis |
|---|---|---|---|
| `bpr_alpha` | **0.15**, applied to **practical capacity** = 0.8 × `lane_capacity_vph` | 0.15–1.12 (1.12 = TM1 freeway-equivalent) | BPR 1964 via [Boyles et al.](https://arxiv.org/pdf/2502.05182); [TM1 SpeedFlowCurve](https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/scripts/block/SpeedFlowCurve.block) |
| `bpr_beta` | **4** | 4–6 | same |
| `lane_capacity_vph` | **900** per lane per hour for downtown arterials (TM1 regional-core FT7); **600** for collectors and alleys | Arterial 855 (HCM 1,900 × 0.45) to 950 (TM1 CBD). Apply about −10% at intersections with heavy pedestrian turning conflict | [TM1 SpeedCapacity](https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/scripts/block/SpeedCapacity_1hour.block); [HPMS App. N](https://www.fhwa.dot.gov/ohim/hpmsmanl/appn5.cfm); SF DTA ped friction. The −10% size is our assumption (unverified) |
| `urban_free_flow_speed_kmh` | **32** (20 mph, TM1 regional-core arterial, includes signal delay) | 24 (15 mph collectors) to 40 (25 mph posted, TM1 CBD) | [TM1](https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/scripts/block/SpeedCapacity_1hour.block); CVC 22352 |

**Why we use replanning "settle days" instead of a one-shot UE solve:**

1. **Heterogeneous agents.** Each agent carries its own VOT, mode set, and schedule (shops, meetings). That is MATSim's agent-plan memory, which static UE cannot represent.
2. **Joint choice.** Route, mode, and departure time co-adapt in one loop. A pedestrianization changes routes on day 1 and modes over later days, which is how evaporation emerges (see `traffic-evaporation-and-induced-demand.md`).
3. **Interpretable dynamics.** Users see Plan vs Baseline traffic "settling" over days, mirroring the short-run vs long-run elasticities (Goodwin's −0.5 to −1.0).

**Our recipe:**

- Each day, about **10%** of agents innovate: re-route on the last day's congested times, and/or re-evaluate mode.
- Everyone else picks among up to 5 remembered plans by **ChangeExpBeta** (MNL, β = 1).
- Innovation is switched off for the final 20% of days, and scores are MSA-averaged.
- **Convergence check:** day-over-day change in total car VHT < 1–2%, and plan-score change near zero. That threshold is our choice and is not taken from a source.

**Link-time computation:** t = t₀·(1 + 0.15·(V/(0.8·C))^4), where t₀ = length / FFS and C = lanes × 900 vph. Gateway links (I-80/Bay Bridge ramps) use the freeway capacity of 2,050 vphpl and could use TM1's steeper α≈1.12/β=6 curve.

---

## 3. Limitations

- **Static BPR has no queues or spillback.** Downtown gridlock, where blocked intersections propagate upstream, needs DTA or queue models. SF DTA calibration runs "devolved into gridlock" without careful tuning. BPR also lets V/C exceed 1 without physical storage limits.
- **Akcelik vs BPR.** TM1 uses Akcelik for arterials because it handles signalized delay better near and above capacity. Our BPR choice is a simplification.
- **Capacity is set by signal timing,** which we do not model per intersection. The g/C defaults (0.45) are national, not SFMTA timing plans.
- **Pedestrianization changes intersection capacity on crossing streets** (fewer conflicting phases could raise g/C). We do not capture that unless we adjust C manually.
- **Speed limits vs operating speeds.** Free-flow speeds should come from observed off-peak speeds (SF DTA used over 500 speed surveys), not posted limits.
- **MATSim's 10% innovation rate and 5-plan memory are conventions,** not behavioural estimates. The number of settle days affects how much evaporation appears.

---

## 4. Sources

1. MTC TM1 `SpeedFlowCurve.block`, `SpeedCapacity_1hour.block`, `FreeFlowSpeed.block`, `HwyAssign.job`. https://github.com/BayAreaMetro/travel-model-one/tree/master/model-files/scripts
2. MTC Master Network Lookup Tables (AT/FT/CAPCLASS). https://github.com/BayAreaMetro/modeling-website/wiki/MasterNetworkLookupTables
3. FHWA HPMS Field Manual, Appendix N (capacity procedures). https://www.fhwa.dot.gov/ohim/hpmsmanl/appn5.cfm
4. Boyles, Lownes, Unnikrishnan, *Transportation Network Analysis* Vol. I. https://arxiv.org/pdf/2502.05182
5. Spiess, H. (1990). Conical volume-delay functions. *Transportation Science* 24(2):153–158. https://ideas.repec.org/a/inm/ortrsc/v24y1990i2p153-158.html
6. SFCTA (2012). SF DTA Final Calibration and Validation Report. https://www.sfcta.org/sites/default/files/2019-03/SFDTAFinalCalibrationandValidationReport.pdf
7. Horni, Nagel, Axhausen (2016). *The Multi-Agent Transport Simulation MATSim*. https://doi.org/10.5334/baw
8. MATSim `RoutingConfigGroup.java` (defaults). https://github.com/matsim-org/matsim-libs/blob/main/matsim/src/main/java/org/matsim/core/config/groups/RoutingConfigGroup.java
9. Sheffi, Y. (1985). *Urban Transportation Networks*. http://web.mit.edu/sheffi/www/selectedMedia/sheffi_urban_trans_networks.pdf
10. Wardrop, J.G. (1952). Some theoretical aspects of road traffic research. *Proc. ICE* Part II 1(3):325–378.
11. California Vehicle Code §22352. https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=VEH&sectionNum=22352
12. SFMTA, AB 43 speed limits. https://www.sfmta.com/blog/new-law-brings-safer-speed-limits-san-francisco · evaluation: https://www.sfmta.com/media/35591/download
13. AToM: Activity-based and agent-based Transport model of Melbourne (MATSim). https://arxiv.org/pdf/2112.12071
