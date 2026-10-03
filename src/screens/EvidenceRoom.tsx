import { useState } from "react";
import { motion } from "motion/react";
import { Link2, FileSearch, AlertOctagon, ExternalLink, Filter } from "lucide-react";
import { cn } from "../utils/cn";
import { evidence, sources, evidenceTypeMeta, type Evidence } from "../research/data";
import { Chip, EvType, Fresh, Panel, WhyBtn, Confidence } from "../research/ui";
import { Reveal } from "../components/scroll/Reveal";
import { useResearch } from "../research/store";

function EvidenceCard({ e }: { e: Evidence }) {
  const { openWhy, traceSource } = useResearch();
  const src = sources.find((s) => s.id === e.sourceId);
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
      transition={{ duration: 0.35 }}
      className={cn(
        "coolie-solid rounded-2xl p-4 ring-1",
        e.rejected ? "ring-rose-400/30" : e.verified ? "ring-emerald-400/20" : "ring-amber-400/20"
      )}
    >
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="font-mono text-[10px] font-bold text-blue-200">{e.id}</span>
        <EvType t={e.type} />
        <Fresh f={e.freshness} />
        {e.rejected ? (
          <Chip tone="bad">REJECTED</Chip>
        ) : e.verified ? (
          <Chip tone="ok">VERIFIED</Chip>
        ) : (
          <Chip tone="warn">AWAITING VERIFICATION</Chip>
        )}
        <WhyBtn
          className="ml-auto"
          onClick={() =>
            openWhy({
              title: e.claim,
              subject: `${e.id} · ${e.type}`,
              value: `${e.confidence}% confidence`,
              evidence: [e.sourceId],
              assumptions: [e.limitations],
              reasoning: e.rejected
                ? `Rejected: ${e.rejectionReason}`
                : `Retrieved ${e.retrieved} from ${e.sourceType}. Limitations recorded on the evidence record itself, so the bound of the claim is always visible.`,
            })
          }
        />
      </div>

      <p className="mt-2.5 text-[13px] font-medium leading-relaxed text-slate-100">{e.claim}</p>

      {e.rejected && (
        <p className="mt-2 rounded-lg bg-rose-400/10 px-2.5 py-2 text-[11px] leading-relaxed text-rose-200 ring-1 ring-rose-400/25">
          Rejected: {e.rejectionReason}
        </p>
      )}

      <div className="mt-3 grid gap-x-4 gap-y-1.5 text-[10px] sm:grid-cols-2">
        <p className="text-slate-500">
          Source:{" "}
          <button onClick={() => traceSource(e.sourceId)} className="font-mono text-blue-200 underline decoration-dotted hover:text-blue-100">
            {e.sourceId}
          </button>{" "}
          <span className="text-slate-600">· {e.sourceType}</span>
        </p>
        <p className="text-slate-500">Retrieved: <span className="font-mono text-slate-400">{e.retrieved}</span></p>
        <p className="text-slate-500">Mission: <span className="font-mono text-slate-400">{e.missionId}</span></p>
        <p className="text-slate-500">Task: <span className="font-mono text-slate-400">{e.taskId}</span> · Opp: <span className="font-mono text-slate-400">{e.opportunityId}</span></p>
      </div>

      <p className="mt-2.5 rounded-lg bg-black/30 px-2.5 py-2 text-[11px] leading-relaxed text-slate-400 ring-1 ring-white/[0.06]">
        <span className="font-semibold text-slate-300">Limitations:</span> {e.limitations}
      </p>

      <div className="mt-3 flex items-center justify-between border-t border-white/[0.07] pt-2.5">
        <Confidence v={e.confidence} />
        {src?.snapshot && (
          <span className="inline-flex items-center gap-1 font-mono text-[9px] text-slate-600">
            <ExternalLink className="h-2.5 w-2.5" /> {src.snapshot}
          </span>
        )}
      </div>
    </motion.div>
  );
}

