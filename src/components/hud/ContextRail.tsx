import { motion } from "motion/react";
import { ShieldCheck, KeyRound, Database, History, Radio } from "lucide-react";
import { activeMandates, hudSessions } from "../../data";
import { Reveal } from "../scroll/Reveal";

export default function ContextRail() {
  return (
    <aside className="space-y-5">
      {/* Owner card */}
      <Reveal dir="right">
        <div className="coolie-metal rounded-2xl p-5">
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 flex-none place-items-center rounded-xl bg-blue-400/15 text-sm font-semibold text-blue-100 ring-1 ring-blue-300/30">
              OM
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-white">Owner · Verified</p>
              <p className="truncate text-[11px] text-slate-500">
                Session 06:12 · encrypted
              </p>
            </div>
          </div>
          <div className="mt-4 flex items-center gap-1.5 rounded-lg bg-emerald-400/10 px-2.5 py-1.5 text-[10px] font-semibold text-emerald-300 ring-1 ring-emerald-400/20">
            <Radio className="h-3 w-3" /> ORCHESTRATOR CHANNEL OPEN
          </div>
        </div>
      </Reveal>

      {/* Active mandates */}
      <Reveal dir="right" delay={0.06}>
        <div className="coolie-glass rounded-2xl p-5">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-blue-300" />
            <p className="text-[11px] font-medium tracking-[0.22em] text-blue-200/80">
              ACTIVE MANDATES
            </p>
          </div>
          <ul className="mt-3.5 space-y-3">
            {activeMandates.map((m) => (
              <li key={m.id} className="border-b border-white/[0.07] pb-2.5 last:border-0 last:pb-0">
                <div className="flex items-baseline justify-between gap-2">
                  <p className="truncate text-[12px] font-medium text-slate-200">
                    {m.label}
                  </p>
                  <span className="flex-none font-mono text-[11px] font-semibold text-blue-100">
                    {m.value}
                  </span>
                </div>
                <p className="mt-0.5 flex items-center gap-1.5 font-mono text-[10px] text-slate-500">
                  {m.id} ·{" "}
                  <span className={m.state === "held" ? "text-amber-300" : "text-emerald-300"}>
                    {m.state}
                  </span>
                </p>
              </li>
            ))}
          </ul>
          <p className="mt-3.5 flex items-start gap-1.5 rounded-lg bg-black/25 px-2.5 py-2 text-[10px] leading-relaxed text-slate-500">
            <KeyRound className="mt-0.5 h-3 w-3 flex-none" />
            Limits are enforced by the backend. The HUD displays them; it cannot override them.
          </p>
        </div>
      </Reveal>

      {/* Memory */}
      <Reveal dir="right" delay={0.12}>
        <div className="coolie-glass rounded-2xl p-5">
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-blue-300" />
            <p className="text-[11px] font-medium tracking-[0.22em] text-blue-200/80">
              MEMORY GRAPH
            </p>
          </div>
          <p className="mt-3 text-2xl font-semibold text-metal">4,281</p>
          <p className="text-[11px] text-slate-500">nodes · 12 recalled this session</p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {["Mandates", "Holdings", "Preferences", "Decisions", "Sector history"].map((t) => (
              <span
                key={t}
                className="rounded-md bg-white/5 px-2 py-1 text-[10px] text-slate-300 ring-1 ring-white/10"
              >
                {t}
              </span>
            ))}
          </div>
        </div>
      </Reveal>

      {/* Sessions */}
      <Reveal dir="right" delay={0.18}>
        <div className="coolie-solid rounded-2xl p-5">
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-blue-300" />
            <p className="text-[11px] font-medium tracking-[0.22em] text-slate-400">
              SESSIONS
            </p>
          </div>
          <ul className="mt-3 space-y-1">
            {hudSessions.map((s) => (
              <motion.li
                key={s.id}
                whileHover={{ x: 2 }}
                className="flex cursor-pointer items-center gap-2 rounded-lg px-2.5 py-2 transition-colors hover:bg-white/[0.04]"
              >
                {s.live ? (
                  <span className="h-1.5 w-1.5 flex-none rounded-full bg-emerald-400 text-emerald-400 anim-dot" />
                ) : (
                  <span className="h-1.5 w-1.5 flex-none rounded-full bg-slate-600" />
                )}
                <span className={`truncate text-[12px] ${s.live ? "text-white" : "text-slate-400"}`}>
                  {s.title}
                </span>
                <span className="ml-auto flex-none font-mono text-[10px] text-slate-600">
                  {s.time}
                </span>
              </motion.li>
            ))}
          </ul>
        </div>
      </Reveal>
    </aside>
  );
}
