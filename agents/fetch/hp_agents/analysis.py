"""What each specialist says. Pure functions over engine results, so every number is grounded.

Each function takes the plan result, the baseline result (both `?lite=1`), `/world`, the
street index and the stretch's edge ids, and returns {"markdown": ..., "facts": {...}}.
`facts` holds the exact engine fields the text quotes, for the brief and for checking.
"""

from __future__ import annotations

from collections import defaultdict

PILLARS = ["mobility", "economy", "health", "social", "environment"]


def usd(x: float, per: str = "/yr") -> str:
    sign = "-" if x < 0 else ""
    a = abs(x)
    if a >= 1e6:
        s = f"${a / 1e6:.2f}M"
    elif a >= 1e3:
        s = f"${a / 1e3:.0f}k"
    else:
        s = f"${a:.0f}"
    return f"{sign}{s}{per}"


def signed(x: float, nd: int = 0) -> str:
    return f"{x:+,.{nd}f}"


def pct(d: float, base: float) -> str:
    return f"{100 * d / base:+.1f}%" if base else "n/a"


def _lines(result: dict, pillar: str) -> list[dict]:
    return [l for l in result["value"]["lines"] if l["pillar"] == pillar and abs(l["usd_per_yr"]) >= 1]


def _line_md(l: dict) -> str:
    return f"- {l['label']}: {signed(l['qty'], 2 if abs(l['qty']) < 10 else 0)} {l['unit']} → **{usd(l['usd_per_yr'])}**"


def _by_street(index, deltas: dict[int, float], skip: set[int]) -> list[tuple[str, float]]:
    """Largest per-block change on each street (summing blocks would count a car once per block)."""
    agg: dict[str, float] = defaultdict(float)
    for i, d in deltas.items():
        if i not in skip and index.names[index.edges[i]["n"]]:
            name = index.edge_name(i)
            agg[name] = max(agg[name], d)
    return sorted(agg.items(), key=lambda kv: -kv[1])


def mobility(plan: dict, base: dict, world: dict, index, edges: list[int]) -> dict:
    m, b, d = plan["metrics"], base["metrics"], plan["delta"]
    sel = set(edges)
    car_plan, car_base = plan["edges"]["car_day"], base["edges"]["car_day"]
    length = sum(index.edges[i]["l"] for i in edges)
    stretch_cars_before = sum(car_base[i] * index.edges[i]["l"] for i in edges) / length
    diff = {i: car_plan[i] - car_base[i] for i in range(len(car_plan))}
    gains = [(s, v) for s, v in _by_street(index, diff, sel) if v > 50][:3]
    pm = plan["edges"]["congestion_pm"], base["edges"]["congestion_pm"]
    worst = max((i for i in range(len(pm[0])) if i not in sel), key=lambda i: pm[0][i] - pm[1][i])
    t = d["trips"]
    md = [
        f"**Mobility** (value {usd(plan['value']['mobility'])})",
        f"- Cars on this stretch today: about {stretch_cars_before:,.0f}/day per block ({length:,.0f} m), all rerouted or gone.",
        f"- Daily trips: car {signed(t['car'])} ({pct(t['car'], b['trips']['car'])}), transit {signed(t['transit'])}, "
        f"walk {signed(t['walk'])}, bike {signed(t['bike'])}, trips not made {signed(t['gone'])}.",
        f"- Driving: total VMT {signed(d['vmt_total'])} mi/day; in-area VMT {signed(d['vmt'])} (detours); "
        f"vehicle delay {signed(d['delay_hours'], 1)} h/day.",
    ]
    if gains:
        md.append("- Where the cars go (busiest block on each street): "
                  + ", ".join(f"{s} {signed(v)}/day" for s, v in gains) + ".")
    md.append(f"- Worst PM-peak slowdown: {index.edge_name(worst)}, travel-time factor "
              f"{pm[1][worst]:.2f} → {pm[0][worst]:.2f}.")
    md += [_line_md(l) for l in _lines(plan, "mobility")]
    return {"markdown": "\n".join(md), "facts": {
        "delta.trips": t, "delta.vmt_total": d["vmt_total"], "delta.vmt": d["vmt"],
        "delta.delay_hours": d["delay_hours"], "stretch_car_day_baseline": round(stretch_cars_before),
        "diversion_by_street": gains, "value.mobility": plan["value"]["mobility"],
        "congestion_pm_worst": {"edge": worst, "street": index.edge_name(worst),
                                "before": pm[1][worst], "after": pm[0][worst]},
    }}