export default function EvidenceRoom() {
  const { focusEvidence, focusSource, traceEvidence } = useResearch();
  const [typeF, setTypeF] = useState<"ALL" | "OBSERVED" | "CALCULATED" | "INFERRED">("ALL");
  const [tab, setTab] = useState<"evidence" | "sources" | "conflicts">(focusSource ? "sources" : "evidence");

  const list = evidence
    .filter((e) => typeF === "ALL" || e.type === typeF)
    .sort((a, b) => Number(b.verified) - Number(a.verified));

  const conflicts = sources.filter((s) => s.conflicts.length > 0);

  return (
    <div className="mx-auto w-full max-w-7xl px-4 pb-28">
      <Reveal>
        <div className="mb-6">
          <p className="text-[11px] font-medium tracking-[0.3em] text-blue-300/70">
            EVIDENCE ROOM · PROVENANCE &amp; VERIFICATION
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-metal sm:text-4xl">
            Where did the information come from?
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            Every claim carries its evidence type, freshness, confidence and stated limitations.
            Nothing is collapsed into a single opaque score.
          </p>
        </div>
      </Reveal>

      {focusEvidence && (
        <Reveal>
          <div className="mb-5 flex flex-wrap items-center gap-2 rounded-2xl bg-blue-400/10 p-3 ring-1 ring-blue-400/25">
            <FileSearch className="h-4 w-4 text-blue-300" />
            <p className="text-[12px] text-blue-100">
              Traced from a score or recommendation to <span className="font-mono font-semibold">{focusEvidence}</span>.
            </p>
            <button
              onClick={() => traceEvidence(focusEvidence)}
              className="ml-auto rounded-lg bg-white/10 px-2.5 py-1 text-[11px] text-blue-50 ring-1 ring-white/15"
            >
              Re-highlight
            </button>
          </div>
        </Reveal>
      )}

      {/* tabs */}
      <Reveal>
        <div className="mb-5 flex flex-wrap gap-2">
          {([
            ["evidence", "Evidence"],
            ["sources", "Source provenance"],
            ["conflicts", `Conflicts (${conflicts.length})`],
          ] as const).map(([id, label]) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={cn(
                "relative rounded-xl px-4 py-2 text-[12px] font-medium transition",
                tab === id ? "text-white" : "text-slate-400 hover:text-slate-200"
              )}
            >
              {tab === id && (
                <motion.span
                  layoutId="ev-tab"
                  className="absolute inset-0 rounded-xl bg-blue-400/15 ring-1 ring-blue-300/25"
                />
              )}
              <span className="relative">{label}</span>
            </button>
          ))}
        </div>
      </Reveal>

      {tab === "evidence" && (
        <>
          <Reveal>
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <Filter className="h-3.5 w-3.5 text-slate-500" />
              {(["ALL", "OBSERVED", "CALCULATED", "INFERRED"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTypeF(t)}
                  className={cn(
                    "rounded-lg px-2.5 py-1 text-[11px] font-semibold ring-1 transition",
                    typeF === t ? "bg-blue-400/15 text-blue-100 ring-blue-300/30" : "bg-white/[0.03] text-slate-400 ring-white/10"
                  )}
                >
                  {t}
                </button>
              ))}
              <span className="ml-auto flex flex-wrap gap-3 text-[10px] text-slate-500">
                <span><span className="text-emerald-300">◉ OBSERVED</span> directly measured</span>
                <span><span className="text-cyan-300">∑ CALCULATED</span> derived from inputs</span>
                <span><span className="text-violet-300">∴ INFERRED</span> reasoned, untested</span>
              </span>
            </div>
          </Reveal>

          <motion.div layout className="grid gap-4 lg:grid-cols-2">
            {list.map((e) => (
              <div key={e.id} className={cn(focusEvidence === e.id && "ring-2 ring-blue-400 rounded-2xl")}>
                <EvidenceCard e={e} />
              </div>
            ))}
          </motion.div>
        </>
      )}

      {tab === "sources" && (
        <div className="grid gap-4 lg:grid-cols-2">
          {sources.map((s, i) => (
            <Reveal key={s.id} delay={i * 0.03}>
              <div
                className={cn(
                  "coolie-solid h-full rounded-2xl p-4 ring-1",
                  focusSource === s.id ? "ring-2 ring-blue-400" : "ring-white/10"
                )}
              >
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="font-mono text-[10px] font-bold text-blue-200">{s.id}</span>
                  <EvType t={s.finding} />
                  <Fresh f={s.freshness} />
                  <Chip tone={s.quality === "HIGH" ? "ok" : s.quality === "MEDIUM" ? "info" : "bad"}>
                    {s.quality} QUALITY
                  </Chip>
                </div>
                <p className="mt-2 text-[13px] font-semibold text-white">{s.name}</p>
                <p className="text-[11px] text-slate-500">{s.type} · retrieved {s.retrieved}</p>

                <div className="mt-3 grid grid-cols-2 gap-3 border-t border-white/[0.07] pt-3 text-[10px]">
                  <div>
                    <p className="text-slate-500">Claims extracted</p>
                    <p className="font-mono text-sm font-semibold text-slate-200">{s.claims}</p>
                  </div>
                  <div>
                    <p className="text-slate-500">Agents using it</p>
                    <p className="font-mono text-[11px] text-slate-300">{s.usedBy.join(", ")}</p>
                  </div>
                  <div>
                    <p className="text-slate-500">Tasks</p>
                    <p className="font-mono text-[11px] text-slate-300">{s.tasks.join(", ")}</p>
                  </div>
                  <div>
                    <p className="text-slate-500">Snapshot</p>
                    <p className="truncate font-mono text-[10px] text-slate-400">{s.snapshot ?? "none retained"}</p>
                  </div>
                </div>

                {s.conflicts.length > 0 && (
                  <p className="mt-3 flex items-center gap-1.5 rounded-lg bg-rose-400/10 px-2.5 py-2 text-[11px] text-rose-200 ring-1 ring-rose-400/25">
                    <AlertOctagon className="h-3.5 w-3.5 flex-none" />
                    Conflicts with {s.conflicts.join(", ")}
                  </p>
                )}
              </div>
            </Reveal>
          ))}
        </div>
      )}

      {tab === "conflicts" && (
        <Reveal>
          <Panel kicker="UNRESOLVED CONFLICTS" title="Claims that disagree" material="solid">
            {conflicts.map((s) => {
              const other = sources.find((x) => x.id === s.conflicts[0])!;
              const ev = evidence.find((e) => e.sourceId === s.id)!;
              return (
                <div key={s.id} className="mb-4 rounded-xl bg-black/25 p-4 ring-1 ring-rose-400/20 last:mb-0">
                  <p className="flex items-center gap-2 text-[11px] font-bold tracking-wider text-rose-200">
                    <AlertOctagon className="h-4 w-4" /> CONFLICT · {ev.id} BLOCKS TASK {ev.taskId}
                  </p>
                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    {[s, other].map((x) => (
                      <div key={x.id} className="rounded-lg bg-black/30 p-3 ring-1 ring-white/[0.07]">
                        <p className="font-mono text-[10px] font-bold text-blue-200">{x.id}</p>
                        <p className="mt-1 text-[12px] text-slate-200">{x.name}</p>
                        <div className="mt-2 flex items-center gap-1.5">
                          <Fresh f={x.freshness} />
                          <Chip tone={x.quality === "HIGH" ? "ok" : x.quality === "MEDIUM" ? "info" : "bad"}>
                            {x.quality}
                          </Chip>
                        </div>
                      </div>
                    ))}
                  </div>
                  <p className="mt-3 text-[12px] leading-relaxed text-slate-300">
                    <span className="font-semibold text-white">Effect:</span> the affected claim is
                    held at {ev.confidence}% confidence and the owning task cannot complete. The
                    Competitor Intelligence Agent is blocked until a manual retailer audit resolves it.
                  </p>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <button
                      onClick={() => traceEvidence(ev.id)}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-blue-400/15 px-2.5 py-1.5 text-[11px] font-medium text-blue-100 ring-1 ring-blue-400/25"
                    >
                      <Link2 className="h-3 w-3" /> Inspect evidence {ev.id}
                    </button>
                    <Chip tone="warn">REQUIRED ACTION · manual price audit</Chip>
                  </div>
                </div>
              );
            })}
          </Panel>
        </Reveal>
      )}

      <Reveal>
        <div className="mt-5 flex flex-wrap items-center gap-2 rounded-2xl coolie-glass p-4">
          <p className="text-[11px] text-slate-400">
            Traceability spine:{" "}
            <span className="font-mono text-blue-200">Recommendation → Claim → Evidence → Source</span>
          </p>
          <span className="ml-auto flex items-center gap-2 text-[11px] text-slate-500">
            {Object.keys(evidenceTypeMeta).length} evidence types · {sources.length} sources retained with snapshots
          </span>
        </div>
      </Reveal>
    </div>
  );
}
