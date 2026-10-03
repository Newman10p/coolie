import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  ShieldAlert, ShieldCheck, Compass, FileSignature, Check, X,
  AlertTriangle, Ban, ArrowRight, HelpCircle, FileText, Lock,
} from "lucide-react";
import { cn } from "../utils/cn";
import {
  riskFindings, riskChecksPassed, moneyInputs, moneyOutputs, moneyAssumptions,
  strategy, recPacket, approvals, type Approval, type RecType,
} from "../research/data";
import { Chip, EvType, Field, Panel, WhyBtn, Confidence } from "../research/ui";
import { Reveal, SectionHeading } from "../components/scroll/Reveal";
import { useResearch } from "../research/store";

const sevTone = {
  BLOCKING: { chip: "bad", ring: "ring-rose-400/35", bg: "bg-rose-500/[0.07]", I: Ban },
  WARNING: { chip: "warn", ring: "ring-amber-400/25", bg: "bg-amber-400/[0.06]", I: AlertTriangle },
  INFO: { chip: "neutral", ring: "ring-white/10", bg: "bg-white/[0.02]", I: ShieldCheck },
} as const;

/* ---------------- Risk & Policy Gate ---------------- */

function RiskGate() {
  const { openWhy, traceEvidence } = useResearch();
  const blocking = riskFindings.filter((f) => f.severity === "BLOCKING");

  return (
    <Reveal>
      <div
        className={cn(
          "rounded-2xl p-5 ring-1",
          blocking.length ? "bg-rose-500/[0.06] ring-rose-400/35" : "coolie-metal"
        )}
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            {blocking.length ? (
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-rose-500/20 ring-1 ring-rose-400/40">
                <Ban className="h-4.5 w-4.5 text-rose-300" />
              </span>
            ) : (
              <ShieldCheck className="h-5 w-5 text-emerald-300" />
            )}
            <div>
              <p className="text-[10px] font-bold tracking-[0.22em] text-rose-200/80">
                RISK &amp; POLICY GATE
              </p>
              <p className="text-sm font-semibold text-white">
                {blocking.length
                  ? "Progression halted — a blocking finding is open"
                  : "All checks passed"}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-1.5">
            <Chip tone="bad">{blocking.length} blocking</Chip>
            <Chip tone="warn">{riskFindings.filter((f) => f.severity === "WARNING").length} warnings</Chip>
            <Chip tone="ok">{riskChecksPassed.length} checks passed</Chip>
          </div>
        </div>

        {/* never confuse "nothing found yet" with "passed" */}
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          <div className={cn("rounded-xl p-3 ring-1", blocking.length ? "bg-rose-500/10 ring-rose-400/30" : "bg-emerald-400/10 ring-emerald-400/25")}>
            <p className="text-[10px] font-bold tracking-wider text-slate-300">STATE OF THE GATE</p>
            <p className="mt-1 text-[12px] leading-relaxed text-white">
              {blocking.length
                ? "BLOCKED. Automatic progression is disabled. No listing, spend or dispatch can occur until RSK-07 clears."
                : "PASSED. Every registered check returned a result."}
            </p>
          </div>
          <div className="rounded-xl bg-emerald-400/[0.07] p-3 ring-1 ring-emerald-400/20">
            <p className="text-[10px] font-bold tracking-wider text-slate-300">CHECKS PASSED</p>
            <ul className="mt-1.5 space-y-0.5">
              {riskChecksPassed.map((c) => (
                <li key={c} className="flex items-center gap-1.5 text-[11px] text-emerald-100/90">
                  <ShieldCheck className="h-3 w-3 flex-none" /> {c}
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="mt-4 space-y-2.5">
          {riskFindings.map((f, i) => {
            const t = sevTone[f.severity];
            return (
              <motion.div
                key={f.id}
                initial={{ opacity: 0, x: -12 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.06 }}
                className={cn("rounded-xl p-4 ring-1", t.bg, t.ring)}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Chip tone={t.chip}>
                    <t.I className="h-2.5 w-2.5" /> {f.severity}
                  </Chip>
                  <span className="font-mono text-[10px] font-bold text-slate-300">{f.id}</span>
                  <span className="text-[11px] font-medium text-slate-400">{f.area}</span>
                  <WhyBtn
                    className="ml-auto"
                    onClick={() =>
                      openWhy({
                        title: f.finding,
                        subject: `Risk finding ${f.id} · ${f.severity}`,
                        evidence: [f.evidence],
                        assumptions: [f.reason],
                        reasoning: `Required action: ${f.action}`,
                      })
                    }
                  />
                </div>
                <p className="mt-2 text-[12px] font-medium leading-relaxed text-slate-100">{f.finding}</p>
                <p className="mt-1.5 text-[11px] leading-relaxed text-slate-400">
                  <span className="font-semibold text-slate-300">Reason:</span> {f.reason}
                </p>
                <div className="mt-2.5 flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => traceEvidence(f.evidence)}
                    className="inline-flex items-center gap-1.5 rounded-md bg-blue-400/10 px-2 py-1 font-mono text-[10px] font-bold text-blue-200 ring-1 ring-blue-400/25 hover:bg-blue-400/20"
                  >
                    <FileText className="h-2.5 w-2.5" /> {f.evidence}
                  </button>
                  <Chip tone="info">ACTION · {f.action}</Chip>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </Reveal>
  );
}

/* ---------------- Money Calculator handoff ---------------- */

function MoneyCalc() {
  const { openWhy, traceEvidence } = useResearch();
  return (
    <Reveal>
      <Panel
        kicker="MONEY CALCULATOR HANDOFF"
        title="Exactly what Research sends to Finance"
        material="solid"
        right={<Chip tone="gold">NORMALIZED INPUTS</Chip>}
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-[12px]">
            <thead>
              <tr className="border-b border-white/10 text-[9px] uppercase tracking-wider text-slate-500">
                {["Input", "Value", "Currency", "Source", "Confidence", "Timestamp", "Nature"].map((h) => (
                  <th key={h} className="whitespace-nowrap px-3 py-2 font-semibold">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {moneyInputs.map((m, i) => (
                <motion.tr
                  key={m.label}
                  initial={{ opacity: 0, x: -8 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.04 }}
                  className="border-b border-white/5 last:border-0"
                >
                  <td className="px-3 py-2.5 font-medium text-slate-200">{m.label}</td>
                  <td className="px-3 py-2.5 font-mono font-semibold text-white">{m.value}</td>
                  <td className="px-3 py-2.5 font-mono text-[11px] text-slate-400">{m.currency}</td>
                  <td className="px-3 py-2.5">
                    <button onClick={() => traceEvidence(m.ev)} className="text-[11px] text-blue-200 underline decoration-dotted">
                      {m.source}
                    </button>
                  </td>
                  <td className="px-3 py-2.5"><Confidence v={m.confidence} /></td>
                  <td className="whitespace-nowrap px-3 py-2.5 font-mono text-[10px] text-slate-500">{m.ts}</td>
                  <td className="px-3 py-2.5">
                    {m.estimate ? <Chip tone="warn">ESTIMATE</Chip> : <Chip tone="ok">VERIFIED</Chip>}
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {moneyOutputs.map((o, i) => (
            <motion.div
              key={o.label}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.06 }}
              className="rounded-xl bg-black/25 p-3.5 ring-1 ring-white/[0.07]"
            >
              <p className="text-[9px] font-bold uppercase tracking-wider text-slate-500">{o.label}</p>
              <p className="mt-1 font-mono text-lg font-semibold text-metal">{o.value}</p>
              <p className="mt-0.5 text-[10px] leading-snug text-slate-500">{o.note}</p>
            </motion.div>
          ))}
        </div>

        <div className="mt-4 rounded-xl bg-amber-400/[0.07] p-3.5 ring-1 ring-amber-400/20">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-[10px] font-bold tracking-wider text-amber-200">KEY ASSUMPTIONS</p>
            <WhyBtn
              label="Why these numbers?"
              className="ml-auto"
              onClick={() =>
                openWhy({
                  title: "Financial evaluation basis",
                  subject: "Money Calculator inputs",
                  value: "AED 65.60 contribution / unit",
                  evidence: ["EV-004", "EV-006", "EV-007", "EV-009"],
                  assumptions: moneyAssumptions,
                  reasoning:
                    "Only two of six inputs are verified observations. The outputs above are therefore provisional and must be re-modelled once customs and freight are confirmed.",
                })
              }
            />
          </div>
          <ul className="mt-2 space-y-1">
            {moneyAssumptions.map((a) => (
              <li key={a} className="flex items-start gap-1.5 text-[11px] leading-relaxed text-amber-100/90">
                <AlertTriangle className="mt-0.5 h-3 w-3 flex-none" /> {a}
              </li>
            ))}
          </ul>
        </div>
      </Panel>
    </Reveal>
  );
}

/* ---------------- Strategy review ---------------- */

function StrategyReview() {
  const { openWhy } = useResearch();
  const rows: [string, string][] = [
    ["Positioning", strategy.positioning],
    ["Customer segment", strategy.segment],
    ["Channel", strategy.channel],
    ["Offer", strategy.offer],
    ["Validation plan", strategy.validationPlan],
    ["Strategic fit", strategy.strategicFit],
    ["Operational complexity", strategy.complexity],
    ["Expansion potential", strategy.expansion],
  ];
  return (
    <Reveal>
      <Panel
        kicker="STRATEGY REVIEW"
        title="What does strategy think?"
        material="metal"
        right={<Chip tone="violet">STRATEGY MANAGER</Chip>}
      >
        <div className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
          {rows.map(([k, v]) => (
            <Field key={k} label={k}>{v}</Field>
          ))}
        </div>

        <div className="mt-4">
          <p className="text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500">
            Strategic concerns
          </p>
          <ul className="mt-2 space-y-1.5">
            {strategy.concerns.map((c) => (
              <li key={c} className="flex items-start gap-2 rounded-lg bg-black/25 px-3 py-2 text-[12px] leading-relaxed text-slate-300 ring-1 ring-white/[0.06]">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 flex-none text-amber-300" /> {c}
              </li>
            ))}
          </ul>
        </div>

        <div className="mt-4 flex flex-wrap items-start gap-2.5 rounded-xl bg-violet-400/[0.08] p-3.5 ring-1 ring-violet-400/25">
          <Compass className="mt-0.5 h-4 w-4 flex-none text-violet-300" />
          <div className="min-w-0 flex-1">
            <p className="text-[12px] font-semibold leading-relaxed text-violet-100">{strategy.verdict}</p>
            <p className="mt-1 text-[10px] leading-relaxed text-violet-200/70">{strategy.by}</p>
          </div>
          <WhyBtn
            onClick={() =>
              openWhy({
                title: "Strategy verdict",
                subject: "Strategy Manager",
                evidence: ["EV-004", "EV-008", "EV-010", "EV-011"],
                assumptions: strategy.concerns,
                reasoning:
                  "Research supplies evidence and structured inputs. The Strategy Manager evaluates strategic implication and returns a verdict — it does not generate the evidence itself.",
              })
            }
          />
        </div>
      </Panel>
    </Reveal>
  );
}

/* ---------------- Recommendation packet ---------------- */

const recTone: Record<RecType, string> = {
  REJECT: "text-rose-200 bg-rose-400/10 ring-rose-400/25",
  ARCHIVE: "text-slate-300 bg-white/[0.05] ring-white/12",
  RESEARCH_MORE: "text-slate-200 bg-white/[0.06] ring-white/15",
  RUN_VALIDATION: "text-violet-200 bg-violet-400/10 ring-violet-400/25",
  REQUEST_APPROVAL: "text-amber-200 bg-amber-400/10 ring-amber-400/25",
  LIMITED_LAUNCH: "text-lime-200 bg-lime-400/10 ring-lime-400/25",
};

function RecPacket() {
  const { openWhy, traceEvidence, go } = useResearch();
  const sections: [string, string[]][] = [
    ["Reasons", recPacket.reasons],
    ["Assumptions", recPacket.assumptions],
    ["Risks", recPacket.risks],
    ["Required approvals", recPacket.approvals],
    ["Invalidation conditions", recPacket.invalidation],
    ["Stopping conditions", recPacket.stopping],
  ];

  return (
    <Reveal>
      <Panel
        kicker="RECOMMENDATION PACKET"
        title="What does Coolie recommend?"
        material="blue"
        right={
          <div className="flex flex-wrap items-center gap-2">
            <span className={cn("rounded-md px-2 py-1 font-mono text-[10px] font-bold ring-1", recTone[recPacket.recommendation])}>
              {recPacket.recommendation}
            </span>
            <Chip tone="gold">
              <Lock className="h-2.5 w-2.5" /> HUMAN APPROVAL REQUIRED
            </Chip>
          </div>
        }
      >
        <div className="flex flex-wrap items-center gap-3">
          <span className="font-mono text-[11px] text-slate-500">{recPacket.id}</span>
          <p className="text-[15px] font-semibold text-white">{recPacket.title}</p>
          <span className="ml-auto flex items-center gap-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Confidence</span>
            <Confidence
              v={recPacket.confidence}
              onWhy={() =>
                openWhy({
                  title: "Recommendation confidence",
                  subject: recPacket.id,
                  value: `${recPacket.confidence}%`,
                  evidence: recPacket.evidenceRefs,
                  assumptions: recPacket.assumptions,
                  reasoning:
                    "Confidence is capped by the weakest verified input. Two material inputs are still estimates, so confidence cannot exceed the low-70s regardless of how attractive the opportunity is.",
                })
              }
            />
          </span>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {sections.map(([title, items]) => (
            <div key={title} className="rounded-xl bg-black/25 p-3.5 ring-1 ring-white/[0.07]">
              <p className="text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500">{title}</p>
              <ul className="mt-2 space-y-1.5">
                {items.map((x) => (
                  <li key={x} className="flex items-start gap-2 text-[11.5px] leading-relaxed text-slate-300">
                    <span className="mt-1.5 h-1 w-1 flex-none rounded-full bg-blue-300" /> {x}
                  </li>
                ))}
              </ul>
            </div>
          ))}

          <div className="rounded-xl bg-black/25 p-3.5 ring-1 ring-white/[0.07]">
            <p className="text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500">
              Evidence references
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {recPacket.evidenceRefs.map((e) => (
                <button
                  key={e}
                  onClick={() => traceEvidence(e)}
                  className="inline-flex items-center gap-1 rounded-md bg-blue-400/10 px-1.5 py-0.5 font-mono text-[10px] font-bold text-blue-200 ring-1 ring-blue-400/25 hover:bg-blue-400/20"
                >
                  <FileText className="h-2.5 w-2.5" /> {e}
                </button>
              ))}
            </div>
          </div>

          <div className="rounded-xl bg-black/25 p-3.5 ring-1 ring-white/[0.07]">
            <p className="text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500">
              Financial &amp; strategic
            </p>
            <p className="mt-2 text-[11.5px] leading-relaxed text-slate-300">{recPacket.financial}</p>
            <p className="mt-2 text-[11.5px] leading-relaxed text-slate-300">{recPacket.strategic}</p>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2.5 rounded-xl bg-amber-400/[0.08] p-3.5 ring-1 ring-amber-400/25">
          <ArrowRight className="h-4 w-4 flex-none text-amber-300" />
          <p className="min-w-0 flex-1 text-[12px] leading-relaxed text-amber-100/90">
            <span className="font-semibold">Suggested next action:</span> {recPacket.nextAction}
          </p>
          <button
            onClick={() => go("decisions")}
            className="flex-none rounded-lg bg-amber-400/20 px-3 py-1.5 text-[11px] font-semibold text-amber-50 ring-1 ring-amber-400/30"
          >
            Go to Approval Center
          </button>
        </div>
      </Panel>
    </Reveal>
  );
}

/* ---------------- Approval Center ---------------- */

function ApprovalRow({ a }: { a: Approval }) {
  const { traceEvidence, openWhy } = useResearch();
  const [state, setState] = useState(a.state);
  const [confirming, setConfirming] = useState(false);
  const pending = state === "PENDING" || state === "ESCALATED";

  const decide = (s: "APPROVED" | "REJECTED") => {
    setState(s);
    setConfirming(false);
  };

  const tone =
    state === "APPROVED" ? "ok" : state === "REJECTED" ? "bad" : state === "ESCALATED" ? "warn" : "info";

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "coolie-solid rounded-2xl p-5 ring-1",
        pending ? "ring-amber-400/25" : "ring-white/10"
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[10px] font-bold text-blue-200">{a.id}</span>
        <Chip tone={tone as "ok"} dot={pending ? "bg-amber-400" : undefined}>
          {state.replace(/_/g, " ")}
        </Chip>
        {pending && <Chip tone="gold">EXPLICIT CONFIRMATION REQUIRED</Chip>}
        <WhyBtn
          className="ml-auto"
          onClick={() =>
            openWhy({
              title: a.what,
              subject: `Approval ${a.id}`,
              evidence: a.evidence,
              assumptions: a.risks.length ? a.risks : ["No risk findings recorded for this request"],
              reasoning: a.why,
            })
          }
        />
      </div>

      <p className="mt-2.5 text-[14px] font-semibold leading-snug text-white">{a.what}</p>
      <p className="mt-1.5 text-[12px] leading-relaxed text-slate-400">{a.why}</p>

      <div className="mt-4 grid gap-x-6 gap-y-3 sm:grid-cols-2">
        <Field label="Related mission" mono>{a.mission}</Field>
        <Field label="Related opportunity" mono>{a.opp}</Field>
        <div className="sm:col-span-2">
          <Field label="Financial implications">{a.financial}</Field>
        </div>
        <div className="sm:col-span-2">
          <p className="text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500">Evidence</p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {a.evidence.length ? (
              a.evidence.map((e) => (
                <button
                  key={e}
                  onClick={() => traceEvidence(e)}
                  className="inline-flex items-center gap-1 rounded-md bg-blue-400/10 px-1.5 py-0.5 font-mono text-[10px] font-bold text-blue-200 ring-1 ring-blue-400/25 hover:bg-blue-400/20"
                >
                  <FileText className="h-2.5 w-2.5" /> {e}
                </button>
              ))
            ) : (
              <span className="text-[11px] text-slate-500">None attached</span>
            )}
          </div>
        </div>
        <div className="sm:col-span-2">
          <Field label="Risks">{a.risks.join(" · ") || "None recorded"}</Field>
        </div>
        <Field label="Requested action">{a.action}</Field>
        <Field label="Who / what must approve">{a.approver}</Field>
        <div className="sm:col-span-2">
          <Field label="Consequences of approving">{a.consequences.join(" · ")}</Field>
        </div>
      </div>

      <div className="mt-4 border-t border-white/[0.07] pt-4">
        <AnimatePresence mode="wait">
          {!pending ? (
            <motion.div
              key="done"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className={cn(
                "flex items-center gap-2 rounded-lg px-3 py-2.5 text-[12px] font-medium ring-1",
                state === "APPROVED"
                  ? "bg-emerald-400/10 text-emerald-200 ring-emerald-400/25"
                  : "bg-rose-400/10 text-rose-200 ring-rose-400/25"
              )}
            >
              {state === "APPROVED" ? <Check className="h-4 w-4" /> : <X className="h-4 w-4" />}
              {state === "APPROVED"
                ? "Approved. Recorded and submitted for server-side re-verification before execution."
                : "Rejected. The requesting agent is notified and the action is not performed."}
            </motion.div>
          ) : confirming ? (
            <motion.div
              key="confirm"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="rounded-xl border border-amber-400/35 bg-amber-400/10 p-3.5"
            >
              <p className="flex items-center gap-2 text-[11px] font-bold tracking-wider text-amber-200">
                <ShieldAlert className="h-3.5 w-3.5" /> CONFIRM CONSEQUENTIAL ACTION
              </p>
              <p className="mt-2 text-[12px] leading-relaxed text-amber-50/90">
                You are about to {a.action.toLowerCase()}. This is an external, consequential action.
                The backend will re-check your mandate and permissions before anything executes.
              </p>
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => decide("APPROVED")}
                  className="flex items-center gap-1.5 rounded-lg bg-emerald-500/25 px-3 py-2 text-[11px] font-semibold text-emerald-100 ring-1 ring-emerald-400/35 hover:bg-emerald-500/40"
                >
                  <Check className="h-3.5 w-3.5" /> Confirm &amp; approve
                </button>
                <button
                  onClick={() => setConfirming(false)}
                  className="rounded-lg bg-white/[0.05] px-3 py-2 text-[11px] font-semibold text-slate-300 ring-1 ring-white/10"
                >
                  Go back
                </button>
              </div>
            </motion.div>
          ) : (
            <motion.div key="acts" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-wrap gap-2">
              <button
                onClick={() => setConfirming(true)}
                className="flex items-center gap-1.5 rounded-lg bg-white/[0.05] px-3.5 py-2.5 text-[12px] font-semibold text-slate-100 ring-1 ring-white/12 transition hover:bg-white/[0.1]"
              >
                <FileSignature className="h-4 w-4" /> {a.action}
              </button>
              <button
                onClick={() => decide("REJECTED")}
                className="flex items-center gap-1.5 rounded-lg bg-rose-500/15 px-3.5 py-2.5 text-[12px] font-semibold text-rose-200 ring-1 ring-rose-400/25 transition hover:bg-rose-500/25"
              >
                <X className="h-4 w-4" /> Reject
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

function ApprovalCenter() {
  return (
    <div>
      <SectionHeading
        kicker="APPROVAL CENTER"
        title="Does anyone need to approve this?"
        desc="Every request states what is being asked, why, what it costs, what could go wrong, who must approve and what happens if you say yes."
      />
      <div className="grid gap-4 lg:grid-cols-2">
        {approvals.map((a, i) => (
          <Reveal key={a.id} delay={i * 0.05}>
            <ApprovalRow a={a} />
          </Reveal>
        ))}
      </div>
    </div>
  );
}

/* ---------------- screen ---------------- */

export default function DecisionCenter() {
  return (
    <div className="mx-auto w-full max-w-7xl px-4 pb-28">
      <Reveal>
        <div className="mb-6">
          <p className="text-[11px] font-medium tracking-[0.3em] text-blue-300/70">
            DECISION CENTER · RECOMMENDATION → APPROVAL
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-metal sm:text-4xl">
            Does it make sense, and who decides?
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            Financial evaluation, strategy review and the risk gate feed one recommendation packet.
            Consequential actions never execute without an explicit, recorded owner approval.
          </p>
        </div>
      </Reveal>

      <RiskGate />
      <div className="mt-5" />
      <MoneyCalc />
      <div className="mt-5" />
      <StrategyReview />
      <div className="mt-5" />
      <RecPacket />

      <div className="mt-10">
        <ApprovalCenter />
      </div>

      <div className="mt-6 flex items-start gap-2.5 rounded-2xl coolie-glass p-4">
        <HelpCircle className="mt-0.5 h-4 w-4 flex-none text-blue-300" />
        <p className="text-[12px] leading-relaxed text-slate-400">
          Recommendation types supported by the backend:{" "}
          {(["REJECT", "ARCHIVE", "RESEARCH_MORE", "RUN_VALIDATION", "REQUEST_APPROVAL", "LIMITED_LAUNCH"] as const).map(
            (r) => (
              <span key={r} className={cn("mr-1.5 inline-block rounded px-1.5 py-0.5 font-mono text-[10px] font-bold ring-1", recTone[r])}>
                {r}
              </span>
            )
          )}
          <span className="mt-2 block">
            Research and the agents produce evidence and structured inputs. The decision is always
            yours, recorded server-side — the UI can explain and collect consent, it cannot grant
            authority. <EvType t="OBSERVED" /> inputs are facts; <EvType t="CALCULATED" /> and{" "}
            <EvType t="INFERRED" /> inputs are not.
          </span>
        </p>
      </div>
    </div>
  );
}
