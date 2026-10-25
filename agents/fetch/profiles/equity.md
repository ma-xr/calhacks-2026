# Equity (CommonGround)

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

Specialist agent for the **SF Street Analyst**. Runs a car-free plan on the CommonGround city simulation and reports who gains and who pays: travel and walking time by income tier, premature deaths avoided (WHO HEAT), new acquaintances and lost neighbour ties on diverted streets, rent pressure, CO₂, and the health, social and environment value lines in $/yr.

Protocol: `HPStreetAnalysis` — `AnalyzeRequest{request_id, label, edges}` → `AnalyzeResponse{markdown, facts_json, scenario_id}`.
