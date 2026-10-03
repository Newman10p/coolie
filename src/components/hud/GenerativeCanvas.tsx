import { AnimatePresence, motion } from "motion/react";
import {
  Activity,
  ArrowUpRight,
  CheckCircle2,
  ClipboardList,
  FileSearch,
  Layers3,
  Lightbulb,
  Radar,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { agents, evidence, missions, moneyOutputs, recPacket, riskFindings, stageMeta, tasks } from "../../research/data";
import { useResearch } from "../../research/store";
import { Chip, Confidence, EvType, WhyBtn } from "../../research/ui";
import type { Intent } from "../../data";

interface Props {
  query: string;
  intent: Intent | null;
  pending: boolean;
  turn: number;
}

function CanvasEmpty() {
  return (
    <div className="flex min-h-[360px] flex-col items-center justify-center px-5 py-10 text-center">
      <div className="relative grid h-16 w-16 place-items-center rounded-2xl bg-blue-400/10 ring-1 ring-blue-300/20">
        <Sparkles className="h-7 w-7 text-blue-200" strokeWidth={1.4} />
        <motion.span
          animate={{ scale: [1, 1.7, 1], opacity: [0.45, 0, 0.45] }}
          transition={{ duration: 2.8, repeat: Infinity, ease: "easeInOut" }}
          className="absolute inset-0 rounded-2xl border border-blue-300/40"
        />
      </div>
      <p className="mt-5 text-[10px] font-bold tracking-[0.24em] text-blue-300/70">
        GENERATIVE RESPONSE SURFACE
      </p>
      <h3 className="mt-2 text-lg font-semibold text-metal">Your answer, made visual.</h3>
      <p className="mt-2 max-w-xs text-[12px] leading-relaxed text-slate-400">
        Talk or type naturally. When a response has structured data, this space can compose the
        mission brief, evidence trail, risk gate, financial handoff or recommendation packet that
        best fits the conversation.
      </p>

      <div className="mt-7 grid w-full max-w-sm grid-cols-2 gap-2">
        {[
          [Radar, "Mission brief"],
          [Layers3, "Opportunity"],
          [FileSearch, "Evidence trail"],
          [ClipboardList, "Decision packet"],
        ].map(([Icon, title]) => {
          const I = Icon as typeof Radar;
          return (
            <div
              key={title as string}
              className="flex items-center gap-2 rounded-xl bg-black/25 px-3 py-2.5 text-left ring-1 ring-white/[0.07]"
            >
              <I className="h-3.5 w-3.5 text-blue-300/70" />
              <span className="text-[11px] text-slate-500">{title as string}</span>
            </div>
          );
        })}
      </div>

      <div className="mt-6 flex items-center gap-2 text-[10px] text-slate-600">
        <span className="h-px w-8 bg-white/10" />
        Responds to your words, not a command palette
        <span className="h-px w-8 bg-white/10" />
      </div>
    </div>
  );
}

function EvidenceList({ ids }: { ids: string[] }) {
  const { traceEvidence } = useResearch();
  const records = ids
    .map((id) => evidence.find((e) => e.id === id))
    .filter((e): e is (typeof evidence)[number] => Boolean(e));
  return (
    <div className="space-y-2">
      {records.map((e) => (
        <button
          key={e.id}
          onClick={() => traceEvidence(e.id)}
          className="w-full rounded-xl bg-black/25 p-3 text-left ring-1 ring-white/[0.07] transition hover:bg-black/40"
        >
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-mono text-[9px] font-bold text-blue-200">{e.id}</span>
            <EvType t={e.type} />
            <span className="ml-auto font-mono text-[9px] text-slate-500">{e.confidence}%</span>
          </div>
          <p className="mt-1.5 line-clamp-2 text-[11px] leading-relaxed text-slate-200">{e.claim}</p>
        </button>
      ))}
    </div>
  );
}

function GenerativeArtifact({ intent }: { intent: Intent }) {
  const { go, traceEvidence, openWhy } = useResearch();
  const mission = missions[0];

  if (intent.id === "research") {
    const items = evidence.filter((e) => e.missionId === mission.id).slice(0, 3);
    return (
      <div className="space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[9px] font-bold tracking-[0.2em] text-blue-300/70">ACTIVE MISSION</p>
            <p className="mt-1 text-[14px] font-semibold text-white">{mission.name}</p>
            <p className="mt-0.5 font-mono text-[9px] text-slate-500">{mission.id}</p>
          </div>
          <Chip tone="violet" dot="bg-violet-400">{stageMeta[mission.stage]?.label}</Chip>
        </div>
        <div className="rounded-xl bg-black/25 p-3 ring-1 ring-white/[0.07]">
          <p className="text-[9px] font-bold uppercase tracking-wider text-slate-500">Mission objective</p>
          <p className="mt-1 text-[11px] leading-relaxed text-slate-200">{mission.objective}</p>
        </div>
        <div className="flex items-center justify-between text-[10px]">
          <span className="text-slate-500">Evidence collected</span>
          <span className="font-mono text-slate-300">14 received · 7 verified</span>
        </div>
        <EvidenceList ids={items.map((e) => e.id)} />
        <button
          onClick={() => go("mission")}
          className="flex w-full items-center justify-center gap-1.5 rounded-xl bg-blue-400/10 py-2.5 text-[11px] font-semibold text-blue-100 ring-1 ring-blue-300/20 hover:bg-blue-400/15"
        >
          Open Mission Control <ArrowUpRight className="h-3 w-3" />
        </button>
      </div>
    );
  }

  if (intent.id === "treasury") {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-2">
          {moneyOutputs.slice(1, 5).map((m) => (
            <div key={m.label} className="rounded-xl bg-black/25 p-3 ring-1 ring-white/[0.07]">
              <p className="text-[8px] font-bold uppercase tracking-wider text-slate-500">{m.label}</p>
              <p className="mt-1 font-mono text-[14px] font-semibold text-metal">{m.value}</p>
              <p className="mt-0.5 text-[9px] text-slate-600">{m.note}</p>
            </div>
          ))}
        </div>
        <div className="rounded-xl bg-amber-400/[0.07] p-3 ring-1 ring-amber-400/20">
          <p className="flex items-center gap-1.5 text-[10px] font-bold text-amber-200">
            <ShieldAlert className="h-3.5 w-3.5" /> ESTIMATES NEED VERIFICATION
          </p>
          <p className="mt-1.5 text-[11px] leading-relaxed text-amber-100/80">
            Four of six financial inputs are estimates. The contribution and payback shown are
            provisional, not verified facts.
          </p>
          <WhyBtn
            className="mt-2"
            onClick={() =>
              openWhy({
                title: "Money Calculator assumptions",
                subject: "Research → Finance handoff",
                value: "AED 65.60 contribution / unit",
                evidence: ["EV-004", "EV-006", "EV-007", "EV-009"],
                assumptions: [
                  "Duty holds at 5%, not confirmed with customs",
                  "Spot freight rate is representative at MOQ 500",
                  "Blended CAC is model-derived and unverified",
                ],
              })
            }
          />
        </div>
        <EvidenceList ids={["EV-004", "EV-006", "EV-007", "EV-009"]} />
        <button
          onClick={() => go("decisions")}
          className="flex w-full items-center justify-center gap-1.5 rounded-xl bg-blue-400/10 py-2.5 text-[11px] font-semibold text-blue-100 ring-1 ring-blue-300/20 hover:bg-blue-400/15"
        >
          Open financial evaluation <ArrowUpRight className="h-3 w-3" />
        </button>
      </div>
    );
  }

  if (intent.id === "compliance") {
    return (
      <div className="space-y-3">
        {riskFindings.slice(0, 4).map((r) => (
          <div
            key={r.id}
            className={
              r.severity === "BLOCKING"
                ? "rounded-xl bg-rose-500/[0.08] p-3 ring-1 ring-rose-400/25"
                : "rounded-xl bg-black/25 p-3 ring-1 ring-white/[0.07]"
            }
          >
            <div className="flex items-center gap-1.5">
              <span className="font-mono text-[9px] font-bold text-slate-300">{r.id}</span>
              <Chip tone={r.severity === "BLOCKING" ? "bad" : r.severity === "WARNING" ? "warn" : "ok"}>
                {r.severity}
              </Chip>
              <button
                onClick={() => traceEvidence(r.evidence)}
                className="ml-auto font-mono text-[9px] text-blue-200 underline decoration-dotted"
              >
                {r.evidence}
              </button>
            </div>
            <p className="mt-1.5 text-[11px] font-medium leading-relaxed text-slate-100">{r.finding}</p>
            <p className="mt-1 text-[10px] leading-relaxed text-slate-500">Required: {r.action}</p>
          </div>
        ))}
        <div className="rounded-xl border border-rose-400/25 bg-rose-500/[0.06] px-3 py-2.5 text-[10px] font-semibold tracking-wide text-rose-200">
          GATE BLOCKED · automatic progression is halted
        </div>
        <button
          onClick={() => go("decisions")}
          className="flex w-full items-center justify-center gap-1.5 rounded-xl bg-blue-400/10 py-2.5 text-[11px] font-semibold text-blue-100 ring-1 ring-blue-300/20 hover:bg-blue-400/15"
        >
          Open Risk &amp; Policy Gate <ArrowUpRight className="h-3 w-3" />
        </button>
      </div>
    );
  }

  if (intent.id === "decisions") {
    return (
      <div className="space-y-4">
        <div className="rounded-xl bg-black/25 p-3 ring-1 ring-white/[0.07]">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[9px] font-bold text-blue-200">{recPacket.id}</span>
            <Chip tone="warn">{recPacket.recommendation}</Chip>
          </div>
          <p className="mt-2 text-[12px] font-semibold text-white">{recPacket.title}</p>
          <p className="mt-1 text-[10px] leading-relaxed text-slate-400">{recPacket.nextAction}</p>
          <div className="mt-3 flex items-center justify-between">
            <span className="text-[9px] font-bold uppercase tracking-wider text-slate-500">Confidence</span>
            <Confidence v={recPacket.confidence} />
          </div>
        </div>
        <div>
          <p className="mb-2 text-[9px] font-bold tracking-[0.18em] text-slate-500">APPROVALS REQUIRED</p>
          {recPacket.approvals.map((a) => (
            <p key={a} className="mb-1.5 flex items-start gap-2 rounded-lg bg-amber-400/[0.06] px-2.5 py-2 text-[10px] leading-relaxed text-amber-100/80 ring-1 ring-amber-400/15">
              <span className="mt-1 h-1 w-1 flex-none rounded-full bg-amber-300" />{a}
            </p>
          ))}
        </div>
        <EvidenceList ids={recPacket.evidenceRefs.slice(0, 4)} />
        <button
          onClick={() => go("decisions")}
          className="flex w-full items-center justify-center gap-1.5 rounded-xl bg-blue-400/10 py-2.5 text-[11px] font-semibold text-blue-100 ring-1 ring-blue-300/20 hover:bg-blue-400/15"
        >
          Open Decision Center <ArrowUpRight className="h-3 w-3" />
        </button>
      </div>
    );
  }

  if (intent.id === "enactor" || intent.id === "sectors") {
    const activeAgents = agents.filter((a) => a.status === "RUNNING" || a.status === "BLOCKED").slice(0, 5);
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between rounded-xl bg-black/25 px-3 py-2.5 ring-1 ring-white/[0.07]">
          <span className="text-[10px] text-slate-400">Research specialists assigned</span>
          <span className="font-mono text-[12px] font-semibold text-white">10</span>
        </div>
        {activeAgents.map((a) => (
          <div key={a.id} className="rounded-xl bg-black/25 p-3 ring-1 ring-white/[0.07]">
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-[10px] font-semibold text-slate-100">{a.n}</span>
              <span className="font-mono text-[8px] text-slate-500">{a.status}</span>
            </div>
            <p className="mt-1 line-clamp-2 text-[10px] leading-relaxed text-slate-400">{a.task}</p>
            <div className="mt-2 h-1 overflow-hidden rounded-full bg-white/10">
              <motion.div
                initial={{ scaleX: 0 }}
                animate={{ scaleX: a.workload / 100 }}
                transition={{ duration: 0.8, delay: 0.1 }}
                className="h-full origin-left rounded-full bg-gradient-to-r from-blue-500 to-cyan-300"
              />
            </div>
          </div>
        ))}
        <button
          onClick={() => go("agents")}
          className="flex w-full items-center justify-center gap-1.5 rounded-xl bg-blue-400/10 py-2.5 text-[11px] font-semibold text-blue-100 ring-1 ring-blue-300/20 hover:bg-blue-400/15"
        >
          Open specialist assignments <ArrowUpRight className="h-3 w-3" />
        </button>
      </div>
    );
  }

  if (intent.id === "memory") {
    return (
      <div className="space-y-3">
        {[
          ["Previous mission", "MSN-2026-0131 · Modest Activewear Q4"],
          ["Outcome", "Launched 1 SKU · AED 214K revenue in 9 weeks"],
          ["Learned", "Apparel return assumption was 2%; actual was 9.4%"],
        ].map(([k, v]) => (
          <div key={k} className="rounded-xl bg-black/25 p-3 ring-1 ring-white/[0.07]">
            <p className="text-[9px] font-bold uppercase tracking-wider text-slate-500">{k}</p>
            <p className="mt-1 text-[11px] leading-relaxed text-slate-200">{v}</p>
          </div>
        ))}
        <button
          onClick={() => go("history")}
          className="flex w-full items-center justify-center gap-1.5 rounded-xl bg-blue-400/10 py-2.5 text-[11px] font-semibold text-blue-100 ring-1 ring-blue-300/20 hover:bg-blue-400/15"
        >
          Open immutable history <ArrowUpRight className="h-3 w-3" />
        </button>
      </div>
    );
  }

  return (
    <div className="flex min-h-[300px] flex-col items-center justify-center px-5 py-8 text-center">
      <Lightbulb className="h-6 w-6 text-blue-300/70" />
      <p className="mt-3 text-[12px] font-semibold text-slate-200">Natural-language response</p>
      <p className="mt-1.5 max-w-xs text-[11px] leading-relaxed text-slate-500">
        The Orchestrator answered conversationally. No structured artifact matched this request yet.
        Ask a follow-up in your own words to explore a mission, evidence, risk finding or decision.
      </p>
      <div className="mt-4 flex items-center gap-2 font-mono text-[9px] text-slate-600">
        <Activity className="h-3 w-3" /> {tasks.length} workflow nodes available in Mission Control
      </div>
    </div>
  );
}

