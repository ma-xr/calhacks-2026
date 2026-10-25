# Kastle Back to Work Barometer (office occupancy)

## What it is
A weekly index of office occupancy across 10 U.S. metros, built from badge entries into buildings that use Kastle Systems access control. Each value is a percentage of the pre-COVID baseline. It is the de facto public proxy for return-to-office.

## Publisher & URL
| Item | Value |
|---|---|
| Publisher | Kastle Systems |
| Barometer page | https://www.kastle.com/safety-wellness/getting-america-back-to-work/ |
| Cadence | Weekly. Each week runs Thursday–Wednesday, and reports usually come out on Wednesdays (per the page) |
| Cities | Austin, Chicago, Dallas, Houston, Los Angeles, New York, Philadelphia, San Francisco, San Jose, Washington DC |

## License / terms
Proprietary. Only the headline percentages are public. Kastle doesn't publish downloadable series, and it shares data for other markets only "with government and nonprofit organizations and partners" (per the page). Cite it and don't redistribute any scraped series. Site Terms: linked from the page footer (not checked).

## Methodology (from the Barometer page)
| Aspect | Detail |
|---|---|
| Raw data | Anonymized keycard, fob and mobile-app access events from **300,000+ Kastle users in 10 cities** |
| Counting | Only each person's **first building entry each day** counts, so multiple swipes aren't overcounted |
| Index | Unique authorized entries ÷ baseline, averaged weekly |
| Baseline (100%) | Average weekly first-swipe activity over a **three-week window in February 2020**. This is normal peak occupancy, not capacity, so values can go above 100%. |
| Representativeness | "Not a national statistical sample". Only buildings that are Kastle customers are included. |

## Fields we use
- SF weekly average %, SF peak-day %, 10-city average, and the Class A+ index (a national figure, not per city).

## How the model uses it
| Module | Use |
|---|---|
| Population | Daily share of LODES/WAC office jobs that physically show up: `attend_prob ≈ Kastle_SF × (Feb-2020 attendance ≈ 1)`. Make it vary by weekday, with Tue–Thu peaks. |
| Scenarios | "RTO mandate" lever: raise the SF index toward the 10-city average or the Class A+ level |
| Validation | Simulated daily office entries in bbox vs Kastle SF × baseline workers |

## Caveats
- **Selection bias.** Only Kastle-secured buildings count, which skews toward multi-tenant Class A/B offices. Coverage of SF towers is not public. Owner-occupied tech HQs with their own security (Salesforce, Meta, etc.) are likely excluded (unverified).
- It is metro-wide (SF metro), not FiDi-specific.
- The baseline is Feb 2020, not capacity, so 50% does not mean half the desks are full.
- Badge-free entry (tailgating, lobby guards) is missed.
- Holidays and weather produce dips from one week to the next. Smooth over 4+ weeks.

## Key numbers
| Metric | Value | Date | Source |
|---|---|---|---|
| **SF weekly occupancy** | **47.2%** (−0.5 pts week over week) | Week including Tue 13 Oct 2026 (latest on page as of 2026-10-24) | https://www.kastle.com/safety-wellness/getting-america-back-to-work/ |
| 10-city average | 55.1% (down from 56.0%) | same week | same |
| Peak day, all buildings (10-city) | Tuesday, 64.4% (down from 68.8%) | same week | same |
| Class A+ national average | 76.2%; peak day Tue 13 Oct at 91.8% | same week | same |
| Other cities, same week | San Jose 46.2%, LA 47.5%, Philadelphia 41.7%, Chicago 56.2%, DC 51.4%, NYC 66.3%, Dallas 65.7%, Austin 70.8% | same week | same |
| SF early-2025 context | "office attendance at 40% to 45% of pre-pandemic levels" | ~2024–25 | SFCTA Downtown Travel Study exec summary (May 2025), https://www.sfcta.org/sites/default/files/2025-05/Downtown_Travel_Study_FINAL_Report_2025-05-22_Executive_Summary.pdf |
| SF Sep 2022 | 39% (secondary report) | late Sep 2022 | https://californiaglobe.com/tag/kastle/ (unverified against Kastle) |

**Suggested parameter:** SF office attendance factor of about **0.47** for an average weekday in Oct 2026. Tuesday–Wednesday should be higher. The SF peak-day value wasn't published, so use roughly the 10-city peak/average ratio, 64.4/55.1 ≈ 1.17, which gives about 0.55 on Tuesday (our inference, unverified for SF).
