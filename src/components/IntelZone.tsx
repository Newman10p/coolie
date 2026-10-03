import { motion, useReducedMotion, useScroll, useTransform } from "motion/react";
import { TrendingUp, TrendingDown, ArrowUpRight, Activity, ChevronsDown } from "lucide-react";
import { plates } from "../data";
import MoneyMatrix from "./MoneyMatrix";
import RevenueChart from "./RevenueChart";
import DossierGather from "./scroll/DossierGather";
import BusinessTrack from "./scroll/BusinessTrack";
import { DecisionsSection, SectorPulse } from "./scroll/DecisionsSection";
import { Reveal } from "./scroll/Reveal";

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08, delayChildren: 0.1 } },
};
const item = {
  hidden: { opacity: 0, y: 24 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] as const },
  },
};

export default function IntelZone() {
  const reduce = useReducedMotion();
  const { scrollY } = useScroll();
  // depth layers: plates drift faster than the matrix, header recedes
  const platesY = useTransform(scrollY, [0, 700], [0, reduce ? 0 : -70]);
  const matrixY = useTransform(scrollY, [0, 700], [0, reduce ? 0 : -25]);
  const headerY = useTransform(scrollY, [0, 400], [0, reduce ? 0 : 40]);
  const headerOpacity = useTransform(scrollY, [0, 320], [1, reduce ? 1 : 0.25]);
  const cueOpacity = useTransform(scrollY, [0, 160], [1, 0]);

  return (
    <>
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="mx-auto w-full max-w-6xl px-4 pb-10"
      >
        {/* Header */}
        <motion.div style={{ y: headerY, opacity: headerOpacity }}>
          <motion.div variants={item} className="mb-8">
            <p className="text-[11px] font-medium tracking-[0.3em] text-blue-300/70">
              EXECUTIVE WORKROOM · LIVE
            </p>
            <h1 className="mt-2 text-3xl font-semibold text-metal sm:text-4xl">
              Good morning, Owner.
            </h1>
            <p className="mt-2 max-w-xl text-sm text-slate-400">
              Four briefing plates are floating in the room. Coolie has reconciled
              overnight activity across all six sectors.
            </p>
          </motion.div>
        </motion.div>

        <div className="grid gap-5 lg:grid-cols-3">
          {/* Briefing plates */}
          <motion.div
            style={{ y: platesY }}
            className="grid gap-5 sm:grid-cols-2 lg:col-span-2"
          >
            {plates.map((p, i) => (
              <motion.div key={p.id} variants={item}>
                <div className={i % 2 === 0 ? "anim-float" : "anim-float-slow"}>
                  <motion.div
                    whileHover={{ y: -6, rotateX: 4, rotateY: -3 }}
                    transition={{ type: "spring", stiffness: 300, damping: 22 }}
                    style={{ transformPerspective: 900 }}
                    className="coolie-metal coolie-metal-sheen group rounded-2xl p-5"
                  >
                    <div className="flex items-start justify-between">
                      <span className="rounded-md bg-white/5 px-2 py-1 text-[9px] font-semibold tracking-[0.18em] text-blue-200/80 ring-1 ring-white/10">
                        {p.tag}
                      </span>
                      <ArrowUpRight className="h-4 w-4 text-slate-500 transition group-hover:text-blue-300" />
                    </div>
                    <p className="mt-4 text-[13px] font-medium text-slate-300">{p.title}</p>
                    <div className="mt-1 flex items-baseline gap-3">
                      <span className="text-3xl font-semibold text-metal">{p.value}</span>
                      <span
                        className={`flex items-center gap-0.5 text-xs font-semibold ${
                          p.positive ? "text-emerald-400" : "text-rose-400"
                        }`}
                      >
                        {p.positive ? (
                          <TrendingUp className="h-3.5 w-3.5" />
                        ) : (
                          <TrendingDown className="h-3.5 w-3.5" />
                        )}
                        {p.delta}
                      </span>
                    </div>
                    <p className="mt-3 text-[12px] leading-relaxed text-slate-500">
                      {p.summary}
                    </p>
                  </motion.div>
                </div>
              </motion.div>
            ))}
          </motion.div>

          {/* Money Matrix */}
          <motion.div style={{ y: matrixY }}>
            <motion.div variants={item} className="coolie-glass h-full rounded-2xl p-6">
              <MoneyMatrix />
            </motion.div>
          </motion.div>
        </div>

        {/* scroll cue */}
        <motion.div
          style={{ opacity: cueOpacity }}
          className="mt-10 flex flex-col items-center gap-1 text-[10px] font-medium tracking-[0.3em] text-slate-500"
        >
          SCROLL TO ENTER THE BRIEFING
          <motion.span
            animate={reduce ? {} : { y: [0, 6, 0] }}
            transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
          >
            <ChevronsDown className="h-4 w-4 text-blue-300/70" />
          </motion.span>
        </motion.div>
      </motion.div>

      {/* Scroll-linked dossier gathering */}
      <DossierGather />

      {/* Revenue + live stream */}
      <section className="mx-auto w-full max-w-6xl px-4 py-16">
        <div className="grid gap-5 lg:grid-cols-3">
          <Reveal dir="right" className="lg:col-span-2">
            <div className="coolie-metal h-full rounded-2xl p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-[11px] font-medium tracking-[0.2em] text-blue-300/70">
                    REVENUE TRAJECTORY · 12M
                  </p>
                  <p className="mt-1 text-xl font-semibold text-metal">
                    $58.0M{" "}
                    <span className="text-sm font-medium text-emerald-400">run-rate</span>
                  </p>
                </div>
                <div className="flex items-center gap-1.5 rounded-lg bg-emerald-400/10 px-2.5 py-1.5 text-[11px] font-semibold text-emerald-300 ring-1 ring-emerald-400/20">
                  <Activity className="h-3.5 w-3.5" /> Forecast beat +8.1%
                </div>
              </div>
              <div className="mt-4 h-28">
                <RevenueChart />
              </div>
            </div>
          </Reveal>

          <Reveal dir="left" delay={0.1}>
            <div className="coolie-glass-blue h-full rounded-2xl p-5">
              <p className="text-[11px] font-medium tracking-[0.2em] text-blue-200/80">
                LIVE STREAM
              </p>
              <ul className="mt-3 space-y-3 text-[12px]">
                {[
                  ["report.published", "Q1 filing draft ready", "text-blue-300"],
                  ["approval.created", "Vertex acquisition · $2.45M", "text-amber-300"],
                  ["finance.tx_recorded", "Solaris Energy · settled", "text-emerald-300"],
                  ["incident.blocked", "Broker order · Sharia gate", "text-rose-300"],
                ].map(([ev, txt, color], i) => (
                  <motion.li
                    key={ev}
                    initial={{ opacity: 0, x: -10 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.2 + i * 0.1 }}
                    className="flex items-start gap-2.5"
                  >
                    <span className={`mt-1.5 h-1.5 w-1.5 flex-none rounded-full bg-current ${color} anim-dot`} />
                    <div>
                      <p className="font-mono text-[10px] text-slate-500">{ev}</p>
                      <p className="text-slate-300">{txt}</p>
                    </div>
                  </motion.li>
                ))}
              </ul>
            </div>
          </Reveal>
        </div>
      </section>

      <DecisionsSection />
      <BusinessTrack />
      <SectorPulse />
      <div className="h-24" />
    </>
  );
}
