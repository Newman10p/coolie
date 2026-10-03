import type { ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import { X, HelpCircle, Link2, AlertTriangle, Lock, Database } from "lucide-react";
import { cn } from "../utils/cn";
import {
  evidenceTypeMeta,
  freshnessMeta,
  LIFECYCLE,
  stageMeta,
  stageIndex,
  type Lifecycle,
} from "./data";
import { useResearch } from "./store";

/* ---------------- status chip ---------------- */

export function Chip({
  children,
  tone = "neutral",
  dot,
  className,
}: {
  children: ReactNode;
  tone?: "neutral" | "ok" | "warn" | "bad" | "info" | "violet" | "gold";
  dot?: string;
  className?: string;
}) {
  const tones = {
    neutral: "text-slate-300 bg-white/[0.05] ring-white/12",
    ok: "text-emerald-200 bg-emerald-400/10 ring-emerald-400/25",
    warn: "text-amber-200 bg-amber-400/10 ring-amber-400/25",
    bad: "text-rose-200 bg-rose-400/10 ring-rose-400/25",
    info: "text-blue-200 bg-blue-400/10 ring-blue-400/25",
    violet: "text-violet-200 bg-violet-400/10 ring-violet-400/25",
    gold: "text-[#e8d39a] bg-[rgb(214_177_106/0.12)] ring-[rgb(214_177_106/0.3)]",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[10px] font-semibold tracking-wide ring-1",
        tones[tone],
        className
      )}
    >
      {dot && <span className={cn("h-1.5 w-1.5 rounded-full", dot)} />}
      {children}
    </span>
  );
}

/* ---------------- evidence type + freshness ---------------- */

export function EvType({ t }: { t: string }) {
  const m = evidenceTypeMeta[t];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[9px] font-bold tracking-wider ring-1",
        m.cls
      )}
    >
      <span aria-hidden>{m.icon}</span>
      {t}
    </span>
  );
}

export function Fresh({ f }: { f: string }) {
  const m = freshnessMeta[f] ?? freshnessMeta.UNKNOWN;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md px-1.5 py-0.5 text-[9px] font-bold tracking-wider ring-1",
        m.cls
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", m.dot)} />
      {f}
    </span>
  );
}

/* ---------------- confidence meter ---------------- */

export function Confidence({ v, onWhy }: { v: number; onWhy?: () => void }) {
  const tone = v >= 75 ? "from-emerald-400 to-emerald-300" : v >= 50 ? "from-amber-400 to-amber-300" : "from-rose-400 to-rose-300";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-white/10">
        <motion.div
          initial={{ scaleX: 0 }}
          whileInView={{ scaleX: v / 100 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          className={cn("h-full w-full origin-left rounded-full bg-gradient-to-r", tone)}
        />
      </div>
      <span className="w-8 font-mono text-[10px] font-semibold tabular-nums text-slate-300">
        {v}%
      </span>
      {onWhy && <WhyBtn onClick={onWhy} />}
    </div>
  );
}

/* ---------------- THE "WHY?" interaction ---------------- */

export function WhyBtn({
  onClick,
  label = "Why?",
  className,
}: {
  onClick: () => void;
  label?: string;
  className?: string;
}) {
  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      className={cn(
        "inline-flex items-center gap-1 rounded-md bg-blue-400/10 px-1.5 py-0.5 text-[9px] font-bold tracking-wider text-blue-200 ring-1 ring-blue-400/25 transition hover:bg-blue-400/20",
        className
      )}
    >
      <HelpCircle className="h-3 w-3" /> {label}
    </button>
  );
}

