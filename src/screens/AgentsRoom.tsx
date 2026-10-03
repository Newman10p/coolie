import { motion } from "motion/react";
import { HelpCircle, ShieldCheck, Ban } from "lucide-react";
import { cn } from "../utils/cn";
import { agents, agentPerf } from "../research/data";
import { Chip, Confidence, Field, Panel, WhyBtn, MockBadge } from "../research/ui";
import { Reveal } from "../components/scroll/Reveal";
import { useResearch } from "../research/store";

const st: Record<string, { c: string; d: string }> = {
  RUNNING: { c: "text-cyan-200 bg-cyan-400/10 ring-cyan-400/25", d: "bg-cyan-400" },
  IDLE: { c: "text-slate-300 bg-white/[0.05] ring-white/12", d: "bg-slate-500" },
  BLOCKED: { c: "text-rose-200 bg-rose-400/10 ring-rose-400/25", d: "bg-rose-400" },
  AWAITING_REVIEW: { c: "text-amber-200 bg-amber-400/10 ring-amber-400/25", d: "bg-amber-400" },
};

export default function AgentsRoom() {
  const { openWhy } = useResearch();

  return (
    <div className="mx-auto w-full max-w-7xl px-4 pb-28">
      <Reveal>
        <div className="mb-6">
          <p className="text-[11px] font-medium tracking-[0.3em] text-blue-300/70">
            RESEARCH ROOM · 10 SPECIALISTS
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-metal sm:text-4xl">
            What is Coolie doing right now?
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            Ten specialists contribute structured research to a mission. None of them decide.
            Conclusions are assembled by the Synthesis Agent from verified evidence only.
          </p>
        </div>
      </Reveal>

      <Reveal>
        <div className="mb-5 flex flex-wrap items-center gap-2.5 rounded-2xl bg-blue-400/[0.08] p-4 ring-1 ring-blue-400/20">
          <ShieldCheck className="h-4 w-4 flex-none text-blue-300" />
          <p className="text-[12px] leading-relaxed text-blue-100/90">
            Agents do not make final decisions. They produce evidence and structured findings that
            feed the mission. Acceptance is the Evidence Verification Agent's job; decisions belong
            to the Strategy Manager and the owner.
          </p>
          <MockBadge />
        </div>
      </Reveal>

      <div className="grid gap-4 lg:grid-cols-2">
        {agents.map((a, i) => {
          const s = st[a.status];
          return (
            <Reveal key={a.id} delay={i * 0.04}>
              <motion.div
                whileHover={{ y: -3 }}
                className={cn(
                  "coolie-metal coolie-metal-sheen h-full rounded-2xl p-5",
                  a.status === "BLOCKED" && "ring-1 ring-rose-400/30"
                )}
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-white/5 px-1.5 py-0.5 font-mono text-[9px] font-bold text-blue-200 ring-1 ring-white/10">
                        {a.id}
                      </span>
                      <span className={cn("rounded px-1.5 py-0.5 text-[9px] font-bold ring-1", s.c)}>
                        <span className={cn("mr-1.5 inline-block h-1.5 w-1.5 rounded-full align-middle", s.d)} />
                        {a.status.replace(/_/g, " ")}
                      </span>
                    </div>
                    <p className="mt-2 text-[14px] font-semibold text-white">{a.n}</p>
                    <p className="mt-0.5 text-[11px] leading-relaxed text-slate-500">{a.purpose}</p>
                  </div>
                  <WhyBtn
                    onClick={() =>
                      openWhy({
                        title: a.n,
                        subject: "Agent contribution record",
                        value: `${a.confidence}% confidence`,
                        evidence: [],
                        assumptions: [
                          `Phase: ${a.phase}`,
                          `Workload ${a.workload}% · ${a.assigned} assigned, ${a.completed} completed, ${a.failed} failed`,
                        ],
                        reasoning: a.note,
                      })
                    }
                  />
                </div>

                <div className="mt-4 rounded-xl bg-black/25 px-3 py-2.5 ring-1 ring-white/[0.07]">
                  <p className="text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500">
                    Current task
                  </p>
                  <p className="mt-1 text-[12px] leading-snug text-slate-100">{a.task}</p>
                </div>

                <div className="mt-3 grid grid-cols-2 gap-x-5 gap-y-3 sm:grid-cols-4">
                  <Field label="Mission" mono>{a.missionId.replace("MSN-2026-", "…")}</Field>
                  <Field label="Phase">{a.phase}</Field>
                  <Field label="Assigned" mono>{a.assigned}</Field>
                  <Field label="Completed" mono>{a.completed}</Field>
                  <Field label="Failed / retried" mono>
                    <span className={a.failed > 0 ? "text-rose-300" : ""}>{a.failed}</span>
                  </Field>
                  <Field label="Evidence produced" mono>{a.evidence}</Field>
                  <Field label="Sources inspected" mono>{a.sources}</Field>
                  <Field label="Last activity" mono>{a.last}</Field>
                </div>

                <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-white/[0.07] pt-3">
                  <Confidence v={a.confidence} />
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] font-bold uppercase tracking-wider text-slate-500">
                      Workload
                    </span>
                    <div className="h-1.5 w-20 overflow-hidden rounded-full bg-white/10">
                      <motion.div
                        initial={{ scaleX: 0 }}
                        whileInView={{ scaleX: a.workload / 100 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.8 }}
                        className="h-full w-full origin-left rounded-full bg-gradient-to-r from-blue-500 to-cyan-300"
                      />
                    </div>
                    <span className="font-mono text-[10px] text-slate-300">{a.workload}%</span>
                  </div>
                </div>

                <p className="mt-3 text-[11px] leading-relaxed text-slate-400">{a.note}</p>
              </motion.div>
            </Reveal>
          );
        })}
      </div>

      <div className="mt-6">
        <Reveal>
          <Panel
            kicker="AGENT PERFORMANCE · HISTORICAL"
            title="Accepted vs rejected contributions"
            material="solid"
            right={<MockBadge />}
          >
            <div className="space-y-3">
              {agentPerf.map((p) => (
                <div key={p.id} className="flex flex-wrap items-center gap-3">
                  <span className="w-[200px] flex-none text-[12px] text-slate-200">{p.n}</span>
                  <div className="flex h-2.5 flex-1 overflow-hidden rounded-full bg-white/[0.06]">
                    <motion.div
                      initial={{ scaleX: 0 }}
                      whileInView={{ scaleX: p.accepted / (p.accepted + p.rejected) }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.9 }}
                      className="h-full w-full origin-left bg-gradient-to-r from-emerald-400 to-emerald-300"
                    />
                    <motion.div
                      initial={{ scaleX: 0 }}
                      whileInView={{ scaleX: p.rejected / (p.accepted + p.rejected) }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.9 }}
                      className="h-full w-full origin-left bg-gradient-to-r from-rose-500 to-rose-400"
                    />
                  </div>
                  <span className="w-24 flex-none font-mono text-[10px] text-slate-400">
                    {p.accepted}✓ / {p.rejected}✗
                  </span>
                  <Chip tone={p.acc >= 80 ? "ok" : p.acc >= 60 ? "warn" : "bad"}>{p.acc}% accuracy</Chip>
                </div>
              ))}
            </div>
            <p className="mt-4 flex items-start gap-2 rounded-lg bg-black/25 px-3 py-2.5 text-[11px] leading-relaxed text-slate-400 ring-1 ring-white/[0.06]">
              <Ban className="mt-0.5 h-3.5 w-3.5 flex-none text-amber-300" />
              Rejections are not failures — they are the Evidence Verification Agent doing its job.
              Marketing Intelligence has the lowest acceptance rate because its inputs are mostly
              model-derived.
            </p>
          </Panel>
        </Reveal>
      </div>

      <div className="mt-5 flex items-start gap-2.5 rounded-2xl coolie-glass p-4">
        <HelpCircle className="mt-0.5 h-4 w-4 flex-none text-blue-300" />
        <p className="text-[12px] leading-relaxed text-slate-400">
          Every agent exposes the same twelve fields so you can compare contribution rather than
          vibes. Confidence is per-agent and per-mission, and it is always paired with a Why.
        </p>
      </div>
    </div>
  );
}