export default function GenerativeCanvas({ query, intent, pending, turn }: Props) {
  return (
    <motion.aside
      initial={{ opacity: 0, x: 18 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, delay: 0.25 }}
      className="order-2 min-w-0 lg:order-3"
      aria-label="Generative response canvas"
    >
      <div className="coolie-glass-blue relative h-full min-h-[480px] overflow-hidden rounded-3xl p-4 sm:p-5">
        <div className="coolie-hud-grid pointer-events-none absolute inset-0 opacity-35" />
        <div className="pointer-events-none absolute -right-16 -top-16 h-44 w-44 rounded-full bg-blue-400/10 blur-3xl" />

        <div className="relative flex items-center justify-between gap-3 border-b border-white/[0.08] pb-3">
          <div>
            <p className="text-[9px] font-bold tracking-[0.22em] text-blue-300/70">
              GENERATIVE UI · RESPONSE CANVAS
            </p>
            <p className="mt-1 text-[12px] font-semibold text-white">
              {pending ? "Composing from your request" : intent ? "Contextual view" : "Awaiting conversation"}
            </p>
          </div>
          <span className="relative grid h-8 w-8 flex-none place-items-center rounded-xl bg-blue-400/10 ring-1 ring-blue-300/20">
            <Sparkles className="h-4 w-4 text-blue-200" />
            {pending && (
              <motion.span
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                className="absolute -inset-1 rounded-[14px] border border-dashed border-blue-300/30"
              />
            )}
          </span>
        </div>

        <div className="relative mt-4">
          <AnimatePresence mode="wait">
            {!intent ? (
              <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <CanvasEmpty />
              </motion.div>
            ) : pending ? (
              <motion.div
                key="pending"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="flex min-h-[380px] flex-col items-center justify-center text-center"
              >
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 7, repeat: Infinity, ease: "linear" }}
                  className="grid h-14 w-14 place-items-center rounded-2xl border border-dashed border-blue-300/30 bg-blue-400/[0.05]"
                >
                  <Layers3 className="h-6 w-6 text-blue-200" />
                </motion.div>
                <p className="mt-4 text-[11px] font-bold tracking-[0.18em] text-blue-200/80">ASSEMBLING VIEW</p>
                <p className="mt-2 max-w-xs text-[11px] leading-relaxed text-slate-400">
                  Connecting your words to mission context, verified evidence and decision records.
                </p>
                <div className="mt-4 flex items-center gap-1.5">
                  {[0, 1, 2].map((i) => (
                    <motion.span
                      key={i}
                      animate={{ opacity: [0.25, 1, 0.25], scale: [0.85, 1, 0.85] }}
                      transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.18 }}
                      className="h-1.5 w-1.5 rounded-full bg-blue-300"
                    />
                  ))}
                </div>
              </motion.div>
            ) : (
              <motion.div
                key={`${intent.id}-${turn}`}
                initial={{ opacity: 0, y: 12, filter: "blur(5px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                exit={{ opacity: 0, y: -8, filter: "blur(4px)" }}
                transition={{ duration: 0.4 }}
              >
                <div className="mb-4 rounded-xl bg-black/25 px-3 py-2.5 ring-1 ring-white/[0.07]">
                  <p className="text-[8px] font-bold uppercase tracking-[0.18em] text-slate-600">Natural-language request</p>
                  <p className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-slate-300">“{query}”</p>
                </div>
                <GenerativeArtifact intent={intent} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="relative mt-4 flex items-center justify-between border-t border-white/[0.08] pt-3">
          <span className="inline-flex items-center gap-1.5 text-[9px] font-medium text-slate-600">
            <CheckCircle2 className="h-3 w-3 text-emerald-400/70" /> Traceable UI · data links to source
          </span>
          <span className="font-mono text-[9px] text-slate-600">TURN {String(turn).padStart(2, "0")}</span>
        </div>
      </div>
    </motion.aside>
  );
}