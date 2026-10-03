/* =====================================================================
   COOLIE RESEARCH OS — backend-shaped objects
   These mirror the architecture document: Mission, ResearchTask, Agent,
   Evidence, Source, OpportunityRecord, ScoreDimension, RiskFinding,
   MoneyEvaluation, StrategyReview, RecommendationPacket, Approval,
   ToolRecord, AuditEvent, LearningRecord.
   MOCK_MODE = true for this prototype. See note at bottom of file.
   ===================================================================== */

export const MOCK_MODE = true;

/* ---------------------------- Lifecycle ---------------------------- */

export const LIFECYCLE = [
  "RECEIVED",
  "VALIDATING",
  "PLANNING",
  "RESEARCHING",
  "VERIFYING",
  "MODELING",
  "STRATEGIZING",
  "WAITING_FOR_APPROVAL",
  "SUBMITTED",
  "COMPLETED",
] as const;

export type Lifecycle = (typeof LIFECYCLE)[number] | "PAUSED" | "FAILED" | "ARCHIVED";

export const stageIndex = (s: Lifecycle) =>
  (LIFECYCLE as readonly string[]).indexOf(s);

export const stageMeta: Record<string, { label: string; tone: string }> = {
  RECEIVED: { label: "Received", tone: "slate" },
  VALIDATING: { label: "Validating", tone: "blue" },
  PLANNING: { label: "Planning", tone: "blue" },
  RESEARCHING: { label: "Researching", tone: "cyan" },
  VERIFYING: { label: "Verifying", tone: "violet" },
  MODELING: { label: "Modeling", tone: "violet" },
  STRATEGIZING: { label: "Strategizing", tone: "amber" },
  WAITING_FOR_APPROVAL: { label: "Awaiting approval", tone: "amber" },
  SUBMITTED: { label: "Submitted", tone: "emerald" },
  COMPLETED: { label: "Completed", tone: "emerald" },
  PAUSED: { label: "Paused", tone: "slate" },
  FAILED: { label: "Failed", tone: "rose" },
  ARCHIVED: { label: "Archived", tone: "slate" },
};

/* ---------------------------- Mission ---------------------------- */

export interface Mission {
  id: string;
  name: string;
  objective: string;
  market: string;
  scope: string;
  capitalLimit: string;
  timeLimit: string;
  evidenceRequirement: string;
  riskTolerance: string;
  allowedTools: string[];
  status: "ACTIVE" | "CLARIFICATION_REQUIRED" | "COMPLETED" | "PAUSED" | "FAILED";
  stage: Lifecycle;
  created: string;
  updated: string;
  clarification?: { question: string; options: string[] };
}

export const missions: Mission[] = [
  {
    id: "MSN-2026-0148",
    name: "UAE Home Fragrance Entry",
    objective:
      "Identify and validate one physically fulfilled home-fragrance product opportunity in the UAE that clears the Sharia gate and reaches break-even inside 90 days.",
    market: "United Arab Emirates · GCC",
    scope: "D2C e-commerce · physical goods · single SKU launch",
    capitalLimit: "$45,000",
    timeLimit: "14 days research · 90 days to break-even",
    evidenceRequirement:
      "Minimum 3 independent sources per material claim. Demand and supplier claims must be OBSERVED. Financial inputs must carry source + confidence.",
    riskTolerance: "Conservative · no trademark-conflicting goods, no restricted imports",
    allowedTools: ["web.search", "marketplace.scan", "supplier.directory", "trends.query", "currency.fx"],
    status: "ACTIVE",
    stage: "VERIFYING",
    created: "2026-02-09 06:02 GST",
    updated: "2026-02-11 14:41 GST",
  },
  {
    id: "MSN-2026-0149",
    name: "Halal Supplement Cross-Border",
    objective:
      "Assess whether a halal-certified supplement line can be launched into KSA from an EU fulfilment base.",
    market: "Kingdom of Saudi Arabia",
    scope: "Cross-border e-commerce · regulated goods",
    capitalLimit: "$120,000",
    timeLimit: "21 days research",
    evidenceRequirement: "Regulatory evidence must be primary-source. 5 sources per claim.",
    riskTolerance: "Moderate",
    allowedTools: ["web.search", "regulatory.lookup", "supplier.directory", "currency.fx"],
    status: "CLARIFICATION_REQUIRED",
    stage: "VALIDATING",
    created: "2026-02-10 09:15 GST",
    updated: "2026-02-10 11:02 GST",
    clarification: {
      question:
        "The objective names 'halal-certified supplement line' but does not constrain the product category. Certification cost and lead time vary by a factor of 6 across categories. Which constraint should bind?",
      options: [
        "Constrain to sports nutrition · fastest certification path",
        "Constrain to children's nutrition · highest margin, slowest path",
        "Leave category open · accept longer research horizon",
      ],
    },
  },
  {
    id: "MSN-2026-0131",
    name: "Modest Activewear Q4",
    objective: "Validate a modest activewear capsule for the GCC winter season.",
    market: "GCC",
    scope: "D2C apparel",
    capitalLimit: "$60,000",
    timeLimit: "Completed",
    evidenceRequirement: "3 sources per claim",
    riskTolerance: "Conservative",
    allowedTools: ["web.search", "marketplace.scan", "trends.query"],
    status: "COMPLETED",
    stage: "COMPLETED",
    created: "2026-01-14 08:00 GST",
    updated: "2026-02-02 17:30 GST",
  },
  {
    id: "MSN-2026-0136",
    name: "Specialty Coffee Subscriptions",
    objective: "Evaluate subscription coffee economics for the UAE market.",
    market: "UAE",
    scope: "Subscription · perishables",
    capitalLimit: "$30,000",
    timeLimit: "10 days",
    evidenceRequirement: "3 sources per claim",
    riskTolerance: "Conservative",
    allowedTools: ["web.search", "marketplace.scan"],
    status: "PAUSED",
    stage: "RESEARCHING",
    created: "2026-01-28 10:20 GST",
    updated: "2026-02-04 12:10 GST",
  },
];

/* ---------------------------- Agents ---------------------------- */

export interface Agent {
  id: string;
  n: string;
  purpose: string;
  task: string;
  missionId: string;
  status: "RUNNING" | "IDLE" | "BLOCKED" | "AWAITING_REVIEW";
  phase: Lifecycle;
  assigned: number;
  completed: number;
  failed: number;
  evidence: number;
  confidence: number;
  sources: number;
  workload: number;
  last: string;
  note: string;
}

export const agents: Agent[] = [
  { id: "AG-01", n: "Market Discovery Agent", purpose: "Establish market size, category activity and entry surface.", task: "Sweeping UAE home-fragrance category across 4 marketplaces", missionId: "MSN-2026-0148", status: "RUNNING", phase: "RESEARCHING", assigned: 3, completed: 2, failed: 0, evidence: 14, confidence: 86, sources: 9, workload: 72, last: "2 min ago", note: "Contributes market-structure findings to the mission. Does not decide." },
  { id: "AG-02", n: "Demand Validation Agent", purpose: "Test whether stated demand is real, repeated and commercially intended.", task: "Separating commercial-intent search volume from informational volume", missionId: "MSN-2026-0148", status: "RUNNING", phase: "VERIFYING", assigned: 2, completed: 1, failed: 0, evidence: 11, confidence: 74, sources: 6, workload: 58, last: "4 min ago", note: "Two of five demand signals failed the commercial-intent test." },
  { id: "AG-03", n: "Competitor Intelligence Agent", purpose: "Map incumbents, pricing, positioning and complaint surfaces.", task: "Reconciling conflicting price observations across 3 retailers", missionId: "MSN-2026-0148", status: "BLOCKED", phase: "VERIFYING", assigned: 2, completed: 1, failed: 1, evidence: 9, confidence: 61, sources: 7, workload: 44, last: "11 min ago", note: "Blocked on price conflict SRC-04 vs SRC-07. Escalated to verification." },
  { id: "AG-04", n: "Supplier & Fulfillment Agent", purpose: "Find real suppliers, unit economics, MOQ and delivery feasibility.", task: "Verifying MOQ and lead time with 2 candidate suppliers", missionId: "MSN-2026-0148", status: "RUNNING", phase: "RESEARCHING", assigned: 2, completed: 1, failed: 0, evidence: 8, confidence: 79, sources: 5, workload: 66, last: "6 min ago", note: "One supplier claim is INFERRED from listing data, not confirmed." },
  { id: "AG-05", n: "Audience & Customer Agent", purpose: "Define segments, severity of problem, objections and triggers.", task: "Clustering 1,240 reviews into objection groups", missionId: "MSN-2026-0148", status: "RUNNING", phase: "RESEARCHING", assigned: 1, completed: 1, failed: 0, evidence: 7, confidence: 83, sources: 4, workload: 39, last: "8 min ago", note: "Review corpus is OBSERVED; objection weighting is INFERRED." },
  { id: "AG-06", n: "Marketing Intelligence Agent", purpose: "Assess channel feasibility, cost and organic surface area.", task: "Estimating CPM bands for 3 paid channels", missionId: "MSN-2026-0148", status: "AWAITING_REVIEW", phase: "MODELING", assigned: 1, completed: 0, failed: 0, evidence: 5, confidence: 57, sources: 3, workload: 31, last: "14 min ago", note: "All CPM figures are CALCULATED estimates pending Evidence Verification Agent." },
  { id: "AG-07", n: "Product & Offer Agent", purpose: "Shape starter offer, bundle and upsell architecture.", task: "Drafting starter offer against observed price bands", missionId: "MSN-2026-0148", status: "IDLE", phase: "PLANNING", assigned: 1, completed: 0, failed: 0, evidence: 3, confidence: 68, sources: 4, workload: 12, last: "31 min ago", note: "Waiting on competitor price reconciliation to unblock." },
  { id: "AG-08", n: "Risk & Policy Agent", purpose: "Screen policy, IP, regulatory, payment and platform risk.", task: "Screening 6 candidate SKUs against trademark registry", missionId: "MSN-2026-0148", status: "RUNNING", phase: "VERIFYING", assigned: 2, completed: 1, failed: 0, evidence: 6, confidence: 91, sources: 5, workload: 54, last: "1 min ago", note: "Raised one blocking finding. See Risk & Policy Gate." },
  { id: "AG-09", n: "Evidence Verification Agent", purpose: "Independently re-verify claims and accept or reject evidence.", task: "Re-verifying 5 claims against independent sources", missionId: "MSN-2026-0148", status: "RUNNING", phase: "VERIFYING", assigned: 5, completed: 3, failed: 1, evidence: 22, confidence: 94, sources: 11, workload: 81, last: "Just now", note: "Gatekeeper. Agent output is not accepted until this agent validates it." },
  { id: "AG-10", n: "Synthesis Agent", purpose: "Assemble verified evidence into OpportunityRecords.", task: "Holding — awaiting verification quorum", missionId: "MSN-2026-0148", status: "IDLE", phase: "PLANNING", assigned: 1, completed: 0, failed: 0, evidence: 0, confidence: 0, sources: 0, workload: 8, last: "22 min ago", note: "Will not synthesise until verification quorum is met." },
];

