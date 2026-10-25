# Paris: Rue de Rivoli (2020) and the Seine riverbank expressway closures (2013 / 2016)

## Context
Rue de Rivoli is the main east-west arterial of central Paris (1st/4th arr.). In 2003 it carried >25,000 vehicles/day across all modes ([fr.wikipedia, citing IAU Île-de-France, *La circulation routière en Île-de-France*, 2005](https://fr.wikipedia.org/wiki/Rue_de_Rivoli); source PDF: [Institut Paris Region](https://www.institutparisregion.fr/fileadmin/NewEtudes/Etude_86/dti_La_circulation_routiere_en_Ile_de_France.pdf)). The Right Bank lower quay expressway (voie Georges-Pompidou) carried ~43,000 vehicles/day ([Streetsblog USA, 2016](https://usa.streetsblog.org/2016/09/28/adieu-cars-paris-riverfront-to-be-permanently-returned-to-the-people/); [en.wikipedia citing The Independent](https://en.wikipedia.org/wiki/Voie_Georges-Pompidou)).

## Interventions
| Item | Date | Detail | Source |
|---|---|---|---|
| Left Bank lower quay closed | 28 Jan 2013 | ~2 km, quai Anatole-France to quai Branly | [fr.wikipedia, Berges de Seine](https://fr.wikipedia.org/wiki/Berges_de_Seine) |
| Right Bank lower quay (Tuileries–Henri IV tunnel) | Council vote 26 Sep 2016; police confirmed 28 Jun 2017 | ~3.3 km ("two miles"); cost ~$50 M; merged into Parc Rives de Seine, opened 2 Apr 2017 | [fr.wikipedia, Voie Georges-Pompidou](https://fr.wikipedia.org/wiki/Voie_Georges-Pompidou); [Streetsblog](https://usa.streetsblog.org/2016/09/28/adieu-cars-paris-riverfront-to-be-permanently-returned-to-the-people/) |
| Legal | Administrative court annulled 2016 decree 21 Feb 2018 (flawed impact study); new decree 2018 upheld on appeal 21 Jun 2019 | — | [fr.wikipedia](https://fr.wikipedia.org/wiki/Voie_Georges-Pompidou); [Tribunal administratif communiqué](http://paris.tribunal-administratif.fr/Actualites-du-Tribunal/Communiques-de-presse/VOIES-SUR-BERGE-Le-Tribunal-administratif-de-Paris-annule-la-fermeture-a-la-circulation-des-voies-sur-les-berges-de-la-rive-droite-de-la-Seine) |
| Rue de Rivoli, step 1 | Sep 2018 | 1 bus lane + 1 general lane + cycle track (to Bd Sébastopol) | [France Bleu, 19 Sep 2018](https://www.francebleu.fr/infos/transports/paris-un-nouveau-troncon-de-la-piste-cyclable-rue-de-rivoli-a-ete-inaugure-1537370153) |
| Rue de Rivoli, COVID "coronapiste" made permanent | May 2020 trial; announced permanent 16 Sep 2020 | Private cars (incl. ride-hail) and motorbikes banned; buses, taxis, professional vehicles allowed; wide two-way bike lanes | [Sortiraparis, 17 Sep 2020](https://www.sortiraparis.com/actualites/a-paris/articles/219085-la-piste-cyclable-rue-de-rivoli-devient-permanente-les-voitures-interdites) |

## Measured: Rue de Rivoli multimodal counter (65 rue de Rivoli / Bourdonnais, Paris Open Data)
Computed by us from [Paris Open Data "comptage-multimodal-comptages"](https://parisdata.opendatasoft.com/explore/dataset/comptage-multimodal-comptages/) (counter `CF0892_65 rue de Rivoli (Bourdonnais)`, all directions, May totals ÷ days with data):
| Month | Days | Bikes + scooters / day | Motor vehicles / day (cars+vans, HGV, buses, motorbikes) | Active share of vehicles |
|---|---|---|---|---|
| May 2022 | 31 | ~15,250 | ~7,680 | 67% |
| May 2024 | 25 | ~13,860 | ~5,900 | 70% |
| May 2025 | 31 | ~17,800 | ~9,620 (motorbike count jumped to 116k/month, possible classification change) | 65% |
| Baseline 2003 (whole street, all modes) | — | — | >25,000 | — |
Wikipedia's reading of the same counter: Jan 2024 weekdays 10,000–14,000 bikes+scooters vs 4,000–6,000 other vehicles; May 2024 weekdays >15,000 bikes vs 6,000–7,000 others ([fr.wikipedia](https://fr.wikipedia.org/wiki/Rue_de_Rivoli)).

## Riverbank closure outcomes
| Metric | Value | Source / quality |
|---|---|---|
| Traffic removed from lower quay | ~43,000 veh/day | [Streetsblog](https://usa.streetsblog.org/2016/09/28/adieu-cars-paris-riverfront-to-be-permanently-returned-to-the-people/) |
| Left Bank 2013 closure "does not penalize traffic" | headline claim | Challenges, 28 Jan 2013 (cited in [fr.wikipedia](https://fr.wikipedia.org/wiki/Berges_de_Seine); not fetched, (unverified)) |
| Share of displaced traffic reappearing on upper quays / Bd Saint-Germain / périphérique | Regional monitoring committee (Carli) and Airparif evaluations exist but were not accessed (unverified) | — |
| Paris-Plages visitors (summer, pre-closure context) | up to 4 M/yr | [Streetsblog](https://usa.streetsblog.org/2016/09/28/adieu-cars-paris-riverfront-to-be-permanently-returned-to-the-people/) |
| Parisian households without a car | ~60% (up from ~40% ~15 years earlier) | Slate via [Streetsblog](https://usa.streetsblog.org/2016/09/28/adieu-cars-paris-riverfront-to-be-permanently-returned-to-the-people/) |

## Caveats / confounds
- Rivoli's transformation coincided with COVID, the 2020 bike boom, Vélib' growth, Paris's citywide 30 km/h limit (2021) and other "Plan Vélo" works. Before/after bike growth on Rivoli has no clean counterfactual. The multimodal counter only starts in Nov 2020, after the change.
- Monthly totals depend on counter uptime (May 2024 had 25 days). The 2025 motorbike spike suggests a classification artefact.
- The 2018 court annulment found the city's riverbank impact study inaccurate. Displacement and evaporation claims for the berges are contested, and we did not verify the official evaluation numbers. Do not cite a berges evaporation % from this file.
- This file still needs: Airparif berges NO2 evaluation, the regional monitoring committee traffic report, and the Ville de Paris *Bilan des déplacements* (city-wide car traffic trend). Search budget ran out before these could be located.

## Sources
- Paris Open Data, multimodal counts: https://parisdata.opendatasoft.com/explore/dataset/comptage-multimodal-comptages/
- fr.wikipedia, Rue de Rivoli (with footnotes to counts): https://fr.wikipedia.org/wiki/Rue_de_Rivoli
- Institut Paris Region, *La circulation routière en Île-de-France* (2005): https://www.institutparisregion.fr/fileadmin/NewEtudes/Etude_86/dti_La_circulation_routiere_en_Ile_de_France.pdf
- Sortiraparis, 17 Sep 2020: https://www.sortiraparis.com/actualites/a-paris/articles/219085-la-piste-cyclable-rue-de-rivoli-devient-permanente-les-voitures-interdites
- France Bleu, 19 Sep 2018: https://www.francebleu.fr/infos/transports/paris-un-nouveau-troncon-de-la-piste-cyclable-rue-de-rivoli-a-ete-inaugure-1537370153
- fr.wikipedia, Voie Georges-Pompidou: https://fr.wikipedia.org/wiki/Voie_Georges-Pompidou
- Streetsblog USA, 28 Sep 2016: https://usa.streetsblog.org/2016/09/28/adieu-cars-paris-riverfront-to-be-permanently-returned-to-the-people/
- Tribunal administratif de Paris, 21 Feb 2018: http://paris.tribunal-administratif.fr/Actualites-du-Tribunal/Communiques-de-presse/VOIES-SUR-BERGE-Le-Tribunal-administratif-de-Paris-annule-la-fermeture-a-la-circulation-des-voies-sur-les-berges-de-la-rive-droite-de-la-Seine

## What our model should reproduce
| Parameter / output | Target |
|---|---|
| Treated arterial throughput | A ~25,000 veh/day arterial converted to bus/taxi/delivery + bikes now carries ~6,000–9,600 motor veh/day plus ~14,000–18,000 bikes/scooters per day. Total *vehicle* throughput incl. bikes (~19,800–27,400/day) is roughly the same as the 2003 all-mode >25,000/day, so the corridor's capacity is reused rather than lost. |
| Mode substitution | ~2:1 bikes to motor vehicles on a converted CBD spine. The sim's mode-choice should let active modes absorb a large share of former car trips when protected space is given. |
| Residual motor traffic | ~25–40% of the original motor volume remains when buses, taxis and deliveries keep access (useful for a "transit + delivery mall" scenario on Market St-type streets). |
| `traffic_evaporation_median` | No verified Paris number in this file. Use the London/Ghent/Cairns-style evidence instead. |
