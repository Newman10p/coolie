import { useEffect, useRef, useState, type ReactNode } from "react";
import { animate, motion, useInView, useReducedMotion } from "motion/react";

type Dir = "up" | "down" | "left" | "right" | "none";

const offset = (dir: Dir, d = 36) => {
  switch (dir) {
    case "up":
      return { y: d };
    case "down":
      return { y: -d };
    case "left":
      return { x: d };
    case "right":
      return { x: -d };
    default:
      return {};
  }
};

/** Fades + slides children in once they enter the viewport. Transform/opacity only. */
export function Reveal({
  children,
  dir = "up",
  delay = 0,
  className,
  amount = 0.25,
}: {
  children: ReactNode;
  dir?: Dir;
  delay?: number;
  className?: string;
  amount?: number;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? { opacity: 0 } : { opacity: 0, ...offset(dir) }}
      whileInView={{ opacity: 1, x: 0, y: 0 }}
      viewport={{ once: true, amount }}
      transition={{
        duration: reduce ? 0.2 : 0.7,
        delay,
        ease: [0.22, 1, 0.36, 1] as const,
      }}
    >
      {children}
    </motion.div>
  );
}

/** Section heading with a metallic rule that draws in on scroll. */
export function SectionHeading({
  kicker,
  title,
  desc,
}: {
  kicker: string;
  title: string;
  desc?: string;
}) {
  return (
    <div className="mb-7">
      <Reveal>
        <div className="flex items-center gap-3">
          <p className="text-[11px] font-medium tracking-[0.3em] text-blue-300/70">
            {kicker}
          </p>
          <motion.span
            initial={{ scaleX: 0 }}
            whileInView={{ scaleX: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] as const, delay: 0.15 }}
            className="h-px flex-1 origin-left bg-gradient-to-r from-blue-300/40 via-white/10 to-transparent"
          />
        </div>
      </Reveal>
      <Reveal delay={0.08}>
        <h2 className="mt-2 text-2xl font-semibold text-metal sm:text-3xl">{title}</h2>
      </Reveal>
      {desc && (
        <Reveal delay={0.14}>
          <p className="mt-2 max-w-xl text-sm text-slate-400">{desc}</p>
        </Reveal>
      )}
    </div>
  );
}

/** Animated number that counts up when scrolled into view. */
export function CountUp({
  to,
  prefix = "",
  suffix = "",
  decimals = 0,
  duration = 1.6,
}: {
  to: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  duration?: number;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.6 });
  const reduce = useReducedMotion();
  const [val, setVal] = useState(0);

  useEffect(() => {
    if (!inView) return;
    if (reduce) {
      setVal(to);
      return;
    }
    const controls = animate(0, to, {
      duration,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setVal(v),
    });
    return () => controls.stop();
  }, [inView, to, duration, reduce]);

  return (
    <span ref={ref} className="tabular-nums">
      {prefix}
      {val.toLocaleString("en-US", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      })}
      {suffix}
    </span>
  );
}
