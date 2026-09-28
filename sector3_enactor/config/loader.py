"""Versioned YAML configuration loader. Invalid policy/config combinations fail closed."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..models.approval import ApprovalLevel
from ..models.shared import Money

CONFIG_DIR = Path(__file__).parent


@dataclass(frozen=True)
class CommunicationLimits:
    customer_messages_per_hour: int
    supplier_messages_per_mission: int
    bulk_email_batch_max: int
    social_posts_per_day: int
    outbound_requires_template: bool
    restricted_intents: frozenset[str]
    recipient_allowlists_required_for: frozenset[str]


@dataclass(frozen=True)
class AutoActionPolicy:
    action_id: str
    trigger_metric: str
    allowed_tool: str
    threshold: float | None = None
    requires_matching_plan_stop_condition: bool = False


@dataclass(frozen=True)
class SectorConfig:
    version: str
    division_tools: dict[str, tuple[str, ...]]
    shared_read_tools: tuple[str, ...]
    escalation_routes: dict[str, str]
    budgets: dict[str, Any]
    approval_expiry_hours: dict[ApprovalLevel, int | None]
    approval_escalations: dict[str, ApprovalLevel]
    auto_actions: tuple[AutoActionPolicy, ...]
    hard_stops: frozenset[str]
    communication: CommunicationLimits
    connectors: dict[str, dict[str, Any]]
    rate_limits: dict[str, int]

    def tools_for_division(self, division: str) -> tuple[str, ...]:
        return self.division_tools.get(division, ()) + self.shared_read_tools


def _require_version(raw: Any, name: str) -> str:
    if not isinstance(raw, dict): raise ValueError(f"Config {name} must be a mapping.")
    version = raw.get("version")
    if not isinstance(version, str) or not version.strip(): raise ValueError(f"Config {name} requires a version.")
    return version


def load_sector_config(directory: Path = CONFIG_DIR) -> SectorConfig:
    documents: dict[str, Any] = {}
    for name in ("policies", "budgets", "approval_levels", "stop_conditions", "communication", "connectors"):
        path = directory / f"{name}.yaml"
        if not path.exists(): raise FileNotFoundError(f"Missing required config: {path}")
        documents[name] = yaml.safe_load(path.read_text())
        _require_version(documents[name], name)

    policies = documents["policies"]
    divisions = policies.get("divisions") or {}
    if not isinstance(divisions, dict) or not divisions: raise ValueError("Policies config requires at least one division.")
    division_tools = {str(div): tuple(tools) for div, tools in divisions.items()}
    for div, tools in division_tools.items():
        if any(not isinstance(tool, str) or "." not in tool for tool in tools):
            raise ValueError(f"Division {div}: tool names must be 'connector.action' strings.")
    shared = tuple(policies.get("shared_read_tools") or ())
    routes = policies.get("escalation_routes") or {}
    for intent, route in routes.items():
        if route not in {"human", "finance", "orchestrator", "strategy_manager"}:
            raise ValueError(f"Escalation route for {intent} must be human/finance/orchestrator/strategy_manager.")

    budgets_doc = documents["budgets"]
    default_budget = budgets_doc.get("default_execution_budget") or {}
    money_fields = {}
    for key in ("ad_spend", "purchases"):
        spec = default_budget.get(key)
        if spec is not None: money_fields[key] = Money(amount=float(spec["amount"]), currency=str(spec["currency"]))
    warning = budgets_doc.get("warning_threshold_percent", 80)
    if not 0 < warning <= 100: raise ValueError("Budget warning threshold must be between 0 and 100.")
    budgets = {
        "model_tokens": int(default_budget.get("model_tokens", 0)),
        "api_calls": int(default_budget.get("api_calls", 0)),
        "ad_spend": money_fields.get("ad_spend"),
        "purchases": money_fields.get("purchases", Money(0.0, "USD")),
        "warning_threshold_percent": warning,
        "block_on_exhaustion": bool(budgets_doc.get("block_on_exhaustion", True)),
    }
    if not budgets["block_on_exhaustion"]:
        raise ValueError("Sector 3 refuses configurations that allow overspend (block_on_exhaustion must be true).")

    levels_doc = documents["approval_levels"]
    expiry: dict[ApprovalLevel, int | None] = {}
    for level_key, spec in (levels_doc.get("levels") or {}).items():
        try: level = ApprovalLevel(level_key)
        except ValueError: raise ValueError(f"Unknown approval level {level_key}.")
        hours = spec.get("default_expiry_hours")
        expiry[level] = None if hours is None else int(hours)
    missing_levels = set(ApprovalLevel) - set(expiry)
    if missing_levels: raise ValueError(f"Approval level config missing: {sorted(l.value for l in missing_levels)}")
    escalations: dict[str, ApprovalLevel] = {}
    for rule in levels_doc.get("policy_escalations") or ():
        target = ApprovalLevel(rule["raise_to"])
        source = ApprovalLevel(next(k for k, v in expiry.items() if k.name.startswith(target.value.replace("A", "A")) and v == expiry[target]) if False else target.value)
        escalations[str(rule["when"])] = target

    stop_doc = documents["stop_conditions"]
    auto_actions = tuple(
        AutoActionPolicy(
            action_id=str(item["id"]), trigger_metric=str(item["trigger_metric"]), allowed_tool=str(item["allowed_tool"]),
            threshold=None if item.get("threshold") is None else float(item["threshold"]),
            requires_matching_plan_stop_condition=bool(item.get("requires_matching_plan_stop_condition", False)),
        ) for item in (stop_doc.get("auto_actions") or ())
    )
    seen_ids: set[str] = set()
    for action in auto_actions:
        if action.action_id in seen_ids: raise ValueError(f"Duplicate auto-action id {action.action_id}.")
        seen_ids.add(action.action_id)
    hard_stops = frozenset(str(item) for item in (stop_doc.get("hard_stops") or ()))

    comms_doc = documents["communication"]
    limits = comms_doc.get("limits") or {}
    communication = CommunicationLimits(
        customer_messages_per_hour=int(limits.get("customer_messages_per_hour", 0)),
        supplier_messages_per_mission=int(limits.get("supplier_messages_per_mission", 0)),
        bulk_email_batch_max=int(limits.get("bulk_email_batch_max", 0)),
        social_posts_per_day=int(limits.get("social_posts_per_day", 0)),
        outbound_requires_template=bool(comms_doc.get("outbound_requires_template", True)),
        restricted_intents=frozenset(str(i) for i in (comms_doc.get("restricted_intents_always_escalate") or ())),
        recipient_allowlists_required_for=frozenset(str(i) for i in (comms_doc.get("recipient_allowlists_required_for") or ())),
    )
    if communication.customer_messages_per_hour <= 0: raise ValueError("Customer messaging rate cap must be positive.")

    conn_doc = documents["connectors"]
    connectors = {str(name): dict(spec) for name, spec in (conn_doc.get("connectors") or {}).items()}
    rate_limits = {str(name): int(value) for name, value in (conn_doc.get("rate_limits") or {}).items()}

    version = policies["version"]
    if len({policies["version"], budgets_doc["version"], levels_doc["version"], stop_doc["version"], comms_doc["version"], conn_doc["version"]}) != 1:
        raise ValueError("All Sector 3 config documents must share one version.")

    return SectorConfig(version=version, division_tools=division_tools, shared_read_tools=shared,
                        escalation_routes={str(k): str(v) for k, v in routes.items()}, budgets=budgets,
                        approval_expiry_hours=expiry, approval_escalations=escalations, auto_actions=auto_actions,
                        hard_stops=hard_stops, communication=communication, connectors=connectors, rate_limits=rate_limits)
