# American Community Survey (ACS)

## What it is
The Census Bureau's continuous household survey. We use it for commute mode, departure and arrival times, travel time, vehicles, income and household size. It comes in two kinds of tables:
- **Residence geography** (B08 0xx–3xx): where workers live.
- **Workplace geography** (B08 4xx–6xx): where people work.

## Publisher & URL
| Item | Value |
|---|---|
| Publisher | U.S. Census Bureau |
| API | `https://api.census.gov/data/{year}/acs/{acs1|acs5}?get=...&for=...&in=...&key=KEY` |
| Latest vintages | **2024 ACS 1-year and 2020–2024 ACS 5-year** are live. `/data/2024/acs/acs5` and `/acs1` return 200; `/data/2025/...` returns 404 (checked 2026-10-24) |
| Browser | https://data.census.gov |
| Keyless mirror (handy for quick checks) | Census Reporter API, e.g. `https://api.censusreporter.org/1.0/data/show/acs2024_5yr?table_ids=B08301&geo_ids=05000US06075` |

**API key needed:** a keyless call to api.census.gov now returns a 302 redirect to `missing_key.html` with header `X-DataWebAPI-KeyError: 1` (tested 2026-10-24). Get a free key at https://api.census.gov/data/key_signup.html.

## License / terms
Public domain (U.S. government work). API Terms of Service: https://www.census.gov/data/developers/about/terms-of-service.html. Cite as "U.S. Census Bureau, ACS 2020–2024 5-year, Table X".

## Key tables (titles checked via Census Reporter table metadata)
| Table | Title | Universe | Geography notes |
|---|---|---|---|
| B08301 | Means of Transportation to Work | Workers 16+ | Residence. Down to block group (5-yr) |
| B08302 | Time of Departure to Go to Work (the "time leaving home" table) | Workers 16+ not WFH | Residence |
| B08303 | Travel Time to Work | Workers 16+ not WFH | Residence |
| B08014 | Sex of Workers by Vehicles Available | Workers 16+ in households | Residence |
| B08141 | Means of Transportation by Vehicles Available | Workers 16+ in households | Residence |
| B19013 | Median Household Income (2024 $) | Households | Residence |
| B25010 | Average Household Size by Tenure | Occupied units | Residence |
| **B08601** | Means of Transportation to Work for Workplace Geography | Workers 16+ | **Workplace. County/place only**: a tract request for B08601 returned nothing |
| B08602 | Time Arriving at Work for Workplace Geography | Workers 16+ not WFH | Workplace |
| B08603 | Travel Time to Work for Workplace Geography | Workers 16+ not WFH | Workplace |
| B08406 | Sex of Workers by Means for Workplace Geography | Workers 16+ | Workplace |
| B08519 | Means by Workers' Earnings, Workplace Geography | Workers 16+ with earnings | Workplace |
| B08532 | Means by Time Arriving at Work, Workplace Geography | Workers 16+ not WFH | Workplace |
| B08130 | Means of Transportation by Place of Work (State and County Level) | Workers 16+ | Residence × work county |

For **tract-level workplace** mode share, use CTPP (Census Transportation Planning Products, AASHTO), https://ctpp.transportation.org. The 2017–2021 CTPP is the latest (unverified).

## 5-year vs 1-year
| | 1-year | 5-year |
|---|---|---|
| Geography | Areas with 65k+ people (SF county and city qualify) | Every geography down to block group |
| Recency | 2024 | Pooled 2020–2024, which includes COVID-era 2020–2021 |
| Use for | County-level shares in the current WFH regime | Tract detail in bbox (accept the pandemic blend) |

## How the model uses it
| Module | Use |
|---|---|
| Population | Resident agents in bbox tracts: count, household size (B25010), income (B19013), cars (B08014) |
| Mode choice | Priors for resident (B08301) and in-commuter (B08601) mode shares. Fit alternative-specific constants to these. |
| Departure schedule | B08602 workplace arrival distribution for SF sets the agent arrival-time distribution |
| Validation | Simulated travel-time distribution vs B08303 and B08603 |

## Caveats
- Commute questions cover "last week, usually". They miss non-work trips and hybrid day-to-day variation. WFH means the main mode last week was WFH.
- Margins of error are large at tract level. Our bbox tracts have about 500–3,600 workers each.
- 5-yr 2020–2024 mixes peak-pandemic years. The 1-yr figures better reflect 2024.
- Workplace tables (B086xx) only go down to county/place, not to FiDi itself.

## Key numbers
### SF County (06075), ACS 2024 1-year
Source: Census Reporter API, `acs2024_1yr`, B08301/B08601/B19013/B25010.

| Mode | Residents (B08301), n=468,430 | People working in SF (B08601), n=632,129 |
|---|---|---|
| Drove alone | 142,260 (30.4%) | 224,109 (35.5%) |
| Carpool | 27,865 (5.9%) | 45,066 (7.1%) |
| Public transit | 117,279 (25.0%) | 181,920 (28.8%) |
| …bus / subway-elevated / commuter rail / light rail / ferry | 77,526 / 26,029 / 5,707 / 7,555 / 462 | 81,311 / 65,536 / 19,006 / 8,745 / 7,322 |
| Bicycle | 17,838 (3.8%) | 17,403 (2.8%) |
| Walked | 46,917 (10.0%) | 45,522 (7.2%) |
| Worked from home | 100,347 (21.4%) | 100,347 (15.9%) |
| **Commuters only, excluding WFH** | — | n=531,782: drive alone 42.1%, transit 34.2%, carpool 8.5%, walk 8.6%, bike 3.3% (our arithmetic) |

- Median household income, SF 2024 1-yr: **$139,801** (B19013).
- Average household size: **2.14** overall; 2.51 owner, 1.93 renter (B25010).

### Arrival time at SF workplaces (B08602, 2020–2024 5-yr, n=477,072)
| Before 7:00 | 7:00–7:59 | 8:00–8:59 | 9:00–9:59 | 10:00–11:59 | 12:00–15:59 | 16:00–23:59 |
|---|---|---|---|---|---|---|
| 15.7% | 18.5% | 27.9% | 18.5% | 8.8% | 6.1% | 4.5% |

### Bbox resident tracts, ACS 2020–2024 5-yr (B08301/B19013/B25010)
These are the 14 FiDi/SoMa/Rincon/South Beach tracts intersecting the bbox: 0611.01–.02, 0615.01–.08, 0176.02, 0178.01, 0178.04, 0180. Tracts were found with a TIGERweb envelope query. The 0611 tracts lie on the Chinatown edge.

| Aggregate | Value |
|---|---|
| Population (B01003) | 37,251 |
| Workers 16+ | 23,178 |
| Drove alone / carpool / transit / bike / walk / WFH | 14.9% / 1.5% / 15.4% / 2.9% / 28.2% / 33.0% |
| Tract median HH income range | $24k (0611.01) to $250k+ (0615.05, 0615.06) |
| Tract avg HH size range | 1.34–2.15 |