def economy(plan: dict, base: dict, world: dict, index, edges: list[int]) -> dict:
    d = plan["delta"]
    pois = world["pois"]
    rev_p, rev_b = plan["pois"]["revenue_day"], base["pois"]["revenue_day"]
    walk_p, walk_b = plan["pois"]["walkby_day"], base["pois"]["walkby_day"]
    near = index.pois_near(edges, pois)
    near_rev = sum(rev_p[i] - rev_b[i] for i in near)
    near_base = sum(rev_b[i] for i in near)
    near_walk = sum(walk_p[i] - walk_b[i] for i in near)
    deltas = sorted(((rev_p[i] - rev_b[i], i) for i in range(len(rev_p))), reverse=True)
    win = [(pois[i]["name"], v) for v, i in deltas[:3] if v > 0]
    lose = [(pois[i]["name"], v) for v, i in deltas[::-1][:3] if v < 0]
    md = [
        f"**Local economy** (value {usd(plan['value']['economy'])})",
        f"- Area-wide: visits {signed(d['visits'])}/day, business revenue {usd(d['revenue'], '/day')} "
        f"({pct(d['revenue'], base['metrics']['revenue'])}).",
        f"- {len(near)} businesses front the stretch: revenue {usd(near_rev, '/day')} "
        f"({pct(near_rev, near_base)}), storefront walk-bys {signed(near_walk)}/day.",
    ]
    if win:
        md.append("- Biggest winners: " + ", ".join(f"{n} {usd(v, '/day')}" for n, v in win) + ".")
    if lose:
        md.append("- Biggest losers: " + ", ".join(f"{n} {usd(v, '/day')}" for n, v in lose) + ".")
    if plan.get("virtual_pois"):
        md.append(f"- New storefronts the model expects: {len(plan['virtual_pois'])}.")
    md += [_line_md(l) for l in _lines(plan, "economy")]
    return {"markdown": "\n".join(md), "facts": {
        "delta.visits": d["visits"], "delta.revenue": d["revenue"], "value.economy": plan["value"]["economy"],
        "stretch_pois": len(near), "stretch_revenue_delta_day": round(near_rev, 2),
        "stretch_walkby_delta_day": round(near_walk), "top_winners": win, "top_losers": lose,
    }}


def equity(plan: dict, base: dict, world: dict, index, edges: list[int]) -> dict:
    d, m, v = plan["delta"], plan["metrics"], plan["value"]
    tiers = []
    for tier in ("low", "mid", "high"):
        cur, dt = m["by_income"][tier], d["by_income"][tier]
        tiers.append(f"{tier} income ({cur['people']:,} people, {cur['car_share']:.0%} drive): "
                     f"travel {signed(dt['travel_min'], 2)} min/day, walking {signed(dt['walk_min'], 2)} min/day")
    burden = max(("low", "mid", "high"), key=lambda k: d["by_income"][k]["travel_min"])
    md = [
        f"**Equity & wellbeing** (health {usd(v['health'])}, social {usd(v['social'])}, "
        f"environment {usd(v['environment'])})",
        *[f"- {t}." for t in tiers],
        f"- Largest added travel time falls on the **{burden}**-income group "
        f"({signed(d['by_income'][burden]['travel_min'], 2)} min/day each).",
        f"- Health: {d['deaths_averted_per_yr']:.2f} premature deaths avoided per year from extra walking "
        f"and cycling (+{d['active_minutes_per_person']:.2f} active min/person/day).",
        f"- Social: {signed(d['new_ties'])} new acquaintances/yr, {signed(d['encounters'])} chance encounters/day; "
        f"neighbour ties on streets that get diverted traffic {signed(d['neighbor_ties'])}.",
        f"- Rent pressure index {signed(d['rent_pressure_index'], 2)}% (displacement risk), "
        f"CO₂ {signed(d['co2_tonnes'], 2)} t/day.",
    ]
    md += [_line_md(l) for p in ("health", "social", "environment") for l in _lines(plan, p)]
    return {"markdown": "\n".join(md), "facts": {
        "metrics.by_income": m["by_income"], "delta.by_income": d["by_income"],
        "delta.deaths_averted_per_yr": d["deaths_averted_per_yr"], "delta.new_ties": d["new_ties"],
        "delta.encounters": d["encounters"], "delta.neighbor_ties": d["neighbor_ties"],
        "delta.rent_pressure_index": d["rent_pressure_index"], "delta.co2_tonnes": d["co2_tonnes"],
        "value.health": v["health"], "value.social": v["social"], "value.environment": v["environment"],
    }}


SPECIALISTS = {"mobility": mobility, "economy": economy, "equity": equity}

