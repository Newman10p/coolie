export type SectorStatus = "operational" | "attention" | "offline";

export interface Sector {
  id: string;
  name: string;
  code: string;
  desc: string;
  status: SectorStatus;
  icon: string;
  metric: string;
  metricLabel: string;
}

export const sectors: Sector[] = [
  {
    id: "brain",
    name: "Brain",
    code: "COGNITION CORE",
    desc: "Central reasoning, memory graph & policy engine.",
    status: "operational",
    icon: "brain",
    metric: "99.98%",
    metricLabel: "Uptime",
  },
  {
    id: "research",
    name: "Research",
    code: "MARKET INTEL",
    desc: "Signal harvesting, competitor tracking, forecasts.",
    status: "operational",
    icon: "search",
    metric: "1,204",
    metricLabel: "Sources live",
  },
  {
    id: "enactor",
    name: "Enactor",
    code: "EXECUTION",
    desc: "Autonomous task execution across connected tools.",
    status: "attention",
    icon: "zap",
    metric: "37",
    metricLabel: "Jobs running",
  },
  {
    id: "evolver",
    name: "Evolver",
    code: "OPTIMIZATION",
    desc: "Self-tuning strategy & continuous improvement.",
    status: "operational",
    icon: "dna",
    metric: "+14.2%",
    metricLabel: "Gain / mo",
  },
  {
    id: "reports",
    name: "Reports",
    code: "BRIEFINGS",
    desc: "Executive summaries, filings & audit trails.",
    status: "operational",
    icon: "file",
    metric: "8",
    metricLabel: "New today",
  },
  {
    id: "treasury",
    name: "Treasury",
    code: "FINANCE GATE",
    desc: "Compliance, Sharia gate & spending controls.",
    status: "attention",
    icon: "vault",
    metric: "3",
    metricLabel: "Awaiting sign",
  },
];

export interface SubAgent {
  id: string;
  name: string;
  role: string;
  status: "working" | "idle" | "blocked" | "review";
  tasks: string[];
}

