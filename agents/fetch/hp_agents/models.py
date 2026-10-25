"""Messages between the SF Street Analyst and its specialists (the "HP Street Analysis" protocol)."""

from __future__ import annotations

from uagents import Model


class AnalyzeRequest(Model):
    request_id: str
    label: str                 # e.g. "2nd Street between Market Street and Folsom Street"
    edges: list[int]           # engine edge ids to pedestrianize


class AnalyzeResponse(Model):
    request_id: str
    specialist: str            # mobility | economy | equity
    scenario_id: str = ""
    markdown: str = ""
    facts_json: str = "{}"     # the exact engine fields the markdown quotes
    error: str = ""
