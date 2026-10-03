import { motion } from "motion/react";
import { Brain, Loader2, Check, Sparkles } from "lucide-react";
import type { ToolCall } from "../../data";

export type Trace =
  | { kind: "thinking"; text: string }
  | { kind: "tool"; tool: ToolCall; state: "running" | "done" };

export default function CognitionPanel({
  traces,
  busy,
}: {
  traces: Trace[];
  busy: boolean;
}) {
  return (
    <div className="coolie-glass-blue rounded-2xl p-5">
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-medium tracking-[0.22em] text-blue-200/80">
          DEMO REASONING TRACE
        </p>
        <span className="flex items-center gap-1.5 font-mono text-[10px] text-blue-300/70">
          {busy ? (
            <>
              <Loader2 className="h-3 w-3 animate-spin" /> WORKING
            </>
          ) : (
            <>
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 text-emerald-400 anim-dot" />
              IDLE
            </>
          )}
        </span>
      </div>

      {traces.length === 0 ? (
        <div className="mt-4 flex flex-col items-center rounded-xl bg-black/25 px-4 py-7 text-center ring-1 ring-white/[0.06]">
          <Brain className="h-6 w-6 text-blue-300/50" strokeWidth={1.5} />
          <p className="mt-2.5 text-[12px] text-slate-400">
            Ask the Orchestrator anything. Every step it takes shows up here.
          </p>
        </div>
      ) : (
        <ul className="mt-3.5 space-y-2.5">
          {traces.map((t, i) => (
            <motion.li
              key={i}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.35 }}
              className="flex items-start gap-2.5 rounded-lg bg-black/25 px-3 py-2.5 ring-1 ring-white/[0.06]"
            >
              {t.kind === "thinking" ? (
                <>
                  <Sparkles className="mt-0.5 h-3.5 w-3.5 flex-none text-blue-300" />
                  <p className="text-[12px] leading-snug text-slate-300">{t.text}</p>
                </>
              ) : (
                <>
                  <span className="mt-0.5 grid h-3.5 w-3.5 flex-none place-items-center">
                    {t.state === "done" ? (
                      <Check className="h-3.5 w-3.5 text-emerald-300" />
                    ) : (
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-300" />
                    )}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline justify-between gap-2">
                      <p className="truncate font-mono text-[11px] text-blue-100">
                        {t.tool.name}
                      </p>
                      {t.state === "done" && (
                        <span className="flex-none font-mono text-[10px] text-slate-500">
                          {t.tool.ms}ms
                        </span>
                      )}
                    </div>
                    <p className="mt-0.5 truncate text-[11px] text-slate-400">
                      {t.tool.detail}
                    </p>
                    {t.state === "running" && (
                      <span className="mt-1.5 block h-0.5 w-full overflow-hidden rounded-full bg-white/10">
                        <motion.span
                          initial={{ x: "-100%" }}
                          animate={{ x: "100%" }}
                          transition={{ duration: 0.9, repeat: Infinity, ease: "linear" }}
                          className="block h-full w-1/2 bg-blue-400"
                        />
                      </span>
                    )}
                  </div>
                </>
              )}
            </motion.li>
          ))}
        </ul>
      )}
    </div>
  );
}