export const subAgents: Record<string, SubAgent[]> = {
  brain: [
    { id: "mnemo", name: "Mnemosyne", role: "Long-term memory", status: "working", tasks: ["Reconciling 4,281 memory nodes", "Pruning stale decision branches", "Re-indexing owner preference graph"] },
    { id: "logos", name: "Logos", role: "Reasoning core", status: "working", tasks: ["Evaluating 3 candidate strategies", "Running counterfactual on Q1 plan", "Scoring policy compliance per branch"] },
    { id: "senti", name: "Sentinel", role: "Policy engine", status: "review", tasks: ["Checking 12 actions against mandate", "Escalating 1 action for owner sign", "Auditing tool permission scopes"] },
    { id: "merid", name: "Meridian", role: "Context router", status: "working", tasks: ["Routing 24 in-flight queries", "Balancing context windows", "Compressing prior conversation"] },
  ],
  research: [
    { id: "aegis", name: "Aegis", role: "Competitor watch", status: "working", tasks: ["Tracking 9 competitor filings", "Diffing quarterly decks for deltas", "Flagging pricing changes in EU"] },
    { id: "fara", name: "Faraday", role: "Signal harvest", status: "working", tasks: ["Scanning 1,204 sources", "Clustering 38 market signals", "Deduplicating news wire feed"] },
    { id: "hypa", name: "Hypatia", role: "Forecast engine", status: "working", tasks: ["Rebuilding demand model", "Backtesting 12-week forecast", "Calibrating confidence bands"] },
    { id: "sable", name: "Sable", role: "Data integrity", status: "idle", tasks: ["Validating 8 datasets", "Repairing 2 malformed records", "Signing source provenance"] },
  ],
  enactor: [
    { id: "tanta", name: "Tantalus", role: "Job scheduler", status: "working", tasks: ["Dispatching 37 jobs", "Rebalancing worker pool", "Retrying 2 failed tasks"] },
    { id: "volta", name: "Volta", role: "Tool bridge", status: "working", tasks: ["Executing 14 API calls", "Rotating 3 service tokens", "Handling 1 rate limit"] },
    { id: "argus", name: "Argus", role: "Quality gate", status: "review", tasks: ["Reviewing 22 outputs", "Returning 2 for revision", "Certifying 18 deliverables"] },
    { id: "kratos", name: "Kratos", role: "Rollout", status: "blocked", tasks: ["Deploying 2 configs", "Canary at 10% traffic", "Watching error budget"] },
  ],
  evolver: [
    { id: "lamar", name: "Lamarck", role: "Strategy tuner", status: "working", tasks: ["Tuning 6 parameters", "A/B testing 3 policies", "Promoting variant B"] },
    { id: "hegel", name: "Hegel", role: "Self-review", status: "working", tasks: ["Reviewing 120 decisions", "Measuring regret per branch", "Proposing 4 improvements"] },
    { id: "nomad", name: "Nomad", role: "Experiment lab", status: "working", tasks: ["Running 9 experiments", "Extending 1 due to variance", "Archiving 3 results"] },
    { id: "chim", name: "Chimera", role: "Mutation pool", status: "idle", tasks: ["Generating 12 variants", "Culling 5 underperformers", "Seeding next generation"] },
  ],
  reports: [
    { id: "quill", name: "Quill", role: "Drafting", status: "working", tasks: ["Drafting Q1 executive brief", "Summarizing 3 board packs", "Rendering 6 charts"] },
    { id: "clio", name: "Clio", role: "Archive", status: "working", tasks: ["Filing 8 documents", "Versioning 4 reports", "Retrieving 1 historical"] },
    { id: "veri", name: "Veritas", role: "Audit trail", status: "working", tasks: ["Hashing 54 records", "Verifying 51 signatures", "Writing immutable ledger"] },
    { id: "iris", name: "Iris", role: "Distribution", status: "idle", tasks: ["Routing 3 briefings", "Formatting for mobile", "Scheduling 2 deliveries"] },
  ],
  treasury: [
    { id: "croe", name: "Croesus", role: "Liquidity", status: "working", tasks: ["Sweeping idle balances", "Rebalancing cash ladder", "Reserving 2 payouts"] },
    { id: "gate", name: "Aegis Gate", role: "Sharia gate", status: "review", tasks: ["Screening 6 instruments", "Blocking 1 non-compliant order", "Re-verifying 2 structures"] },
    { id: "nume", name: "Numera", role: "Reconciliation", status: "working", tasks: ["Matching 210 entries", "Flagging 3 mismatches", "Closing 198 positions"] },
    { id: "bast", name: "Bastion", role: "Risk & limits", status: "blocked", tasks: ["Measuring 12 exposures", "Testing 2 limit breaches", "Adjusting 1 threshold"] },
  ],
};

export const sectorAlerts: Record<string, string[]> = {
  brain: ["Mandate #44 requires owner sign-off", "Memory compaction queued for 02:00", "1 policy branch exceeded latency budget"],
  research: ["EU pricing change detected · 3 competitors", "Forecast confidence below 80% in sector 4", "2 sources rejected: unverified provenance"],
  enactor: ["Job #3721 retry loop detected", "Rate limit reached on CRM bridge", "Config rollout held at canary"],
  evolver: ["Variant B promotion pending review", "Experiment 04 shows high variance", "Regret score improved 6.2% this cycle"],
  reports: ["Q1 filing draft awaits owner approval", "Board pack #2 has 2 open comments", "Audit ledger hash verified 54/54"],
  treasury: ["Broker order TX-90430 blocked · Sharia gate", "Limit breach on acquisition desk", "3 transactions awaiting signature"],
};

export interface BriefPlate {
  id: string;
  title: string;
  tag: string;
  summary: string;
  value: string;
  delta: string;
  positive: boolean;
}

export const plates: BriefPlate[] = [
  {
    id: "p1",
    title: "Portfolio Net Worth",
    tag: "TREASURY",
    summary: "Aggregate value across 6 businesses and liquid reserves.",
    value: "$42.8M",
    delta: "+6.4%",
    positive: true,
  },
  {
    id: "p2",
    title: "Monthly Cash Flow",
    tag: "FINANCE",
    summary: "Operating inflow net of committed spend this cycle.",
    value: "$3.19M",
    delta: "+2.1%",
    positive: true,
  },
  {
    id: "p3",
    title: "Active Mandates",
    tag: "ENACTOR",
    summary: "Autonomous directives currently in execution.",
    value: "37",
    delta: "-4",
    positive: false,
  },
  {
    id: "p4",
    title: "Compliance Score",
    tag: "SHARIA GATE",
    summary: "Weighted verification across all transaction gates.",
    value: "98.2",
    delta: "+0.6",
    positive: true,
  },
];