export function WhyDrawer() {
  const { why, closeWhy, traceEvidence } = useResearch();
  return (
    <AnimatePresence>
      {why && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closeWhy}
            className="fixed inset-0 z-[70] bg-black/60"
          />
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 300, damping: 32 }}
            className="coolie-glass-blue fixed inset-y-0 right-0 z-[71] w-full max-w-md overflow-y-auto p-6"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[10px] font-bold tracking-[0.25em] text-blue-300/80">
                  WHY DOES COOLIE BELIEVE THIS?
                </p>
                <p className="mt-2 text-lg font-semibold text-metal">{why.title}</p>
                {why.value && (
                  <p className="mt-1 font-mono text-2xl font-semibold text-white">{why.value}</p>
                )}
              </div>
              <button
                onClick={closeWhy}
                className="grid h-8 w-8 flex-none place-items-center rounded-lg text-slate-400 ring-1 ring-white/10 hover:bg-white/5"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <p className="mt-5 text-[10px] font-bold tracking-[0.2em] text-slate-500">
              SUPPORTING EVIDENCE
            </p>
            <div className="mt-2 space-y-2">
              {why.evidence.length === 0 && (
                <p className="rounded-lg bg-rose-400/10 px-3 py-2.5 text-[12px] text-rose-200 ring-1 ring-rose-400/25">
                  No evidence recorded. This value is unsupported — treat it as an open
                  assumption, not a finding.
                </p>
              )}
              {why.evidence.map((id) => (
                <button
                  key={id}
                  onClick={() => {
                    closeWhy();
                    traceEvidence(id);
                  }}
                  className="flex w-full items-center gap-2.5 rounded-lg bg-black/30 px-3 py-2.5 text-left ring-1 ring-white/10 transition hover:bg-black/50"
                >
                  <Link2 className="h-3.5 w-3.5 flex-none text-blue-300" />
                  <span className="font-mono text-[11px] font-semibold text-blue-100">{id}</span>
                  <span className="ml-auto text-[10px] text-slate-500">open in Evidence Room</span>
                </button>
              ))}
            </div>

            <p className="mt-5 text-[10px] font-bold tracking-[0.2em] text-slate-500">
              ASSUMPTIONS IN PLAY
            </p>
            <ul className="mt-2 space-y-2">
              {why.assumptions.map((a) => (
                <li
                  key={a}
                  className="flex items-start gap-2 rounded-lg bg-amber-400/[0.07] px-3 py-2 text-[12px] leading-relaxed text-amber-100/90 ring-1 ring-amber-400/20"
                >
                  <AlertTriangle className="mt-0.5 h-3.5 w-3.5 flex-none" />
                  {a}
                </li>
              ))}
            </ul>

            {why.reasoning && (
              <>
                <p className="mt-5 text-[10px] font-bold tracking-[0.2em] text-slate-500">
                  REASONING
                </p>
                <p className="mt-2 rounded-lg bg-black/30 px-3 py-2.5 text-[12px] leading-relaxed text-slate-300 ring-1 ring-white/10">
                  {why.reasoning}
                </p>
              </>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

/* ---------------- lifecycle timeline ---------------- */

export function LifecycleTimeline({ stage }: { stage: Lifecycle }) {
  const cur = stageIndex(stage);
  const terminal = !LIFECYCLE.includes(stage as (typeof LIFECYCLE)[number]);
  return (
    <div>
      <div className="flex items-center gap-1 overflow-x-auto pb-1">
        {LIFECYCLE.map((s, i) => {
          const done = i < cur || stage === "COMPLETED";
          const active = i === cur && !terminal;
          const m = stageMeta[s];
          return (
            <div key={s} className="flex flex-none items-center gap-1">
              <div className="flex flex-col items-center gap-1.5">
                <motion.span
                  initial={{ scale: 0.4, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: i * 0.045, type: "spring", stiffness: 400, damping: 22 }}
                  className={cn(
                    "grid h-4 w-4 place-items-center rounded-full ring-1 transition",
                    active
                      ? "bg-blue-400 ring-blue-300 shadow-[0_0_12px_rgba(96,165,250,0.9)]"
                      : done
                        ? "bg-emerald-400/80 ring-emerald-300/50"
                        : "bg-slate-700 ring-white/10"
                  )}
                />
                <span
                  className={cn(
                    "w-[74px] text-center text-[8px] font-semibold leading-tight tracking-wide",
                    active ? "text-blue-200" : done ? "text-emerald-300/70" : "text-slate-600"
                  )}
                >
                  {m.label.toUpperCase()}
                </span>
              </div>
              {i < LIFECYCLE.length - 1 && (
                <div className="relative mx-0.5 mb-4 h-px w-6 overflow-hidden bg-white/10 sm:w-10">
                  <motion.div
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: i < cur || stage === "COMPLETED" ? 1 : 0 }}
                    transition={{ duration: 0.5, delay: i * 0.045 }}
                    className="h-full w-full origin-left bg-gradient-to-r from-emerald-400/70 to-blue-400/70"
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
      {terminal && (
        <div className="mt-2">
          <Chip tone={stage === "FAILED" ? "bad" : stage === "PAUSED" ? "neutral" : "neutral"} dot={stage === "FAILED" ? "bg-rose-400" : "bg-slate-400"}>
            MISSION {stageMeta[stage]?.label.toUpperCase() ?? stage}
          </Chip>
        </div>
      )}
    </div>
  );
}

/* ---------------- key/value field ---------------- */

export function Field({
  label,
  children,
  mono,
}: {
  label: string;
  children: ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="min-w-0">
      <p className="text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className={cn("mt-1 text-[12px] leading-relaxed text-slate-200", mono && "font-mono")}>
        {children}
      </p>
    </div>
  );
}

/* ---------------- section card ---------------- */

export function Panel({
  title,
  kicker,
  right,
  children,
  material = "metal",
  className,
}: {
  title?: string;
  kicker?: string;
  right?: ReactNode;
  children: ReactNode;
  material?: "metal" | "glass" | "blue" | "solid";
  className?: string;
}) {
  const mat = {
    metal: "coolie-metal",
    glass: "coolie-glass",
    blue: "coolie-glass-blue",
    solid: "coolie-solid",
  }[material];
  return (
    <div className={cn("rounded-2xl p-5", mat, className)}>
      {(title || kicker) && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <div>
            {kicker && (
              <p className="text-[10px] font-bold tracking-[0.22em] text-blue-300/70">{kicker}</p>
            )}
            {title && <p className="mt-0.5 text-sm font-semibold text-white">{title}</p>}
          </div>
          {right}
        </div>
      )}
      {children}
    </div>
  );
}

/* ---------------- mock-mode disclosure (#18) ---------------- */

export function MockBadge() {
  return (
    <span
      title="This prototype renders a static, backend-shaped dataset. No live agent, task or financial activity is generated."
      className="inline-flex items-center gap-1 rounded-md bg-amber-400/10 px-1.5 py-0.5 text-[9px] font-bold tracking-wider text-amber-200 ring-1 ring-amber-400/25"
    >
      <Database className="h-2.5 w-2.5" /> MOCK DATASET
    </span>
  );
}

/* ---------------- distinction: received vs accepted ---------------- */

export function AcceptanceBadge({ accepted }: { accepted: boolean }) {
  return accepted ? (
    <Chip tone="ok">
      <Lock className="h-2.5 w-2.5" /> VALIDATED &amp; ACCEPTED
    </Chip>
  ) : (
    <Chip tone="warn">
      <AlertTriangle className="h-2.5 w-2.5" /> OUTPUT RECEIVED · NOT ACCEPTED
    </Chip>
  );
}
