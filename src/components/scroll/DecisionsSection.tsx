import { useState } from "react";
import { motion } from "motion/react";
import { ShieldCheck, ShieldAlert, FileSignature, PauseCircle, Check } from "lucide-react";
import { decisions, type Decision } from "../../data";
import { Reveal, SectionHeading, CountUp } from "./Reveal";

type Stage = "idle" | "confirm" | "submitted" | "held";

function DecisionDoc({ d, i }: { d: Decision; i: number }) {
  const [stage, setStage] = useState<Stage>("idle");
  const verified = d.gate === "verified";

  return (
    <Reveal dir={i % 2 === 0 ? "right" : "left"} delay={i * 0.1}>
      <div className="coolie-solid relative h-full overflow-hidden rounded-2xl p-6">
        {/* paper header strip */}
        <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-[rgb(214_177_106/0.7)] via-[rgb(214_177_106/0.3)] to-transparent" />
        <div className="flex items-center justify-between">
          <span className="font-mono text-[11px] text-slate-500">{d.ref}</span>
          <span
            className={`flex items-center gap-1.5 text-[11px] font-semibold ${
              verified ? "text-emerald-300" : "text-amber-300"
            }`}
          >
            {verified ? <ShieldCheck className="h-4 w-4" /> : <ShieldAlert className="h-4 w-4" />}
            Sharia gate · {verified ? "verified" : "in review"}
          </span>
        </div>
        <p className="mt-4 text-lg font-semibold text-white">{d.title}</p>
        <p className="mt-1 text-2xl font-semibold tabular-nums text-metal">{d.amount}</p>
        <p className="mt-3 text-[13px] leading-relaxed text-slate-400">{d.note}</p>
        <p className="mt-4 text-[11px] text-slate-500">
          Requested by <span className="text-slate-300">{d.requestedBy}</span>
        </p>

        <div className="mt-5 border-t border-white/[0.07] pt-4">
          {stage === "submitted" || stage === "held" ? (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex items-center gap-2 rounded-lg px-3 py-2.5 text-[12px] font-medium ring-1 ${
                stage === "submitted"
                  ? "bg-emerald-400/10 text-emerald-200 ring-emerald-400/25"
                  : "bg-amber-400/10 text-amber-200 ring-amber-400/25"
              }`}
            >
              {stage === "submitted" ? <Check className="h-4 w-4" /> : <PauseCircle className="h-4 w-4" />}
              {stage === "submitted"
                ? "Signature submitted · awaiting server verification"
                : "Placed on hold · Orchestrator notified"}
            </motion.div>
          ) : (
            <div className="flex gap-2">
              <button
                onClick={() => setStage(stage === "confirm" ? "submitted" : "confirm")}
                className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-[12px] font-semibold ring-1 transition ${
                  stage === "confirm"
                    ? "bg-emerald-500/25 text-emerald-100 ring-emerald-400/40"
                    : "bg-white/[0.04] text-slate-200 ring-white/10 hover:bg-white/[0.08]"
                }`}
              >
                <FileSignature className="h-4 w-4" />
                {stage === "confirm" ? "Confirm signature" : "Sign"}
              </button>
              <button
                onClick={() => setStage("held")}
                className="flex items-center justify-center gap-2 rounded-lg bg-white/[0.04] px-3 py-2.5 text-[12px] font-semibold text-slate-300 ring-1 ring-white/10 transition hover:bg-white/[0.08]"
              >
                <PauseCircle className="h-4 w-4" /> Hold
              </button>
            </div>
          )}
        </div>
      </div>
    </Reveal>
  );
}

export function DecisionsSection() {
  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-20">
      <SectionHeading
        kicker="DECISIONS AWAITING YOU"
        title="Three documents need your signature."
        desc="Solid documents for consequential actions. Every signature is re-checked server-side before anything executes."
      />
      <div className="grid gap-5 md:grid-cols-3">
        {decisions.map((d, i) => (
          <DecisionDoc key={d.id} d={d} i={i} />
        ))}
      </div>
    </section>
  );
}

const pulse = [
  { label: "Sub-agents online", to: 24, suffix: "", decimals: 0 },
  { label: "Tasks completed today", to: 12840, suffix: "", decimals: 0 },
  { label: "Sources monitored", to: 1204, suffix: "", decimals: 0 },
  { label: "Avg. event latency", to: 180, suffix: " ms", decimals: 0 },
  { label: "Compliance score", to: 98.2, suffix: "", decimals: 1 },
  { label: "Capital deployed", to: 31.6, suffix: "M", prefix: "$", decimals: 1 },
];

export function SectorPulse() {
  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-20">
      <SectionHeading
        kicker="SECTOR PULSE · LAST 24H"
        title="The workroom, by the numbers."
      />
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
        {pulse.map((p, i) => (
          <Reveal key={p.label} delay={i * 0.07}>
            <div className="coolie-metal rounded-2xl p-5 sm:p-6">
              <p className="text-3xl font-semibold text-metal sm:text-4xl">
                <CountUp to={p.to} suffix={p.suffix} prefix={p.prefix} decimals={p.decimals} />
              </p>
              <p className="mt-2 text-[11px] uppercase tracking-wider text-slate-500">
                {p.label}
              </p>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