export interface LedgerRow {
  id: string;
  ref: string;
  entity: string;
  category: string;
  amount: number;
  status: "approved" | "pending" | "blocked";
  sharia: "verified" | "review" | "flagged";
  date: string;
}

export const ledger: LedgerRow[] = [
  { id: "l1", ref: "TX-90412", entity: "Aramex Logistics", category: "Operations", amount: 184500, status: "approved", sharia: "verified", date: "2026-02-11" },
  { id: "l2", ref: "TX-90418", entity: "Noor Capital Fund", category: "Investment", amount: 920000, status: "pending", sharia: "review", date: "2026-02-11" },
  { id: "l3", ref: "TX-90421", entity: "Zenith Media Buy", category: "Marketing", amount: 62300, status: "approved", sharia: "verified", date: "2026-02-10" },
  { id: "l4", ref: "TX-90425", entity: "Vertex Holdings", category: "Acquisition", amount: 2450000, status: "pending", sharia: "review", date: "2026-02-10" },
  { id: "l5", ref: "TX-90430", entity: "Unverified Broker", category: "Derivatives", amount: 510000, status: "blocked", sharia: "flagged", date: "2026-02-09" },
  { id: "l6", ref: "TX-90436", entity: "Solaris Energy", category: "Infrastructure", amount: 1340000, status: "approved", sharia: "verified", date: "2026-02-09" },
  { id: "l7", ref: "TX-90441", entity: "Payroll · Q1 Cycle", category: "Payroll", amount: 388000, status: "approved", sharia: "verified", date: "2026-02-08" },
];

export interface MatrixSegment {
  label: string;
  value: number;
  color: string;
}

export const matrix: MatrixSegment[] = [
  { label: "Equities", value: 38, color: "#60a5fa" },
  { label: "Real Estate", value: 24, color: "#34d399" },
  { label: "Ventures", value: 18, color: "#d6b16a" },
  { label: "Liquid", value: 12, color: "#a78bfa" },
  { label: "Sukuk", value: 8, color: "#f472b6" },
];

export interface Business {
  id: string;
  name: string;
  sector: string;
  revenue: string;
  margin: string;
  status: "growing" | "stable" | "watch";
  trend: number[];
}

export const businesses: Business[] = [
  { id: "b1", name: "Noor Logistics", sector: "Freight & supply chain", revenue: "$14.2M", margin: "18.4%", status: "growing", trend: [4, 5, 5, 6, 7, 7, 8, 9, 9, 11] },
  { id: "b2", name: "Solaris Grid", sector: "Renewable infrastructure", revenue: "$11.8M", margin: "22.1%", status: "growing", trend: [3, 4, 4, 5, 5, 6, 7, 7, 8, 9] },
  { id: "b3", name: "Zenith Media", sector: "Digital publishing", revenue: "$6.4M", margin: "12.7%", status: "stable", trend: [6, 6, 7, 6, 7, 7, 6, 7, 7, 7] },
  { id: "b4", name: "Atlas Realty", sector: "Commercial real estate", revenue: "$9.1M", margin: "31.0%", status: "stable", trend: [7, 7, 8, 8, 8, 9, 8, 9, 9, 9] },
  { id: "b5", name: "Halal Pay", sector: "Fintech · payments", revenue: "$4.7M", margin: "9.8%", status: "watch", trend: [8, 7, 7, 6, 6, 5, 6, 5, 5, 4] },
  { id: "b6", name: "Vertex Labs", sector: "Applied AI research", revenue: "$3.2M", margin: "-4.1%", status: "watch", trend: [2, 3, 3, 4, 3, 4, 4, 5, 4, 5] },
];

export interface Decision {
  id: string;
  ref: string;
  title: string;
  amount: string;
  requestedBy: string;
  gate: "verified" | "review";
  note: string;
}

export const decisions: Decision[] = [
  { id: "d1", ref: "APR-2207", title: "Vertex Holdings acquisition", amount: "$2,450,000", requestedBy: "Croesus · Treasury", gate: "review", note: "Structure under Sharia re-verification. Recommended: hold until gate clears." },
  { id: "d2", ref: "APR-2211", title: "Noor Capital Fund allocation", amount: "$920,000", requestedBy: "Lamarck · Evolver", gate: "review", note: "Sukuk-backed allocation. Exposure within mandate limit (61%)." },
  { id: "d3", ref: "APR-2214", title: "Q1 executive filing release", amount: "—", requestedBy: "Quill · Reports", gate: "verified", note: "Audit trail hashed 54/54. Ready for owner signature and distribution." },
];

