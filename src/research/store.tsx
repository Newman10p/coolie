import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  createResearchMission,
  fetchWorkspace,
  type CreateMissionInput,
  type ResearchMission,
  type ServiceStatus,
} from "./api";

export type View =
  | "mission" | "opportunities" | "evidence" | "agents"
  | "tools" | "decisions" | "history"
  | "intel" | "hall" | "ledger" | "wallet" | "hud";

interface Ctx {
  view: View;
  go: (v: View) => void;
  activeMission: string;
  setActiveMission: (id: string) => void;
  openOpp: string | null;
  openOpportunity: (id: string | null) => void;
  focusEvidence: string | null;
  /** jump to the Evidence Room scoped to one evidence item — the "Why?" spine */
  traceEvidence: (id: string) => void;
  traceSource: (id: string) => void;
  focusSource: string | null;
  why: WhyPayload | null;
  openWhy: (p: WhyPayload) => void;
  closeWhy: () => void;
  connection: "checking" | "connected" | "unavailable";
  connectionError: string | null;
  services: ServiceStatus[];
  missions: ResearchMission[];
  refreshWorkspace: () => Promise<void>;
  submitMission: (input: CreateMissionInput) => Promise<void>;
}

export interface WhyPayload {
  title: string;
  subject: string;
  value?: string;
  evidence: string[];
  assumptions: string[];
  reasoning?: string;
}

const C = createContext<Ctx | null>(null);

export function ResearchProvider({ children }: { children: ReactNode }) {
  const [view, setView] = useState<View>("intel");
  const [activeMission, setActiveMission] = useState("MSN-2026-0148");
  const [openOpp, openOpportunity] = useState<string | null>(null);
  const [focusEvidence, setFocusEvidence] = useState<string | null>(null);
  const [focusSource, setFocusSource] = useState<string | null>(null);
  const [why, setWhy] = useState<WhyPayload | null>(null);
  const [connection, setConnection] = useState<"checking" | "connected" | "unavailable">("checking");
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [missions, setMissions] = useState<ResearchMission[]>([]);

  const refreshWorkspace = useCallback(async () => {
    try {
      const workspace = await fetchWorkspace();
      setServices(workspace.services);
      setMissions(workspace.missions);
      setConnectionError(null);
      setConnection("connected");
    } catch (error) {
      setConnection("unavailable");
      setConnectionError(error instanceof Error ? error.message : "Could not read Coolie backend status.");
    }
  }, []);

  useEffect(() => {
    void refreshWorkspace();
  }, [refreshWorkspace]);

  const submitMission = useCallback(async (input: CreateMissionInput) => {
    await createResearchMission(input);
    await refreshWorkspace();
  }, [refreshWorkspace]);

  const go = useCallback((v: View) => {
    setView(v);
    if (v !== "evidence") setFocusEvidence(null);
    if (v !== "evidence") setFocusSource(null);
    window.scrollTo({ top: 0 });
  }, []);

  const traceEvidence = useCallback(
    (id: string) => {
      setFocusEvidence(id);
      setFocusSource(null);
      setView("evidence");
      window.scrollTo({ top: 0 });
    },
    []
  );

  const traceSource = useCallback((id: string) => {
    setFocusSource(id);
    setFocusEvidence(null);
    setView("evidence");
    window.scrollTo({ top: 0 });
  }, []);

  const value = useMemo(
    () => ({
      view, go, activeMission, setActiveMission, openOpp, openOpportunity,
      focusEvidence, traceEvidence, traceSource, focusSource, why,
      openWhy: setWhy, closeWhy: () => setWhy(null),
      connection, connectionError, services, missions, refreshWorkspace, submitMission,
    }),
    [view, go, activeMission, openOpp, focusEvidence, traceEvidence, traceSource, focusSource, why,
      connection, connectionError, services, missions, refreshWorkspace, submitMission]
  );

  return <C.Provider value={value}>{children}</C.Provider>;
}

export function useResearch() {
  const c = useContext(C);
  if (!c) throw new Error("useResearch outside provider");
  return c;
}
