import { useLayoutEffect, useRef, useState } from "react";
import {
  motion,
  useMotionValue,
  useReducedMotion,
  useScroll,
  useTransform,
} from "motion/react";
import { Building2, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { businesses, type Business } from "../../data";

const statusMeta: Record<Business["status"], { label: string; cls: string; icon: typeof TrendingUp }> = {
  growing: { label: "Growing", cls: "text-emerald-300 bg-emerald-400/10 ring-emerald-400/25", icon: TrendingUp },
  stable: { label: "Stable", cls: "text-blue-300 bg-blue-400/10 ring-blue-400/25", icon: Minus },
  watch: { label: "Watch", cls: "text-amber-300 bg-amber-400/10 ring-amber-400/25", icon: TrendingDown },
};

function BusinessCard({ b, i }: { b: Business; i: number }) {
  const meta = statusMeta[b.status];
  const max = Math.max(...b.trend);
  return (
    <div className="coolie-metal coolie-metal-sheen w-[300px] flex-none rounded-2xl p-6 sm:w-[340px]">
      <div className="flex items-start justify-between">
        <div className="grid h-11 w-11 place-items-center rounded-xl bg-white/5 ring-1 ring-white/10">
          <Building2 className="h-5 w-5 text-blue-200" strokeWidth={1.6} />
        </div>
        <span className="font-mono text-[10px] text-slate-500">
          BIZ-0{i + 1}
        </span>
      </div>
      <p className="mt-5 text-lg font-semibold text-white">{b.name}</p>
      <p className="text-[12px] text-slate-500">{b.sector}</p>

      <div className="mt-5 flex h-16 items-end gap-1.5">
        {b.trend.map((t, k) => (
          <motion.span
            key={k}
            initial={{ scaleY: 0 }}
            whileInView={{ scaleY: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: k * 0.04 }}
            className="flex-1 origin-bottom rounded-sm bg-gradient-to-t from-blue-500/40 to-cyan-300/70"
            style={{ height: `${(t / max) * 100}%` }}
          />
        ))}
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3 border-t border-white/[0.07] pt-4">
        <div>
          <p className="text-[10px] uppercase tracking-wider text-slate-500">Revenue</p>
          <p className="text-lg font-semibold text-metal">{b.revenue}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider text-slate-500">Margin</p>
          <p className="text-lg font-semibold text-metal">{b.margin}</p>
        </div>
      </div>
      <span className={`mt-4 inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11px] font-semibold ring-1 ${meta.cls}`}>
        <meta.icon className="h-3.5 w-3.5" /> {meta.label}
      </span>
    </div>
  );
}

export default function BusinessTrack() {
  const ref = useRef<HTMLElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const [distance, setDistance] = useState(0);
  const dist = useMotionValue(0);

  useLayoutEffect(() => {
    const measure = () => {
      const el = trackRef.current;
      if (!el) return;
      const d = Math.max(0, el.scrollWidth - window.innerWidth + 32);
      setDistance(d);
      dist.set(d);
    };
    measure();
    const ro = new ResizeObserver(measure);
    if (trackRef.current) ro.observe(trackRef.current);
    window.addEventListener("resize", measure);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, [dist]);

  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end end"],
  });
  const x = useTransform([scrollYProgress, dist], ([p, d]: number[]) => -p * d);
  const bar = useTransform(scrollYProgress, [0, 1], [0, 1]);

  const header = (
    <div className="mx-auto mb-8 w-full max-w-6xl px-4">
      <p className="text-[11px] font-medium tracking-[0.3em] text-blue-300/70">
        BUSINESS PORTFOLIO · 6 HOLDINGS
      </p>
      <div className="mt-2 flex flex-wrap items-end justify-between gap-4">
        <h2 className="text-2xl font-semibold text-metal sm:text-3xl">
          Your holdings, in motion.
        </h2>
        {!reduce && (
          <div className="h-1 w-40 overflow-hidden rounded-full bg-white/10">
            <motion.div
              style={{ scaleX: bar }}
              className="h-full origin-left rounded-full bg-gradient-to-r from-blue-400 to-cyan-300"
            />
          </div>
        )}
      </div>
    </div>
  );

  if (reduce) {
    return (
      <section className="py-16">
        {header}
        <div className="flex gap-5 overflow-x-auto px-4 pb-4">
          {businesses.map((b, i) => (
            <BusinessCard key={b.id} b={b} i={i} />
          ))}
        </div>
      </section>
    );
  }

  return (
    <section
      ref={ref}
      className="relative"
      style={{ height: `calc(100vh + ${distance}px)` }}
    >
      <div className="sticky top-0 flex h-screen flex-col justify-center overflow-hidden">
        {header}
        <motion.div
          ref={trackRef}
          style={{ x }}
          className="flex w-max gap-5 pl-4 sm:pl-[max(1rem,calc((100vw-72rem)/2+1rem))]"
        >
          {businesses.map((b, i) => (
            <BusinessCard key={b.id} b={b} i={i} />
          ))}
          <div className="w-4 flex-none" />
        </motion.div>
      </div>
    </section>
  );
}