/* ---------------- Orchestrator HUD ---------------- */

export interface ToolCall {
  name: string;
  detail: string;
  ms: number;
}

export interface Intent {
  id: string;
  match: RegExp;
  reply: string;
  tools: ToolCall[];
  memory: string[];
  chips: string[];
  /** consequential action that needs explicit owner confirmation */
  confirm?: { label: string; detail: string; action: string };
}

export const intents: Intent[] = [
  {
    id: "treasury",
    match: /treasur|money|portfolio|net worth|cash|balance|financ|wealth|exposure/i,
    reply:
      "Treasury came back clean. Net worth is $42.8M, up 6.4% overnight. Cash flow is running at $3.19M a month and the Money Matrix has drifted 2.1% toward Sukuk — still inside mandate. Two transactions are waiting on your signature: the Vertex acquisition at $2.45M and a $920K allocation to Noor Capital. One broker order for $510K in derivatives was blocked by the Sharia gate overnight.",
    tools: [
      { name: "treasury.query_balances", detail: "6 accounts · reconciled", ms: 320 },
      { name: "treasury.money_matrix", detail: "recomputed allocation", ms: 180 },
      { name: "sharia_gate.screen", detail: "7 instruments · 1 blocked", ms: 410 },
    ],
    memory: ["Mandate #44 · max single exposure $3M", "Owner prefers Sukuk over derivatives"],
    chips: ["Sign the Vertex acquisition", "Why was the broker order blocked?", "Show pending approvals"],
  },
  {
    id: "compliance",
    match: /sharia|complian|gate|blocked|why.*block|flagged|reject|ethic/i,
    reply:
      "The order came from an unverified broker trading in derivatives. The gate flagged it on two grounds: the counterparty has no provenance signature, and the structure carries a gharar exposure above your 15% ceiling. I quarantined it rather than cancelling it, so the audit trail stays intact. Compliance score sits at 98.2 across all gates.",
    tools: [
      { name: "sharia_gate.explain", detail: "2 rule violations cited", ms: 260 },
      { name: "audit.trace", detail: "record TX-90430", ms: 140 },
    ],
    memory: ["Gharar ceiling · 15%", "Counterparty allowlist enforced by backend"],
    chips: ["Approve the allowlist", "Show the audit trail", "Brief me on compliance"],
  },
  {
    id: "enactor",
    match: /enact|execut|run|do|task|job|deploy|schedule|automat|mandate/i,
    reply:
      "I can queue that with the Enactor. It would dispatch across your connected tools and report back through the live stream. Because this changes state outside the workroom, I need your explicit confirmation before anything executes — and the backend will re-check your permissions and spending limits when it does.",
    tools: [
      { name: "enactor.dry_run", detail: "plan simulated · 3 steps", ms: 380 },
      { name: "policy.check_scope", detail: "within mandate", ms: 120 },
    ],
    memory: ["Consequential actions require owner confirmation"],
    chips: ["Confirm and dispatch", "Show me the 3 steps first", "Cancel"],
    confirm: {
      label: "Dispatch to Enactor",
      detail: "3 steps · tools: CRM, Payments, Docs · limit check passed",
      action: "Dispatched",
    },
  },
  {
    id: "research",
    match: /research|market|competitor|news|trend|forecast|signal|industry/i,
    reply:
      "Research is holding 1,204 live sources and clustered 38 signals overnight. The one that matters: three of your EU competitors moved pricing last week, and the forecast engine has dropped confidence below 80% in your fourth sector. I have a demand model rebuild queued if you want the full read.",
    tools: [
      { name: "research.scan", detail: "1,204 sources · 38 signals", ms: 520 },
      { name: "forecast.rebuild", detail: "12-week model", ms: 340 },
    ],
    memory: ["Owner reviews EU pricing on Mondays"],
    chips: ["Rebuild the demand model", "Which competitors moved?", "Forecast next quarter"],
  },
  {
    id: "decisions",
    match: /decision|sign|approv|pending|signature|hold|waiting|document|filing/i,
    reply:
      "Three documents are on your desk. The Vertex acquisition at $2.45M is held because the structure is still in Sharia re-verification. The Noor Capital allocation is Sukuk-backed and sitting at 61% of your exposure limit. The Q1 filing is fully verified — audit trail hashed 54 of 54 — and only needs your signature to go out.",
    tools: [
      { name: "approvals.list", detail: "3 open · 2 need owner", ms: 160 },
      { name: "audit.verify", detail: "54/54 records hashed", ms: 220 },
    ],
    memory: ["Owner signs filings personally"],
    chips: ["Open the Office Table", "Sign the Q1 filing", "Hold the Vertex deal"],
  },
  {
    id: "sectors",
    match: /sector|status|health|agent|who|online|system|uptime|hall|department/i,
    reply:
      "All six sectors are up. Brain is at 99.98% uptime, Reports filed 8 briefings today, and Evolver has a variant promotion pending your review. Enactor is the only one degraded — one job is in a retry loop and the config rollout is still parked at canary. Treasury is flagged because of the blocked broker order.",
    tools: [
      { name: "sectors.health", detail: "6 sectors polled", ms: 240 },
      { name: "enactor.jobs", detail: "37 active · 1 retry", ms: 200 },
    ],
    memory: ["Enactor canary held at 10% traffic"],
    chips: ["Open the Department Hall", "Why is Enactor retrying?", "Promote the Evolver variant"],
  },
  {
    id: "memory",
    match: /remember|memory|forget|preference|context|know about me/i,
    reply:
      "I hold a live memory graph of 4,281 nodes: your mandates, the holdings you watch, how you like reports framed, and every decision you have signed. Mnemosyne is re-indexing the preference graph right now. Nothing in memory is a substitute for authorization — it only helps me anticipate what you need.",
    tools: [
      { name: "memory.recall", detail: "4,281 nodes · 12 relevant", ms: 180 },
      { name: "memory.reindex", detail: "preference graph", ms: 260 },
    ],
    memory: ["Owner reads briefings before 07:00", "Prefers Sukuk over derivatives"],
    chips: ["What do you know about me?", "Update my preferences", "Show my mandates"],
  },
];

