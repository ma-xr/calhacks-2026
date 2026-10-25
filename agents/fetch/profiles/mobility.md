# Mobility (Human Project)

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

Specialist agent for the **SF Street Analyst**. Given engine edge ids of a San Francisco street stretch, it runs a car-free plan on the Human Project city simulation and reports daily trips by mode, total and in-area vehicle miles, vehicle delay, where diverted cars go, the worst PM-peak slowdown, and the mobility value lines in $/yr.

Protocol: `HPStreetAnalysis` — `AnalyzeRequest{request_id, label, edges}` → `AnalyzeResponse{markdown, facts_json, scenario_id}`.