/* ---------------------------- Task Graph ---------------------------- */

export type TaskState =
  | "QUEUED" | "RUNNING" | "BLOCKED" | "VERIFYING" | "COMPLETED" | "FAILED" | "RETRYING";

export interface ResearchTask {
  id: string;
  objective: string;
  agent: string;
  state: TaskState;
  priority: "P0" | "P1" | "P2";
  depends: string[];
  retries: number;
  timeout: string;
  cost: string;
  evidenceThreshold: string;
  output: string;
  criteria: string;
  col: number;
  row: number;
  accepted?: boolean;
}

export const tasks: ResearchTask[] = [
  { id: "TSK-01", objective: "Map UAE home-fragrance category structure", agent: "AG-01", state: "COMPLETED", priority: "P0", depends: [], retries: 0, timeout: "45m", cost: "$1.20", evidenceThreshold: "3 independent sources", output: "MarketStructureReport", criteria: "≥3 independent sources agree on category size within 20%", col: 0, row: 1, accepted: true },
  { id: "TSK-02", objective: "Validate commercial purchase intent", agent: "AG-02", state: "COMPLETED", priority: "P0", depends: ["TSK-01"], retries: 0, timeout: "60m", cost: "$2.40", evidenceThreshold: "3 sources · 1 behavioural", output: "DemandEvidence", criteria: "Commercial-intent share ≥40% of measured volume", col: 1, row: 0, accepted: true },
  { id: "TSK-03", objective: "Map competitors, pricing and complaints", agent: "AG-03", state: "BLOCKED", priority: "P0", depends: ["TSK-01"], retries: 1, timeout: "60m", cost: "$1.80", evidenceThreshold: "4 sources · conflict resolution required", output: "CompetitorMatrix", criteria: "No unresolved price conflict across sources", col: 1, row: 1 },
  { id: "TSK-04", objective: "Identify suppliers, MOQ and lead times", agent: "AG-04", state: "VERIFYING", priority: "P0", depends: ["TSK-01"], retries: 0, timeout: "90m", cost: "$3.10", evidenceThreshold: "2 confirmed suppliers", output: "SupplierOptions", criteria: "≥2 suppliers confirmed with stated MOQ", col: 2, row: 2 },
  { id: "TSK-05", objective: "Cluster audience objections and triggers", agent: "AG-05", state: "COMPLETED", priority: "P1", depends: ["TSK-02"], retries: 0, timeout: "40m", cost: "$0.90", evidenceThreshold: "≥400 reviewed data points", output: "AudienceProfile", criteria: "Objection clusters cover ≥70% of corpus", col: 2, row: 0, accepted: true },
  { id: "TSK-06", objective: "Estimate channel cost and organic surface", agent: "AG-06", state: "VERIFYING", priority: "P1", depends: ["TSK-02", "TSK-05"], retries: 0, timeout: "50m", cost: "$2.00", evidenceThreshold: "3 sources per channel", output: "MarketingAssessment", criteria: "All CPM figures carry source + confidence", col: 3, row: 0 },
  { id: "TSK-07", objective: "Shape starter offer against price bands", agent: "AG-07", state: "QUEUED", priority: "P1", depends: ["TSK-03"], retries: 0, timeout: "35m", cost: "$0.60", evidenceThreshold: "Observed price band from ≥4 retailers", output: "OfferArchitecture", criteria: "Offer sits inside observed price band", col: 3, row: 2 },
  { id: "TSK-08", objective: "Screen trademark and import restrictions", agent: "AG-08", state: "RUNNING", priority: "P0", depends: ["TSK-04"], retries: 0, timeout: "70m", cost: "$1.50", evidenceThreshold: "Registry check per SKU", output: "RiskFindings", criteria: "Zero unresolved blocking findings", col: 4, row: 2 },
  { id: "TSK-09", objective: "Independently verify all material claims", agent: "AG-09", state: "RUNNING", priority: "P0", depends: ["TSK-02", "TSK-03", "TSK-04", "TSK-05", "TSK-06"], retries: 1, timeout: "120m", cost: "$4.20", evidenceThreshold: "Quorum of 2 independent confirmations", output: "VerifiedEvidenceSet", criteria: "≥85% of material claims verified", col: 5, row: 1 },
  { id: "TSK-10", objective: "Assemble OpportunityRecord from verified evidence", agent: "AG-10", state: "QUEUED", priority: "P0", depends: ["TSK-09"], retries: 0, timeout: "40m", cost: "$0.80", evidenceThreshold: "Only verified evidence admitted", output: "OpportunityRecord", criteria: "Every field traces to an evidence ID", col: 6, row: 1 },
  { id: "TSK-11", objective: "Run financial evaluation via Money Calculator", agent: "system", state: "QUEUED", priority: "P0", depends: ["TSK-10"], retries: 0, timeout: "15m", cost: "$0.10", evidenceThreshold: "All inputs sourced", output: "MoneyEvaluation", criteria: "No unsourced financial input", col: 7, row: 1 },
  { id: "TSK-12", objective: "Request strategy review", agent: "system", state: "QUEUED", priority: "P1", depends: ["TSK-11"], retries: 0, timeout: "30m", cost: "$0.05", evidenceThreshold: "Complete strategic inputs", output: "StrategyReview", criteria: "Strategy manager returns a verdict", col: 8, row: 1 },
  { id: "TSK-13", objective: "Compile recommendation packet for approval", agent: "AG-10", state: "QUEUED", priority: "P0", depends: ["TSK-12"], retries: 0, timeout: "20m", cost: "$0.05", evidenceThreshold: "Full trace to evidence", output: "RecommendationPacket", criteria: "Owner can trace packet to source", col: 9, row: 1 },
];

export const taskStateMeta: Record<TaskState, { label: string; cls: string; dot: string }> = {
  QUEUED: { label: "QUEUED", cls: "text-slate-400 bg-white/[0.04] ring-white/10", dot: "bg-slate-500" },
  RUNNING: { label: "RUNNING", cls: "text-cyan-200 bg-cyan-400/10 ring-cyan-400/25", dot: "bg-cyan-400" },
  BLOCKED: { label: "BLOCKED", cls: "text-rose-200 bg-rose-400/10 ring-rose-400/25", dot: "bg-rose-400" },
  VERIFYING: { label: "VERIFYING", cls: "text-violet-200 bg-violet-400/10 ring-violet-400/25", dot: "bg-violet-400" },
  COMPLETED: { label: "COMPLETED", cls: "text-emerald-200 bg-emerald-400/10 ring-emerald-400/25", dot: "bg-emerald-400" },
  FAILED: { label: "FAILED", cls: "text-rose-200 bg-rose-500/15 ring-rose-400/30", dot: "bg-rose-500" },
  RETRYING: { label: "RETRYING", cls: "text-amber-200 bg-amber-400/10 ring-amber-400/25", dot: "bg-amber-400" },
};

/* ---------------------------- Sources ---------------------------- */

export interface Source {
  id: string;
  name: string;
  type: string;
  retrieved: string;
  quality: "HIGH" | "MEDIUM" | "LOW";
  freshness: "CURRENT" | "AGING" | "STALE" | "UNKNOWN";
  claims: number;
  usedBy: string[];
  tasks: string[];
  conflicts: string[];
  finding: "OBSERVED" | "CALCULATED" | "INFERRED";
  snapshot?: string;
}

