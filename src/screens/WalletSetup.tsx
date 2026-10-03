import { useCallback, useEffect, useState, type FormEvent } from "react";
import { AlertTriangle, ArrowDownToLine, ArrowUpFromLine, Pencil, Shield, Wallet, X } from "lucide-react";
import {
  deactivateWallet,
  fetchWithdrawalRequests,
  fetchWallets,
  registerWallet,
  requestWalletWithdrawal,
  updateWallet,
  type RegisterWalletInput,
  type WalletAccount,
  type WalletWithdrawalRequest,
} from "../research/api";

const emptyForm: RegisterWalletInput = {
  purpose: "profits",
  label: "",
  network: "",
  asset: "",
  address: "",
};

export default function WalletSetup() {
  const [wallets, setWallets] = useState<WalletAccount[]>([]);
  const [withdrawalRequests, setWithdrawalRequests] = useState<WalletWithdrawalRequest[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [withdrawal, setWithdrawal] = useState({
    walletId: "",
    destinationAddress: "",
    amount: "",
    memo: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [result, requests] = await Promise.all([
        fetchWallets(),
        fetchWithdrawalRequests(),
      ]);
      setWallets(result.wallets);
      setWithdrawalRequests(requests.withdrawalRequests);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load wallet records.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const input = {
        ...form,
        label: form.label.trim(),
        network: form.network.trim().toLowerCase(),
        asset: form.asset.trim().toUpperCase(),
        address: form.address.trim(),
      };
      if (editingId) {
        await updateWallet(editingId, input);
      } else {
        await registerWallet(input);
      }
      setEditingId(null);
      setForm(emptyForm);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Wallet registration failed.");
    } finally {
      setSaving(false);
    }
  }

  async function deactivate(walletId: string) {
    if (!window.confirm("Remove this wallet from active use? Existing withdrawal requests remain on record.")) return;
    setError(null);
    try {
      await deactivateWallet(walletId);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not deactivate wallet.");
    }
  }

  function editWallet(account: WalletAccount) {
    setEditingId(account.walletId);
    setForm({
      purpose: account.purpose,
      label: account.label,
      network: account.network,
      asset: account.asset,
      address: account.address,
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function submitWithdrawal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await requestWalletWithdrawal({
        walletId: withdrawal.walletId,
        destinationAddress: withdrawal.destinationAddress.trim(),
        amount: withdrawal.amount,
        ...(withdrawal.memo.trim() ? { memo: withdrawal.memo.trim() } : {}),
      });
      setWithdrawal({ walletId: "", destinationAddress: "", amount: "", memo: "" });
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Withdrawal request failed.");
    } finally {
      setSaving(false);
    }
  }

  const activeWallets = wallets.filter((account) => account.status === "active");

  return (
    <main className="mx-auto w-full max-w-6xl px-4 pb-28">
      <header className="mb-7">
        <p className="text-[11px] font-medium tracking-[0.3em] text-blue-300/70">
          TREASURY · WATCH-ONLY ADDRESSES
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-metal sm:text-4xl">
          Crypto Wallet Setup
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400">
          Register separate public addresses for profit receipts and spending funds. Coolie records
          the intended purpose; it does not custody assets, verify balances, or send transactions.
        </p>
      </header>

      <section className="mb-6 grid gap-4 sm:grid-cols-2">
        <div className="coolie-solid rounded-2xl p-5">
          <div className="mb-3 flex items-center gap-2 text-emerald-200">
            <ArrowDownToLine className="h-4 w-4" />
            <h2 className="text-sm font-semibold">Profit receipts</h2>
          </div>
          <p className="text-xs leading-relaxed text-slate-400">
            An externally created address designated to receive profits. Verify the chain and
            address with your wallet provider before sharing it.
          </p>
          <p className="mt-3 text-2xl font-semibold text-white">
            {activeWallets.filter((account) => account.purpose === "profits").length}
            <span className="ml-2 text-xs font-normal text-slate-500">active addresses</span>
          </p>
        </div>
        <div className="coolie-solid rounded-2xl p-5">
          <div className="mb-3 flex items-center gap-2 text-amber-200">
            <ArrowUpFromLine className="h-4 w-4" />
            <h2 className="text-sm font-semibold">Spending funds</h2>
          </div>
          <p className="text-xs leading-relaxed text-slate-400">
            A separate externally controlled address intended for approved operational spending.
            Registration alone never authorizes a payment or transfer.
          </p>
          <p className="mt-3 text-2xl font-semibold text-white">
            {activeWallets.filter((account) => account.purpose === "spending").length}
            <span className="ml-2 text-xs font-normal text-slate-500">active addresses</span>
          </p>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
        <form onSubmit={(event) => void submit(event)} className="coolie-solid rounded-2xl p-5 sm:p-6">
          <div className="mb-5 flex items-center gap-2">
            <Wallet className="h-4 w-4 text-blue-200" />
            <h2 className="text-sm font-semibold text-slate-100">
              {editingId ? "Modify wallet details" : "Register public address"}
            </h2>
          </div>
          <label className="mb-4 block text-xs text-slate-300">
            Purpose
            <select
              className="mt-2 w-full rounded-lg border border-white/10 bg-slate-950/70 px-3 py-2.5 text-sm text-slate-100"
              value={form.purpose}
              onChange={(event) => setForm({ ...form, purpose: event.target.value as RegisterWalletInput["purpose"] })}
            >
              <option value="profits">Profit receipts</option>
              <option value="spending">Spending funds</option>
            </select>
          </label>
          <label className="mb-4 block text-xs text-slate-300">
            Display label
            <input required maxLength={80} value={form.label} onChange={(event) => setForm({ ...form, label: event.target.value })} className="mt-2 w-full rounded-lg border border-white/10 bg-slate-950/70 px-3 py-2.5 text-sm text-white" placeholder="e.g. Treasury receive" />
          </label>
          <div className="mb-4 grid gap-3 sm:grid-cols-2">
            <label className="block text-xs text-slate-300">
              Network identifier
              <input required value={form.network} onChange={(event) => setForm({ ...form, network: event.target.value })} className="mt-2 w-full rounded-lg border border-white/10 bg-slate-950/70 px-3 py-2.5 text-sm text-white" placeholder="e.g. ethereum-mainnet" />
            </label>
            <label className="block text-xs text-slate-300">
              Asset ticker
              <input required maxLength={16} value={form.asset} onChange={(event) => setForm({ ...form, asset: event.target.value })} className="mt-2 w-full rounded-lg border border-white/10 bg-slate-950/70 px-3 py-2.5 text-sm uppercase text-white" placeholder="e.g. USDC" />
            </label>
          </div>
          <label className="mb-5 block text-xs text-slate-300">
            Public wallet address
            <input required minLength={20} maxLength={160} autoComplete="off" spellCheck={false} value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} className="mt-2 w-full rounded-lg border border-white/10 bg-slate-950/70 px-3 py-2.5 font-mono text-xs text-white" placeholder="Paste a public address only" />
          </label>
          <button disabled={saving} className="w-full rounded-lg bg-blue-300 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-blue-200 disabled:opacity-50">
            {saving ? "Saving address…" : editingId ? "Save wallet changes" : "Register watch-only address"}
          </button>
          {editingId && (
            <button
              type="button"
              onClick={() => { setEditingId(null); setForm(emptyForm); }}
              className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-lg px-4 py-2 text-xs text-slate-400 hover:text-white"
            >
              <X className="h-3.5 w-3.5" /> Cancel edit
            </button>
          )}
          <p className="mt-3 text-[11px] leading-relaxed text-slate-500">
            Never enter a seed phrase, private key, password, or signing token here. Checksum and
            chain-specific ownership verification are not provided yet.
          </p>
        </form>

        <section className="coolie-solid rounded-2xl p-5 sm:p-6">
          <div className="mb-5 flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold text-slate-100">Registered addresses</h2>
            <span className="rounded-full bg-blue-300/10 px-2.5 py-1 text-[10px] text-blue-200 ring-1 ring-blue-200/15">
              {loading ? "Loading…" : "Workspace scoped"}
            </span>
          </div>
          {error && (
            <p role="alert" className="mb-4 rounded-lg border border-red-300/20 bg-red-950/30 px-3 py-2 text-xs text-red-200">
              {error}
            </p>
          )}
          {loading ? (
            <p className="py-8 text-center text-xs text-slate-500">Loading saved wallet metadata…</p>
          ) : wallets.length === 0 ? (
            <p className="rounded-xl border border-dashed border-white/10 px-4 py-8 text-center text-xs text-slate-500">
              No public wallet addresses registered for this workspace.
            </p>
          ) : (
            <div className="space-y-3">
              {wallets.map((account) => (
                <article key={account.walletId} className="rounded-xl border border-white/[0.08] bg-slate-950/35 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={`h-1.5 w-1.5 rounded-full ${account.status === "active" ? "bg-emerald-300" : "bg-slate-500"}`} />
                        <h3 className="text-sm font-medium text-white">{account.label}</h3>
                      </div>
                      <p className="mt-1 pl-3.5 text-[10px] uppercase tracking-wider text-slate-500">
                        {account.purpose} · {account.network} · {account.asset} · {account.status}
                      </p>
                    </div>
                    {account.status === "active" && (
                      <div className="flex items-center gap-3">
                        <button onClick={() => editWallet(account)} className="inline-flex items-center gap-1 text-[11px] text-blue-200/80 hover:text-blue-100">
                          <Pencil className="h-3 w-3" /> Edit
                        </button>
                        <button onClick={() => void deactivate(account.walletId)} className="text-[11px] text-amber-200/80 underline decoration-amber-200/30 underline-offset-4 hover:text-amber-100">
                          Remove
                        </button>
                      </div>
                    )}
                  </div>
                  <code className="mt-3 block break-all rounded-lg bg-black/25 px-3 py-2 text-[11px] text-slate-300">
                    {account.address}
                  </code>
                  <p className="mt-2 flex items-center gap-1.5 text-[10px] text-slate-500">
                    <Shield className="h-3 w-3 text-blue-300/70" /> Watch-only · no balance or transaction data
                  </p>
                </article>
              ))}
            </div>
          )}
        </section>
      </section>

      <section className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
        <form onSubmit={(event) => void submitWithdrawal(event)} className="coolie-solid rounded-2xl p-5 sm:p-6">
          <div className="mb-2 flex items-center gap-2">
            <ArrowUpFromLine className="h-4 w-4 text-amber-200" />
            <h2 className="text-sm font-semibold text-slate-100">Request a withdrawal</h2>
          </div>
          <p className="mb-5 text-xs leading-relaxed text-slate-500">
            Submits a review request only. No wallet is signed, and no funds move from Coolie.
          </p>
          <label className="mb-4 block text-xs text-slate-300">
            Spending wallet
            <select
              required
              value={withdrawal.walletId}
              onChange={(event) => setWithdrawal({ ...withdrawal, walletId: event.target.value })}
              className="mt-2 w-full rounded-lg border border-white/10 bg-slate-950/70 px-3 py-2.5 text-sm text-slate-100"
            >
              <option value="">Select an active spending wallet</option>
              {activeWallets.filter((wallet) => wallet.purpose === "spending").map((wallet) => (
                <option key={wallet.walletId} value={wallet.walletId}>
                  {wallet.label} · {wallet.asset} on {wallet.network}
                </option>
              ))}
            </select>
          </label>
          <label className="mb-4 block text-xs text-slate-300">
            Destination public address
            <input required minLength={20} maxLength={160} autoComplete="off" spellCheck={false} value={withdrawal.destinationAddress} onChange={(event) => setWithdrawal({ ...withdrawal, destinationAddress: event.target.value })} className="mt-2 w-full rounded-lg border border-white/10 bg-slate-950/70 px-3 py-2.5 font-mono text-xs text-white" />
          </label>
          <div className="mb-4 grid gap-3 sm:grid-cols-2">
            <label className="block text-xs text-slate-300">
              Amount
              <input required inputMode="decimal" value={withdrawal.amount} onChange={(event) => setWithdrawal({ ...withdrawal, amount: event.target.value })} className="mt-2 w-full rounded-lg border border-white/10 bg-slate-950/70 px-3 py-2.5 text-sm text-white" placeholder="0.00" />
            </label>
            <label className="block text-xs text-slate-300">
              Memo (optional)
              <input maxLength={280} value={withdrawal.memo} onChange={(event) => setWithdrawal({ ...withdrawal, memo: event.target.value })} className="mt-2 w-full rounded-lg border border-white/10 bg-slate-950/70 px-3 py-2.5 text-sm text-white" placeholder="Purpose / reference" />
            </label>
          </div>
          <button disabled={saving || !activeWallets.some((wallet) => wallet.purpose === "spending")} className="w-full rounded-lg border border-amber-200/20 bg-amber-300/10 px-4 py-3 text-sm font-semibold text-amber-100 transition hover:bg-amber-300/15 disabled:opacity-40">
            {saving ? "Submitting request…" : "Submit for manual review"}
          </button>
          <p className="mt-3 text-[10px] leading-relaxed text-slate-500">
            Confirm network and address independently. Requests are immutable and are not a transfer authorization.
          </p>
        </form>

        <section className="coolie-solid rounded-2xl p-5 sm:p-6">
          <h2 className="mb-4 text-sm font-semibold text-slate-100">Withdrawal requests</h2>
          {withdrawalRequests.length === 0 ? (
            <p className="rounded-xl border border-dashed border-white/10 px-4 py-8 text-center text-xs text-slate-500">
              No withdrawal requests submitted.
            </p>
          ) : (
            <div className="space-y-3">
              {withdrawalRequests.map((request) => (
                <article key={request.requestId} className="rounded-xl border border-white/[0.08] bg-slate-950/35 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-mono text-xs text-white">{request.amount} {request.asset}</p>
                    <span className="rounded-full bg-amber-300/10 px-2 py-1 text-[10px] text-amber-200">
                      {request.status.replace("_", " ")} · not executed
                    </span>
                  </div>
                  <p className="mt-2 text-[10px] text-slate-500">{request.network} · from wallet {request.walletId}</p>
                  <code className="mt-2 block break-all text-[10px] text-slate-400">{request.destinationAddress}</code>
                  {request.memo && <p className="mt-2 text-[10px] text-slate-500">{request.memo}</p>}
                </article>
              ))}
            </div>
          )}
        </section>
      </section>

      <aside className="mt-6 flex gap-3 rounded-xl border border-amber-200/15 bg-amber-950/15 p-4 text-xs leading-relaxed text-amber-100/70">
        <AlertTriangle className="mt-0.5 h-4 w-4 flex-none text-amber-200" />
        <span>
          Crypto transfers can be irreversible. Before depositing funds, confirm the network,
          asset contract, and address independently. This setup does not create a wallet, confirm
          address ownership, display balances, allocate capital, or execute withdrawals.
        </span>
      </aside>
    </main>
  );
}
