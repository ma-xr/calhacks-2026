# Google Maps places via Apify "Google Maps Scraper"

## What it is
A third-party Apify actor that scrapes Google Maps place listings: names, categories, ratings, price level, hours, and **Popular Times** histograms. We use it to give the retail and social layer realistic hourly visit patterns.

## Publisher & URL
| Item | Value |
|---|---|
| Actor | `compass/crawler-google-places` ("Google Maps Scraper", developer Compass) |
| URL | https://apify.com/compass/crawler-google-places |
| API | `POST https://api.apify.com/v2/acts/compass~crawler-google-places/runs?token=APIFY_TOKEN` (standard Apify run API; endpoint form not checked separately) |
| Pricing | "From $1.50 per 1,000 scraped places", pay-per-event. Add-ons (details, reviews, contacts) cost extra. (actor page, 2026-10-24) |

## License / terms (important)
| Party | Terms |
|---|---|
| Google Maps (end-user ToS) | https://www.google.com/help/terms_maps/ §2 Prohibited Conduct bars, among other things, mass-downloading or creating "bulk feeds of the content" (§2.3), copying content (§2.2), and using Google Maps to create or augment another mapping dataset such as a business-listing database (§2.4). |
| Google Maps Platform ToS (API customers) | Includes a "No Scraping" clause banning extracting, exporting or scraping Maps content for use outside the Services, and caps caching (generally 30 days). https://cloud.google.com/maps-platform/terms (exact section number not checked; secondary summary: https://conductatlas.com/platform/google-maps/google-maps-platform-terms-of-service/no-scraping-or-content-extraction/) |
| Apify | The actor page tells users to consider Google's Terms and says users need a legal basis for any personal data, such as reviewer names. |

**Our policy (recommended):**
- Hackathon research and demo use only.
- Don't redistribute raw Google content: no `world.json` in a public repo carrying Google names, reviews or ratings.
- Store derived aggregates only, such as a normalized 24×7 visit curve per category or block.
- Skip reviews and reviewer personal data entirely.
- Delete raw dumps after 30 days.
- For production, switch to the official Places API (which has no Popular Times), SafeGraph/Advan, or DataSF Registered Businesses joined to OSM.

This is not legal advice.

## Fields we use (output field names per the actor page)
| Field | Use |
|---|---|
| `placeId`, `title`, `categoryName`, `location.lat/lng`, `address` | Join to OSM POIs and DataSF `g8m3-pdis` |
| `totalScore`, `reviewsCount` | Attractiveness term in destination choice |
| `price` (e.g. "$10–20") | Spend per visit, affordability by income tier |
| `openingHours` | Availability constraint |
| `popularTimesHistogram` (relative 0–100 by hour, per weekday) | Hourly visit-demand curve |
| `popularTimesLiveText`, `popularTimesLivePercent` | Live crowding for the demo (optional) |

Inputs:
- `searchStringsArray` (e.g. "restaurant", "cafe", "bar", "gym")
- `customGeolocation` (GeoJSON Polygon of our bbox; **lon, lat order**)
- `maxCrawledPlacesPerSearch`
- `scrapePlaceDetailPage=true` (required for Popular Times)

## How the model uses it
| Module | Use |
|---|---|
| Retail | Destination choice for lunch and after-work trips. Hourly attraction ∝ `popularTimesHistogram` × capacity. |
| Social | Bars, cafes and gyms as evening and third places |
| Valuation | Rating and price level as ground-floor retail quality proxies |
| Validation | Simulated hourly visits vs Popular Times shape (correlation, not absolute counts) |

## Caveats
- **Popular Times is relative.** Each place is scaled to its own weekly peak (100), so it can't be compared in absolute terms between places. Scale with capacity, reviewsCount, or sq ft from DataSF Land Use.
- Popular Times is often missing. The actor page says Google mainly shows it to logged-in users, and small places lack it. Fill gaps with category averages.
- Search caps: about 120 results per query without a location. Use the polygon and several search terms, then dedupe on `placeId`.
- Data is a point-in-time snapshot. Closures lag, so cross-check against DataSF `location_end_date`.
- Google's Popular Times method (from location-history users) isn't documented and likely under-represents some groups (unverified).

## Key numbers
- Not scraped yet. Expect on the order of 1,300+ amenity/shop POIs in the bbox: OSM has 723 amenity and 644 shop tags (see `openstreetmap.md`).