export const sources: Source[] = [
  { id: "SRC-01", name: "Amazon.ae · Home Fragrance category crawl", type: "Marketplace listing", retrieved: "2026-02-11 06:14 GST", quality: "HIGH", freshness: "CURRENT", claims: 8, usedBy: ["AG-01", "AG-03"], tasks: ["TSK-01", "TSK-03"], conflicts: [], finding: "OBSERVED", snapshot: "snap-2026-02-11T0614Z.html" },
  { id: "SRC-02", name: "Google Trends · 'oud burner' UAE 24mo", type: "Search trends", retrieved: "2026-02-11 06:22 GST", quality: "MEDIUM", freshness: "CURRENT", claims: 4, usedBy: ["AG-02"], tasks: ["TSK-02"], conflicts: [], finding: "OBSERVED", snapshot: "trends-oud-burner-uae.csv" },
  { id: "SRC-03", name: "Noon.com · Bakhoor & Oud top-100", type: "Marketplace listing", retrieved: "2026-02-11 06:31 GST", quality: "HIGH", freshness: "CURRENT", claims: 6, usedBy: ["AG-01", "AG-05"], tasks: ["TSK-01", "TSK-05"], conflicts: [], finding: "OBSERVED", snapshot: "snap-noon-bakhoor.csv" },
  { id: "SRC-04", name: "Retailer A · published price list (PDF)", type: "First-party price list", retrieved: "2026-02-10 18:40 GST", quality: "MEDIUM", freshness: "AGING", claims: 3, usedBy: ["AG-03"], tasks: ["TSK-03"], conflicts: ["SRC-07"], finding: "OBSERVED", snapshot: "retailer-a-pricelist.pdf" },
  { id: "SRC-05", name: "Alibaba · supplier quotes (3 verified)", type: "Supplier directory", retrieved: "2026-02-11 07:05 GST", quality: "MEDIUM", freshness: "CURRENT", claims: 5, usedBy: ["AG-04"], tasks: ["TSK-04"], conflicts: [], finding: "OBSERVED", snapshot: "alibaba-quotes.pdf" },
  { id: "SRC-06", name: "1,240 product reviews · corpus", type: "Review corpus", retrieved: "2026-02-11 07:20 GST", quality: "HIGH", freshness: "CURRENT", claims: 7, usedBy: ["AG-05"], tasks: ["TSK-05"], conflicts: [], finding: "OBSERVED", snapshot: "reviews-corpus.json" },
  { id: "SRC-07", name: "Retailer B · Shopify storefront scrape", type: "Storefront scrape", retrieved: "2026-02-11 07:48 GST", quality: "LOW", freshness: "CURRENT", claims: 3, usedBy: ["AG-03"], tasks: ["TSK-03"], conflicts: ["SRC-04"], finding: "OBSERVED", snapshot: "retailer-b-scrape.html" },
  { id: "SRC-08", name: "Meta Ads Library · GCC fragrance ads", type: "Ad library", retrieved: "2026-02-11 08:02 GST", quality: "MEDIUM", freshness: "CURRENT", claims: 4, usedBy: ["AG-06"], tasks: ["TSK-06"], conflicts: [], finding: "OBSERVED", snapshot: "meta-ads-library.csv" },
  { id: "SRC-09", name: "CPM benchmark model · internal", type: "Internal model", retrieved: "2026-02-11 08:15 GST", quality: "LOW", freshness: "UNKNOWN", claims: 3, usedBy: ["AG-06"], tasks: ["TSK-06"], conflicts: [], finding: "CALCULATED" },
  { id: "SRC-10", name: "UAE trademark registry · class 3", type: "Government registry", retrieved: "2026-02-11 08:30 GST", quality: "HIGH", freshness: "CURRENT", claims: 6, usedBy: ["AG-08"], tasks: ["TSK-08"], conflicts: [], finding: "OBSERVED", snapshot: "tm-class3-uae.pdf" },
  { id: "SRC-11", name: "Analyst synthesis · positioning read", type: "Derived analysis", retrieved: "2026-02-11 09:00 GST", quality: "MEDIUM", freshness: "CURRENT", claims: 2, usedBy: ["AG-07"], tasks: ["TSK-07"], conflicts: [], finding: "INFERRED" },
];

/* ---------------------------- Evidence ---------------------------- */

export interface Evidence {
  id: string;
  claim: string;
  sourceId: string;
  sourceType: string;
  retrieved: string;
  type: "OBSERVED" | "CALCULATED" | "INFERRED";
  confidence: number;
  freshness: "CURRENT" | "AGING" | "STALE" | "UNKNOWN";
  limitations: string;
  missionId: string;
  taskId: string;
  opportunityId: string;
  verified: boolean;
  rejected?: boolean;
  rejectionReason?: string;
}

export const evidence: Evidence[] = [
  { id: "EV-001", claim: "UAE home-fragrance category lists 4,180 active SKUs across the two dominant marketplaces.", sourceId: "SRC-01", sourceType: "Marketplace listing", retrieved: "2026-02-11 06:14", type: "OBSERVED", confidence: 92, freshness: "CURRENT", limitations: "Counts listings, not sales. Delisted items excluded.", missionId: "MSN-2026-0148", taskId: "TSK-01", opportunityId: "OPP-0091", verified: true },
  { id: "EV-002", claim: "Search interest for 'oud burner' in the UAE rose 34% over 24 months with a Nov–Jan peak.", sourceId: "SRC-02", sourceType: "Search trends", retrieved: "2026-02-11 06:22", type: "OBSERVED", confidence: 78, freshness: "CURRENT", limitations: "Relative volume only. No absolute purchase data. Seasonal peak may skew annual read.", missionId: "MSN-2026-0148", taskId: "TSK-02", opportunityId: "OPP-0091", verified: true },
  { id: "EV-003", claim: "68% of measured search volume carries commercial intent ('buy', 'price', 'delivery'), above the 40% threshold.", sourceId: "SRC-02", sourceType: "Search trends", retrieved: "2026-02-11 06:22", type: "CALCULATED", confidence: 71, freshness: "CURRENT", limitations: "Intent classification is model-based, not human-labelled.", missionId: "MSN-2026-0148", taskId: "TSK-02", opportunityId: "OPP-0091", verified: true },
  { id: "EV-004", claim: "Median observed retail price for a ceramic oud burner is AED 129 across 41 listings.", sourceId: "SRC-01", sourceType: "Marketplace listing", retrieved: "2026-02-11 06:14", type: "OBSERVED", confidence: 88, freshness: "CURRENT", limitations: "Excludes bundle listings. 6 of 47 listings had no price.", missionId: "MSN-2026-0148", taskId: "TSK-03", opportunityId: "OPP-0091", verified: true },
  { id: "EV-005", claim: "Retailer A lists an equivalent burner at AED 95 while Retailer B shows AED 189 for the same SKU.", sourceId: "SRC-04", sourceType: "First-party price list", retrieved: "2026-02-10 18:40", type: "OBSERVED", confidence: 44, freshness: "AGING", limitations: "CONFLICT unresolved. Retailer A list is 26h old and may reflect a promotion. Retailer B scrape quality rated LOW.", missionId: "MSN-2026-0148", taskId: "TSK-03", opportunityId: "OPP-0091", verified: false },
  { id: "EV-006", claim: "Confirmed supplier quotes land at $6.80–$9.20/unit FOB at MOQ 500.", sourceId: "SRC-05", sourceType: "Supplier directory", retrieved: "2026-02-11 07:05", type: "OBSERVED", confidence: 84, freshness: "CURRENT", limitations: "Quotes valid 14 days. Does not include tooling for custom glaze.", missionId: "MSN-2026-0148", taskId: "TSK-04", opportunityId: "OPP-0091", verified: true },
  { id: "EV-007", claim: "Estimated landed unit cost of AED 41 including freight, 5% duty and last-mile.", sourceId: "SRC-05", sourceType: "Supplier directory", retrieved: "2026-02-11 07:05", type: "CALCULATED", confidence: 76, freshness: "CURRENT", limitations: "Freight rate taken from a spot quote; duty assumed at 5% pending customs confirmation.", missionId: "MSN-2026-0148", taskId: "TSK-04", opportunityId: "OPP-0091", verified: false },
  { id: "EV-008", claim: "Top three complaint clusters in 1,240 reviews are: weak scent throw (31%), cracking on arrival (22%), packaging not gift-ready (18%).", sourceId: "SRC-06", sourceType: "Review corpus", retrieved: "2026-02-11 07:20", type: "OBSERVED", confidence: 86, freshness: "CURRENT", limitations: "Corpus is marketplace-only; no direct customer interviews. Complaint weighting is INFERRED.", missionId: "MSN-2026-0148", taskId: "TSK-05", opportunityId: "OPP-0091", verified: true },
  { id: "EV-009", claim: "Estimated blended CPM of AED 22 across Meta and TikTok for the GCC fragrance vertical.", sourceId: "SRC-09", sourceType: "Internal model", retrieved: "2026-02-11 08:15", type: "CALCULATED", confidence: 52, freshness: "UNKNOWN", limitations: "Model-derived, no primary buy data. Requires verification before any spend decision.", missionId: "MSN-2026-0148", taskId: "TSK-06", opportunityId: "OPP-0091", verified: false },
  { id: "EV-010", claim: "Candidate SKU 'Amber Oud No. 4' has no live trademark conflict in UAE class 3.", sourceId: "SRC-10", sourceType: "Government registry", retrieved: "2026-02-11 08:30", type: "OBSERVED", confidence: 95, freshness: "CURRENT", limitations: "Registry check is point-in-time. Filing within 14 days recommended.", missionId: "MSN-2026-0148", taskId: "TSK-08", opportunityId: "OPP-0091", verified: true },
  { id: "EV-011", claim: "Positioning as a gift-first premium burner should command the top quartile of the observed price band.", sourceId: "SRC-11", sourceType: "Derived analysis", retrieved: "2026-02-11 09:00", type: "INFERRED", confidence: 58, freshness: "CURRENT", limitations: "Inference from review-sentiment and price-band correlation. Not directly tested with buyers.", missionId: "MSN-2026-0148", taskId: "TSK-07", opportunityId: "OPP-0091", verified: false },
  { id: "EV-012", claim: "Two incumbent brands hold registered figurative marks that visually resemble the candidate packaging direction.", sourceId: "SRC-10", sourceType: "Government registry", retrieved: "2026-02-11 08:30", type: "OBSERVED", confidence: 90, freshness: "CURRENT", limitations: "Visual similarity assessed by agent; requires counsel review before use.", missionId: "MSN-2026-0148", taskId: "TSK-08", opportunityId: "OPP-0091", verified: true },
  { id: "EV-013", claim: "KSA supplement import permit requires in-country legal representation.", sourceId: "SRC-10", sourceType: "Government registry", retrieved: "2026-02-10 12:00", type: "OBSERVED", confidence: 93, freshness: "CURRENT", limitations: "Primary source confirmed. Cost of representation not yet quantified.", missionId: "MSN-2026-0149", taskId: "TSK-01", opportunityId: "OPP-0094", verified: true },
  { id: "EV-014", claim: "Reported 4.6x return on ad spend for a comparable GCC fragrance launch.", sourceId: "SRC-07", sourceType: "Storefront scrape", retrieved: "2026-02-11 07:48", type: "INFERRED", confidence: 21, freshness: "CURRENT", limitations: "REJECTED. Source quality LOW and figure is a vendor marketing claim with no methodology.", missionId: "MSN-2026-0148", taskId: "TSK-06", opportunityId: "OPP-0091", verified: false, rejected: true, rejectionReason: "Single unverified vendor claim. No methodology disclosed. Source quality LOW." },
];