export const fallbackIntent: Intent = {
  id: "fallback",
  match: /.*/,
  reply:
    "I heard you. I can reach into Treasury, Research, Enactor, Evolver, Reports and the Sharia gate — ask me about money, compliance, market signals, running tasks, or what needs your signature. I will always tell you what I am about to do before I do anything that matters.",
  tools: [{ name: "orchestrator.parse", detail: "no strong intent matched", ms: 90 }],
  memory: [],
  chips: ["Brief me on treasury", "What needs my signature?", "Are all sectors healthy?"],
};

export function resolveIntent(text: string): Intent {
  return intents.find((i) => i.match.test(text)) ?? fallbackIntent;
}

export const quickPrompts = [
  "Brief me on treasury",
  "What needs my signature?",
  "Are all sectors healthy?",
  "What did research find overnight?",
  "Why was the broker order blocked?",
  "Run the demand model rebuild",
];

export const activeMandates = [
  { id: "M-44", label: "Single exposure ceiling", value: "$3.0M", state: "61% used" },
  { id: "M-51", label: "Sharia gate · gharar", value: "15%", state: "armed" },
  { id: "M-58", label: "Autonomous spend cap", value: "$50K", state: "armed" },
  { id: "M-63", label: "Canary rollout", value: "10%", state: "held" },
];

export const hudSessions = [
  { id: "s1", title: "Morning treasury briefing", time: "06:12", live: true },
  { id: "s2", title: "Vertex acquisition review", time: "Yesterday" },
  { id: "s3", title: "EU pricing analysis", time: "Yesterday" },
  { id: "s4", title: "Payroll cycle approval", time: "Mon 09:40" },
  { id: "s5", title: "Q1 filing walkthrough", time: "Mon 08:05" },
];

export const revenueSeries = [
  32, 34, 33, 38, 41, 39, 44, 47, 45, 49, 53, 58,
];

export const transcript = [
  { role: "owner", text: "Coolie, brief me on treasury exposure this morning." },
  { role: "coolie", text: "Net worth is up 6.4% to $42.8M. Two transactions await your signature; one broker order was blocked by the Sharia gate." },
  { role: "owner", text: "Show the blocked order and hold the Vertex acquisition." },
  { role: "coolie", text: "Vertex acquisition placed on hold. The blocked order — Unverified Broker, $510K derivatives — is flagged for non-compliance. Awaiting your directive." },
];
