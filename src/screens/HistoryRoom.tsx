import { motion } from "motion/react";
import { Archive, Lock, ThumbsUp, ThumbsDown, Lightbulb, FlaskConical, UserCheck } from "lucide-react";
import { cn } from "../utils/cn";
import { historyMissions, wrongAssumptions, sourcePerf, agentPerf, validationResults, lessons } from "../research/data";
import { Chip, Field, Panel, MockBadge } from "../research/ui";
import { Reveal } from "../components/scroll/Reveal";

export default function HistoryRoom() {
  return (
    <div className="mx-auto w-full max-w-7xl px-4 pb-28">
      <Reveal>
        <div className="mb-6">
          <p className="text-[11px] font-medium tracking-[0.3em] text-blue-300/70">
            HISTORY &amp; LEARNING · IMMUTABLE RECORDS
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-metal sm:text-4xl">
            What happened after the decision?
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            Completed missions, the actions actually taken, what turned out to be wrong, and which
            sources deserve trust. Learning is a separate layer — past reports are never rewritten.
          </p>
        </div>
      </Reveal>

      {/* missions */}
      <Reveal>
        <Panel kicker="COMPLETED & CLOSED MISSIONS" title="Archive" material="metal" right={<MockBadge />}>
          <div className="grid gap-3 lg:grid-cols-2">
            {historyMissions.map((m, i) => (
              <motion.div
                key={m.id}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.06 }}
                className="rounded-xl bg-black/25 p-4 ring-1 ring-white/[0.07]"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-[10px] font-bold text-blue-200">{m.id}</span>
                  <Chip tone={m.stage === "COMPLETED" ? "ok" : m.stage === "ARCHIVED" ? "neutral" : "warn"}>
                    {m.stage}
                  </Chip>
                  <Chip tone="gold">{m.rec}</Chip>
                </div>
                <p className="mt-2 text-[14px] font-semibold text-white">{m.name}</p>
                <div className="mt-3 grid gap-x-5 gap-y-3 sm:grid-cols-2">
                  <Field label="Outcome">{m.outcome}</Field>
                  <Field label="Actions taken">{m.actions}</Field>
                  <Field label="Closed" mono>{m.closed}</Field>
                  <Field label="Record integrity">
                    <span className="inline-flex items-center gap-1.5 text-emerald-300">
                      <Lock className="h-3 w-3" /> Immutable
                    </span>
                  </Field>
                </div>
              </motion.div>
            ))}
          </div>
        </Panel>
      </Reveal>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        {/* wrong assumptions */}
        <Reveal>
          <Panel kicker="WRONG ASSUMPTIONS · WHAT WE GOT WRONG" title="Corrected priors" material="solid">
            <div className="space-y-3">
              {wrongAssumptions.map((w, i) => (
                <motion.div
                  key={w.assumption}
                  initial={{ opacity: 0, x: -10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.06 }}
                  className="rounded-xl bg-rose-500/[0.06] p-3.5 ring-1 ring-rose-400/20"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <ThumbsDown className="h-3.5 w-3.5 flex-none text-rose-300" />
                    <span className="font-mono text-[10px] text-slate-500">{w.mission}</span>
                    <Chip tone="bad" className="ml-auto">{w.cost}</Chip>
                  </div>
                  <p className="mt-2 text-[12px] text-slate-300">
                    <span className="text-slate-500">Assumed:</span> {w.assumption}
                  </p>
                  <p className="mt-1 text-[12px] text-slate-100">
                    <span className="text-slate-500">Actual:</span> {w.actual}
                  </p>
                  <p className="mt-2 flex items-start gap-1.5 rounded-lg bg-black/30 px-2.5 py-2 text-[11px] leading-relaxed text-amber-100/90 ring-1 ring-amber-400/20">
                    <Lightbulb className="mt-0.5 h-3 w-3 flex-none" /> {w.lesson}
                  </p>
                </motion.div>
              ))}
            </div>
          </Panel>
        </Reveal>

        {/* source performance */}
        <Reveal>
          <Panel kicker="SOURCE RELIABILITY" title="Which sources earn trust" material="solid">
            <p className="text-[9px] font-bold uppercase tracking-[0.18em] text-emerald-300">
              Reliable
            </p>
            <div className="mt-2 space-y-2">
              {sourcePerf.reliable.map((s) => (
                <div key={s.name} className="flex items-start gap-2 rounded-lg bg-emerald-400/[0.07] px-3 py-2 ring-1 ring-emerald-400/20">
                  <ThumbsUp className="mt-0.5 h-3.5 w-3.5 flex-none text-emerald-300" />
                  <div>
                    <p className="text-[12px] font-medium text-slate-100">{s.name}</p>
                    <p className="text-[11px] text-slate-400">{s.note}</p>
                  </div>
                  <Chip tone="ok" className="ml-auto">{s.quality}</Chip>
                </div>
              ))}
            </div>

            <p className="mt-5 text-[9px] font-bold uppercase tracking-[0.18em] text-rose-300">
              Poor performing
            </p>
            <div className="mt-2 space-y-2">
              {sourcePerf.poor.map((s) => (
                <div key={s.name} className="flex items-start gap-2 rounded-lg bg-rose-500/[0.07] px-3 py-2 ring-1 ring-rose-400/20">
                  <ThumbsDown className="mt-0.5 h-3.5 w-3.5 flex-none text-rose-300" />
                  <div>
                    <p className="text-[12px] font-medium text-slate-100">{s.name}</p>
                    <p className="text-[11px] text-slate-400">{s.note}</p>
                  </div>
                  <Chip tone="bad" className="ml-auto">{s.quality}</Chip>
                </div>
              ))}
            </div>
          </Panel>
        </Reveal>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-[1.3fr_1fr]">
        {/* validation results */}
        <Reveal>
          <Panel kicker="VALIDATION RESULTS · PREDICTED VS ACTUAL" title="Where the model was wrong" material="glass">
            <div className="space-y-2.5">
              {validationResults.map((v, i) => {
                const wrong = v.verdict.startsWith("Wrong");
                return (
                  <motion.div
                    key={v.test}
                    initial={{ opacity: 0, x: -8 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: i * 0.05 }}
                    className={cn(
                      "flex flex-wrap items-center gap-x-4 gap-y-1.5 rounded-xl px-3.5 py-3 ring-1",
                      wrong ? "bg-rose-500/[0.06] ring-rose-400/20" : "bg-emerald-400/[0.06] ring-emerald-400/20"
                    )}
                  >
                    <div className="min-w-[150px]">
                      <p className="font-mono text-[10px] text-slate-500">{v.mission}</p>
                      <p className="text-[12px] font-medium text-slate-100">{v.test}</p>
                    </div>
                    <div>
                      <p className="text-[9px] uppercase tracking-wider text-slate-500">Predicted</p>
                      <p className="font-mono text-[12px] text-slate-300">{v.predicted}</p>
                    </div>
                    <div>
                      <p className="text-[9px] uppercase tracking-wider text-slate-500">Actual</p>
                      <p className="font-mono text-[12px] text-white">{v.actual}</p>
                    </div>
                    <Chip tone={wrong ? "bad" : "ok"} className="ml-auto">{v.verdict}</Chip>
                  </motion.div>
                );
              })}
            </div>
          </Panel>
        </Reveal>

        {/* lessons */}
        <Reveal>
          <Panel kicker="LEARNING LAYER" title="Lessons carried forward" material="blue">
            <ul className="space-y-2.5">
              {lessons.map((l, i) => (
                <motion.li
                  key={l}
                  initial={{ opacity: 0, y: 10 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.06 }}
                  className="flex items-start gap-2.5 rounded-xl bg-black/25 px-3.5 py-3 text-[12px] leading-relaxed text-slate-200 ring-1 ring-white/[0.07]"
                >
                  <Lightbulb className="mt-0.5 h-3.5 w-3.5 flex-none text-blue-300" />
                  {l}
                </motion.li>
              ))}
            </ul>
            <p className="mt-4 flex items-start gap-2 rounded-lg bg-black/30 px-3 py-2.5 text-[11px] leading-relaxed text-slate-400 ring-1 ring-white/[0.06]">
              <Archive className="mt-0.5 h-3.5 w-3.5 flex-none" />
              Lessons never alter a historical report. They change how the next mission is framed,
              which is a different and much safer thing.
            </p>
          </Panel>
        </Reveal>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Reveal>
          <Panel kicker="AGENT PERFORMANCE OVER TIME" title="Contribution quality" material="solid">
            <div className="space-y-3">
              {agentPerf.map((p) => (
                <div key={p.id} className="flex items-center gap-3">
                  <span className="w-[190px] flex-none text-[12px] text-slate-200">{p.n}</span>
                  <div className="flex h-2 flex-1 overflow-hidden rounded-full bg-white/[0.06]">
                    <motion.div
                      initial={{ scaleX: 0 }}
                      whileInView={{ scaleX: p.acc / 100 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.8 }}
                      className={cn(
                        "h-full w-full origin-left bg-gradient-to-r",
                        p.acc >= 80 ? "from-emerald-400 to-emerald-300" : p.acc >= 60 ? "from-amber-400 to-amber-300" : "from-rose-400 to-rose-300"
                      )}
                    />
                  </div>
                  <span className="w-10 flex-none font-mono text-[11px] text-slate-300">{p.acc}%</span>
                </div>
              ))}
            </div>
          </Panel>
        </Reveal>

        <Reveal>
          <Panel kicker="HOW TO READ THIS ROOM" title="The full loop" material="metal">
            <div className="space-y-2">
              {[
                "Mission created from an unambiguous objective",
                "Task graph decomposes the work with dependencies",
                "Ten specialists contribute structured research",
                "Evidence Verification accepts or rejects each claim",
                "Synthesis assembles verified evidence into OpportunityRecords",
                "Money Calculator, Strategy and Risk evaluate in parallel",
                "One recommendation packet is produced",
                "Owner approves; the backend re-checks authority",
                "Outcome is recorded and becomes a lesson",
              ].map((s, i) => (
                <motion.div
                  key={s}
                  initial={{ opacity: 0, x: -8 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.04 }}
                  className="flex items-center gap-2.5 rounded-lg bg-black/25 px-3 py-2 text-[11.5px] text-slate-300 ring-1 ring-white/[0.06]"
                >
                  <span className="grid h-5 w-5 flex-none place-items-center rounded-md bg-blue-400/15 font-mono text-[10px] font-bold text-blue-200">
                    {i + 1}
                  </span>
                  {s}
                </motion.div>
              ))}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <Chip tone="ok"><FlaskConical className="h-2.5 w-2.5" /> Validation tracked</Chip>
              <Chip tone="gold"><UserCheck className="h-2.5 w-2.5" /> Owner authority recorded</Chip>
              <Chip tone="info"><Lock className="h-2.5 w-2.5" /> Records immutable</Chip>
            </div>
          </Panel>
        </Reveal>
      </div>
    </div>
  );
}
