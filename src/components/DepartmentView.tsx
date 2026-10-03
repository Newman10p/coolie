import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import {
  ArrowLeft,
  Pause,
  Play,
  ShieldAlert,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Info,
  type LucideIcon,
} from "lucide-react";
import {
  subAgents,
  sectorAlerts,
  type Sector,
  type SubAgent,
} from "../data";

interface FeedItem {
  id: number;
  time: string;
  agent: string;
  text: string;
  level: "info" | "ok" | "warn";
}

const statusMeta: Record<
  SubAgent["status"],
  { dot: string; label: string; ring: string }
> = {
  working: { dot: "bg-emerald-400", label: "Working", ring: "ring-emerald-400/25" },
  idle: { dot: "bg-slate-500", label: "Idle", ring: "ring-white/10" },
  blocked: { dot: "bg-rose-400", label: "Blocked", ring: "ring-rose-400/25" },
  review: { dot: "bg-amber-400", label: "In review", ring: "ring-amber-400/25" },
};

const levelIcon: Record<FeedItem["level"], { icon: LucideIcon; cls: string }> = {
  info: { icon: Info, cls: "text-blue-300" },
  ok: { icon: CheckCircle2, cls: "text-emerald-300" },
  warn: { icon: AlertTriangle, cls: "text-amber-300" },
};

const clock = () =>
  new Date().toLocaleTimeString("en-GB", { hour12: false });

interface AgentState {
  base: SubAgent;
  task: string;
  load: number;
  rate: number;
  done: number;
  bars: number[];
}

