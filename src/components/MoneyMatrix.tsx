import { motion } from "motion/react";
import { matrix } from "../data";

const R = 78;
const C = 2 * Math.PI * R;

export default function MoneyMatrix() {
  let offset = 0;
  const total = matrix.reduce((s, m) => s + m.value, 0);

  return (
    <div className="relative flex flex-col items-center">
      <div className="relative h-[210px] w-[210px]">
        {/* metallic rings */}
        <div className="absolute inset-0 rounded-full border border-white/10 anim-ring-spin" style={{ borderStyle: "dashed" }} />
        <div className="absolute inset-3 rounded-full border border-blue-300/15 anim-ring-spin-rev" />
        <div className="absolute inset-6 rounded-full bg-gradient-to-br from-slate-700/40 to-slate-900/60 shadow-[inset_0_2px_10px_rgba(0,0,0,0.6)]" />

        {/* svg donut */}
        <svg viewBox="0 0 200 200" className="absolute inset-0 -rotate-90">
          <circle cx="100" cy="100" r={R} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="14" />
          {matrix.map((m) => {
            const len = (m.value / total) * C;
            const seg = (
              <motion.circle
                key={m.label}
                cx="100"
                cy="100"
                r={R}
                fill="none"
                stroke={m.color}
                strokeWidth="14"
                strokeLinecap="round"
                strokeDasharray={`${len} ${C - len}`}
                strokeDashoffset={-offset}
                initial={{ opacity: 0, strokeDasharray: `0 ${C}` }}
                animate={{ opacity: 1, strokeDasharray: `${len} ${C - len}` }}
                transition={{ duration: 1, delay: 0.2, ease: "easeOut" }}
                style={{ filter: `drop-shadow(0 0 6px ${m.color}88)` }}
              />
            );
            offset += len + 4;
            return seg;
          })}
        </svg>

        {/* center readout */}
        <div className="absolute inset-0 grid place-items-center text-center">
          <div>
            <p className="text-[10px] font-medium tracking-[0.25em] text-blue-300/70">
              MONEY MATRIX
            </p>
            <p className="mt-1 text-3xl font-semibold text-metal">$42.8M</p>
            <p className="text-[11px] text-emerald-400">▲ 6.4% allocation</p>
          </div>
        </div>
      </div>

      {/* legend */}
      <div className="mt-5 grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3">
        {matrix.map((m) => (
          <div key={m.label} className="flex items-center gap-2 text-[12px]">
            <span
              className="h-2.5 w-2.5 rounded-sm"
              style={{ background: m.color, boxShadow: `0 0 8px ${m.color}` }}
            />
            <span className="text-slate-300">{m.label}</span>
            <span className="ml-auto font-medium text-slate-400">{m.value}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