export const freshnessMeta: Record<string, { cls: string; dot: string }> = {
  CURRENT: { cls: "text-emerald-200 bg-emerald-400/10 ring-emerald-400/25", dot: "bg-emerald-400" },
  AGING: { cls: "text-amber-200 bg-amber-400/10 ring-amber-400/25", dot: "bg-amber-400" },
  STALE: { cls: "text-rose-200 bg-rose-400/10 ring-rose-400/25", dot: "bg-rose-400" },
  UNKNOWN: { cls: "text-slate-300 bg-white/[0.05] ring-white/15", dot: "bg-slate-500" },
};

export const evidenceTypeMeta: Record<string, { cls: string; icon: string }> = {
  OBSERVED: { cls: "text-emerald-200 ring-emerald-400/30 bg-emerald-400/10", icon: "◉" },
  CALCULATED: { cls: "text-cyan-200 ring-cyan-400/30 bg-cyan-400/10", icon: "∑" },
  INFERRED: { cls: "text-violet-200 ring-violet-400/30 bg-violet-400/10", icon: "∴" },
};

/* ---------------------------- Opportunities ---------------------------- */

export interface ScoreDim {
  label: string;
  value: number;
  why: { evidence: string[]; assumptions: string[] };
}

export interface Opp {
  id: string;
  name: string;
  model: string;
  market: string;
  problem: string;
  offer: string;
  status:
    | "Researching" | "Validating" | "Promising" | "Needs more research"
    | "Validation required" | "Approval required" | "Rejected" | "Archived" | "Limited launch";
  confidence: number;
  demandEvidence: string;
  competitors: string;
  suppliers: string;
  fulfillment: string;
  marketing: string;
  risk: string;
  scores: ScoreDim[];
  dossier: {
    demand: { k: string; v: string; ev: string; kind: "OBSERVED" | "CALCULATED" | "INFERRED" }[];
    competitors: { k: string; v: string; kind: "OBSERVED" | "INFERRED"; ev: string }[];
    suppliers: { k: string; v: string; ev: string; kind?: string }[];
    audience: { k: string; v: string; ev: string; kind?: string }[];
    marketing: { k: string; v: string; ev: string; kind?: string }[];
    product: { k: string; v: string; ev: string; kind?: string }[];
    validation: { k: string; v: string }[];
    history: { when: string; what: string; by: string; immutable: boolean }[];
  };
}