export default function DepartmentView({
  sector,
  onClose,
}: {
  sector: Sector;
  onClose: () => void;
}) {
  const [agents, setAgents] = useState<AgentState[]>(() =>
    subAgents[sector.id].map((a) => ({
      base: a,
      task: a.tasks[0],
      load: 28 + Math.random() * 55,
      rate: 12 + Math.round(Math.random() * 42),
      done: 120 + Math.round(Math.random() * 800),
      bars: Array.from({ length: 14 }, () => 20 + Math.random() * 70),
    }))
  );
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [paused, setPaused] = useState(false);
  const idRef = useRef(0);

  // Escape returns to the hall
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  // seed the stream so the panel is never empty
  useEffect(() => {
    const initial = Array.from({ length: 4 }, (_, i) => {
      const a = subAgents[sector.id][i % 4];
      return {
        id: idRef.current++,
        time: clock(),
        agent: a.name,
        text: a.tasks[i % a.tasks.length],
        level: "info",
      } as FeedItem;
    }).reverse();
    setFeed(initial);
  }, [sector.id]);

  useEffect(() => {
    if (paused) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const timer = setInterval(() => {
      const pool = subAgents[sector.id];
      const pick = Math.floor(Math.random() * pool.length);
      const a = pool[pick];

      setAgents((prev) =>
        prev.map((s, i) =>
          i === pick
            ? {
                ...s,
                load: Math.max(14, Math.min(97, s.load + (Math.random() * 22 - 11))),
                rate: Math.max(6, s.rate + Math.round(Math.random() * 10 - 5)),
                done: s.done + Math.round(Math.random() * 4),
                task:
                  Math.random() > 0.55
                    ? a.tasks[Math.floor(Math.random() * a.tasks.length)]
                    : s.task,
                bars: [...s.bars.slice(1), 22 + Math.random() * 68],
              }
            : { ...s, bars: [...s.bars.slice(1), 22 + Math.random() * 68] }
        )
      );

      const level: FeedItem["level"] =
        Math.random() > 0.82 ? "warn" : Math.random() > 0.72 ? "ok" : "info";
      setFeed((f) =>
        [
          {
            id: idRef.current++,
            time: clock(),
            agent: a.name,
            text: a.tasks[Math.floor(Math.random() * a.tasks.length)],
            level,
          },
          ...f,
        ].slice(0, 14)
      );
    }, reduce ? 5200 : 2100);
    return () => clearInterval(timer);
  }, [paused, sector.id]);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 1.04, filter: "blur(10px)" }}
      animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
      exit={{ opacity: 0, scale: 0.98, filter: "blur(10px)" }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] as const }}
      className="coolie-room fixed inset-0 z-[35] overflow-y-auto"
    >
      <div className="coolie-grid-floor pointer-events-none absolute inset-x-0 bottom-0 h-[40vh]" />
      <div className="pointer-events-none absolute right-0 top-0 h-[460px] w-[460px] rounded-full bg-blue-400/10 blur-[110px]" />

      <div className="relative mx-auto w-full max-w-6xl px-4 pb-28 pt-28 sm:pt-32">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div>
            <button
              onClick={onClose}
              className="group mb-5 inline-flex items-center gap-2 rounded-full bg-white/5 px-3.5 py-1.5 text-[12px] font-medium text-slate-300 ring-1 ring-white/10 transition hover:bg-white/10 hover:text-white"
            >
              <ArrowLeft className="h-3.5 w-3.5 transition group-hover:-translate-x-0.5" />
              Return to Department Hall
            </button>
            <p className="text-[11px] font-medium tracking-[0.3em] text-blue-300/70">
              {sector.code} · SECTOR INTERIOR
            </p>
            <h1 className="mt-2 text-4xl font-semibold text-metal">
              {sector.name}
            </h1>
            <p className="mt-2 max-w-lg text-sm text-slate-400">{sector.desc}</p>
          </div>

          <div className="flex items-center gap-3">
            <div className="coolie-metal rounded-2xl px-5 py-3.5 text-center">
              <p className="text-2xl font-semibold text-metal">{sector.metric}</p>
              <p className="text-[10px] uppercase tracking-wider text-slate-500">
                {sector.metricLabel}
              </p>
            </div>
            <button
              onClick={() => setPaused((p) => !p)}
              className={`flex items-center gap-2 rounded-2xl px-4 py-3.5 text-[12px] font-semibold ring-1 transition ${
                paused
                  ? "bg-amber-400/10 text-amber-200 ring-amber-400/25"
                  : "coolie-glass-blue text-blue-100 hover:brightness-125"
              }`}
            >
              {paused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
              {paused ? "Resume stream" : "Pause stream"}
            </button>
          </div>
        </div>

        <div className="mt-8 grid gap-5 lg:grid-cols-3">
          {/* Sub-agents */}
          <div className="lg:col-span-2">
            <div className="mb-3 flex items-center gap-2">
              <Activity className="h-4 w-4 text-blue-300" />
              <p className="text-[11px] font-medium tracking-[0.22em] text-blue-300/80">
                SUB-AGENTS · 4 IN THIS SECTOR · SIMULATED
              </p>
              {!paused && (
                <span className="ml-auto flex items-center gap-1.5 text-[11px] text-emerald-300">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 text-emerald-400 anim-dot" />
                  live
                </span>
              )}
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              {agents.map((s, idx) => {
                const meta = statusMeta[s.base.status];
                return (
                  <motion.div
                    key={s.base.id}
                    initial={{ opacity: 0, y: 28, scale: 0.97 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ duration: 0.55, delay: 0.3 + idx * 0.09, ease: [0.22, 1, 0.36, 1] as const }}
                    className={`coolie-metal coolie-metal-sheen rounded-2xl p-5 ring-1 ${meta.ring}`}
                  >
                    <div className="flex items-start gap-3">
                      <div className="grid h-10 w-10 flex-none place-items-center rounded-xl bg-white/5 ring-1 ring-white/10">
                        <span className="text-sm font-semibold text-blue-200">
                          {s.base.name.charAt(0)}
                        </span>
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold text-white">
                          {s.base.name}
                        </p>
                        <p className="truncate text-[11px] text-slate-500">
                          {s.base.role}
                        </p>
                      </div>
                      <span className="flex items-center gap-1.5 rounded-full bg-white/5 px-2 py-0.5 text-[10px] font-medium text-slate-300 ring-1 ring-white/10">
                        <span className={`h-1.5 w-1.5 rounded-full ${meta.dot} anim-dot`} />
                        {meta.label}
                      </span>
                    </div>

                    {/* live task */}
                    <div className="mt-4 min-h-[34px] rounded-lg bg-black/25 px-3 py-2 ring-1 ring-white/[0.06]">
                      <motion.p
                        key={s.task}
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.35 }}
                        className="text-[12px] leading-snug text-slate-200"
                      >
                        {s.task}
                      </motion.p>
                    </div>

                    {/* load bar */}
                    <div className="mt-3">
                      <div className="flex items-center justify-between text-[10px] text-slate-500">
                        <span className="uppercase tracking-wider">Load</span>
                        <span className="font-semibold tabular-nums text-slate-300">
                          {Math.round(s.load)}%
                        </span>
                      </div>
                      <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-white/[0.06]">
                        <motion.div
                          className="h-full rounded-full bg-gradient-to-r from-blue-500 to-cyan-300"
                          animate={{ width: `${s.load}%` }}
                          transition={{ duration: 0.8, ease: "easeOut" }}
                        />
                      </div>
                    </div>

                    {/* sparkline */}
                    <div className="mt-3 flex h-8 items-end gap-[3px]">
                      {s.bars.map((b, i) => (
                        <span
                          key={i}
                          className="flex-1 rounded-sm bg-blue-400/30 transition-all duration-500"
                          style={{ height: `${b}%` }}
                        />
                      ))}
                    </div>

                    <div className="mt-3 flex items-center justify-between border-t border-white/[0.06] pt-3 text-[11px]">
                      <span className="text-slate-500">
                        Throughput{" "}
                        <span className="font-semibold tabular-nums text-slate-300">
                          {s.rate}/s
                        </span>
                      </span>
                      <span className="text-slate-500">
                        Completed{" "}
                        <span className="font-semibold tabular-nums text-slate-300">
                          {s.done}
                        </span>
                      </span>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>

          {/* Right rail */}
          <div className="space-y-5">
            {/* Live stream */}
            <div className="coolie-glass-blue rounded-2xl p-5">
              <div className="flex items-center justify-between">
                <p className="text-[11px] font-medium tracking-[0.22em] text-blue-200/80">
                  LIVE ACTIVITY
                </p>
                <span className="flex items-center gap-1.5 font-mono text-[10px] text-blue-300/70">
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${
                      paused ? "bg-amber-400" : "bg-emerald-400 text-emerald-400 anim-dot"
                    }`}
                  />
                  {paused ? "PAUSED" : "SSE"}
                </span>
              </div>
              <ul className="mt-3 max-h-[300px] space-y-2.5 overflow-y-auto pr-1">
                {feed.map((f) => {
                  const lv = levelIcon[f.level];
                  return (
                    <motion.li
                      key={f.id}
                      initial={{ opacity: 0, x: -12 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.35 }}
                      className="flex items-start gap-2 rounded-lg bg-black/20 px-2.5 py-2 ring-1 ring-white/[0.05]"
                    >
                      <lv.icon className={`mt-0.5 h-3.5 w-3.5 flex-none ${lv.cls}`} />
                      <div className="min-w-0">
                        <p className="truncate text-[11px] text-slate-200">{f.text}</p>
                        <p className="mt-0.5 font-mono text-[9px] text-slate-500">
                          {f.time} · {f.agent}
                        </p>
                      </div>
                    </motion.li>
                  );
                })}
              </ul>
            </div>

            {/* Attention queue */}
            <div className="coolie-solid rounded-2xl p-5">
              <div className="flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 text-amber-300" />
                <p className="text-[11px] font-medium tracking-[0.22em] text-amber-200/90">
                  ATTENTION QUEUE
                </p>
              </div>
              <ul className="mt-3 space-y-2.5">
                {(sectorAlerts[sector.id] ?? []).map((a, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2.5 rounded-lg bg-white/[0.03] px-3 py-2.5 text-[12px] leading-relaxed text-slate-300 ring-1 ring-white/[0.06]"
                  >
                    <span className="mt-1.5 h-1.5 w-1.5 flex-none rounded-full bg-amber-400" />
                    {a}
                  </li>
                ))}
              </ul>
            </div>

            {/* Sector health */}
            <div className="coolie-glass rounded-2xl p-5">
              <p className="text-[11px] font-medium tracking-[0.22em] text-blue-200/80">
                SECTOR HEALTH
              </p>
              <div className="mt-3 space-y-3">
                {[
                  ["Agent availability", "92%"],
                  ["Event latency", "180 ms"],
                  ["Policy compliance", "100%"],
                  ["Owner sign-offs", "2 pending"],
                ].map(([k, v]) => (
                  <div
                    key={k}
                    className="flex items-center justify-between border-b border-white/[0.07] pb-2 text-[12px] last:border-0 last:pb-0"
                  >
                    <span className="text-slate-400">{k}</span>
                    <span className="font-semibold tabular-nums text-slate-100">{v}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
