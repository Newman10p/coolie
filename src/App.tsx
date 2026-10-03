import { useState } from "react";
import AuthGate from "./AuthGate";
import {
  AnimatePresence,
  motion,
  useReducedMotion,
  useScroll,
  useSpring,
  useTransform,
} from "motion/react";
import { Database, RotateCcw, RefreshCw } from "lucide-react";
import NavRail from "./components/NavRail";
import MissionControl from "./screens/MissionControl";
import Opportunities from "./screens/Opportunities";
import EvidenceRoom from "./screens/EvidenceRoom";
import AgentsRoom from "./screens/AgentsRoom";
import ToolsRoom from "./screens/ToolsRoom";
import DecisionCenter from "./screens/DecisionCenter";
import HistoryRoom from "./screens/HistoryRoom";
import IntelZone from "./components/IntelZone";
import DepartmentHall from "./components/DepartmentHall";
import LedgerPanel from "./components/LedgerPanel";
import WalletSetup from "./screens/WalletSetup";
import OrchestratorHUD from "./components/hud/OrchestratorHUD";
import SplashScreen from "./components/SplashScreen";
import { WhyDrawer } from "./research/ui";
import { ResearchProvider, useResearch } from "./research/store";

function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 140, damping: 30, mass: 0.3 });
  return (
    <motion.div
      style={{ scaleX }}
      className="fixed inset-x-0 top-0 z-[48] h-[2px] origin-left bg-gradient-to-r from-blue-500 via-cyan-300 to-blue-200 shadow-[0_0_12px_rgba(96,165,250,0.8)]"
    />
  );
}

function AmbientRoom() {
  const reduce = useReducedMotion();
  const { scrollY } = useScroll();
  const y1 = useTransform(scrollY, [0, 3000], [0, reduce ? 0 : 240]);
  const y2 = useTransform(scrollY, [0, 3000], [0, reduce ? 0 : -180]);
  const floorOpacity = useTransform(scrollY, [0, 600], [1, 0.4]);
  return (
    <div className="pointer-events-none fixed inset-0 z-0">
      <motion.div
        style={{ y: y1 }}
        className="absolute -top-40 right-0 h-[520px] w-[520px] rounded-full bg-blue-400/10 blur-[120px]"
      />
      <motion.div
        style={{ y: y2 }}
        className="absolute bottom-0 left-1/4 h-[420px] w-[620px] rounded-full bg-indigo-500/10 blur-[130px]"
      />
      <motion.div
        style={{ opacity: floorOpacity }}
        className="coolie-grid-floor absolute inset-x-0 bottom-0 h-[45vh]"
      />
    </div>
  );
}

const screens = {
  mission: MissionControl,
  opportunities: Opportunities,
  evidence: EvidenceRoom,
  agents: AgentsRoom,
  tools: ToolsRoom,
  decisions: DecisionCenter,
  history: HistoryRoom,
  intel: IntelZone,
  hall: DepartmentHall,
  ledger: LedgerPanel,
  wallet: WalletSetup,
  hud: OrchestratorHUD,
} as const;

function Shell() {
  const { view, go, connection, connectionError, services, refreshWorkspace } = useResearch();
  const [booted, setBooted] = useState(false);
  const Screen = screens[view];

  return (
    <div className="coolie-room relative min-h-screen overflow-x-clip">
      <AnimatePresence>
        {!booted && <SplashScreen key="splash" onDone={() => setBooted(true)} />}
      </AnimatePresence>

      {booted && (
        <>
          <AmbientRoom />
          <ScrollProgress />
          <NavRail view={view} onChange={go} />

          <main className="relative z-10 pt-24 sm:pt-28">
            <AnimatePresence mode="wait">
              <motion.div
                key={view}
                initial={{ opacity: 0, y: 18, filter: "blur(6px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                exit={{ opacity: 0, y: -12, filter: "blur(6px)" }}
                transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] as const }}
              >
                <Screen />
              </motion.div>
            </AnimatePresence>
          </main>

          {/* status footer */}
          <motion.div
            initial={{ y: 40, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.5 }}
            className="pointer-events-none fixed inset-x-0 bottom-0 z-[45] flex justify-center px-4 pb-4"
          >
            <div className="coolie-glass pointer-events-auto flex flex-wrap items-center justify-center gap-x-4 gap-y-1 rounded-full px-5 py-2 text-[11px] text-slate-300">
              <span className={`flex items-center gap-1.5 ${connection === "connected" ? "text-emerald-100" : "text-amber-100"}`}>
                <Database className={`h-3.5 w-3.5 ${connection === "connected" ? "text-emerald-300" : "text-amber-300"}`} />
                {connection === "checking"
                  ? "Connecting to Coolie backend…"
                  : connection === "connected"
                    ? `Backend connected · ${services.filter((service) => service.readiness === "ready").length}/${services.length} sectors ready · other panels use preview data`
                    : `Backend unavailable · preview data only${connectionError ? ` · ${connectionError}` : ""}`}
              </span>
              <button
                onClick={() => void refreshWorkspace()}
                className="flex items-center gap-1.5 rounded-full bg-white/5 px-2.5 py-1 ring-1 ring-white/10 transition hover:bg-white/10 hover:text-white"
                title="Refresh backend connection"
              >
                <RefreshCw className="h-3 w-3" /> Refresh
              </button>
              <button
                onClick={() => {
                  window.scrollTo({ top: 0 });
                  setBooted(false);
                }}
                className="flex items-center gap-1.5 rounded-full bg-white/5 px-2.5 py-1 ring-1 ring-white/10 transition hover:bg-white/10 hover:text-white"
                title="Replay boot sequence"
              >
                <RotateCcw className="h-3 w-3" /> Replay
              </button>
            </div>
          </motion.div>
        </>
      )}

      {/* universal Why? traceability drawer */}
      <WhyDrawer />
    </div>
  );
}

export default function App() {
  return (
    <AuthGate>
      <ResearchProvider>
        <Shell />
      </ResearchProvider>
    </AuthGate>
  );
}
