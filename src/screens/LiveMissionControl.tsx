import { useState, type FormEvent } from "react";
import { Activity, Plus, RefreshCw, ShieldCheck } from "lucide-react";
import { useResearch } from "../research/store";

export default function LiveMissionControl() {
  const { connectionError, missions, services, refreshWorkspace, submitMission } = useResearch();
  const [objective, setObjective] = useState("");
  const [market, setMarket] = useState("");
  const [businessModel, setBusinessModel] = useState("");
  const [riskTolerance, setRiskTolerance] = useState<"low" | "medium" | "high">("medium");
  const [evidenceLevel, setEvidenceLevel] = useState<"basic" | "standard" | "high">("standard");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await submitMission({
        objective: objective.trim(),
        markets: [market.trim()],
        businessModels: [businessModel.trim()],
        riskTolerance,
        requiredEvidenceLevel: evidenceLevel,
      });
      setObjective("");
      setMarket("");
      setBusinessModel("");
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "Mission creation failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-7xl px-4 pb-40 sm:pb-32">
      <header className="mb-6">
        <p className="text-[11px] font-medium tracking-[0.3em] text-blue-300/70">
          LIVE RESEARCH ROOM · CONNECTED BACKEND DATA
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-metal sm:text-4xl">Research missions</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          This view reads the composed Research Room service. Mission creation is submitted to the
          backend and remains subject to its policies and system failsafe.
        </p>
      </header>

      <section className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-label="Live sector readiness">
        {services.map((service) => (
          <article key={service.service} className="coolie-metal rounded-xl p-4">
            <div className="flex items-center justify-between gap-2">
              <p className="truncate text-xs font-semibold text-slate-100">{service.service.replace(/_/g, " ")}</p>
              <span className={`h-2 w-2 rounded-full ${service.readiness === "ready" ? "bg-emerald-400" : "bg-amber-400"}`} />
            </div>
            <p className="mt-2 text-[10px] text-slate-400">
              {service.readiness.replace("_", " ")} · {service.status}
            </p>
            {service.reason && <p className="mt-1 line-clamp-2 text-[10px] text-slate-500">{service.reason}</p>}
          </article>
        ))}
      </section>

      <section className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        <div className="coolie-metal rounded-2xl p-5 sm:p-6">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-metal">Persisted missions</h2>
              <p className="mt-1 text-xs text-slate-400">{missions.length} mission(s) returned by Research Room</p>
            </div>
            <button
              type="button"
              onClick={() => void refreshWorkspace()}
              className="flex items-center gap-2 rounded-lg bg-white/5 px-3 py-2 text-xs text-slate-200 ring-1 ring-white/10 hover:bg-white/10"
            >
              <RefreshCw className="h-3.5 w-3.5" /> Refresh
            </button>
          </div>
          {connectionError && <p className="mb-3 text-xs text-rose-300">{connectionError}</p>}
          {missions.length === 0 ? (
            <div className="rounded-xl bg-black/20 p-5 text-sm text-slate-400 ring-1 ring-white/10">
              No persisted missions are available from the connected Research Room.
            </div>
          ) : (
            <ul className="space-y-3">
              {missions.map((mission) => (
                <li key={mission.missionId} className="rounded-xl bg-black/20 p-4 ring-1 ring-white/10">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-mono text-[10px] text-blue-200">{mission.missionId}</span>
                    <span className="rounded-full bg-blue-400/10 px-2.5 py-1 text-[10px] text-blue-100 ring-1 ring-blue-300/20">
                      {mission.status.replace(/_/g, " ")}
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-relaxed text-slate-100">{mission.objective}</p>
                  <p className="mt-2 text-[11px] text-slate-400">
                    {mission.markets.join(", ")} · {mission.businessModels.join(", ")} · {mission.riskTolerance} risk
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>

        <form onSubmit={handleSubmit} className="coolie-metal space-y-4 rounded-2xl p-5 sm:p-6">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-semibold text-metal">
              <Plus className="h-4 w-4 text-blue-300" /> Create a mission
            </h2>
            <p className="mt-1 text-xs text-slate-400">Requires authenticated workspace write access.</p>
          </div>
          <label className="block text-xs text-slate-300">
            Objective
            <textarea
              required
              minLength={4}
              value={objective}
              onChange={(event) => setObjective(event.target.value)}
              className="mt-1.5 min-h-24 w-full rounded-lg bg-black/30 p-3 text-sm text-white outline-none ring-1 ring-white/10 focus:ring-blue-300/50"
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-xs text-slate-300">
              Market / geography
              <input required value={market} onChange={(event) => setMarket(event.target.value)} className="mt-1.5 w-full rounded-lg bg-black/30 p-2.5 text-sm text-white outline-none ring-1 ring-white/10 focus:ring-blue-300/50" />
            </label>
            <label className="block text-xs text-slate-300">
              Business model
              <input required value={businessModel} onChange={(event) => setBusinessModel(event.target.value)} className="mt-1.5 w-full rounded-lg bg-black/30 p-2.5 text-sm text-white outline-none ring-1 ring-white/10 focus:ring-blue-300/50" />
            </label>
            <label className="block text-xs text-slate-300">
              Risk tolerance
              <select value={riskTolerance} onChange={(event) => setRiskTolerance(event.target.value as typeof riskTolerance)} className="mt-1.5 w-full rounded-lg bg-slate-950 p-2.5 text-sm text-white ring-1 ring-white/10">
                <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>
              </select>
            </label>
            <label className="block text-xs text-slate-300">
              Evidence level
              <select value={evidenceLevel} onChange={(event) => setEvidenceLevel(event.target.value as typeof evidenceLevel)} className="mt-1.5 w-full rounded-lg bg-slate-950 p-2.5 text-sm text-white ring-1 ring-white/10">
                <option value="basic">Basic</option><option value="standard">Standard</option><option value="high">High</option>
              </select>
            </label>
          </div>
          {error && <p role="alert" className="text-xs text-rose-300">{error}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-400/15 px-4 py-2.5 text-xs font-semibold text-blue-100 ring-1 ring-blue-300/25 transition hover:bg-blue-400/25 disabled:cursor-wait disabled:opacity-50"
          >
            <ShieldCheck className="h-4 w-4" /> {submitting ? "Submitting…" : "Submit to Research Room"}
          </button>
          <div className="flex items-start gap-2 text-[10px] leading-relaxed text-slate-500">
            <Activity className="mt-0.5 h-3.5 w-3.5 flex-none text-amber-300" />
            Submission creates a real backend mission. This form does not start external research or execute tools.
          </div>
        </form>
      </section>
    </div>
  );
}
