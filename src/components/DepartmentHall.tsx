import { useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "motion/react";
import {
  Brain,
  Search,
  Zap,
  Dna,
  FileText,
  Vault,
  ChevronRight,
  type LucideIcon,
} from "lucide-react";
import { sectors, type Sector, type SectorStatus } from "../data";
import DepartmentView from "./DepartmentView";

const iconMap: Record<string, LucideIcon> = {
  brain: Brain,
  search: Search,
  zap: Zap,
  dna: Dna,
  file: FileText,
  vault: Vault,
};

const statusStyle: Record<SectorStatus, { dot: string; label: string; ring: string }> = {
  operational: { dot: "bg-emerald-400 text-emerald-400", label: "Operational", ring: "ring-emerald-400/30" },
  attention: { dot: "bg-amber-400 text-amber-400", label: "Needs sign-off", ring: "ring-amber-400/30" },
  offline: { dot: "bg-rose-400 text-rose-400", label: "Offline", ring: "ring-rose-400/30" },
};

export default function DepartmentHall() {
  const [opening, setOpening] = useState<Sector | null>(null);
  const [active, setActive] = useState<Sector | null>(null);

  const handleOpen = (s: Sector) => {
    if (opening || active) return;
    setOpening(s);
    window.setTimeout(() => {
      setActive(s);
      setOpening(null);
    }, 640);
  };

  return (
    <>
      <div className="mx-auto w-full max-w-6xl px-4 pb-24">
        <div className="mb-8">
          <p className="text-[11px] font-medium tracking-[0.3em] text-blue-300/70">
            SPATIAL NAVIGATION · 6 SECTORS
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-metal sm:text-4xl">
            Department Hall
          </h1>
          <p className="mt-2 max-w-xl text-sm text-slate-400">
            Heavy brushed-steel vault doors lead into each digital sector. Open a
            door to watch its sub-agents work in real time.
          </p>
        </div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {sectors.map((s, i) => {
            const Icon = iconMap[s.icon];
            const st = statusStyle[s.status];
            return (
              <motion.button
                key={s.id}
                initial={{ opacity: 0, y: 50, rotateX: 12 }}
                whileInView={{ opacity: 1, y: 0, rotateX: 0 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{ duration: 0.7, delay: (i % 3) * 0.1, ease: [0.22, 1, 0.36, 1] as const }}
                style={{ transformPerspective: 1000 }}
                whileHover="hover"
                onClick={() => handleOpen(s)}
                aria-label={`Open ${s.name} department — ${st.label}`}
                className="group relative rounded-2xl text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400/70 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0a0f18]"
              >
                {/* Door */}
                <motion.div
                  variants={{ hover: { y: -4 } }}
                  className="coolie-metal coolie-metal-sheen relative h-64 overflow-hidden rounded-2xl"
                >
                  <div className="absolute inset-y-4 left-1/2 w-px -translate-x-1/2 bg-black/40 shadow-[1px_0_0_rgba(255,255,255,0.05)]" />
                  <motion.div
                    variants={{ hover: { opacity: 1 } }}
                    initial={{ opacity: 0 }}
                    className="absolute inset-y-4 left-1/2 w-24 -translate-x-1/2 bg-gradient-to-b from-blue-400/20 via-blue-300/10 to-transparent blur-xl"
                  />
                  {/* left panel */}
                  <motion.div
                    variants={{ hover: { x: -26 } }}
                    transition={{ type: "spring", stiffness: 220, damping: 26 }}
                    className="absolute inset-y-0 left-0 w-1/2 border-r border-black/40 bg-gradient-to-br from-slate-700/30 to-slate-900/40"
                  >
                    <div className="absolute right-3 top-1/2 h-10 w-1.5 -translate-y-1/2 rounded-full bg-white/10" />
                  </motion.div>
                  {/* right panel */}
                  <motion.div
                    variants={{ hover: { x: 26 } }}
                    transition={{ type: "spring", stiffness: 220, damping: 26 }}
                    className="absolute inset-y-0 right-0 w-1/2 border-l border-black/40 bg-gradient-to-bl from-slate-700/30 to-slate-900/40"
                  >
                    <div className="absolute left-3 top-1/2 h-10 w-1.5 -translate-y-1/2 rounded-full bg-white/10" />
                  </motion.div>

                  <div className="absolute inset-0 grid place-items-center">
                    <div className="grid h-16 w-16 place-items-center rounded-2xl bg-slate-900/60 ring-1 ring-white/10 shadow-inner">
                      <Icon className="h-7 w-7 text-blue-300" strokeWidth={1.5} />
                    </div>
                  </div>

                  <div className="absolute right-4 top-4 flex items-center gap-1.5">
                    <span className={`h-2 w-2 rounded-full ${st.dot} anim-dot`} />
                  </div>

                  <div className="absolute bottom-4 left-4">
                    <p className="text-xl font-semibold text-metal">{s.metric}</p>
                    <p className="text-[10px] uppercase tracking-wider text-slate-500">
                      {s.metricLabel}
                    </p>
                  </div>
                  <ChevronRight className="absolute bottom-4 right-4 h-5 w-5 text-slate-500 transition group-hover:translate-x-1 group-hover:text-blue-300" />
                </motion.div>

                {/* Glass nameplate */}
                <div className={`coolie-glass mt-3 flex items-center gap-3 rounded-xl px-4 py-3 ring-1 ${st.ring}`}>
                  <div className="grid h-9 w-9 flex-none place-items-center rounded-lg bg-white/5 ring-1 ring-white/10">
                    <Icon className="h-4 w-4 text-blue-200" strokeWidth={1.6} />
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold tracking-wide text-white">
                      {s.name.toUpperCase()}
                    </p>
                    <p className="truncate text-[10px] font-medium tracking-[0.15em] text-blue-300/70">
                      {s.code}
                    </p>
                  </div>
                  <span className="ml-auto flex-none rounded-full bg-white/5 px-2 py-0.5 text-[10px] font-medium text-slate-300 ring-1 ring-white/10">
                    {st.label}
                  </span>
                </div>
              </motion.button>
            );
          })}
        </div>
      </div>

      {createPortal(
        <>
          {/* ---- Vault door opening transition ---- */}
          <AnimatePresence>
            {opening &&
              (() => {
                const OIcon = iconMap[opening.icon];
                return (
                  <motion.div
                    key="opening"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.25 }}
                    className="pointer-events-none fixed inset-0 z-[60]"
                  >
                    <div className="absolute inset-0 bg-[#070b12]" />

                    {/* revealed core */}
                    <motion.div
                      initial={{ opacity: 0, scale: 0.7 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ duration: 0.55, delay: 0.18, ease: [0.22, 1, 0.36, 1] as const }}
                      className="absolute inset-0 grid place-items-center"
                    >
                      <div className="flex flex-col items-center">
                        <div className="relative grid h-24 w-24 place-items-center rounded-3xl bg-blue-500/20 ring-1 ring-blue-300/30">
                          <OIcon className="h-11 w-11 text-blue-200" strokeWidth={1.4} />
                          <span className="absolute -inset-8 rounded-full bg-blue-400/25 blur-3xl" />
                        </div>
                        <p className="mt-6 text-3xl font-semibold text-metal">
                          {opening.name}
                        </p>
                        <p className="mt-1.5 text-[11px] font-medium tracking-[0.35em] text-blue-300/80">
                          {opening.code}
                        </p>
                      </div>
                    </motion.div>

                    {/* left leaf */}
                    <motion.div
                      initial={{ x: 0 }}
                      animate={{ x: "-100%" }}
                      transition={{ duration: 0.55, ease: [0.7, 0, 0.3, 1] as const }}
                      className="coolie-metal absolute inset-y-0 left-0 w-1/2 border-r-2 border-black/60"
                    >
                      <div className="absolute right-6 top-1/2 h-24 w-2 -translate-y-1/2 rounded-full bg-white/10" />
                    </motion.div>
                    {/* right leaf */}
                    <motion.div
                      initial={{ x: 0 }}
                      animate={{ x: "100%" }}
                      transition={{ duration: 0.55, ease: [0.7, 0, 0.3, 1] as const }}
                      className="coolie-metal absolute inset-y-0 right-0 w-1/2 border-l-2 border-black/60"
                    >
                      <div className="absolute left-6 top-1/2 h-24 w-2 -translate-y-1/2 rounded-full bg-white/10" />
                    </motion.div>

                    {/* light spill along the seam */}
                    <motion.div
                      initial={{ opacity: 0, scaleX: 1 }}
                      animate={{ opacity: [0, 1, 0], scaleX: [1, 8, 20] }}
                      transition={{ duration: 0.7, times: [0, 0.35, 1] }}
                      className="absolute inset-y-0 left-1/2 w-1 -translate-x-1/2 bg-gradient-to-b from-transparent via-blue-200 to-transparent blur-sm"
                    />
                  </motion.div>
                );
              })()}
          </AnimatePresence>

          {/* ---- Department interior ---- */}
          <AnimatePresence>
            {active && (
              <DepartmentView
                key={active.id}
                sector={active}
                onClose={() => setActive(null)}
              />
            )}
          </AnimatePresence>
        </>,
        document.body
      )}
    </>
  );
}
