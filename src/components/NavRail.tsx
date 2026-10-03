import { useState } from "react";
import { AnimatePresence, motion, useScroll, useTransform } from "motion/react";
import {
  LayoutGrid,
  DoorOpen,
  ScrollText,
  Hexagon,
  ChevronDown,
  Radar,
  Boxes,
  FileSearch,
  Bot,
  Wrench,
  Gavel,
  History as HistIcon,
  Database,
  Command,
  Wallet,
} from "lucide-react";
import { cn } from "../utils/cn";
import type { View } from "../research/store";
import { MOCK_MODE } from "../research/data";

const researchItems: { id: View; label: string; icon: typeof Radar }[] = [
  { id: "mission", label: "Mission Control", icon: Radar },
  { id: "opportunities", label: "Opportunities", icon: Boxes },
  { id: "evidence", label: "Evidence Room", icon: FileSearch },
  { id: "agents", label: "Research Agents", icon: Bot },
  { id: "tools", label: "Tool Registry", icon: Wrench },
  { id: "decisions", label: "Decision Center", icon: Gavel },
  { id: "history", label: "History & Learning", icon: HistIcon },
];

const roomItems: { id: View; label: string; icon: typeof Radar }[] = [
  { id: "hall", label: "Department Hall", icon: DoorOpen },
  { id: "ledger", label: "Office Table", icon: ScrollText },
  { id: "wallet", label: "Crypto Wallet Setup", icon: Wallet },
];

