import { useState } from "react";
import { motion } from "motion/react";
import {
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  Check,
  Clock,
  Ban,
  Filter,
} from "lucide-react";
import { ledger, type LedgerRow } from "../data";

const fmt = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const statusChip: Record<LedgerRow["status"], { cls: string; icon: typeof Check; label: string }> = {
  approved: { cls: "bg-emerald-400/10 text-emerald-300 ring-emerald-400/25", icon: Check, label: "Approved" },
  pending: { cls: "bg-amber-400/10 text-amber-300 ring-amber-400/25", icon: Clock, label: "Pending" },
  blocked: { cls: "bg-rose-400/10 text-rose-300 ring-rose-400/25", icon: Ban, label: "Blocked" },
};

const shariaChip: Record<LedgerRow["sharia"], { cls: string; icon: typeof ShieldCheck; label: string }> = {
  verified: { cls: "text-emerald-300", icon: ShieldCheck, label: "Verified" },
  review: { cls: "text-amber-300", icon: ShieldAlert, label: "In review" },
  flagged: { cls: "text-rose-300", icon: ShieldX, label: "Flagged" },
};

const filters = ["all", "pending", "approved", "blocked"] as const;

export default function LedgerPanel() {
  const [filter, setFilter] = useState<(typeof filters)[number]>("all");
  const rows = ledger.filter((r) => filter === "all" || r.status === filter);
  const total = ledger.reduce((s, r) => s + (r.status !== "blocked" ? r.amount : 0), 0);
  const pending = ledger.filter((r) => r.status === "pending").length;

  return (
    <div className="mx-auto w-full max-w-6xl px-4 pb-24">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-medium tracking-[0.3em] text-blue-300/70">
            OFFICE TABLE · FINANCIAL LEDGER
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-metal sm:text-4xl">
            Approvals & Compliance
          </h1>
          <p className="mt-2 max-w-xl text-sm text-slate-400">
            High-density transactional records on solid slate. Every entry passes
            the Sharia gate before it can settle.
          </p>
        </div>
        <div className="flex gap-3">
          <div className="coolie-solid rounded-xl px-4 py-3">
            <p className="text-[10px] uppercase tracking-wider text-slate-500">Net settled</p>
            <p className="text-lg font-semibold text-metal">{fmt.format(total)}</p>
          </div>
          <div className="coolie-solid rounded-xl px-4 py-3">
            <p className="text-[10px] uppercase tracking-wider text-slate-500">Awaiting sign</p>
            <p className="text-lg font-semibold text-amber-300">{pending}</p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="mb-4 flex items-center gap-2">
        <Filter className="h-4 w-4 text-slate-500" />
        {filters.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`rounded-lg px-3 py-1.5 text-[12px] font-medium capitalize transition ring-1 ${
              filter === f
                ? "bg-blue-400/15 text-blue-200 ring-blue-300/30"
                : "bg-white/[0.03] text-slate-400 ring-white/10 hover:text-slate-200"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Table (solid, maximum readability) */}
      <div className="coolie-solid overflow-hidden rounded-2xl">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead>
              <tr className="border-b border-white/10 text-[10px] uppercase tracking-wider text-slate-500">
                <th className="px-5 py-3 font-medium">Ref</th>
                <th className="px-5 py-3 font-medium">Entity</th>
                <th className="px-5 py-3 font-medium">Category</th>
                <th className="px-5 py-3 text-right font-medium">Amount</th>
                <th className="px-5 py-3 font-medium">Sharia Gate</th>
                <th className="px-5 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => {
                const sc = statusChip[r.status];
                const sh = shariaChip[r.sharia];
                const ShIcon = sh.icon;
                const ScIcon = sc.icon;
                return (
                  <motion.tr
                    key={r.id}
                    initial={{ opacity: 0, x: -16 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true, amount: 0.5 }}
                    transition={{ duration: 0.45, delay: i * 0.05 }}
                    className="border-b border-white/5 transition-colors last:border-0 hover:bg-white/[0.025]"
                  >
                    <td className="px-5 py-3.5 font-mono text-[12px] text-slate-400">{r.ref}</td>
                    <td className="px-5 py-3.5 font-medium text-slate-100">{r.entity}</td>
                    <td className="px-5 py-3.5 text-slate-400">{r.category}</td>
                    <td className="px-5 py-3.5 text-right font-semibold tabular-nums text-white">
                      {fmt.format(r.amount)}
                    </td>
                    <td className="px-5 py-3.5">
                      <span className={`flex items-center gap-1.5 text-[12px] font-medium ${sh.cls}`}>
                        <ShIcon className="h-4 w-4" /> {sh.label}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11px] font-semibold ring-1 ${sc.cls}`}>
                        <ScIcon className="h-3.5 w-3.5" /> {sc.label}
                      </span>
                    </td>
                  </motion.tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
      <p className="mt-3 flex items-center gap-1.5 text-[11px] text-slate-500">
        <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
        All figures are authoritative, timestamped and enforced server-side. The UI collects consent; it does not grant authorization.
      </p>
    </div>
  );
}
