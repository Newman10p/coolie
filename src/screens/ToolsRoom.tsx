import { motion } from "motion/react";
import { Wrench, ShieldAlert, Ban, CheckCircle2, ScrollText } from "lucide-react";
import { cn } from "../utils/cn";
import { tools } from "../research/data";
import { Chip, Field, Panel, MockBadge } from "../research/ui";
import { Reveal } from "../components/scroll/Reveal";

const riskTone = { LOW: "ok", MEDIUM: "info", HIGH: "bad" } as const;

export default function ToolsRoom() {
  return (
    <div className="mx-auto w-full max-w-7xl px-4 pb-28">
      <Reveal>
        <div className="mb-6">
          <p className="text-[11px] font-medium tracking-[0.3em] text-blue-300/70">
            TOOL REGISTRY · CONTROLLED CAPABILITY
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-metal sm:text-4xl">
            What are agents allowed to do?
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            Agents have no ambient capability. Every tool is registered, scoped to named agents,
            risk-rated, cost-accounted and audited. Consequential tools are blocked until approval
            is recorded server-side.
          </p>
        </div>
      </Reveal>

      <Reveal>
        <div className="mb-5 grid gap-3 sm:grid-cols-3">
          <div className="coolie-metal rounded-2xl p-4">
            <p className="text-2xl font-semibold text-metal">{tools.length}</p>
            <p className="text-[9px] font-bold uppercase tracking-wider text-slate-500">Registered tools</p>
          </div>
          <div className="coolie-metal rounded-2xl p-4 ring-1 ring-rose-400/25">
            <p className="flex items-center gap-2 text-2xl font-semibold text-rose-200">
              <Ban className="h-5 w-5" /> 1
            </p>
            <p className="text-[9px] font-bold uppercase tracking-wider text-slate-500">
              Hard-blocked without approval
            </p>
          </div>
          <div className="coolie-metal rounded-2xl p-4">
            <p className="text-2xl font-semibold text-metal">2,640</p>
            <p className="text-[9px] font-bold uppercase tracking-wider text-slate-500">Audited calls · 30d</p>
          </div>
        </div>
      </Reveal>

      <div className="grid gap-4 lg:grid-cols-2">
        {tools.map((t, i) => (
          <Reveal key={t.name} delay={i * 0.04}>
            <motion.div
              whileHover={{ y: -3 }}
              className={cn(
                "coolie-solid h-full rounded-2xl p-5 ring-1",
                t.available ? "ring-white/10" : "ring-rose-400/30"
              )}
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="inline-flex items-center gap-1.5 rounded-md bg-white/5 px-2 py-1 font-mono text-[10px] font-semibold text-blue-100 ring-1 ring-white/10">
                      <Wrench className="h-3 w-3 text-blue-300" /> {t.name}
                    </span>
                    <Chip tone={riskTone[t.risk]}>{t.risk} RISK</Chip>
                    {!t.available && <Chip tone="bad">DISABLED</Chip>}
                  </div>
                  <p className="mt-2 text-[11px] text-slate-500">{t.category}</p>
                </div>
                {t.available ? (
                  <CheckCircle2 className="h-4 w-4 flex-none text-emerald-400" />
                ) : (
                  <ShieldAlert className="h-4 w-4 flex-none text-rose-400" />
                )}
              </div>

              <div className="mt-4 grid grid-cols-2 gap-x-5 gap-y-3">
                <div className="col-span-2">
                  <Field label="Allowed agents">
                    {t.allowed.length ? (
                      <span className="flex flex-wrap gap-1">
                        {t.allowed.map((a) => (
                          <span key={a} className="rounded bg-white/5 px-1.5 py-0.5 font-mono text-[10px] text-slate-300 ring-1 ring-white/10">
                            {a}
                          </span>
                        ))}
                      </span>
                    ) : (
                      <span className="text-rose-300">No agent is authorised</span>
                    )}
                  </Field>
                </div>
                <Field label="Approval required">{t.approval}</Field>
                <Field label="Estimated cost" mono>{t.cost}</Field>
                <Field label="Rate limit" mono>{t.rate}</Field>
                <Field label="Recent calls" mono>{t.calls}</Field>
                <div className="col-span-2">
                  <Field label="Data policy">{t.policy}</Field>
                </div>
              </div>

              <div className="mt-4 border-t border-white/[0.07] pt-3">
                <p className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500">
                  <ScrollText className="h-3 w-3" /> Audit events
                </p>
                <ul className="mt-2 space-y-1">
                  {t.audit.map((a) => (
                    <li key={a} className="font-mono text-[10px] leading-relaxed text-slate-400">
                      {a}
                    </li>
                  ))}
                </ul>
              </div>
            </motion.div>
          </Reveal>
        ))}
      </div>

      <div className="mt-5">
        <Reveal>
          <Panel kicker="CAPABILITY BOUNDARY" title="Why this is visible" material="glass">
            <p className="text-[12px] leading-relaxed text-slate-400">
              Showing the tool registry makes the system's limits inspectable.{" "}
              <span className="font-mono text-rose-200">external.purchase</span> is registered but
              disabled: an agent attempted it at 14:44 without owner approval and was refused. That
              refusal is itself an audit event, which is exactly the behaviour you want to be able to
              see.
            </p>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <Chip tone="bad">BLOCKED · external.purchase</Chip>
              <Chip tone="warn">ESCALATED · enactor.dispatch requires dry-run</Chip>
              <Chip tone="ok">LOGGED · marketplace.scan retains snapshots</Chip>
              <MockBadge />
            </div>
          </Panel>
        </Reveal>
      </div>
    </div>
  );
}
