# Local Economy (Human Project)

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

Specialist agent for the **SF Street Analyst**. Runs a car-free plan on the Human Project city simulation and reports area-wide visits and business revenue, revenue and walk-bys for the businesses fronting the stretch, the biggest winners and losers by name, and the economy value lines (local value added, sales tax) in $/yr.

Protocol: `HPStreetAnalysis` — `AnalyzeRequest{request_id, label, edges}` → `AnalyzeResponse{markdown, facts_json, scenario_id}`.
