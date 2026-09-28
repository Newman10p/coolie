"""The §7 tool registry, declared as data. Approval levels here are the FLOOR;
context rules in approval_levels.yaml may only raise them."""
from __future__ import annotations

from ..models.approval import ApprovalLevel
from ..models.shared import ToolMode
from .registry import EnactorToolDefinition, ToolRegistry

M = ToolMode
A = ApprovalLevel


def _t(name, description, mode, risk, agents, level, reversible, dry_run, budget, scope, *, target="target", cost=lambda a: 0.0):
    return EnactorToolDefinition(name=name, description=description, mode=mode, risk_level=risk,
                                 allowed_agents=frozenset(agents), approval_level=level, reversible=reversible,
                                 supports_dry_run=dry_run, budget_type=budget, data_scope=scope,
                                 target_argument=target, cost_estimate=cost)


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    defs = [
        # Brain (shared by all divisions that declare it)
        _t("brain.complete", "LLM completion via the shared brain connector.", M.READ, "low",
           {"messengers.support_triage","messengers.supply_communications","designers.brand_designer","designers.graphic_designer","marketers.content_writer","marketers.campaign_manager","seo.seo_specialist","analytics.metric_collector","commerce.catalog_manager"}, A.A0_NONE, True, False, "model_tokens", "internal_read",
           cost=lambda a: float(a.get("estimatedTokens", 1000))),
        # Messenger division (§5.1)
        _t("triage.classify_request", "Classify inbound message intent/replyType.", M.READ, "low", {"messengers.support_triage"}, A.A0_NONE, True, False, "none", "customer_read"),
        _t("triage.route_request", "Route a classified request to a queue or escalation.", M.WRITE, "low", {"messengers.support_triage"}, A.A1_INTERNAL, True, False, "none", "customer_read"),
        _t("email.read_inbox", "Read inbox messages.", M.READ, "low", {"messengers.support_triage"}, A.A0_NONE, True, False, "api_calls", "customer_read"),
        _t("messaging.read_conversations", "Read WhatsApp/Instagram conversations.", M.READ, "low", {"messengers.support_triage"}, A.A0_NONE, True, False, "api_calls", "customer_read"),
        _t("store.read_orders", "Read order records.", M.READ, "low", {"messengers.support_triage","commerce.fulfillment_coordinator","commerce.returns_processor"}, A.A0_NONE, True, False, "none", "customer_read"),
        _t("store.read_customers", "Read customer profiles.", M.READ, "low", {"messengers.support_triage"}, A.A0_NONE, True, False, "none", "customer_read"),
        _t("tickets.create", "Create a support ticket.", M.WRITE, "low", {"messengers.support_triage"}, A.A1_INTERNAL, True, False, "none", "customer_read"),
        _t("tickets.update", "Update a support ticket.", M.WRITE, "low", {"messengers.support_triage"}, A.A1_INTERNAL, True, False, "none", "customer_read"),
        _t("email.send_approved", "Send an approved email to a customer.", M.EXTERNAL_ACTION, "high", {"messengers.support_triage","marketers.campaign_manager"}, A.A3_STANDARD, False, True, "api_calls", "comms_send", target="recipient", cost=lambda a: 1.0),
        _t("messaging.send_approved", "Send an approved WhatsApp/DM reply.", M.EXTERNAL_ACTION, "high", {"messengers.support_triage"}, A.A3_STANDARD, False, True, "api_calls", "comms_send", target="recipient", cost=lambda a: 1.0),
        _t("supplier.draft_message", "Draft a supplier communication.", M.DRAFT, "low", {"messengers.supply_communications","commerce.inventory_planner"}, A.A1_INTERNAL, True, False, "none", "internal_read"),
        _t("supplier.send_approved", "Send an approved message to a known supplier.", M.EXTERNAL_ACTION, "medium", {"messengers.supply_communications","commerce.inventory_planner"}, A.A2_LIGHTWEIGHT, True, True, "api_calls", "comms_send", target="recipient", cost=lambda a: 1.0),
        _t("internal.notify", "Notify a human/finance/orchestrator channel internally.", M.WRITE, "low", {"messengers.support_triage","analytics.metric_collector","qa.quality_gate"}, A.A1_INTERNAL, True, False, "none", "internal_read", target="channel"),
        # Designers (§5.2)
        _t("design.generate_concept", "Generate design concepts.", M.DRAFT, "low", {"designers.brand_designer","designers.graphic_designer"}, A.A1_INTERNAL, True, True, "model_tokens", "internal_read", cost=lambda a: float(a.get("estimatedTokens", 4000))),
        _t("design.produce_asset_draft", "Produce a draft asset from an approved concept.", M.DRAFT, "low", {"designers.graphic_designer"}, A.A1_INTERNAL, True, True, "model_tokens", "internal_read", cost=lambda a: float(a.get("estimatedTokens", 6000))),
        _t("assets.store_version", "Store an immutable hashed asset version.", M.WRITE, "low", {"designers.brand_designer","designers.graphic_designer","builders.web_developer","marketers.campaign_manager","seo.seo_specialist","qa.quality_gate"}, A.A1_INTERNAL, True, False, "none", "internal_read", target="assetId"),
        _t("assets.advance_stage", "Advance an asset one lifecycle stage (draft→reviewed→approved).", M.WRITE, "medium", {"designers.brand_designer","qa.quality_gate"}, A.A2_LIGHTWEIGHT, True, False, "none", "internal_read", target="assetId"),
        # Builders (§5.3, §8.3)
        _t("repo.create_branch", "Create a repository branch.", M.WRITE, "low", {"builders.web_developer","builders.automation_engineer"}, A.A1_INTERNAL, True, False, "api_calls", "code_write", target="branch"),
        _t("repo.commit_patch", "Commit a patch to a branch.", M.WRITE, "medium", {"builders.web_developer","builders.automation_engineer"}, A.A2_LIGHTWEIGHT, True, False, "api_calls", "code_write", target="branch"),
        _t("repo.open_pull_request", "Open a pull request for human review.", M.EXTERNAL_ACTION, "medium", {"builders.web_developer","builders.automation_engineer"}, A.A2_LIGHTWEIGHT, True, True, "api_calls", "code_write", target="branch"),
        _t("sandbox.run_command", "Run an allowlisted command in an ephemeral sandbox.", M.WRITE, "medium", {"builders.web_developer","builders.automation_engineer"}, A.A2_LIGHTWEIGHT, True, False, "api_calls", "code_read", target="command"),
        _t("ci.run_pipeline", "Run CI checks on a branch.", M.WRITE, "low", {"builders.web_developer"}, A.A0_NONE if False else ApprovalLevel.A1_INTERNAL, True, False, "api_calls", "code_read", target="branch"),
        _t("hosting.deploy_staging", "Deploy an artifact to staging.", M.EXTERNAL_ACTION, "high", {"builders.web_developer"}, A.A3_STANDARD, True, True, "api_calls", "code_write", target="environment"),
        _t("hosting.read_logs", "Read hosting logs.", M.READ, "low", {"builders.web_developer","analytics.metric_collector"}, A.A0_NONE, True, False, "api_calls", "code_read"),
        _t("hosting.request_production_deploy", "Request a production deployment (never executes one).", M.EXTERNAL_ACTION, "critical", {"builders.web_developer"}, A.A4_STRICT, False, True, "none", "code_write", target="artifactKey"),
        _t("hosting.rollback", "Roll back to the previous successful deployment.", M.EXTERNAL_ACTION, "high", {"builders.web_developer"}, A.A3_STANDARD, True, True, "none", "code_write", target="environment"),
        _t("code.review_report", "File a structured code-review report.", M.WRITE, "low", {"builders.web_developer","qa.quality_gate"}, A.A1_INTERNAL, True, False, "none", "code_read", target="reportId"),
        # Marketers (§5.4)
        _t("campaigns.draft", "Draft a campaign (internal only).", M.DRAFT, "low", {"marketers.campaign_manager"}, A.A1_INTERNAL, True, False, "model_tokens", "internal_read", cost=lambda a: float(a.get("estimatedTokens", 3000))),
        _t("campaigns.validate_policy", "Validate campaign copy against claims policy.", M.READ, "low", {"marketers.campaign_manager","marketers.content_writer","qa.quality_gate"}, A.A0_NONE, True, False, "none", "internal_read"),
        _t("claims.check_marketing_claims", "Check every claim references evidence/approved product info.", M.READ, "low", {"marketers.campaign_manager","qa.quality_gate"}, A.A0_NONE, True, False, "none", "internal_read"),
        _t("campaigns.publish_approved", "Publish a fully approved campaign.", M.EXTERNAL_ACTION, "critical", {"marketers.campaign_manager"}, A.A4_STRICT, False, True, "ad_spend", "ads_write", target="campaignId", cost=lambda a: float(a.get("budgetAmount", 0.0))),
        _t("campaigns.pause", "Pause a running campaign.", M.EXTERNAL_ACTION, "medium", {"marketers.campaign_manager"}, A.A2_LIGHTWEIGHT, True, True, "none", "ads_write", target="campaignId"),
        _t("social.schedule_post", "Schedule a social post (internal state).", M.DRAFT, "low", {"marketers.content_writer"}, A.A1_INTERNAL, True, False, "none", "internal_read", target="platform"),
        _t("social.publish_approved_post", "Publish a scheduled post after approval.", M.EXTERNAL_ACTION, "high", {"marketers.content_writer"}, A.A3_STANDARD, False, True, "api_calls", "comms_send", target="postId", cost=lambda a: 1.0),
        _t("ads.get_metrics", "Read advertising metrics.", M.READ, "low", {"marketers.campaign_manager","analytics.metric_collector"}, A.A0_NONE, True, False, "api_calls", "public_read"),
        _t("ads.recommend_optimization", "Record an optimization recommendation (never applies spend changes).", M.DRAFT, "low", {"marketers.campaign_manager"}, A.A1_INTERNAL, True, False, "none", "internal_read", target="campaignId"),
        # SEO (§5.6)
        _t("seo.run_technical_audit", "Run a technical SEO audit.", M.READ, "low", {"seo.seo_specialist"}, A.A0_NONE, True, False, "api_calls", "public_read"),
        _t("seo.draft_content_brief", "Draft a content brief.", M.DRAFT, "low", {"seo.seo_specialist"}, A.A1_INTERNAL, True, False, "model_tokens", "internal_read", cost=lambda a: float(a.get("estimatedTokens", 2000))),
        _t("seo.submit_changeset", "Submit an SEO changeset for review.", M.WRITE, "medium", {"seo.seo_specialist"}, A.A2_LIGHTWEIGHT, True, False, "none", "seo_write", target="changesetId"),
        _t("seo.apply_approved_changes", "Apply an approved SEO changeset to the live site.", M.EXTERNAL_ACTION, "high", {"seo.seo_specialist"}, A.A3_STANDARD, True, True, "none", "seo_write", target="changesetId"),
        _t("analytics.read_search_performance", "Read search performance data.", M.READ, "low", {"seo.seo_specialist","analytics.metric_collector"}, A.A0_NONE, True, False, "api_calls", "public_read"),
        # Commerce (§5.5)
        _t("store.read_products", "Read the product catalog (shared read tool).", M.READ, "low", {"commerce.catalog_manager","commerce.inventory_planner","marketers.campaign_manager","seo.seo_specialist"}, A.A0_NONE, True, False, "none", "internal_read"),
        _t("catalog.create_draft", "Create a draft product listing.", M.DRAFT, "low", {"commerce.catalog_manager"}, A.A1_INTERNAL, True, False, "none", "product_write", target="productId"),
        _t("catalog.update_draft", "Update a draft product listing.", M.WRITE, "low", {"commerce.catalog_manager"}, A.A1_INTERNAL, True, False, "none", "product_write", target="productId"),
        _t("catalog.validate_listing", "Validate a listing against policy/evidence.", M.READ, "low", {"commerce.catalog_manager","qa.quality_gate"}, A.A0_NONE, True, False, "none", "internal_read"),
        _t("catalog.publish_approved", "Publish an approved listing to the store.", M.EXTERNAL_ACTION, "high", {"commerce.catalog_manager"}, A.A3_STANDARD, True, True, "none", "product_write", target="productId"),
        _t("inventory.preview_sync", "Preview an inventory synchronization.", M.READ, "low", {"commerce.inventory_planner"}, A.A0_NONE, True, True, "none", "inventory_write", target="syncId"),
        _t("inventory.apply_sync", "Apply an inventory sync above the oversell-risk threshold.", M.EXTERNAL_ACTION, "high", {"commerce.inventory_planner"}, A.A3_STANDARD, True, True, "none", "inventory_write", target="syncId"),
        _t("inventory.alert_low_stock", "Raise a low-stock alert.", M.WRITE, "low", {"commerce.inventory_planner"}, A.A1_INTERNAL, True, False, "none", "internal_read", target="productId"),
        _t("fulfillment.route_order", "Route an order to a fulfillment location.", M.EXTERNAL_ACTION, "medium", {"commerce.fulfillment_coordinator"}, A.A2_LIGHTWEIGHT, True, True, "none", "inventory_write", target="orderId"),
        _t("fulfillment.update_tracking", "Update tracking information.", M.WRITE, "low", {"commerce.fulfillment_coordinator"}, A.A1_INTERNAL, True, False, "none", "internal_read", target="orderId"),
        _t("returns.recommend", "Record a return RECOMMENDATION (money never moves here).", M.WRITE, "medium", {"commerce.returns_processor"}, A.A2_LIGHTWEIGHT, True, False, "none", "payments_none", target="orderId"),
        # QA (§5.7)
        _t("qa.evaluate_output", "Evaluate an artifact against acceptance criteria.", M.READ, "low", {"qa.quality_gate"}, A.A0_NONE, True, False, "model_tokens", "internal_read", cost=lambda a: float(a.get("estimatedTokens", 1500))),
        _t("qa.block_release", "Block a release pending fixes.", M.WRITE, "medium", {"qa.quality_gate"}, A.A2_LIGHTWEIGHT, True, False, "none", "internal_read", target="executionId"),
        _t("qa.run_design_qa", "Run design QA checks on an asset.", M.READ, "low", {"qa.quality_gate"}, A.A0_NONE, True, False, "none", "internal_read"),
        # Analytics (§5.8, §5.9)
        _t("analytics.read_campaign_metrics", "Read campaign performance metrics.", M.READ, "low", {"analytics.metric_collector","marketers.campaign_manager"}, A.A0_NONE, True, False, "api_calls", "public_read"),
        _t("analytics.read_store_metrics", "Read store funnel metrics.", M.READ, "low", {"analytics.metric_collector","commerce.catalog_manager"}, A.A0_NONE, True, False, "api_calls", "internal_read"),
        _t("analytics.collect_business_metrics", "Collect a business metric snapshot.", M.WRITE, "low", {"analytics.metric_collector"}, A.A1_INTERNAL, True, False, "api_calls", "internal_read", target="metricId"),
        _t("analytics.detect_anomalies", "Detect anomalies against expected ranges.", M.READ, "low", {"analytics.metric_collector"}, A.A0_NONE, True, False, "none", "internal_read"),
        _t("analytics.report_outcome", "File an outcome report.", M.WRITE, "low", {"analytics.metric_collector"}, A.A1_INTERNAL, True, False, "none", "internal_read", target="reportId"),
        _t("research.submit_outcome", "Submit an outcome report into the Research Room.", M.EXTERNAL_ACTION, "medium", {"analytics.metric_collector"}, A.A2_LIGHTWEIGHT, True, False, "none", "internal_read", target="reportId"),
    ]
    for definition in defs:
        registry.register(definition)
    return registry
