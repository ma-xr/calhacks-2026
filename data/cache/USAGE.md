# External API usage log

| time (UTC) | service | what | approx cost |
|---|---|---|---|
| 2026-10-24T21:43:23+00:00 | LODES | GET https://lehd.ces.census.gov/data/lodes/LODES8/ca/ca_xwalk.csv.gz | free |
| 2026-10-24T21:44:27+00:00 | LODES | GET https://lehd.ces.census.gov/data/lodes/LODES8/ca/wac/ca_wac_S000_JT00_2023.csv.gz | free |
| 2026-10-24T21:51:53+00:00 | census_acs | ACS5 2023 group(B08406) for=county:075 | free (keyed) |
| 2026-10-24T21:51:54+00:00 | census_acs | ACS5 2023 group(B08301) for=county:075 | free (keyed) |
| 2026-10-24T21:51:55+00:00 | census_acs | ACS5 2023 group(B08302) for=county:075 | free (keyed) |
| 2026-10-24T21:51:59+00:00 | census_acs | ACS5 2023 group(B08602) for=county:075 | free (keyed) |
| 2026-10-24T21:52:01+00:00 | census_acs | ACS5 2023 group(B08303) for=county:075 | free (keyed) |
| 2026-10-24T21:52:02+00:00 | census_acs | ACS5 2023 group(B08534) for=county:075 | free (keyed) |
| 2026-10-24T21:52:04+00:00 | census_acs | ACS5 2023 group(B08136) for=county:075 | free (keyed) |
| 2026-10-24T21:52:05+00:00 | census_acs | ACS5 2023 group(B08536) for=county:075 | free (keyed) |
| 2026-10-24T21:52:06+00:00 | census_gazetteer | GET https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_gaz_tracts_06.txt | free |
| 2026-10-24T21:52:08+00:00 | census_acs | ACS5 2023 NAME,B01003_001E,B11001_001E,B19013_001E,B25010_001E,B08201_ for=tract:* | free (keyed) |
| 2026-10-24T21:57:15+00:00 | LODES | GET https://lehd.ces.census.gov/data/lodes/LODES8/ca/od/ca_od_main_JT00_2023.csv.gz | free |
| 2026-10-24T21:59:24+00:00 | datasf | c5ge-t6pj bbox page 0 (1000 rows) | free |
| 2026-10-24T21:59:26+00:00 | datasf | c5ge-t6pj bbox page 1 (1000 rows) | free |
| 2026-10-24T21:59:28+00:00 | datasf | c5ge-t6pj bbox page 2 (207 rows) | free |
| 2026-10-24T21:59:32+00:00 | datasf | fdfd-xptc bbox page 0 (1000 rows) | free |
| 2026-10-24T21:59:37+00:00 | datasf | fdfd-xptc bbox page 1 (1000 rows) | free |
| 2026-10-24T21:59:42+00:00 | datasf | fdfd-xptc bbox page 2 (220 rows) | free |
| 2026-10-24T21:59:45+00:00 | datasf | 3i4a-hu95 bbox page 0 (425 rows) | free |
| 2026-10-24T22:01:32+00:00 | apify | start run t842O99WQClgBGUJs (test) cap $0.5 | <= $0.5 (estimate logged separately) |
| 2026-10-24T22:02:16+00:00 | apify | run t842O99WQClgBGUJs (test) SUCCEEDED, 8 items, dataset gJzqDqgVbbfw5t7BA | actual $0.0482 |
| 2026-10-24T22:02:27+00:00 | apify | ESTIMATE full run: <= 880 places x $0.006 (place $0.004 + details $0.002, FREE tier) = <= $5.28; hard cap maxTotalChargeUsd=$8.0 | est <= $5.28 |
| 2026-10-24T22:02:28+00:00 | apify | start run vbfPXBeCW7izCHgG1 (full) cap $8.0 | <= $8.0 (estimate logged separately) |
| 2026-10-24T22:02:51+00:00 | bart.gov | GET https://www.bart.gov/sites/default/files/2026-10/Ridership_202609.xlsx | free |
| 2026-10-24T22:04:01+00:00 | afcweb.bart.gov | GET https://afcweb.bart.gov/ridership/origin-destination/date-hour-soo-dest-2025.csv.gz | free |
| 2026-10-24T22:06:15+00:00 | caltrans | AADT bbox query (5 pts) | free |
| 2026-10-24T22:06:16+00:00 | datasf | v4v2-5x7s bbox (17 rows) | free |
| 2026-10-24T22:06:33+00:00 | apify | run vbfPXBeCW7izCHgG1 (full) SUCCEEDED, 868 items, dataset gG8r6GzU7zcZHtRdK | actual $5.208200000000001 |
| note | apify | correction: full run actually used 6 terms x maxCrawledPlacesPerSearch=150 (<= 900 places, est <= $5.40); actual 868 places, $5.21. Test run $0.05. Total Apify spend ~ $5.26 | $5.26 total |
