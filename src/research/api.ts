import { getSupabaseAccessToken } from "../auth";

export interface ServiceStatus {
  service: string;
  liveness: boolean;
  startupComplete: boolean;
  readiness: "ready" | "not_ready";
  status: "healthy" | "degraded" | "stalled" | "dead" | "paused";
  reason: string;
}

export interface ResearchMission {
  missionId: string;
  objective: string;
  requestedBy: "orchestrator" | "strategy_manager" | "human";
  markets: string[];
  businessModels: string[];
  riskTolerance: "low" | "medium" | "high";
  requiredEvidenceLevel: "basic" | "standard" | "high";
  capitalLimit: { amount: number; currency: string } | null;
  timeLimitDays: number | null;
  status: string;
  createdAt: string;
}

export interface WorkspaceBootstrap {
  dataMode: "live";
  services: ServiceStatus[];
  missions: ResearchMission[];
}

export interface CreateMissionInput {
  objective: string;
  markets: string[];
  businessModels: string[];
  riskTolerance: "low" | "medium" | "high";
  requiredEvidenceLevel: "basic" | "standard" | "high";
  capitalLimit?: { amount: number; currency: string };
  timeLimitDays?: number;
}

export interface WalletAccount {
  walletId: string;
  purpose: "profits" | "spending";
  label: string;
  network: string;
  asset: string;
  address: string;
  custody: "watch_only";
  status: "active" | "inactive";
  createdBy: string;
  createdAt: string;
  updatedBy: string | null;
}

export interface RegisterWalletInput {
  purpose: WalletAccount["purpose"];
  label: string;
  network: string;
  asset: string;
  address: string;
}

export interface WalletWithdrawalRequest {
  requestId: string;
  walletId: string;
  destinationAddress: string;
  network: string;
  asset: string;
  amount: string;
  memo: string | null;
  requestedBy: string;
  requestedAt: string;
  status: "pending_review";
  execution: "not_executed";
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await getSupabaseAccessToken();
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (init?.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(path, {
    ...init,
    headers,
  });
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const message =
      payload && typeof payload === "object" && "error" in payload
        ? String(payload.error)
        : `Coolie API request failed (${response.status}).`;
    throw new Error(message);
  }
  return payload as T;
}

export const fetchWorkspace = () =>
  requestJson<WorkspaceBootstrap>("/api/ui/bootstrap");

export const createResearchMission = (input: CreateMissionInput) =>
  requestJson<ResearchMission>("/api/ui/missions", {
    method: "POST",
    body: JSON.stringify(input),
  });

export const fetchWallets = async () =>
  requestJson<{ dataMode: "live"; custody: "watch_only"; wallets: WalletAccount[] }>(
    "/api/wallets"
  );

export const registerWallet = (input: RegisterWalletInput) =>
  requestJson<WalletAccount>("/api/wallets", {
    method: "POST",
    body: JSON.stringify(input),
  });

export const deactivateWallet = (walletId: string) =>
  requestJson<WalletAccount>(`/api/wallets/${encodeURIComponent(walletId)}`, {
    method: "DELETE",
  });

export const updateWallet = (
  walletId: string,
  input: Partial<RegisterWalletInput>,
) =>
  requestJson<WalletAccount>(`/api/wallets/${encodeURIComponent(walletId)}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });

export const fetchWithdrawalRequests = async () =>
  requestJson<{ dataMode: "live"; withdrawalRequests: WalletWithdrawalRequest[] }>(
    "/api/wallets/withdrawals"
  );

export const requestWalletWithdrawal = (input: {
  walletId: string;
  destinationAddress: string;
  amount: string;
  memo?: string;
}) =>
  requestJson<WalletWithdrawalRequest>("/api/wallets/withdrawals", {
    method: "POST",
    body: JSON.stringify(input),
  });
