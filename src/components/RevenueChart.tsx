import { motion } from "motion/react";
import { revenueSeries } from "../data";

export default function RevenueChart() {
  const max = Math.max(...revenueSeries);
  const min = Math.min(...revenueSeries);
  const w = 320;
  const h = 90;
  const pts = revenueSeries.map((v, i) => {
    const x = (i / (revenueSeries.length - 1)) * w;
    const y = h - ((v - min) / (max - min)) * (h - 12) - 6;
    return [x, y];
  });
  const line = pts.map((p, i) => (i === 0 ? `M${p[0]},${p[1]}` : `L${p[0]},${p[1]}`)).join(" ");
  const area = `${line} L${w},${h} L0,${h} Z`;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-full w-full" preserveAspectRatio="none">
      <defs>
        <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#60a5fa" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#60a5fa" stopOpacity="0" />
        </linearGradient>
      </defs>
      <motion.path
        d={area}
        fill="url(#rev)"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true, amount: 0.5 }}
        transition={{ duration: 1, delay: 0.4 }}
      />
      <motion.path
        d={line}
        fill="none"
        stroke="#60a5fa"
        strokeWidth="2"
        strokeLinecap="round"
        style={{ filter: "drop-shadow(0 0 5px rgba(96,165,250,0.6))" }}
        initial={{ pathLength: 0 }}
        whileInView={{ pathLength: 1 }}
        viewport={{ once: true, amount: 0.5 }}
        transition={{ duration: 1.2, ease: "easeInOut" }}
      />
      {pts.map((p, i) => (
        <circle key={i} cx={p[0]} cy={p[1]} r={i === pts.length - 1 ? 3.5 : 0} fill="#bfdbfe" />
      ))}
    </svg>
  );
}
