import { useCallback, useEffect, useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import { Check, Loader2, AlertTriangle, ArrowRight } from "lucide-react";

/**
 * Boot / "awakening" screen.
 * NOTE: In production this checklist must be driven by the backend readiness
 * snapshot + SSE events (startup.service_ready / startup.service_degraded).
 * Here the sequence is simulated for the prototype.
 */
const services: { name: string; detail: string; degraded?: boolean }[] = [
  { name: "Secure session", detail: "Owner identity verified" },
  { name: "Brain", detail: "Cognition core online" },
  { name: "Research", detail: "1,204 sources connected" },
  { name: "Enactor", detail: "Degraded · 1 retry loop", degraded: true },
  { name: "Evolver", detail: "Strategy models loaded" },
  { name: "Reports", detail: "8 new briefings filed" },
  { name: "Treasury", detail: "Sharia gate armed" },
  { name: "Orchestrator", detail: "Voice channel ready" },
];

const word = "COOLIE".split("");
const ease = [0.22, 1, 0.36, 1] as const;

export default function SplashScreen({ onDone }: { onDone: () => void }) {
  const reduce = useReducedMotion();
  const [ready, setReady] = useState(0);
  const allReady = ready >= services.length;

  const finish = useCallback(() => onDone(), [onDone]);

  // sequence services coming online
  useEffect(() => {
    if (allReady) return;
    const t = setTimeout(
      () => setReady((r) => r + 1),
      ready === 0 ? (reduce ? 200 : 1100) : reduce ? 80 : 260 + Math.random() * 160
    );
    return () => clearTimeout(t);
  }, [ready, allReady, reduce]);

  // auto-enter shortly after everything is ready
  useEffect(() => {
    if (!allReady) return;
    const t = setTimeout(finish, reduce ? 500 : 1600);
    return () => clearTimeout(t);
  }, [allReady, finish, reduce]);

  // keyboard: Enter / Escape skip
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Enter" || e.key === "Escape") finish();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [finish]);

  const pct = Math.round((Math.min(ready, services.length) / services.length) * 100);

  const shutter = (side: "top" | "bottom") => ({
    exit: {
      y: side === "top" ? "-100%" : "100%",
      transition: { duration: reduce ? 0.3 : 0.85, delay: reduce ? 0 : 0.25, ease: [0.7, 0, 0.3, 1] as const },
    },
  });

  return (
    <motion.div
      key="splash"
      initial="show"
      animate="show"
      exit="exit"
      variants={{ show: {}, exit: {} }}
      className="fixed inset-0 z-[100]"
      role="dialog"
      aria-label="Coolie is starting up"
    >
      {/* Metal shutters */}
      <motion.div
        variants={shutter("top")}
        className="coolie-room absolute inset-x-0 top-0 h-1/2 border-b border-black/60"
      >
        <div className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-blue-300/50 to-transparent" />
      </motion.div>
      <motion.div
        variants={shutter("bottom")}
        className="coolie-room absolute inset-x-0 bottom-0 h-1/2 border-t border-black/60"
      >
        <div className="coolie-grid-floor absolute inset-0 opacity-70" />
      </motion.div>

      {/* seam flare on exit */}
      <motion.div
        variants={{
          show: { opacity: 0, scaleX: 0.2 },
          exit: { opacity: [0, 1, 0], scaleX: [0.2, 1, 1], transition: { duration: 0.8 } },
        }}
        className="pointer-events-none absolute inset-x-0 top-1/2 h-[2px] -translate-y-1/2 bg-gradient-to-r from-transparent via-blue-200 to-transparent shadow-[0_0_30px_8px_rgba(96,165,250,0.45)]"
      />

      {/* Content */}
      <motion.div
        variants={{
          show: { opacity: 1, scale: 1 },
          exit: { opacity: 0, scale: 1.06, transition: { duration: 0.35 } },
        }}
        className="absolute inset-0 flex flex-col items-center justify-center overflow-y-auto px-6 py-10"
      >
        <div className="pointer-events-none absolute left-1/2 top-1/3 h-[420px] w-[420px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-blue-500/15 blur-[120px]" />

        {/* Logo */}
        <div className="relative h-24 w-24">
          <motion.div
            initial={{ opacity: 0, scale: 0.6 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, ease }}
            className="absolute -inset-4 rounded-full border border-dashed border-blue-300/20 anim-ring-spin"
          />
          <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full">
            <defs>
              <linearGradient id="hexg" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#dbeafe" />
                <stop offset="100%" stopColor="#60a5fa" />
              </linearGradient>
            </defs>
            <motion.path
              d="M50 6 L88 28 L88 72 L50 94 L12 72 L12 28 Z"
              fill="none"
              stroke="url(#hexg)"
              strokeWidth="2.5"
              strokeLinejoin="round"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: reduce ? 0.2 : 1.2, ease: "easeInOut" }}
              style={{ filter: "drop-shadow(0 0 6px rgba(96,165,250,0.8))" }}
            />
            <motion.path
              d="M50 26 L69 37 L69 63 L50 74 L31 63 L31 37 Z"
              fill="rgba(96,165,250,0.12)"
              stroke="rgba(191,219,254,0.5)"
              strokeWidth="1.5"
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{ duration: reduce ? 0.2 : 0.9, delay: reduce ? 0 : 0.5 }}
            />
            <motion.circle
              cx="50"
              cy="50"
              r="5"
              fill="#bfdbfe"
              initial={{ scale: 0 }}
              animate={{ scale: [0, 1.4, 1] }}
              transition={{ duration: 0.6, delay: reduce ? 0 : 1.1 }}
              style={{ transformOrigin: "50px 50px", filter: "drop-shadow(0 0 8px #60a5fa)" }}
            />
          </svg>
        </div>

        {/* Wordmark */}
        <div className="mt-8 flex gap-1.5 sm:gap-2">
          {word.map((ch, i) => (
            <motion.span
              key={i}
              initial={{ opacity: 0, y: 18, filter: "blur(8px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              transition={{ duration: 0.6, delay: (reduce ? 0 : 0.6) + i * 0.07, ease }}
              className="text-4xl font-semibold tracking-wide text-metal sm:text-5xl"
            >
              {ch}
            </motion.span>
          ))}
        </div>
        <motion.p
          initial={{ opacity: 0, letterSpacing: "0.1em" }}
          animate={{ opacity: 1, letterSpacing: "0.5em" }}
          transition={{ duration: 1.2, delay: reduce ? 0 : 1.0, ease }}
          className="mt-3 text-[11px] font-medium text-blue-300/80"
        >
          INTEL ZONE
        </motion.p>

        {/* Readiness checklist (glass) */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: reduce ? 0 : 1.0, ease }}
          className="coolie-glass mt-9 w-full max-w-md rounded-2xl p-5"
        >
          <div className="mb-3 flex items-center justify-between">
            <p className="text-[10px] font-semibold tracking-[0.25em] text-slate-400">
              {allReady ? "DEMO WORKROOM READY" : "SIMULATING DEMO STARTUP"}
            </p>
            <p className="font-mono text-[11px] tabular-nums text-blue-200">{pct}%</p>
          </div>
          <div className="mb-4 h-1 overflow-hidden rounded-full bg-white/10">
            <motion.div
              animate={{ scaleX: pct / 100 }}
              initial={{ scaleX: 0 }}
              transition={{ duration: 0.4, ease: "easeOut" }}
              className="h-full origin-left rounded-full bg-gradient-to-r from-blue-500 to-cyan-300"
            />
          </div>

          <ul className="grid gap-1.5 sm:grid-cols-2 sm:gap-x-4">
            {services.map((s, i) => {
              const done = i < ready;
              const loading = i === ready;
              return (
                <li key={s.name} className="flex items-center gap-2.5 py-0.5">
                  <span className="grid h-4 w-4 flex-none place-items-center">
                    {done ? (
                      <motion.span
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ type: "spring", stiffness: 500, damping: 22 }}
                      >
                        {s.degraded ? (
                          <AlertTriangle className="h-3.5 w-3.5 text-amber-300" />
                        ) : (
                          <Check className="h-3.5 w-3.5 text-emerald-300" />
                        )}
                      </motion.span>
                    ) : loading ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-300" />
                    ) : (
                      <span className="h-1.5 w-1.5 rounded-full bg-slate-600" />
                    )}
                  </span>
                  <div className="min-w-0">
                    <p
                      className={`text-[12px] font-medium transition-colors ${
                        done ? "text-slate-100" : "text-slate-500"
                      }`}
                    >
                      {s.name}
                    </p>
                    <p
                      className={`truncate text-[10px] transition-opacity ${
                        done ? (s.degraded ? "text-amber-300/80" : "text-slate-500") : "opacity-0"
                      }`}
                    >
                      {s.detail}
                    </p>
                  </div>
                </li>
              );
            })}
          </ul>
        </motion.div>

        {/* Enter / skip */}
        <div className="mt-7 h-11">
          {allReady ? (
            <motion.button
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              onClick={finish}
              className="coolie-glass-blue group flex items-center gap-2 rounded-full px-6 py-3 text-[13px] font-semibold text-blue-50 transition hover:brightness-125"
            >
              Enter workroom
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
            </motion.button>
          ) : (
            <motion.button
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: reduce ? 0 : 1.4 }}
              onClick={finish}
              className="rounded-full px-4 py-2 text-[11px] font-medium tracking-wider text-slate-500 transition hover:text-slate-300"
            >
              SKIP INTRO · ESC
            </motion.button>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}
