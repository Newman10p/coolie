import { useRef, useState } from "react";
import {
  motion,
  useMotionValue,
  useMotionValueEvent,
  useReducedMotion,
  useScroll,
  useTransform,
  type MotionValue,
} from "motion/react";
import { CheckCircle2, FolderClosed } from "lucide-react";

const docs = [
  { tag: "TREASURY", title: "Treasury Overnight", line: "$42.8M net · 2 signatures pending", from: [-270, -150, -18], color: "text-emerald-300" },
  { tag: "RESEARCH", title: "Market Intel Digest", line: "38 signals · EU pricing shift", from: [250, -170, 14], color: "text-blue-300" },
  { tag: "ENACTOR", title: "Execution Log", line: "37 jobs · 1 retry loop", from: [-290, 140, 10], color: "text-amber-300" },
  { tag: "SHARIA GATE", title: "Compliance Findings", line: "1 order blocked · score 98.2", from: [280, 150, -12], color: "text-rose-300" },
  { tag: "EVOLVER", title: "Strategy Delta", line: "Variant B · +6.2% improvement", from: [10, -250, 7], color: "text-violet-300" },
];

function GatherCard({
  progress,
  index,
  doc,
}: {
  progress: MotionValue<number>;
  index: number;
  doc: (typeof docs)[number];
}) {
  const start = index * 0.08;
  const end = 0.42 + index * 0.08;
  const [fx, fy, fr] = doc.from;
  const x = useTransform(progress, [start, end], [fx, index * 4 - 8]);
  const y = useTransform(progress, [start, end], [fy, -index * 7 + 14]);
  const rotate = useTransform(progress, [start, end], [fr, (index - 2) * 1.6]);
  const scale = useTransform(progress, [start, end], [0.88, 1]);
  const opacity = useTransform(progress, [0, start + 0.05], [0.55, 1]);

  return (
    <motion.div
      style={{ x, y, rotate, scale, opacity, zIndex: index }}
      className="coolie-metal absolute left-1/2 top-1/2 -ml-[130px] -mt-[80px] h-[160px] w-[260px] rounded-2xl p-4"
    >
      <div className="flex items-center justify-between">
        <span className={`text-[9px] font-semibold tracking-[0.2em] ${doc.color}`}>
          {doc.tag}
        </span>
        <FolderClosed className="h-4 w-4 text-slate-500" />
      </div>
      <p className="mt-3 text-[15px] font-semibold text-white">{doc.title}</p>
      <p className="mt-1 text-[12px] text-slate-400">{doc.line}</p>
      <div className="mt-4 space-y-1.5">
        <div className="h-1.5 w-full rounded-full bg-white/[0.07]" />
        <div className="h-1.5 w-4/5 rounded-full bg-white/[0.07]" />
        <div className="h-1.5 w-3/5 rounded-full bg-white/[0.07]" />
      </div>
    </motion.div>
  );
}

export default function DossierGather() {
  const ref = useRef<HTMLElement>(null);
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end end"],
  });
  const done = useMotionValue(1);
  const progress = reduce ? done : scrollYProgress;

  const [gathered, setGathered] = useState(reduce ? docs.length : 0);
  useMotionValueEvent(progress, "change", (v) => {
    const n = docs.filter((_, i) => v >= 0.42 + i * 0.08 - 0.02).length;
    setGathered(n);
  });

  const stampOpacity = useTransform(progress, [0.78, 0.88], [0, 1]);
  const stampScale = useTransform(progress, [0.78, 0.9], [1.3, 1]);
  const railScale = useTransform(progress, [0, 0.85], [0, 1]);
  const glow = useTransform(progress, [0.6, 0.9], [0, 0.6]);

  return (
    <section
      ref={ref}
      className={`relative overflow-x-clip ${reduce ? "" : "h-[240vh]"}`}
    >
      <div
        className={`${
          reduce ? "py-20" : "sticky top-0 h-screen"
        } flex items-center`}
      >
        <div className="mx-auto grid w-full max-w-6xl items-center gap-10 px-4 lg:grid-cols-[1fr_1.4fr]">
          {/* copy + progress rail */}
          <div className="flex gap-5">
            <div className="relative hidden w-px bg-white/10 sm:block">
              <motion.div
                style={{ scaleY: railScale }}
                className="absolute inset-0 origin-top bg-gradient-to-b from-blue-300 to-cyan-200 shadow-[0_0_10px_rgba(96,165,250,0.7)]"
              />
            </div>
            <div>
              <p className="text-[11px] font-medium tracking-[0.3em] text-blue-300/70">
                MORNING DOSSIER · SCROLL TO GATHER
              </p>
              <h2 className="mt-2 text-2xl font-semibold text-metal sm:text-3xl">
                Every sector reports in.
              </h2>
              <p className="mt-3 max-w-sm text-sm leading-relaxed text-slate-400">
                Overnight, each department filed its findings. As you scroll, Coolie
                gathers the scattered folders into a single briefing dossier.
              </p>
              <div className="mt-6 inline-flex items-center gap-3 rounded-xl bg-white/[0.04] px-4 py-2.5 ring-1 ring-white/10">
                <span className="text-2xl font-semibold tabular-nums text-metal">
                  {gathered}/{docs.length}
                </span>
                <span className="text-[11px] uppercase tracking-wider text-slate-500">
                  folders compiled
                </span>
              </div>
            </div>
          </div>

          {/* stage */}
          <div className="relative h-[420px] w-full sm:h-[460px]">
            <motion.div
              style={{ opacity: glow }}
              className="absolute left-1/2 top-1/2 h-72 w-72 -translate-x-1/2 -translate-y-1/2 rounded-full bg-blue-500/30 blur-[90px]"
            />
            {docs.map((d, i) => (
              <GatherCard key={d.title} progress={progress} index={i} doc={d} />
            ))}
            <motion.div
              style={{ opacity: stampOpacity, scale: stampScale }}
              className="coolie-glass-blue absolute bottom-2 left-1/2 z-10 flex -translate-x-1/2 items-center gap-2 whitespace-nowrap rounded-full px-4 py-2 text-[12px] font-semibold text-blue-100"
            >
              <CheckCircle2 className="h-4 w-4 text-emerald-300" />
              Daily Dossier compiled · 06:00
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  );
}
