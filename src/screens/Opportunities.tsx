import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  ArrowLeft, HelpCircle, TrendingUp, Users, Factory, Megaphone, Package,
  Calculator, ShieldAlert, FileText, FlaskConical, History, Boxes, Eye, X,
} from "lucide-react";
import { cn } from "../utils/cn";
import { opportunities, oppStatusMeta, type Opp, type ScoreDim } from "../research/data";
import { Chip, EvType, Field, Panel, WhyBtn, Confidence } from "../research/ui";
import { Reveal } from "../components/scroll/Reveal";
import { useResearch } from "../research/store";

/* ---------- transparent scoring ---------- */

function ScoreGrid({ scores }: { scores: ScoreDim[] }) {
  const { openWhy } = useResearch();
  return (
    <div className="space-y-2.5">
      {scores.map((s, i) => {
        const tone = s.value >= 75 ? "from-emerald-400 to-emerald-300" : s.value >= 50 ? "from-amber-400 to-amber-300" : "from-rose-400 to-rose-300";
        return (
          <motion.div
            key={s.label}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className="rounded-xl bg-black/25 p-3 ring-1 ring-white/[0.07]"
          >
            <div className="flex items-center gap-2">
              <p className="w-[132px] flex-none text-[11px] font-medium text-slate-300">{s.label}</p>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-white/10">
                <motion.div
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: s.value / 100 }}
                  transition={{ duration: 0.9, delay: 0.1 + i * 0.05, ease: [0.22, 1, 0.36, 1] }}
                  className={cn("h-full w-full origin-left rounded-full bg-gradient-to-r", tone)}
                />
              </div>
              <span className="w-7 flex-none font-mono text-[11px] font-bold tabular-nums text-white">
                {s.value}
              </span>
              <WhyBtn
                onClick={() =>
                  openWhy({
                    title: s.label,
                    subject: "Score dimension · 0–100",
                    value: `${s.value} / 100`,
                    evidence: s.why.evidence,
                    assumptions: s.why.assumptions,
                    reasoning:
                      "This is one of eight independent dimensions. No single aggregate score is produced, and no dimension is hidden behind another.",
                  })
                }
              />
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}

/* ---------- dossier tabs ---------- */

const TABS = [
  ["overview", "Overview", Boxes],
  ["demand", "Demand", TrendingUp],
  ["competitors", "Competitors", Eye],
  ["suppliers", "Suppliers & Fulfillment", Factory],
  ["audience", "Audience", Users],
  ["marketing", "Marketing", Megaphone],
  ["product", "Product & Offer", Package],
  ["financials", "Financials", Calculator],
  ["risk", "Risk", ShieldAlert],
  ["evidence", "Evidence", FileText],
  ["validation", "Validation", FlaskConical],
  ["history", "Decision History", History],
] as const;

function Rows({
  rows,
  kindLabel,
}: {
  rows: { k: string; v: string; ev?: string; kind?: string }[];
  kindLabel?: boolean;
}) {
  const { traceEvidence } = useResearch();
  return (
    <div className="divide-y divide-white/[0.06]">
      {rows.map((r, i) => (
        <motion.div
          key={r.k}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.04 }}
          className="flex flex-wrap items-start gap-x-4 gap-y-1.5 py-2.5"
        >
          <p className="w-[190px] flex-none text-[11px] font-medium text-slate-400">{r.k}</p>
          <p className="min-w-[180px] flex-1 text-[12px] leading-relaxed text-slate-100">{r.v}</p>
          <div className="flex flex-none items-center gap-1.5">
            {kindLabel && r.kind && <EvType t={r.kind} />}
            {/* eslint-disable-next-line */}
            {r.ev && r.ev !== "—" && (
              <button
                onClick={() => traceEvidence(r.ev!)}
                className="inline-flex items-center gap-1 rounded-md bg-blue-400/10 px-1.5 py-0.5 font-mono text-[9px] font-bold text-blue-200 ring-1 ring-blue-400/25 hover:bg-blue-400/20"
              >
                {r.ev}
              </button>
            )}
          </div>
        </motion.div>
      ))}
    </div>
  );
}

function Dossier({ o }: { o: Opp }) {
  const [tab, setTab] = useState<string>("overview");
  const { go } = useResearch();

  return (
    <div className="coolie-glass-blue rounded-2xl p-5 sm:p-6">
      <div className="flex flex-wrap gap-1.5 border-b border-white/[0.08] pb-4">
        {TABS.map(([id, label, Icon]) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={cn(
              "relative flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[11px] font-medium transition",
              tab === id ? "text-white" : "text-slate-400 hover:text-slate-200"
            )}
          >
            {tab === id && (
              <motion.span layoutId="dossier-tab" className="absolute inset-0 rounded-lg bg-blue-400/15 ring-1 ring-blue-300/25" />
            )}
            <Icon className="relative h-3.5 w-3.5" strokeWidth={1.8} />
            <span className="relative hidden sm:inline">{label}</span>
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={tab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.28 }}
          className="pt-5"
        >
          {tab === "overview" && (
            <div className="grid gap-5 lg:grid-cols-[1.3fr_1fr]">
              <div className="space-y-5">
                <div className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
                  <Field label="Business model">{o.model}</Field>
                  <Field label="Target market">{o.market}</Field>
                  <div className="sm:col-span-2">
                    <Field label="Customer problem">{o.problem}</Field>
                  </div>
                  <div className="sm:col-span-2">
                    <Field label="Proposed offer">{o.offer}</Field>
                  </div>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  {[
                    ["Demand evidence", o.demandEvidence],
                    ["Competitors", o.competitors],
                    ["Suppliers", o.suppliers],
                    ["Fulfillment", o.fulfillment],
                    ["Marketing", o.marketing],
                    ["Risk", o.risk],
                  ].map(([k, v]) => (
                    <div key={k} className="rounded-xl bg-black/25 p-3 ring-1 ring-white/[0.07]">
                      <p className="text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500">{k}</p>
                      <p className="mt-1 text-[12px] leading-relaxed text-slate-200">{v}</p>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <p className="mb-3 text-[10px] font-bold tracking-[0.22em] text-blue-300/70">
                  TRANSPARENT SCORING · 8 DIMENSIONS
                </p>
                <ScoreGrid scores={o.scores} />
              </div>
            </div>
          )}

          {tab === "demand" && <Rows rows={o.dossier.demand} kindLabel />}
          {tab === "competitors" && (
            <>
              <p className="mb-3 rounded-lg bg-black/25 px-3 py-2 text-[11px] text-slate-400 ring-1 ring-white/[0.06]">
                Observed findings are directly measured. Inferred findings are reasoned and must be
                tested before they are trusted.
              </p>
              <Rows rows={o.dossier.competitors} kindLabel />
            </>
          )}
          {tab === "suppliers" && <Rows rows={o.dossier.suppliers} />}
          {tab === "audience" && <Rows rows={o.dossier.audience} />}
          {tab === "marketing" && <Rows rows={o.dossier.marketing} />}
          {tab === "product" && <Rows rows={o.dossier.product} />}

          {tab === "financials" && (
            <div>
              <p className="mb-3 text-[12px] text-slate-400">
                Normalized financial inputs sent to the Money Calculator. Estimated values are
                marked — they are not verified facts.
              </p>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[620px] text-left text-[12px]">
                  <thead>
                    <tr className="border-b border-white/10 text-[9px] uppercase tracking-wider text-slate-500">
                      {["Input", "Value", "Currency", "Source", "Confidence", "Timestamp", "Nature"].map((h) => (
                        <th key={h} className="px-3 py-2 font-semibold">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      ["Selling price", "169.00", "AED", "SRC-01 · observed", 88, "06:14", false, "EV-004"],
                      ["Product cost", "31.20", "AED", "SRC-05 · quote midpoint", 84, "07:05", false, "EV-006"],
                      ["Shipping cost", "9.80", "AED", "SRC-05 · CALCULATED", 76, "07:05", true, "EV-007"],
                      ["Import duty", "5.0", "%", "ASSUMED · unconfirmed", 40, "07:05", true, "EV-007"],
                      ["Blended CAC", "48.00", "AED", "SRC-09 · model", 52, "08:15", true, "EV-009"],
                      ["Payment + packaging", "7.40", "AED", "SRC-05 · derived", 70, "07:05", true, "EV-007"],
                    ].map((r, i) => (
                      <motion.tr
                        key={String(r[0])}
                        initial={{ opacity: 0, x: -8 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.04 }}
                        className="border-b border-white/5 last:border-0"
                      >
                        <td className="px-3 py-2.5 font-medium text-slate-200">{r[0]}</td>
                        <td className="px-3 py-2.5 font-mono font-semibold text-white">{r[1]}</td>
                        <td className="px-3 py-2.5 font-mono text-[11px] text-slate-400">{r[2]}</td>
                        <td className="px-3 py-2.5 text-[11px] text-slate-400">{r[3]}</td>
                        <td className="px-3 py-2.5"><Confidence v={r[4] as number} /></td>
                        <td className="px-3 py-2.5 font-mono text-[10px] text-slate-500">{r[5]}</td>
                        <td className="px-3 py-2.5">
                          {r[6] ? <Chip tone="warn">ESTIMATE</Chip> : <Chip tone="ok">OBSERVED</Chip>}
                        </td>
                      </motion.tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <button
                onClick={() => go("decisions")}
                className="mt-4 inline-flex items-center gap-2 rounded-xl coolie-glass-blue px-4 py-2.5 text-[12px] font-semibold text-blue-100"
              >
                <Calculator className="h-4 w-4" /> Open Money Calculator handoff
              </button>
            </div>
          )}

          {tab === "risk" && (
            <div>
              <button
                onClick={() => go("decisions")}
                className="mb-3 inline-flex items-center gap-2 rounded-lg bg-rose-400/15 px-3 py-2 text-[12px] font-semibold text-rose-100 ring-1 ring-rose-400/30"
              >
                <ShieldAlert className="h-4 w-4" /> Open the Risk &amp; Policy Gate
              </button>
              <Rows
                rows={[{ k: "Risk assessment", v: o.risk, ev: "EV-012" }]}
              />
            </div>
          )}

          {tab === "evidence" && (
            <div className="grid gap-2 sm:grid-cols-2">
              {o.scores.flatMap((s) => s.why.evidence).filter((v, i, a) => a.indexOf(v) === i).map((id) => (
                <button
                  key={id}
                  onClick={() => go("evidence")}
                  className="flex items-center gap-2.5 rounded-lg bg-black/25 px-3 py-2.5 text-left ring-1 ring-white/[0.07] hover:bg-black/40"
                >
                  <FileText className="h-3.5 w-3.5 flex-none text-blue-300" />
                  <span className="font-mono text-[11px] font-semibold text-blue-100">{id}</span>
                  <span className="ml-auto text-[10px] text-slate-500">Evidence Room</span>
                </button>
              ))}
            </div>
          )}

          {tab === "validation" && (
            <div>
              <Rows rows={o.dossier.validation} />
              <p className="mt-4 rounded-lg bg-amber-400/[0.07] px-3 py-2.5 text-[11px] leading-relaxed text-amber-100/90 ring-1 ring-amber-400/20">
                Validation is a requirement, not a formality. No capital commitment is released while
                a required experiment is outstanding.
              </p>
            </div>
          )}

          {tab === "history" && (
            <div className="relative pl-5">
              <div className="absolute bottom-2 left-[7px] top-2 w-px bg-gradient-to-b from-blue-400/50 via-white/10 to-transparent" />
              {o.dossier.history.map((h, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.07 }}
                  className="relative mb-4 last:mb-0"
                >
                  <span className="absolute -left-[19px] top-1 h-2.5 w-2.5 rounded-full bg-blue-400 ring-2 ring-[#0b1320]" />
                  <p className="font-mono text-[10px] text-slate-500">{h.when}</p>
                  <p className="mt-0.5 text-[12px] text-slate-100">{h.what}</p>
                  <div className="mt-1 flex items-center gap-2">
                    <span className="text-[10px] text-slate-500">{h.by}</span>
                    <Chip tone={h.immutable ? "ok" : "neutral"}>
                      {h.immutable ? "IMMUTABLE RECORD" : "MUTABLE"}
                    </Chip>
                  </div>
                </motion.div>
              ))}
              <p className="mt-3 flex items-start gap-2 rounded-lg bg-black/25 px-3 py-2.5 text-[11px] leading-relaxed text-slate-400 ring-1 ring-white/[0.06]">
                <History className="mt-0.5 h-3.5 w-3.5 flex-none" />
                History is append-only. Learning is layered on top in a separate surface — previous
                reports are never rewritten.
              </p>
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

/* ---------- screen ---------- */

export default function Opportunities() {
  const { openOpp, openOpportunity, openWhy } = useResearch();
  const active = opportunities.find((o) => o.id === openOpp) ?? null;

  return (
    <div className="mx-auto w-full max-w-7xl px-4 pb-28">
      <AnimatePresence mode="wait">
        {!active ? (
          <motion.div key="list" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <Reveal>
              <div className="mb-6">
                <p className="text-[11px] font-medium tracking-[0.3em] text-blue-300/70">
                  OPPORTUNITY EXPLORER · STRUCTURED OpportunityRecord OBJECTS
                </p>
                <h1 className="mt-2 text-3xl font-semibold text-metal sm:text-4xl">
                  What opportunities were discovered?
                </h1>
                <p className="mt-2 max-w-2xl text-sm text-slate-400">
                  Research produces structured records, not reports. Each carries demand,
                  competition, suppliers, audience, marketing, offer, financials, risk and a
                  validation plan — with eight exposed score dimensions.
                </p>
              </div>
            </Reveal>

            <div className="grid gap-4 lg:grid-cols-2">
              {opportunities.map((o, i) => {
                const st = oppStatusMeta[o.status];
                const avg = Math.round(o.scores.reduce((s, d) => s + d.value, 0) / o.scores.length);
                return (
                  <Reveal key={o.id} delay={i * 0.06}>
                    <motion.button
                      onClick={() => openOpportunity(o.id)}
                      whileHover={{ y: -4 }}
                      className="coolie-metal coolie-metal-sheen group h-full w-full rounded-2xl p-5 text-left"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <span className="font-mono text-[10px] text-slate-500">{o.id}</span>
                          <p className="mt-1 text-[15px] font-semibold leading-snug text-white">{o.name}</p>
                          <p className="mt-0.5 text-[11px] text-slate-500">{o.model}</p>
                        </div>
                        <span className={cn("flex-none rounded-md px-2 py-0.5 text-[10px] font-bold ring-1", st.cls)}>
                          <span className={cn("mr-1.5 inline-block h-1.5 w-1.5 rounded-full align-middle", st.dot)} />
                          {o.status}
                        </span>
                      </div>

                      <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2">
                        <div>
                          <p className="text-[9px] font-bold uppercase tracking-wider text-slate-500">Confidence</p>
                          <Confidence
                            v={o.confidence}
                            onWhy={() =>
                              openWhy({
                                title: `${o.name} · overall confidence`,
                                subject: "Aggregate of evidence confidence",
                                value: `${o.confidence}%`,
                                evidence: o.scores.flatMap((s) => s.why.evidence),
                                assumptions: [
                                  "Confidence reflects how well-evidenced the record is, not how attractive it is",
                                  "An attractive opportunity with weak evidence scores low",
                                ],
                              })
                            }
                          />
                        </div>
                        <div>
                          <p className="text-[9px] font-bold uppercase tracking-wider text-slate-500">Mean of 8 dimensions</p>
                          <p className="font-mono text-sm font-semibold text-slate-200">{avg}</p>
                        </div>
                      </div>

                      <div className="mt-4 grid grid-cols-4 gap-1.5">
                        {o.scores.slice(0, 8).map((s) => (
                          <div key={s.label} className="rounded-lg bg-black/25 p-2 ring-1 ring-white/[0.06]">
                            <p className="truncate text-[8px] uppercase tracking-wide text-slate-500">
                              {s.label.split(" ")[0]}
                            </p>
                            <p className="mt-0.5 font-mono text-[12px] font-bold text-slate-100">{s.value}</p>
                          </div>
                        ))}
                      </div>

                      <p className="mt-4 flex items-center gap-1.5 text-[11px] font-medium text-blue-200">
                        <HelpCircle className="h-3.5 w-3.5" /> Open dossier · every dimension explains itself
                      </p>
                    </motion.button>
                  </Reveal>
                );
              })}
            </div>
          </motion.div>
        ) : (
          <motion.div key="dossier" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }}>
            <button
              onClick={() => openOpportunity(null)}
              className="group mb-5 inline-flex items-center gap-2 rounded-full bg-white/5 px-3.5 py-1.5 text-[12px] font-medium text-slate-300 ring-1 ring-white/10 hover:bg-white/10"
            >
              <ArrowLeft className="h-3.5 w-3.5 transition group-hover:-translate-x-0.5" />
              All opportunities
            </button>

            <div className="coolie-metal coolie-metal-sheen mb-5 rounded-2xl p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-md bg-white/5 px-2 py-1 font-mono text-[10px] text-blue-200 ring-1 ring-white/10">
                      {active.id}
                    </span>
                    <span className={cn("rounded-md px-2 py-0.5 text-[10px] font-bold ring-1", oppStatusMeta[active.status].cls)}>
                      <span className={cn("mr-1.5 inline-block h-1.5 w-1.5 rounded-full align-middle", oppStatusMeta[active.status].dot)} />
                      {active.status}
                    </span>
                    <Chip tone="violet">OPPORTUNITY RECORD</Chip>
                  </div>
                  <h1 className="mt-3 text-2xl font-semibold text-metal sm:text-3xl">{active.name}</h1>
                  <p className="mt-1.5 text-[12px] text-slate-400">{active.model} · {active.market}</p>
                </div>
                <div className="text-right">
                  <p className="text-[9px] font-bold uppercase tracking-wider text-slate-500">Confidence</p>
                  <p className="font-mono text-3xl font-semibold text-metal">{active.confidence}%</p>
                  <WhyBtn
                    className="mt-1"
                    onClick={() =>
                      openWhy({
                        title: `${active.name} · confidence`,
                        subject: "Evidence-backed confidence",
                        value: `${active.confidence}%`,
                        evidence: active.scores.flatMap((s) => s.why.evidence),
                        assumptions: ["Reflects evidence quality, not attractiveness"],
                      })
                    }
                  />
                </div>
              </div>
            </div>

            <Dossier o={active} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* comparison strip */}
      <Reveal>
        <div className="mt-6">
          <Panel kicker="COMPARISON · ALL RECORDS" title="Side by side" material="solid">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-[12px]">
                <thead>
                  <tr className="border-b border-white/10 text-[9px] uppercase tracking-wider text-slate-500">
                    {["Record", "Status", "Demand", "Competition", "Margin", "Fulfill", "Marketing", "Fit", "Risk", "Evidence"].map((h) => (
                      <th key={h} className="whitespace-nowrap px-3 py-2 font-semibold">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {opportunities.map((o) => (
                    <tr
                      key={o.id}
                      onClick={() => openOpportunity(o.id)}
                      className="cursor-pointer border-b border-white/5 last:border-0 hover:bg-white/[0.03]"
                    >
                      <td className="px-3 py-2.5">
                        <p className="font-medium text-slate-100">{o.name}</p>
                        <p className="font-mono text-[9px] text-slate-500">{o.id}</p>
                      </td>
                      <td className="px-3 py-2.5">
                        <span className={cn("whitespace-nowrap rounded px-1.5 py-0.5 text-[9px] font-bold ring-1", oppStatusMeta[o.status].cls)}>
                          {o.status}
                        </span>
                      </td>
                      {o.scores.map((s) => (
                        <td key={s.label} className="px-3 py-2.5">
                          <span className="font-mono text-[11px] font-semibold text-slate-200">{s.value}</span>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3 flex items-start gap-2 text-[11px] text-slate-500">
              <X className="mt-0.5 h-3 w-3 flex-none" />
              There is deliberately no single ranked "AI score". Records are compared dimension by
              dimension so you can disagree with a specific input rather than a black box.
            </p>
          </Panel>
        </div>
      </Reveal>
    </div>
  );
}