export const opportunities: Opp[] = [
  {
    id: "OPP-0091",
    name: "Amber Oud No. 4 · Gift-Grade Burner",
    model: "D2C e-commerce · single SKU · physical fulfilment",
    market: "UAE · English + Arabic · Dubai & Abu Dhabi first",
    problem: "Buyers want a burner that reads as a gift, not a cheap import; 31% of reviews cite weak scent throw and 22% cite breakage in transit.",
    offer: "One gift-grade ceramic burner at AED 169 with a protective double-wall box and a scent-intensity card.",
    status: "Approval required",
    confidence: 74,
    demandEvidence: "4,180 active SKUs (EV-001); 34% 24-month search growth with Nov–Jan peak (EV-002); 68% commercial-intent share (EV-003).",
    competitors: "Median AED 129 across 41 listings (EV-004). Two incumbents own premium positioning. One unresolved price conflict (EV-005).",
    suppliers: "Two confirmed suppliers at $6.80–$9.20 FOB, MOQ 500 (EV-006). Landed cost estimated at AED 41 (EV-007, CALCULATED).",
    fulfillment: "Feasible. Air freight 9–12 days, last-mile via local courier. Custom glaze would add tooling and 3 weeks.",
    marketing: "Organic search surface is strong; paid CPM is modelled, not verified (EV-009). Ad library shows 14 active competitors (EV-008).",
    risk: "No trademark conflict on candidate name (EV-010). Two incumbents hold visually similar figurative marks (EV-012) — packaging direction must change.",
    scores: [
      { label: "Demand", value: 82, why: { evidence: ["EV-001", "EV-002", "EV-003"], assumptions: ["Search interest proxies purchase interest in this category", "Seasonal peak is repeatable rather than a one-off trend"] } },
      { label: "Competition", value: 64, why: { evidence: ["EV-004", "EV-005"], assumptions: ["Price conflict resolves toward the higher observed band", "Premium tier is not already saturated"] } },
      { label: "Margin", value: 77, why: { evidence: ["EV-004", "EV-006", "EV-007"], assumptions: ["Landed cost holds at AED 41 (CALCULATED, unverified)", "Duty stays at 5%"] } },
      { label: "Fulfillment", value: 81, why: { evidence: ["EV-006", "EV-008"], assumptions: ["Breakage rate stays under 3% with double-wall packaging", "Spot freight rate is representative"] } },
      { label: "Marketing feasibility", value: 59, why: { evidence: ["EV-008", "EV-009"], assumptions: ["Blended CPM of AED 22 is achievable (CALCULATED, unverified)", "Organic can carry 30% of first-quarter volume"] } },
      { label: "Strategic fit", value: 86, why: { evidence: ["EV-010", "EV-011"], assumptions: ["Gift-first positioning is compatible with the existing holdings strategy"] } },
      { label: "Risk", value: 68, why: { evidence: ["EV-010", "EV-012"], assumptions: ["Packaging redesign resolves visual-similarity exposure", "No platform policy change in the launch window"] } },
      { label: "Evidence confidence", value: 71, why: { evidence: ["EV-005", "EV-007", "EV-009", "EV-014"], assumptions: ["Two material inputs remain unverified", "One evidence item rejected outright"] } },
    ],
    dossier: {
      demand: [
        { k: "Search demand · 'oud burner' UAE", v: "34% growth over 24 months, Nov–Jan peak", ev: "EV-002", kind: "OBSERVED" },
        { k: "Commercial-intent share", v: "68% of measured volume (threshold 40%)", ev: "EV-003", kind: "CALCULATED" },
        { k: "Marketplace activity", v: "4,180 active SKUs across 2 marketplaces", ev: "EV-001", kind: "OBSERVED" },
        { k: "Social engagement", v: "14 active paid competitors in Meta Ad Library", ev: "EV-008", kind: "OBSERVED" },
        { k: "Seasonality", v: "Peak Nov–Jan; trough Jun–Jul. Launch must land before November.", ev: "EV-002", kind: "OBSERVED" },
        { k: "Repeat purchase", v: "Low for burners alone. Requires consumable attach to build LTV.", ev: "EV-011", kind: "INFERRED" },
        { k: "Geographic relevance", v: "Concentrated Dubai (54%) and Abu Dhabi (23%) of review corpus", ev: "EV-008", kind: "OBSERVED" },
      ],
      competitors: [
        { k: "Median price · 41 listings", v: "AED 129", kind: "OBSERVED", ev: "EV-004" },
        { k: "Premium tier ceiling", v: "AED 189 (single retailer, LOW-quality source)", kind: "OBSERVED", ev: "EV-005" },
        { k: "Positioning", v: "Two incumbents own 'premium gift'. None lead on breakage guarantee.", kind: "INFERRED", ev: "EV-008" },
        { k: "Delivery promise", v: "Category standard is 3–5 days domestic", kind: "OBSERVED", ev: "EV-001" },
        { k: "Dominant complaint", v: "Weak scent throw (31%) and transit cracking (22%) — a defensible wedge", kind: "OBSERVED", ev: "EV-008" },
        { k: "Differentiation available", v: "Breakage-replacement guarantee + scent-intensity specification", kind: "INFERRED", ev: "EV-011" },
      ],
      suppliers: [
        { k: "Supplier A · Shenzhen ceramics", v: "$6.80/unit FOB · MOQ 500 · 22 days", ev: "EV-006" },
        { k: "Supplier B · Guangzhou ceramics", v: "$9.20/unit FOB · MOQ 500 · 14 days", ev: "EV-006" },
        { k: "Shipping", v: "Air freight 9–12 days · spot rate, not contracted", ev: "EV-007" },
        { k: "Delivery region", v: "UAE only at launch. KSA requires a separate customs registrant.", ev: "EV-007" },
        { k: "Returns", v: "Local return address required; no 3PL confirmed yet", ev: "EV-007" },
        { k: "Customs / import", v: "5% duty ASSUMED, not confirmed with customs", ev: "EV-007" },
        { k: "Local alternative", v: "One UAE pottery workshop found; unit cost 3.1x higher but zero import risk", ev: "EV-006" },
        { k: "Fulfillment feasibility", v: "Feasible without custom tooling. Custom glaze adds 3 weeks + tooling.", ev: "EV-006" },
      ],
      audience: [
        { k: "Segment", v: "Gift buyers, 28–45, UAE, mixed Arabic/English", ev: "EV-008" },
        { k: "Problem severity", v: "High for gifting occasions; low for personal use", ev: "EV-008" },
        { k: "Motivation", v: "Appearance and perceived quality outrank price in review language", ev: "EV-008" },
        { k: "Objections", v: "Weak throw (31%), transit cracking (22%), packaging not gift-ready (18%)", ev: "EV-008" },
        { k: "Budget", v: "Willingness clusters AED 120–180, above the AED 129 median", ev: "EV-011" },
        { k: "Triggers", v: "Eid, Diwali, wedding season, corporate gifting cycles", ev: "EV-002" },
        { k: "Channels", v: "Instagram and TikTok discovery; search for purchase", ev: "EV-008" },
        { k: "Retention potential", v: "Depends entirely on a consumable attach (oud chips, pellets)", ev: "EV-011" },
      ],
      marketing: [
        { k: "Primary channel", v: "Instagram + TikTok short-form for discovery", ev: "EV-008" },
        { k: "Campaign angle", v: "'Doesn't crack, actually throws' — attacks the two dominant complaints", ev: "EV-008" },
        { k: "Organic opportunity", v: "Unclaimed search surface around scent-throw comparisons", ev: "EV-011" },
        { k: "Influencers / affiliates", v: "12 mid-tier UAE home accounts identified, not yet contacted", ev: "EV-011" },
        { k: "Testing requirement", v: "CPM figure is modelled (EV-009). A AED 3,000 test buy must precede any scale decision.", ev: "EV-009" },
      ],
      product: [
        { k: "Starter offer", v: "One burner, AED 169, double-wall gift box", ev: "EV-004" },
        { k: "Bundle", v: "Burner + 90g oud chips at AED 219", ev: "EV-011" },
        { k: "Subscription", v: "Quarterly consumable refill · not validated", ev: "EV-011" },
        { k: "Upsell", v: "Extended breakage cover at checkout", ev: "EV-011" },
        { k: "Cross-sell", v: "Muhassabah charcoal and tongs", ev: "EV-011" },
        { k: "Trial", v: "Not applicable for a physical durable at this price", ev: "EV-011" },
        { k: "Localization", v: "Bilingual Arabic/English packaging required for retail credibility", ev: "EV-008" },
      ],
      validation: [
        { k: "Experiment 1", v: "AED 3,000 paid test to validate CPM and landing conversion before any inventory commitment" },
        { k: "Experiment 2", v: "Pre-order landing page with 50-unit commitment threshold over 10 days" },
        { k: "Experiment 3", v: "Ship 20 units through the real courier to measure actual breakage rate" },
        { k: "Experiment 4", v: "Resolve the AED 95 vs AED 189 price conflict with a manual retailer audit" },
        { k: "Requirement", v: "Break-even contribution margin must be re-modelled with verified landed cost before approval" },
      ],
      history: [
        { when: "2026-02-11 06:20", what: "OpportunityRecord created from verified market structure", by: "AG-10 Synthesis", immutable: true },
        { when: "2026-02-11 08:05", what: "Evidence EV-014 rejected — unverified vendor ROAS claim", by: "AG-09 Verification", immutable: true },
        { when: "2026-02-11 09:12", what: "Blocking risk finding raised on packaging visual similarity", by: "AG-08 Risk & Policy", immutable: true },
        { when: "2026-02-11 14:41", what: "Financial evaluation requested from Money Calculator", by: "System", immutable: true },
        { when: "2026-02-11 14:52", what: "Recommendation packet compiled · REQUEST_APPROVAL", by: "AG-10 Synthesis", immutable: true },
      ],
    },
  },
  {
    id: "OPP-0092",
    name: "Refill-First Oud Chip Subscription",
    model: "Subscription · consumable",
    market: "UAE",
    problem: "Burner owners have no reliable local source for quality consumable chips.",
    offer: "Quarterly 90g chip refill at AED 89.",
    status: "Validation required",
    confidence: 48,
    demandEvidence: "Inferred from burner attach logic. No independent demand measurement yet.",
    competitors: "Two incumbents sell consumables as an afterthought, not a subscription.",
    suppliers: "One supplier identified. MOQ unconfirmed.",
    fulfillment: "Feasible; light parcel. Cold chain not required.",
    marketing: "Depends entirely on first owning the hardware customer.",
    risk: "Churn assumption is unsupported. No retention evidence.",
    scores: [
      { label: "Demand", value: 41, why: { evidence: ["EV-011"], assumptions: ["Burner buyers want refills from the same brand"] } },
      { label: "Competition", value: 70, why: { evidence: ["EV-004"], assumptions: ["Incumbents will not lead with subscriptions"] } },
      { label: "Margin", value: 66, why: { evidence: ["EV-006"], assumptions: ["Chip cost scales linearly with volume"] } },
      { label: "Fulfillment", value: 84, why: { evidence: ["EV-006"], assumptions: ["No cold chain or hazmat constraint"] } },
      { label: "Marketing feasibility", value: 38, why: { evidence: ["EV-009"], assumptions: ["Acquisition cost can be amortised over 3 cycles"] } },
      { label: "Strategic fit", value: 79, why: { evidence: ["EV-011"], assumptions: ["Complements the hardware opportunity rather than cannibalising it"] } },
      { label: "Risk", value: 72, why: { evidence: ["EV-010"], assumptions: ["No regulatory exposure for processed wood chips"] } },
      { label: "Evidence confidence", value: 34, why: { evidence: ["EV-011"], assumptions: ["Nearly all supporting material is INFERRED"] } },
    ],
    dossier: {
      demand: [{ k: "Measured demand", v: "None. Entirely inferred from hardware attach logic.", ev: "EV-011", kind: "INFERRED" }],
      competitors: [{ k: "Incumbent behaviour", v: "Consumables sold as accessories, not subscriptions", kind: "INFERRED", ev: "EV-004" }],
      suppliers: [{ k: "Supplier", v: "One candidate, MOQ unconfirmed", ev: "EV-006" }],
      audience: [{ k: "Segment", v: "Existing burner owners — size unknown", ev: "EV-011" }],
      marketing: [{ k: "Channel", v: "Owned post-purchase only", ev: "EV-011" }],
      product: [{ k: "Offer", v: "Quarterly 90g refill, AED 89", ev: "EV-011" }],
      validation: [{ k: "Requirement", v: "Measure real attach intent from 100 hardware buyers before any build" }],
      history: [{ when: "2026-02-11 09:40", what: "OpportunityRecord created — flagged low evidence confidence", by: "AG-10 Synthesis", immutable: true }],
    },
  },
  {
    id: "OPP-0093",
    name: "Corporate Gifting Bulk Tier",
    model: "B2B · bulk order",
    market: "UAE · corporate procurement",
    problem: "Companies need culturally appropriate gifts at predictable volume.",
    offer: "Bulk burner + chips tier at AED 142/unit from 50 units.",
    status: "Promising",
    confidence: 69,
    demandEvidence: "Review corpus references corporate gifting repeatedly. No procurement-side interviews.",
    competitors: "No incumbent leads on B2B gifting in this category.",
    suppliers: "Same supplier base as OPP-0091. MOQ satisfied naturally.",
    fulfillment: "Simple; single-drop pallet delivery.",
    marketing: "Outbound-led. Low paid-media dependency.",
    risk: "Long payment terms strain working capital at the stated capital limit.",
    scores: [
      { label: "Demand", value: 62, why: { evidence: ["EV-008"], assumptions: ["Review mentions translate into procurement demand"] } },
      { label: "Competition", value: 78, why: { evidence: ["EV-004"], assumptions: ["B2B tier is genuinely unserved"] } },
      { label: "Margin", value: 58, why: { evidence: ["EV-007"], assumptions: ["Bulk discount does not exceed 18%"] } },
      { label: "Fulfillment", value: 88, why: { evidence: ["EV-006"], assumptions: ["Pallet delivery available at this volume"] } },
      { label: "Marketing feasibility", value: 71, why: { evidence: ["EV-011"], assumptions: ["Outbound can reach procurement without paid media"] } },
      { label: "Strategic fit", value: 74, why: { evidence: ["EV-011"], assumptions: ["B2B smooths seasonality of D2C"] } },
      { label: "Risk", value: 55, why: { evidence: ["EV-007"], assumptions: ["Payment terms within 45 days"] } },
      { label: "Evidence confidence", value: 52, why: { evidence: ["EV-008"], assumptions: ["No procurement-side primary evidence yet"] } },
    ],
    dossier: {
      demand: [{ k: "Signal", v: "Repeated corporate-gifting references in review corpus", ev: "EV-008", kind: "OBSERVED" }],
      competitors: [{ k: "B2B coverage", v: "No incumbent leads the tier", kind: "INFERRED", ev: "EV-004" }],
      suppliers: [{ k: "Supplier base", v: "Shared with OPP-0091; MOQ met at 50 units", ev: "EV-006" }],
      audience: [{ k: "Buyer", v: "HR and marketing procurement, Q3–Q4 peak", ev: "EV-008" }],
      marketing: [{ k: "Channel", v: "Direct outbound and LinkedIn", ev: "EV-011" }],
      product: [{ k: "Offer", v: "AED 142/unit from 50 units, co-branded card option", ev: "EV-011" }],
      validation: [{ k: "Requirement", v: "Run 5 procurement discovery calls before committing capital" }],
      history: [{ when: "2026-02-11 10:05", what: "OpportunityRecord created", by: "AG-10 Synthesis", immutable: true }],
    },
  },
  {
    id: "OPP-0094",
    name: "KSA Halal Supplement Line",
    model: "Cross-border · regulated",
    market: "Kingdom of Saudi Arabia",
    problem: "Demand for certified supplements outpaces local supply.",
    offer: "Three-SKU certified line.",
    status: "Needs more research",
    confidence: 31,
    demandEvidence: "Mission paused pending clarification. No demand evidence collected.",
    competitors: "Not researched.",
    suppliers: "Not researched.",
    fulfillment: "Requires in-country legal representation (EV-013).",
    marketing: "Not researched.",
    risk: "Regulatory cost unknown. Category constraint unresolved.",
    scores: [
      { label: "Demand", value: 30, why: { evidence: [], assumptions: ["No measurement performed — mission awaiting clarification"] } },
      { label: "Competition", value: 40, why: { evidence: [], assumptions: ["Unresearched"] } },
      { label: "Margin", value: 45, why: { evidence: ["EV-013"], assumptions: ["Certification cost unknown"] } },
      { label: "Fulfillment", value: 35, why: { evidence: ["EV-013"], assumptions: ["Legal representation cost unquantified"] } },
      { label: "Marketing feasibility", value: 40, why: { evidence: [], assumptions: ["Unresearched"] } },
      { label: "Strategic fit", value: 50, why: { evidence: [], assumptions: ["Unresearched"] } },
      { label: "Risk", value: 22, why: { evidence: ["EV-013"], assumptions: ["Regulatory exposure is the dominant unknown"] } },
      { label: "Evidence confidence", value: 15, why: { evidence: ["EV-013"], assumptions: ["Only one evidence item collected"] } },
    ],
    dossier: {
      demand: [{ k: "Status", v: "Mission in VALIDATING — clarification required before research begins", ev: "—", kind: "OBSERVED" }],
      competitors: [{ k: "Status", v: "Not started", ev: "—", kind: "OBSERVED" }],
      suppliers: [{ k: "Status", v: "Not started", ev: "—", kind: "OBSERVED" }],
      audience: [{ k: "Status", v: "Not started", ev: "—", kind: "OBSERVED" }],
      marketing: [{ k: "Status", v: "Not started", ev: "—", kind: "OBSERVED" }],
      product: [{ k: "Status", v: "Category constraint unresolved", ev: "—", kind: "OBSERVED" }],
      validation: [{ k: "Blocking", v: "Owner must choose a category constraint before research proceeds" }],
      history: [{ when: "2026-02-10 11:02", what: "Mission paused — ambiguity escalated to owner", by: "System", immutable: true }],
    },
  },
];

