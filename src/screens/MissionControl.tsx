import { useState } from "react";
import { motion } from "motion/react";
import {
  CircleDot, Clock, Wallet, ShieldCheck, Wrench, Target, HelpCircle,
  GitBranch, AlertCircle, CheckCircle2, Lock, ChevronRight, XCircle,
} from "lucide-react";
import { cn } from "../utils/cn";
import {
  missions, tasks, taskStateMeta, agents, events, LIFECYCLE, stageMeta,
} from "../research/data";
import {
  Chip, Field, LifecycleTimeline, Panel, WhyBtn, MockBadge, AcceptanceBadge,
} from "../research/ui";
import { useResearch } from "../research/store";
import { Reveal } from "../components/scroll/Reveal";
import LiveMissionControl from "./LiveMissionControl";

/* ================= mission brief ================= */

function MissionBrief() {
  const { activeMission, setActiveMission } = useResearch();
  const m = missions.find((x) => x.id === activeMission)!;
  const ambiguous = m.status === "CLARIFICATION_REQUIRED";

  return (
    <div className="space-y-5">
      {/* selector */}
      <Reveal>
        <div className="flex flex-wrap gap-2">
          {missions.map((x) => (
            <button
              key={x.id}
              onClick={() => setActiveMission(x.id)}
              className={cn(
                "rounded-xl px-3 py-2 text-left text-[11px] font-medium ring-1 transition",
                x.id === activeMission
                  ? "bg-blue-400/15 text-white ring-blue-300/30"
                  : "bg-white/[0.03] text-slate-400 ring-white/10 hover:text-slate-200"
              )}
            >
              <span className="block font-mono text-[9px] text-slate-500">{x.id}</span>
              {x.name}
            </button>
          ))}
        </div>
      </Reveal>

      <Reveal delay={0.05}>
        <div className="coolie-metal coolie-metal-sheen rounded-2xl p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-md bg-white/5 px-2 py-1 font-mono text-[10px] font-semibold text-blue-200 ring-1 ring-white/10">
                  {m.id}
                </span>
                <Chip
                  tone={m.status === "ACTIVE" ? "ok" : ambiguous ? "warn" : m.status === "PAUSED" ? "neutral" : "info"}
                  dot={m.status === "ACTIVE" ? "bg-emerald-400" : ambiguous ? "bg-amber-400" : "bg-blue-400"}
                >
                  {m.status.replace(/_/g, " ")}
                </Chip>
                <Chip tone="violet">{stageMeta[m.stage]?.label ?? m.stage}</Chip>
                <MockBadge />
              </div>
              <h1 className="mt-3 text-2xl font-semibold text-metal sm:text-3xl">{m.name}</h1>
            </div>
          </div>

          {/* lifecycle */}
          <div className="mt-6 rounded-2xl bg-black/25 p-4 ring-1 ring-white/[0.07]">
            <p className="mb-3 text-[10px] font-bold tracking-[0.22em] text-blue-300/70">
              MISSION LIFECYCLE
            </p>
            <LifecycleTimeline stage={m.stage} />
          </div>

          {/* clarification */}
          {ambiguous && m.clarification && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-5 rounded-2xl border border-amber-400/30 bg-amber-400/10 p-4"
            >
              <p className="flex items-center gap-2 text-[11px] font-bold tracking-wider text-amber-200">
                <AlertCircle className="h-4 w-4" /> CLARIFICATION REQUIRED — MISSION IS NOT PROCEEDING
              </p>
              <p className="mt-2.5 text-[13px] leading-relaxed text-amber-50/90">
                {m.clarification.question}
              </p>
              <div className="mt-3 space-y-2">
                {m.clarification.options.map((o) => (
                  <button
                    key={o}
                    className="flex w-full items-center gap-2 rounded-lg bg-black/25 px-3 py-2 text-left text-[12px] text-amber-50 ring-1 ring-amber-400/20 transition hover:bg-black/40"
                  >
                    <CircleDot className="h-3.5 w-3.5 flex-none text-amber-300" /> {o}
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          {/* structured mission fields */}
          <div className="mt-6 grid gap-x-6 gap-y-5 sm:grid-cols-2 lg:grid-cols-3">
            <Field label="Objective">{m.objective}</Field>
            <Field label="Target market / geography">{m.market}</Field>
            <Field label="Business-model scope">{m.scope}</Field>
            <Field label="Capital / budget limit" mono>{m.capitalLimit}</Field>
            <Field label="Time limit">{m.timeLimit}</Field>
            <Field label="Risk tolerance">{m.riskTolerance}</Field>
            <div className="sm:col-span-2 lg:col-span-3">
              <Field label="Evidence requirement">{m.evidenceRequirement}</Field>
            </div>
            <div className="sm:col-span-2 lg:col-span-2">
              <p className="text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500">
                Allowed tools
              </p>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {m.allowedTools.map((t) => (
                  <span key={t} className="inline-flex items-center gap-1 rounded-md bg-white/5 px-2 py-1 font-mono text-[10px] text-slate-300 ring-1 ring-white/10">
                    <Wrench className="h-2.5 w-2.5 text-blue-300" /> {t}
                  </span>
                ))}
              </div>
            </div>
            <div className="flex gap-6">
              <Field label="Created" mono>{m.created}</Field>
              <Field label="Last update" mono>{m.updated}</Field>
            </div>
          </div>
        </div>
      </Reveal>
    </div>
  );
}

/* ================= task graph (DAG) ================= */

const COL_W = 190;
const ROW_H = 132;
const NODE_W = 168;
const NODE_H = 96;

function TaskNode({
  t,
  onWhy,
}: {
  t: (typeof tasks)[number];
  onWhy: () => void;
}) {
  const meta = taskStateMeta[t.state];
  const agent = agents.find((a) => a.id === t.agent);
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.85 }}
      whileInView={{ opacity: 1, scale: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.45 }}
      style={{ left: t.col * COL_W, top: t.row * ROW_H, width: NODE_W }}
      className="coolie-solid absolute rounded-xl p-3 ring-1 ring-white/10"
    >
      <div className="flex items-center justify-between gap-1">
        <span className="font-mono text-[9px] font-semibold text-blue-200">{t.id}</span>
        <span className={cn("h-1.5 w-1.5 rounded-full", meta.dot)} />
      </div>
      <p className="mt-1.5 line-clamp-2 text-[11px] font-medium leading-snug text-slate-100">
        {t.objective}
      </p>
      <p className="mt-1 truncate font-mono text-[9px] text-slate-500">
        {agent ? agent.n.replace(" Agent", "") : t.agent}
      </p>
      <div className="mt-2 flex flex-wrap items-center gap-1">
        <span className={cn("rounded px-1.5 py-0.5 text-[8px] font-bold tracking-wider ring-1", meta.cls)}>
          {meta.label}
        </span>
        <span className="rounded bg-white/5 px-1.5 py-0.5 text-[8px] font-bold text-slate-400">
          {t.priority}
        </span>
        {t.state === "COMPLETED" && (t.accepted ? (
          <span className="inline-flex items-center gap-0.5 rounded bg-emerald-400/15 px-1 py-0.5 text-[8px] font-bold text-emerald-200">
            <Lock className="h-2 w-2" /> ACCEPTED
          </span>
        ) : (
          <span className="rounded bg-amber-400/15 px-1 py-0.5 text-[8px] font-bold text-amber-200">
            RECEIVED
          </span>
        ))}
      </div>
      <div className="absolute -right-1 -top-1">
        <WhyBtn onClick={onWhy} label="i" />
      </div>
    </motion.div>
  );
}

function TaskGraph() {
  const { openWhy } = useResearch();
  const [hover, setHover] = useState<string | null>(null);
  const width = Math.max(...tasks.map((t) => t.col)) * COL_W + NODE_W + 24;
  const height = (Math.max(...tasks.map((t) => t.row)) + 1) * ROW_H;

  return (
    <Reveal>
      <Panel
        kicker="RESEARCH DAG · DEPENDENCY-AWARE"
        title="Task Graph"
        material="glass"
        right={
          <div className="flex flex-wrap gap-1.5">
            {(["QUEUED", "RUNNING", "BLOCKED", "VERIFYING", "COMPLETED"] as const).map((s) => (
              <span key={s} className={cn("rounded px-1.5 py-0.5 text-[9px] font-bold ring-1", taskStateMeta[s].cls)}>
                {s}
              </span>
            ))}
          </div>
        }
      >
        <p className="mb-4 text-[12px] leading-relaxed text-slate-400">
          A task is <span className="text-white">COMPLETED</span> only when its output has been
          independently validated. Receiving an agent payload is a separate, lesser state.
        </p>

        <div className="-mx-2 overflow-x-auto px-2 pb-2">
          <div className="relative" style={{ width, height, minWidth: width }}>
            {/* edges */}
            <svg className="absolute inset-0" width={width} height={height}>
              {tasks.flatMap((t) =>
                t.depends.map((d) => {
                  const from = tasks.find((x) => x.id === d)!;
                  const x1 = from.col * COL_W + NODE_W;
                  const y1 = from.row * ROW_H + NODE_H / 2;
                  const x2 = t.col * COL_W;
                  const y2 = t.row * ROW_H + NODE_H / 2;
                  const mx = (x1 + x2) / 2;
                  const active = hover === t.id || hover === d;
                  return (
                    <motion.path
                      key={`${d}-${t.id}`}
                      d={`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`}
                      fill="none"
                      stroke={active ? "#60a5fa" : "rgba(148,180,220,0.25)"}
                      strokeWidth={active ? 2 : 1.2}
                      strokeDasharray={t.state === "BLOCKED" ? "4 3" : undefined}
                      initial={{ pathLength: 0 }}
                      whileInView={{ pathLength: 1 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.8, delay: t.col * 0.05 }}
                      style={{ filter: active ? "drop-shadow(0 0 4px #60a5fa)" : undefined }}
                    />
                  );
                })
              )}
            </svg>
            {tasks.map((t) => (
              <div
                key={t.id}
                onMouseEnter={() => setHover(t.id)}
                onMouseLeave={() => setHover(null)}
              >
                <TaskNode
                  t={t}
                  onWhy={() =>
                    openWhy({
                      title: t.objective,
                      subject: `${t.id} · ${taskStateMeta[t.state].label}`,
                      evidence: [],
                      assumptions: [
                        `Assigned to ${agents.find((a) => a.id === t.agent)?.n ?? t.agent}`,
                        `Retry count ${t.retries} · timeout ${t.timeout} · cost limit ${t.cost}`,
                        `Evidence threshold: ${t.evidenceThreshold}`,
                      ],
                      reasoning: `Expected output: ${t.output}. Completion criteria: ${t.criteria}.`,
                    })
                  }
                />
              </div>
            ))}
          </div>
        </div>
      </Panel>
    </Reveal>
  );
}

/* ================= task table ================= */

function TaskTable() {
  const { openWhy } = useResearch();
  return (
    <Reveal>
      <Panel kicker="STRUCTURED TASK RECORDS" title="Research Tasks" material="solid">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-left text-[12px]">
            <thead>
              <tr className="border-b border-white/10 text-[9px] uppercase tracking-wider text-slate-500">
                {["Task", "Objective", "Agent", "State", "Pri", "Depends", "Retry", "Timeout", "Cost", "Evidence threshold", "Output", "Criteria"].map((h) => (
                  <th key={h} className="whitespace-nowrap px-3 py-2.5 font-semibold">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tasks.map((t, i) => {
                const meta = taskStateMeta[t.state];
                return (
                  <motion.tr
                    key={t.id}
                    initial={{ opacity: 0, x: -10 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: i * 0.03 }}
                    className="border-b border-white/5 last:border-0 hover:bg-white/[0.02]"
                  >
                    <td className="whitespace-nowrap px-3 py-2.5 font-mono text-[11px] text-blue-200">{t.id}</td>
                    <td className="max-w-[220px] px-3 py-2.5 text-slate-200">{t.objective}</td>
                    <td className="whitespace-nowrap px-3 py-2.5 font-mono text-[10px] text-slate-400">{t.agent}</td>
                    <td className="px-3 py-2.5">
                      <span className={cn("whitespace-nowrap rounded px-1.5 py-0.5 text-[9px] font-bold ring-1", meta.cls)}>{meta.label}</span>
                    </td>
                    <td className="px-3 py-2.5 font-mono text-[10px] text-slate-400">{t.priority}</td>
                    <td className="px-3 py-2.5 font-mono text-[9px] text-slate-500">{t.depends.length ? t.depends.join(", ") : "—"}</td>
                    <td className="px-3 py-2.5 font-mono text-[10px] text-slate-400">{t.retries}</td>
                    <td className="whitespace-nowrap px-3 py-2.5 font-mono text-[10px] text-slate-400">{t.timeout}</td>
                    <td className="whitespace-nowrap px-3 py-2.5 font-mono text-[10px] text-slate-400">{t.cost}</td>
                    <td className="max-w-[150px] px-3 py-2.5 text-[10px] text-slate-400">{t.evidenceThreshold}</td>
                    <td className="whitespace-nowrap px-3 py-2.5 font-mono text-[10px] text-slate-400">{t.output}</td>
                    <td className="max-w-[200px] px-3 py-2.5 text-[10px] text-slate-400">
                      {t.criteria}
                    </td>
                  </motion.tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-2 rounded-lg bg-black/25 px-3 py-2.5 ring-1 ring-white/[0.06]">
          <AcceptanceBadge accepted={false} />
          <p className="text-[11px] text-slate-400">
            3 of 5 finished tasks have validated output. TSK-06 and TSK-04 returned payloads that
            have not yet cleared verification.
          </p>
          <WhyBtn
            className="ml-auto"
            onClick={() =>
              openWhy({
                title: "Why isn't a returned payload accepted?",
                subject: "Acceptance policy",
                evidence: ["EV-007", "EV-009", "EV-014"],
                assumptions: ["Agent output is a claim, not a finding", "Only the Evidence Verification Agent can accept a claim"],
                reasoning:
                  "The Marketing Intelligence and Supplier agents returned structured payloads, but the Evidence Verification Agent has not independently re-confirmed them. Until it does, they are labelled OUTPUT RECEIVED and are excluded from scoring.",
              })
            }
          />
        </div>
      </Panel>
    </Reveal>
  );
}

/* ================= agent strip ================= */

function AgentStrip() {
  const { go } = useResearch();
  return (
    <Reveal>
      <Panel
        kicker="10 RESEARCH ROOM SPECIALISTS · CONTRIBUTING, NOT DECIDING"
        title="Agents on this mission"
        material="metal"
        right={
          <button
            onClick={() => go("agents")}
            className="inline-flex items-center gap-1 rounded-lg bg-white/5 px-2.5 py-1.5 text-[11px] font-medium text-slate-300 ring-1 ring-white/10 hover:bg-white/10"
          >
            Open Agents room <ChevronRight className="h-3 w-3" />
          </button>
        }
      >
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {agents.map((a, i) => (
            <motion.div
              key={a.id}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.04 }}
              className="rounded-xl bg-black/25 p-3 ring-1 ring-white/[0.07]"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-[9px] text-slate-500">{a.id}</span>
                <span
                  className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    a.status === "RUNNING" ? "bg-cyan-400" : a.status === "BLOCKED" ? "bg-rose-400" : a.status === "AWAITING_REVIEW" ? "bg-amber-400" : "bg-slate-500"
                  )}
                />
              </div>
              <p className="mt-1.5 line-clamp-2 text-[11px] font-semibold leading-tight text-white">
                {a.n.replace(" Agent", "")}
              </p>
              <p className="mt-1 line-clamp-2 text-[10px] leading-snug text-slate-500">{a.task}</p>
              <div className="mt-2 flex items-center justify-between font-mono text-[9px] text-slate-500">
                <span>{a.evidence} ev</span>
                <span>{a.confidence}% conf</span>
              </div>
              <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-white/10">
                <motion.div
                  initial={{ scaleX: 0 }}
                  whileInView={{ scaleX: a.workload / 100 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.7 }}
                  className="h-full origin-left rounded-full bg-gradient-to-r from-blue-500 to-cyan-300"
                />
              </div>
            </motion.div>
          ))}
        </div>
      </Panel>
    </Reveal>
  );
}

/* ================= event stream ================= */

const lvl = {
  info: { c: "text-slate-400", dot: "bg-slate-500", I: CircleDot },
  ok: { c: "text-emerald-300", dot: "bg-emerald-400", I: CheckCircle2 },
  warn: { c: "text-amber-300", dot: "bg-amber-400", I: AlertCircle },
  block: { c: "text-rose-300", dot: "bg-rose-400", I: XCircle },
};

function EventStream() {
  return (
    <Reveal>
      <Panel
        kicker="BACKEND EVENT STREAM"
        title="Audit events"
        material="blue"
        right={<MockBadge />}
      >
        <div className="max-h-[420px] space-y-1.5 overflow-y-auto pr-1">
          {events.map((e, i) => {
            const L = lvl[e.level];
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: Math.min(i * 0.03, 0.4) }}
                className="rounded-lg bg-black/25 px-3 py-2 ring-1 ring-white/[0.06]"
              >
                <div className="flex items-start gap-2.5">
                  <L.I className={cn("mt-0.5 h-3.5 w-3.5 flex-none", L.c)} />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline gap-x-2">
                      <span className="font-mono text-[10px] text-slate-500">{e.ts}</span>
                      <span className="font-mono text-[10px] font-semibold text-blue-100">{e.event}</span>
                    </div>
                    <p className="mt-0.5 text-[11px] leading-snug text-slate-300">{e.result}</p>
                    <p className="mt-1 flex flex-wrap gap-x-2 font-mono text-[9px] text-slate-600">
                      <span>{e.mission}</span>
                      <span>· {e.task}</span>
                      <span>· {e.agent}</span>
                    </p>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </Panel>
    </Reveal>
  );
}

/* ================= screen ================= */

export default function MissionControl() {
  const { activeMission, connection } = useResearch();
  if (connection === "connected") return <LiveMissionControl />;
  const m = missions.find((x) => x.id === activeMission)!;
  const idx = LIFECYCLE.indexOf(m.stage as (typeof LIFECYCLE)[number]);

  const stats = [
    { icon: GitBranch, label: "Tasks in graph", v: `${tasks.length}`, s: `${tasks.filter((t) => t.state === "COMPLETED").length} completed` },
    { icon: Clock, label: "Current stage", v: stageMeta[m.stage]?.label ?? m.stage, s: `stage ${idx + 1} of ${LIFECYCLE.length}` },
    { icon: Wallet, label: "Capital limit", v: m.capitalLimit, s: "uncommitted" },
    { icon: ShieldCheck, label: "Blocking findings", v: "1", s: "progression halted" },
    { icon: Target, label: "Verified evidence", v: "7", s: "of 14 collected" },
  ];

  return (
    <div className="mx-auto w-full max-w-7xl px-4 pb-40 sm:pb-32">
      <Reveal>
        <div className="mb-6">
          <p className="text-[11px] font-medium tracking-[0.3em] text-blue-300/70">
            MISSION CONTROL · RESEARCH OPERATING SYSTEM
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-metal sm:text-4xl">
            What is Coolie researching?
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            Missions decompose into a dependency-aware task graph, worked by ten specialist
            agents. Nothing becomes a finding until evidence verifies it.
          </p>
        </div>
      </Reveal>

      <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-5">
        {stats.map((s, i) => (
          <Reveal key={s.label} delay={i * 0.05}>
            <div className="coolie-metal rounded-xl p-4">
              <s.icon className="h-4 w-4 text-blue-300" strokeWidth={1.7} />
              <p className="mt-2.5 text-xl font-semibold text-metal">{s.v}</p>
              <p className="text-[9px] font-bold uppercase tracking-wider text-slate-500">{s.label}</p>
              <p className="mt-0.5 text-[10px] text-slate-500">{s.s}</p>
            </div>
          </Reveal>
        ))}
      </div>

      <MissionBrief />

      <div className="mt-5 grid gap-5 lg:grid-cols-[2fr_1fr]">
        <div className="space-y-5">
          <TaskGraph />
          <AgentStrip />
        </div>
        <EventStream />
      </div>

      <div className="mt-5">
        <TaskTable />
      </div>

      <div className="mt-5 flex items-start gap-2.5 rounded-2xl bg-amber-400/[0.07] p-4 ring-1 ring-amber-400/20">
        <HelpCircle className="mt-0.5 h-4 w-4 flex-none text-amber-300" />
        <p className="text-[12px] leading-relaxed text-amber-100/90">
          Progress is expressed as the actual lifecycle stage above — never a percentage. A mission
          does not advance past a blocking risk finding, and an ambiguous objective halts the
          mission entirely rather than letting it run on a guess.
        </p>
      </div>
    </div>
  );
}