export default function NavRail({
  view,
  onChange,
}: {
  view: View;
  onChange: (v: View) => void;
}) {
  const [open, setOpen] = useState<"research" | "rooms" | null>(null);
  const { scrollY } = useScroll();
  const scale = useTransform(scrollY, [0, 160], [1, 0.97]);
  const lift = useTransform(scrollY, [0, 160], [0, -6]);
  const shade = useTransform(scrollY, [0, 160], [0, 1]);
  const researchActive = researchItems.some((item) => item.id === view);
  const roomsActive = roomItems.some((item) => item.id === view);

  const menuButton = (id: "research" | "rooms", active: boolean, label: string, Icon: typeof Radar) => (
    <div className="relative flex-none" key={id}>
      <button
        onClick={() => setOpen((current) => (current === id ? null : id))}
        aria-expanded={open === id}
        aria-label={label}
        className={cn(
          "flex items-center gap-1.5 rounded-xl px-2.5 py-2 text-[12px] font-medium ring-1 transition sm:px-3",
          active
            ? "bg-blue-400/15 text-blue-100 ring-blue-300/25"
            : "bg-white/[0.04] text-slate-300 ring-white/10 hover:bg-white/[0.08]"
        )}
      >
        <Icon className="h-3.5 w-3.5" strokeWidth={1.9} />
        <span className="hidden sm:inline">{label}</span>
        <ChevronDown className={cn("h-3 w-3 transition", open === id && "rotate-180")} />
      </button>

      <AnimatePresence>
        {open === id && (
          <>
            <button
              aria-label="Close navigation menu"
              onClick={() => setOpen(null)}
              className="fixed inset-0 z-10 cursor-default"
            />
            <motion.div
              initial={{ opacity: 0, y: -8, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.97 }}
              transition={{ duration: 0.18 }}
              className="coolie-glass-blue absolute right-0 top-full z-20 mt-2 w-[min(19rem,calc(100vw-2rem))] rounded-2xl p-1.5"
            >
              <p className="px-2.5 py-1.5 text-[9px] font-bold tracking-[0.2em] text-blue-300/70">
                {id === "research" ? "RESEARCH OPERATING SYSTEM" : "SPATIAL WORKROOMS"}
              </p>
              {(id === "research" ? researchItems : roomItems).map((item) => (
                <button
                  key={item.id}
                  onClick={() => {
                    onChange(item.id);
                    setOpen(null);
                  }}
                  className={cn(
                    "flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2.5 text-left text-[12px] font-medium transition",
                    view === item.id
                      ? "bg-blue-400/15 text-white"
                      : "text-slate-300 hover:bg-white/[0.06]"
                  )}
                >
                  <item.icon className="h-3.5 w-3.5 text-blue-300" strokeWidth={1.8} />
                  <span className="flex-1">{item.label}</span>
                  {view === item.id && (
                    <span className="h-1.5 w-1.5 rounded-full bg-blue-300 shadow-[0_0_8px_rgba(96,165,250,0.8)]" />
                  )}
                </button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );

  return (
    <motion.div
      style={{ scale, y: lift }}
      className="pointer-events-none fixed inset-x-0 top-0 z-40 flex justify-center px-3 pt-3 sm:px-4 sm:pt-5"
    >
      <motion.nav
        initial={{ y: -40, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.3, ease: [0.22, 1, 0.36, 1] as const }}
        aria-label="Coolie main navigation"
        className="coolie-glass pointer-events-auto relative flex w-full max-w-5xl items-center gap-2 rounded-2xl px-2.5 py-2.5 sm:gap-3 sm:px-3.5"
      >
        <motion.span
          aria-hidden
          style={{ opacity: shade }}
          className="pointer-events-none absolute inset-0 -z-10 rounded-2xl bg-[#0b1320]/60 shadow-[0_18px_50px_rgba(0,0,0,0.5)]"
        />

        {/* Brand always returns to the welcoming Intel Zone. */}
        <button
          onClick={() => {
            onChange("intel");
            setOpen(null);
          }}
          aria-label="Coolie Intel Zone home"
          className="flex flex-none items-center gap-2.5 pr-1 sm:pr-2"
        >
          <span className="relative grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-blue-500/30 to-indigo-700/30 ring-1 ring-blue-300/30">
            <Hexagon className="h-5 w-5 text-blue-300" strokeWidth={1.6} />
            <span className="absolute h-1.5 w-1.5 rounded-full bg-blue-300 text-blue-300 anim-dot" />
          </span>
          <span className="hidden leading-tight lg:block">
            <span className="block text-[13px] font-semibold tracking-wide text-metal">COOLIE</span>
            <span className="block text-[9px] font-medium tracking-[0.2em] text-blue-300/70">
              INTEL ZONE
            </span>
          </span>
        </button>

        <span className="mx-0.5 hidden h-7 w-px bg-white/10 sm:block" />

        {/* Intel Zone is the primary landing page, not hidden in a menu. */}
        <button
          onClick={() => {
            onChange("intel");
            setOpen(null);
          }}
          className={cn(
            "flex flex-none items-center gap-1.5 rounded-xl px-2.5 py-2 text-[12px] font-semibold transition sm:px-3",
            view === "intel"
              ? "bg-blue-400/15 text-white ring-1 ring-blue-300/25"
              : "text-slate-300 hover:bg-white/[0.05] hover:text-white"
          )}
        >
          <LayoutGrid className="h-3.5 w-3.5 text-blue-300" />
          <span className="hidden md:inline">Intel Zone</span>
        </button>

        <div className="flex flex-1 items-center justify-end gap-1.5 sm:justify-start sm:gap-2">
          {menuButton("research", researchActive, "Research OS", Radar)}
          {menuButton("rooms", roomsActive, "Rooms", LayoutGrid)}
        </div>

        {MOCK_MODE && (
          <span
            title="Static backend-shaped dataset. No live agent or financial activity is generated."
            className="hidden flex-none items-center gap-1 rounded-lg bg-amber-400/10 px-2 py-1.5 text-[9px] font-bold tracking-wider text-amber-200 ring-1 ring-amber-400/25 md:flex"
          >
            <Database className="h-2.5 w-2.5" /> DEMO
          </span>
        )}

        {/* Conversational workspace stays one click away. */}
        <button
          onClick={() => {
            onChange("hud");
            setOpen(null);
          }}
          className={cn(
            "coolie-glass-blue group flex flex-none items-center gap-1.5 rounded-xl px-2.5 py-2 text-[12px] font-semibold transition hover:brightness-125 sm:px-3",
            view === "hud" && "ring-1 ring-blue-200/40"
          )}
        >
          <Command className="h-3.5 w-3.5 text-blue-200" />
          <span className="hidden sm:inline">Talk to Coolie</span>
        </button>
      </motion.nav>
    </motion.div>
  );
}