export const oppStatusMeta: Record<string, { cls: string; dot: string }> = {
  Researching: { cls: "text-cyan-200 bg-cyan-400/10 ring-cyan-400/25", dot: "bg-cyan-400" },
  Validating: { cls: "text-blue-200 bg-blue-400/10 ring-blue-400/25", dot: "bg-blue-400" },
  Promising: { cls: "text-emerald-200 bg-emerald-400/10 ring-emerald-400/25", dot: "bg-emerald-400" },
  "Needs more research": { cls: "text-slate-200 bg-white/[0.06] ring-white/15", dot: "bg-slate-400" },
  "Validation required": { cls: "text-violet-200 bg-violet-400/10 ring-violet-400/25", dot: "bg-violet-400" },
  "Approval required": { cls: "text-amber-200 bg-amber-400/10 ring-amber-400/25", dot: "bg-amber-400" },
  Rejected: { cls: "text-rose-200 bg-rose-400/10 ring-rose-400/25", dot: "bg-rose-400" },
  Archived: { cls: "text-slate-400 bg-white/[0.04] ring-white/10", dot: "bg-slate-500" },
  "Limited launch": { cls: "text-lime-200 bg-lime-400/10 ring-lime-400/25", dot: "bg-lime-400" },
};

/* ---------------------------- Risk gate ---------------------------- */

export interface RiskFinding {
  id: string;
  severity: "BLOCKING" | "WARNING" | "INFO";
  area: string;
  finding: string;
  reason: string;
  evidence: string;
  action: string;
}

export const riskFindings: RiskFinding[] = [
  { id: "RSK-07", severity: "BLOCKING", area: "IP / Trademark", finding: "Candidate packaging direction is visually similar to two registered figurative marks in UAE class 3.", reason: "Launching as drawn creates a credible infringement exposure and a takedown risk on marketplace channels.", evidence: "EV-012", action: "Redesign packaging with counsel review before any listing is created." },
  { id: "RSK-04", severity: "WARNING", area: "Customs / Import", finding: "Import duty assumed at 5% without customs confirmation.", reason: "A duty move to 12% removes roughly 11 points of contribution margin.", evidence: "EV-007", action: "Obtain written customs confirmation before capital commitment." },
  { id: "RSK-05", severity: "WARNING", area: "Financial input", finding: "Landed unit cost is a CALCULATED estimate, not an observed cost.", reason: "Freight is a spot quote and may not be representative at MOQ 500.", evidence: "EV-007", action: "Convert to an observed cost with a contracted freight quote." },
  { id: "RSK-09", severity: "WARNING", area: "Marketing", finding: "Blended CPM of AED 22 is model-derived with UNKNOWN freshness.", reason: "Acquisition cost is the largest unverified variable in the model.", evidence: "EV-009", action: "Run the AED 3,000 test buy before any scale decision." },
  { id: "RSK-02", severity: "INFO", area: "Policy", finding: "Product category is permitted on both target marketplaces.", reason: "No restricted-substance or platform-policy flag found.", evidence: "EV-010", action: "No action required." },
  { id: "RSK-03", severity: "INFO", area: "Payment", finding: "No fraud or chargeback signal in the category.", reason: "Chargeback rate for home goods in UAE is within normal band.", evidence: "EV-008", action: "No action required." },
];

export const riskChecksPassed = [
  "Platform policy · both marketplaces",
  "Payment / fraud screening",
  "Privacy · no personal data in corpus",
  "Sharia gate · structure compliant",
  "Return-handling feasibility",
];

/* ---------------------------- Money calculator ---------------------------- */

export interface MoneyInput {
  label: string;
  value: string;
  currency: string;
  source: string;
  confidence: number;
  ts: string;
  estimate: boolean;
  ev: string;
}

export const moneyInputs: MoneyInput[] = [
  { label: "Selling price", value: "169.00", currency: "AED", source: "SRC-01 · observed median of premium tier", confidence: 88, ts: "2026-02-11 06:14", estimate: false, ev: "EV-004" },
  { label: "Product cost", value: "31.20", currency: "AED", source: "SRC-05 · supplier quote midpoint", confidence: 84, ts: "2026-02-11 07:05", estimate: false, ev: "EV-006" },
  { label: "Shipping cost", value: "9.80", currency: "AED", source: "SRC-05 · CALCULATED from spot freight + last-mile", confidence: 76, ts: "2026-02-11 07:05", estimate: true, ev: "EV-007" },
  { label: "Import duty", value: "5.0", currency: "%", source: "ASSUMED · not confirmed with customs", confidence: 40, ts: "2026-02-11 07:05", estimate: true, ev: "EV-007" },
  { label: "Blended CAC", value: "48.00", currency: "AED", source: "SRC-09 · internal CPM model", confidence: 52, ts: "2026-02-11 08:15", estimate: true, ev: "EV-009" },
  { label: "Payment + packaging", value: "7.40", currency: "AED", source: "SRC-05 · derived", confidence: 70, ts: "2026-02-11 07:05", estimate: true, ev: "EV-007" },
];

export const moneyOutputs = [
  { label: "Gross margin", value: "72.4%", note: "before duty and acquisition" },
  { label: "Contribution / unit", value: "AED 65.60", note: "after duty, fulfilment and CAC" },
  { label: "Break-even volume", value: "686 units", note: "against AED 45,000 capital limit" },
  { label: "Capital requirement", value: "AED 38,900", note: "MOQ 500 + freight + 90d media" },
  { label: "Payback", value: "74 days", note: "inside the 90-day mission limit" },
];

export const moneyAssumptions = [
  "Duty holds at 5% — ASSUMED, customs not yet confirmed",
  "Spot freight rate is representative at MOQ 500",
  "CAC of AED 48 is model-derived and unverified",
  "Breakage rate stays under 3% with double-wall packaging",
  "No return-rate provision above 6%",
];

/* ---------------------------- Strategy review ---------------------------- */

export const strategy = {
  positioning: "Gift-grade burner that guarantees scent throw and survives transit — attacks the two dominant complaints in the category.",
  segment: "Gift buyers 28–45, UAE, bilingual, occasion-driven.",
  channel: "Instagram / TikTok discovery into branded search purchase.",
  offer: "AED 169 single SKU with double-wall box and scent-intensity card.",
  validationPlan: "AED 3,000 media test, 50-unit pre-order threshold, 20-unit transit trial, manual price audit.",
  strategicFit: "High. Strengthens the consumer-goods holding and builds a consumable attach path.",
  complexity: "Moderate. Single SKU, one supplier, one market, no custom tooling.",
  expansion: "Clear path to KSA via a separate customs registrant, and to a consumable subscription (OPP-0092).",
  concerns: [
    "Seasonality is severe — a November miss costs the whole cycle",
    "Breakage guarantee creates a contingent liability not yet costed",
    "Dependence on one supplier at launch volume",
  ],
  verdict: "SUPPORTS proceeding to approval, conditional on the packaging redesign clearing the blocking risk finding.",
  by: "Strategy Manager · evaluated on structured inputs supplied by Research",
};

/* ---------------------------- Recommendation packet ---------------------------- */

export type RecType = "REJECT" | "ARCHIVE" | "RESEARCH_MORE" | "RUN_VALIDATION" | "REQUEST_APPROVAL" | "LIMITED_LAUNCH";

export const recPacket = {
  id: "REC-0455",
  opportunity: "OPP-0091 · Amber Oud No. 4",
  recommendation: "REQUEST_APPROVAL" as RecType,
  title: "Request owner approval to commit AED 38,900",
  reasons: [
    "Verified demand signal with commercial intent above threshold (EV-003)",
    "Margin structure clears mission requirements on observed costs (EV-004, EV-006)",
    "Break-even of 686 units fits inside the 90-day mission window",
    "Category has a defensible wedge: breakage and scent throw (EV-008)",
  ],
  evidenceRefs: ["EV-001", "EV-002", "EV-003", "EV-004", "EV-006", "EV-007", "EV-008", "EV-010", "EV-012"],
  assumptions: moneyAssumptions,
  financial: "Contribution AED 65.60/unit · break-even 686 units · capital AED 38,900 · payback 74 days",
  strategic: strategy.verdict,
  risks: [
    "BLOCKING · packaging visual similarity must be redesigned (RSK-07)",
    "WARNING · duty and landed cost unconfirmed (RSK-04, RSK-05)",
    "WARNING · CAC unverified (RSK-09)",
  ],
  approvals: [
    "Owner · capital commitment above the AED 50K autonomous cap (mandate M-58 exception)",
    "Risk & Policy Agent · blocking finding RSK-07 must clear before listing creation",
  ],
  nextAction: "Redesign packaging, obtain customs confirmation, then return for final approval.",
  invalidation: [
    "Verified landed cost exceeds AED 48/unit",
    "Price conflict resolves below AED 110 median, collapsing the premium tier",
    "Breakage rate above 6% in the 20-unit transit trial",
  ],
  stopping: [
    "Pre-order commits fewer than 50 units in 10 days",
    "Media test CAC exceeds AED 80",
    "Counsel advises against the category on IP grounds",
  ],
  confidence: 74,
};

/* ---------------------------- Approvals ---------------------------- */

export interface Approval {
  id: string;
  what: string;
  why: string;
  mission: string;
  opp: string;
  evidence: string[];
  financial: string;
  risks: string[];
  action: string;
  approver: string;
  consequences: string[];
  state: "PENDING" | "APPROVED" | "REJECTED" | "ESCALATED";
}

export const approvals: Approval[] = [
  { id: "APR-0455", what: "Commit AED 38,900 to a 500-unit first production run of OPP-0091", why: "Recommendation packet REC-0455 reached REQUEST_APPROVAL after verification quorum was met.", mission: "MSN-2026-0148", opp: "OPP-0091", evidence: ["EV-004", "EV-006", "EV-007", "EV-010"], financial: "AED 38,900 capital · AED 65.60 contribution/unit · 74-day payback", risks: ["BLOCKING RSK-07 packaging similarity", "Duty and CAC unverified"], action: "Approve capital commitment", approver: "Owner · exceeds autonomous cap M-58", consequences: ["Funds released to supplier deposit", "Packaging redesign must clear RSK-07 before any listing is created", "Mission advances to SUBMITTED"], state: "PENDING" },
  { id: "APR-0456", what: "Authorise a AED 3,000 paid media test", why: "CAC of AED 48 is model-derived (EV-009). The test converts it into an observed figure.", mission: "MSN-2026-0148", opp: "OPP-0091", evidence: ["EV-009"], financial: "AED 3,000 spend · resolves the largest unverified model input", risks: ["Spend may be wasted if CPM assumption is materially wrong"], action: "Approve media test", approver: "Enactor · within autonomous cap, escalated for visibility", consequences: ["Test runs 7 days", "CAC input is replaced with an observed value", "No inventory commitment"], state: "PENDING" },
  { id: "APR-0457", what: "Provide the missing category constraint for MSN-2026-0149", why: "The objective is ambiguous and certification cost varies 6x across categories. The mission cannot proceed safely.", mission: "MSN-2026-0149", opp: "OPP-0094", evidence: ["EV-013"], financial: "Certification cost varies AED 8K–48K depending on category", risks: ["Continuing on an ambiguous objective would waste the full research budget"], action: "Choose a constraint", approver: "Owner · objective clarification", consequences: ["Mission resumes in PLANNING", "Research budget is spent against a bounded question"], state: "ESCALATED" },
  { id: "APR-0431", what: "Archive MSN-2026-0136 specialty coffee subscription", why: "Two consecutive stall findings; unit economics never cleared the capital limit.", mission: "MSN-2026-0136", opp: "—", evidence: [], financial: "AED 0 committed", risks: [], action: "Confirm archive", approver: "Owner", consequences: ["Mission moved to ARCHIVED", "Historical report remains immutable"], state: "APPROVED" },
];

/* ---------------------------- Tools ---------------------------- */

export interface ToolRec {
  name: string;
  category: string;
  allowed: string[];
  risk: "LOW" | "MEDIUM" | "HIGH";
  approval: string;
  cost: string;
  rate: string;
  policy: string;
  available: boolean;
  calls: number;
  audit: string[];
}

export const tools: ToolRec[] = [
  { name: "web.search", category: "Retrieval", allowed: ["AG-01", "AG-02", "AG-03", "AG-05", "AG-06"], risk: "LOW", approval: "None", cost: "$0.004 / call", rate: "120 / min", policy: "Public web only · no login-gated content", available: true, calls: 1842, audit: ["2026-02-11 09:14 AG-01 · 24 calls", "2026-02-11 08:51 AG-03 · 12 calls"] },
  { name: "marketplace.scan", category: "Retrieval", allowed: ["AG-01", "AG-03", "AG-07"], risk: "MEDIUM", approval: "Logged, no approval", cost: "$0.02 / scan", rate: "30 / min", policy: "Public listings · snapshot retained for provenance", available: true, calls: 214, audit: ["2026-02-11 06:14 AG-01 · category crawl", "2026-02-11 06:31 AG-01 · top-100"] },
  { name: "supplier.directory", category: "Retrieval", allowed: ["AG-04"], risk: "MEDIUM", approval: "Logged, no approval", cost: "$0.05 / query", rate: "20 / min", policy: "Quotes stored with validity window", available: true, calls: 38, audit: ["2026-02-11 07:05 AG-04 · 3 quotes"] },
  { name: "trends.query", category: "Analysis", allowed: ["AG-02", "AG-06"], risk: "LOW", approval: "None", cost: "$0.01 / query", rate: "60 / min", policy: "Aggregated data only", available: true, calls: 96, audit: ["2026-02-11 06:22 AG-02 · 24mo series"] },
  { name: "currency.fx", category: "Analysis", allowed: ["AG-04", "AG-10"], risk: "LOW", approval: "None", cost: "$0.001 / call", rate: "10 / min", policy: "Rate + timestamp stored with every conversion", available: true, calls: 412, audit: ["2026-02-11 07:05 AG-04 · USD→AED 3.6725"] },
  { name: "regulatory.lookup", category: "Compliance", allowed: ["AG-08"], risk: "HIGH", approval: "Risk & Policy Agent sign-off", cost: "$0.09 / lookup", rate: "10 / min", policy: "Primary registry sources only · retained permanently", available: true, calls: 27, audit: ["2026-02-11 08:30 AG-08 · trademark class 3"] },
  { name: "money.calculator", category: "Financial", allowed: ["AG-10", "system"], risk: "HIGH", approval: "Owner approval for commitments", cost: "$0.00", rate: "60 / min", policy: "Rejects any unsourced financial input", available: true, calls: 8, audit: ["2026-02-11 14:41 system · OPP-0091 evaluation"] },
  { name: "external.purchase", category: "Execution", allowed: [], risk: "HIGH", approval: "Owner approval · always", cost: "n/a", rate: "disabled", policy: "Hard-blocked until owner approval is recorded server-side", available: false, calls: 0, audit: ["2026-02-11 14:44 blocked · attempted by AG-04 without approval"] },
  { name: "enactor.dispatch", category: "Execution", allowed: ["AG-06"], risk: "HIGH", approval: "Owner approval for consequential actions", cost: "n/a", rate: "5 / min", policy: "Dry-run required before dispatch", available: true, calls: 3, audit: ["2026-02-11 14:52 AG-06 · dry-run only"] },
];

/* ---------------------------- Events ---------------------------- */

export type EvLevel = "info" | "ok" | "warn" | "block";

export interface AuditEvent {
  ts: string;
  mission: string;
  task: string;
  agent: string;
  event: string;
  result: string;
  level: EvLevel;
}

export const events: AuditEvent[] = [
  { ts: "14:52:08", mission: "MSN-2026-0148", task: "TSK-13", agent: "AG-10", event: "RECOMMENDATION_SUBMITTED", result: "REC-0455 · REQUEST_APPROVAL", level: "warn" },
  { ts: "14:44:31", mission: "MSN-2026-0148", task: "TSK-08", agent: "AG-04", event: "RISK_BLOCK_TRIGGERED", result: "external.purchase denied · no owner approval", level: "block" },
  { ts: "14:41:02", mission: "MSN-2026-0148", task: "TSK-11", agent: "system", event: "FINANCIAL_EVALUATION_REQUESTED", result: "accepted · 6 inputs, 4 estimated", level: "info" },
  { ts: "14:38:55", mission: "MSN-2026-0148", task: "TSK-06", agent: "AG-09", event: "EVIDENCE_CREATED", result: "EV-009 · CALCULATED · conf 52", level: "warn" },
  { ts: "14:22:19", mission: "MSN-2026-0148", task: "TSK-09", agent: "AG-09", event: "CLAIM_VERIFIED", result: "EV-010 · trademark clear", level: "ok" },
  { ts: "14:19:44", mission: "MSN-2026-0148", task: "TSK-03", agent: "AG-09", event: "CONFLICT_DETECTED", result: "EV-005 unresolved · AED 95 vs AED 189", level: "block" },
  { ts: "13:58:07", mission: "MSN-2026-0148", task: "TSK-09", agent: "AG-09", event: "CLAIM_VERIFIED", result: "EV-008 · complaint clusters", level: "ok" },
  { ts: "13:41:12", mission: "MSN-2026-0148", task: "TSK-03", agent: "AG-03", event: "TASK_RETRYING", result: "attempt 2 of 3 · price reconciliation", level: "warn" },
  { ts: "13:12:30", mission: "MSN-2026-0148", task: "TSK-09", agent: "AG-09", event: "CLAIM_VERIFIED", result: "EV-001 · category size", level: "ok" },
  { ts: "12:47:03", mission: "MSN-2026-0148", task: "TSK-05", agent: "AG-05", event: "SOURCE_RETRIEVED", result: "SRC-06 · 1,240 reviews", level: "info" },
  { ts: "12:02:41", mission: "MSN-2026-0148", task: "TSK-08", agent: "AG-08", event: "RISK_BLOCK_TRIGGERED", result: "RSK-07 · packaging visual similarity", level: "block" },
  { ts: "11:30:18", mission: "MSN-2026-0148", task: "TSK-10", agent: "AG-10", event: "OPPORTUNITY_CREATED", result: "OPP-0091 · Approval required", level: "ok" },
  { ts: "11:04:55", mission: "MSN-2026-0148", task: "TSK-02", agent: "AG-02", event: "EVIDENCE_CREATED", result: "EV-003 · intent share 68%", level: "ok" },
  { ts: "10:38:09", mission: "MSN-2026-0149", task: "—", agent: "system", event: "APPROVAL_REQUIRED", result: "APR-0457 · objective clarification", level: "warn" },
  { ts: "09:40:22", mission: "MSN-2026-0148", task: "TSK-09", agent: "AG-09", event: "EVIDENCE_CREATED", result: "EV-014 REJECTED · unverified ROAS", level: "block" },
  { ts: "09:12:40", mission: "MSN-2026-0148", task: "TSK-09", agent: "AG-09", event: "TASK_STARTED", result: "verification pass 2 · 5 claims", level: "info" },
  { ts: "08:20:11", mission: "MSN-2026-0148", task: "TSK-01", agent: "AG-01", event: "TASK_ASSIGNED", result: "AG-01 · P0", level: "info" },
  { ts: "06:02:00", mission: "MSN-2026-0148", task: "—", agent: "system", event: "MISSION_VALIDATED", result: "objective unambiguous · budget within cap", level: "ok" },
  { ts: "06:01:12", mission: "MSN-2026-0148", task: "—", agent: "system", event: "MISSION_CREATED", result: "capital $45,000 · 14 day horizon", level: "info" },
];

/* ---------------------------- History / Learning ---------------------------- */

export const historyMissions = [
  { id: "MSN-2026-0131", name: "Modest Activewear Q4", stage: "COMPLETED" as Lifecycle, rec: "LIMITED_LAUNCH", outcome: "Launched 1 SKU. Revenue AED 214K in 9 weeks against a AED 60K budget.", actions: "500-unit run, 2 media tests, 1 supplier", closed: "2026-02-02" },
  { id: "MSN-2026-0122", name: "Smart Home Retrofit GCC", stage: "COMPLETED" as Lifecycle, rec: "REJECT", outcome: "No launch. Margin never cleared the floor after duty.", actions: "None — recommendation rejected", closed: "2026-01-22" },
  { id: "MSN-2026-0118", name: "Pet Nutrition Subscription", stage: "ARCHIVED" as Lifecycle, rec: "ARCHIVE", outcome: "Archived after validation failed on retention.", actions: "1 landing test", closed: "2026-01-11" },
  { id: "MSN-2026-0136", name: "Specialty Coffee Subscriptions", stage: "PAUSED" as Lifecycle, rec: "RESEARCH_MORE", outcome: "Stalled twice on unit economics. Awaiting owner direction.", actions: "None", closed: "paused 2026-02-04" },
];

export const wrongAssumptions = [
  { mission: "MSN-2026-0131", assumption: "Assumed 2% return rate on apparel", actual: "Actual 9.4% due to size variance", cost: "AED 11,200", lesson: "Apparel return assumptions require a category-specific prior, never a flat 2%." },
  { mission: "MSN-2026-0122", assumption: "Assumed 5% import duty on smart devices", actual: "Actual 12% + conformity cert", cost: "Removed 14 margin points", lesson: "Duty must be confirmed with customs before it enters any margin model." },
  { mission: "MSN-2026-0118", assumption: "Assumed 3-month retention on subscriptions", actual: "Actual 1.4 months", cost: "Model overstates LTV by 2.1x", lesson: "Retention claims need observed cohort data before entering LTV." },
];

export const sourcePerf = {
  reliable: [
    { name: "Government registries", note: "6/6 claims later confirmed", quality: "HIGH" },
    { name: "Marketplace listing crawls", note: "31/34 claims confirmed; prices shift within 48h", quality: "HIGH" },
    { name: "Verified supplier quotes", note: "9/11 confirmed; validity window matters", quality: "MEDIUM" },
  ],
  poor: [
    { name: "Vendor marketing pages", note: "1/7 claims confirmed · EV-014 rejected", quality: "LOW" },
    { name: "Aggregator CPM benchmarks", note: "0/4 confirmed · consistently 30% optimistic", quality: "LOW" },
    { name: "Storefront scrapes without snapshot", note: "2/6 confirmed · provenance gaps", quality: "LOW" },
  ],
};

export const agentPerf = [
  { id: "AG-09", n: "Evidence Verification", accepted: 61, rejected: 9, acc: 87 },
  { id: "AG-01", n: "Market Discovery", accepted: 48, rejected: 3, acc: 94 },
  { id: "AG-03", n: "Competitor Intelligence", accepted: 29, rejected: 6, acc: 83 },
  { id: "AG-06", n: "Marketing Intelligence", accepted: 12, rejected: 11, acc: 52 },
  { id: "AG-04", n: "Supplier & Fulfillment", accepted: 22, rejected: 4, acc: 85 },
];

export const validationResults = [
  { mission: "MSN-2026-0131", test: "Landing conversion test", predicted: "2.4%", actual: "2.1%", verdict: "Within tolerance" },
  { mission: "MSN-2026-0131", test: "Return-rate assumption", predicted: "2.0%", actual: "9.4%", verdict: "Wrong — now a stored lesson" },
  { mission: "MSN-2026-0118", test: "Retention cohort", predicted: "3.0 mo", actual: "1.4 mo", verdict: "Wrong — archive triggered" },
  { mission: "MSN-2026-0122", test: "Landed cost model", predicted: "AED 61", actual: "AED 88", verdict: "Wrong — rejection justified" },
];

export const lessons = [
  "No financial input enters a margin model without a source, a confidence value and a timestamp.",
  "Duty and freight must be observed, not assumed. They have caused two of three historical misses.",
  "Vendor marketing claims are treated as INFERRED and rejected unless methodology is disclosed.",
  "A completed task means validated output, not a returned payload. Agent text alone is never acceptance.",
  "Ambiguous objectives escalate to the owner instead of consuming the research budget.",
];
