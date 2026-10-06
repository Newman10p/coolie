import { createClient } from "@supabase/supabase-js";

export interface DesktopSetup {
  SUPABASE_URL: string;
  SUPABASE_REGION: string;
  SUPABASE_ANON_KEY: string;
  SUPABASE_DB_PASSWORD: string;
  COOLIE_WORKSPACE_ID: string;
  FIRECRAWL_API_KEY: string;
  OPENSEARCH_URL: string;
  OPENSEARCH_INDEX: string;
  OPENSEARCH_USERNAME: string;
  OPENSEARCH_PASSWORD: string;
  COOLIE_RESEARCH_BROWSER_ALLOWED_HOSTS: string;
  COOLIE_AI_API_KEY: string;
  CLEAR_COOLIE_AI_API_KEY: boolean;
}

export interface SupabaseBootstrap {
  authConfigured: boolean;
  configured: boolean;
  aiKeyConfigured: boolean;
  supabaseUrl: string;
  supabaseAnonKey: string;
}

export let supabaseAuthConfigured = false;
export let supabase: ReturnType<typeof createClient> | null = null;
let configuredUrl: string | null = null;
let configuredAnonKey: string | null = null;

const authStorage = {
  getItem(key: string) {
    const storage = key.endsWith("-code-verifier") ? window.localStorage : window.sessionStorage;
    return storage.getItem(key);
  },
  setItem(key: string, value: string) {
    const storage = key.endsWith("-code-verifier") ? window.localStorage : window.sessionStorage;
    storage.setItem(key, value);
  },
  removeItem(key: string) {
    const storage = key.endsWith("-code-verifier") ? window.localStorage : window.sessionStorage;
    storage.removeItem(key);
  },
};

function configureSupabase(url: string, anonKey: string) {
  if (supabase && configuredUrl === url && configuredAnonKey === anonKey) return;
  supabase = createClient(url, anonKey, {
    auth: {
      // Email recovery links often open a new tab; share only PKCE verifiers across tabs.
      storage: authStorage,
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
      flowType: "pkce",
    },
  });
  configuredUrl = url;
  configuredAnonKey = anonKey;
  supabaseAuthConfigured = true;
}

export async function initializeSupabaseAuth(): Promise<SupabaseBootstrap> {
  const response = await fetch("/api/setup/config", { headers: { Accept: "application/json" } });
  if (response.ok) {
    const settings: unknown = await response.json();
    if (
      settings &&
      typeof settings === "object" &&
      "authConfigured" in settings &&
      typeof settings.authConfigured === "boolean" &&
      "configured" in settings &&
      typeof settings.configured === "boolean" &&
      "aiKeyConfigured" in settings &&
      typeof settings.aiKeyConfigured === "boolean" &&
      "supabaseUrl" in settings &&
      typeof settings.supabaseUrl === "string" &&
      "supabaseAnonKey" in settings &&
      typeof settings.supabaseAnonKey === "string"
    ) {
      if (settings.authConfigured) {
        configureSupabase(settings.supabaseUrl, settings.supabaseAnonKey);
      }
      return {
        authConfigured: settings.authConfigured,
        configured: settings.configured,
        aiKeyConfigured: settings.aiKeyConfigured,
        supabaseUrl: settings.supabaseUrl,
        supabaseAnonKey: settings.supabaseAnonKey,
      };
    }
    throw new Error("Coolie setup returned an invalid configuration response.");
  }

  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
  const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
  if (supabaseUrl && supabaseAnonKey) {
    configureSupabase(supabaseUrl, supabaseAnonKey);
    return {
      authConfigured: true,
      configured: true,
      aiKeyConfigured: false,
      supabaseUrl,
      supabaseAnonKey,
    };
  }
  throw new Error(`Coolie configuration could not be loaded (${response.status}).`);
}

export async function saveDesktopAuthSettings(supabaseUrl: string, supabaseAnonKey: string): Promise<void> {
  const response = await fetch("/api/setup/auth", {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ SUPABASE_URL: supabaseUrl, SUPABASE_ANON_KEY: supabaseAnonKey }),
  });
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    const message =
      payload && typeof payload === "object" && "error" in payload
        ? String(payload.error)
        : `Coolie connection setup failed (${response.status}).`;
    throw new Error(message);
  }
  configureSupabase(supabaseUrl, supabaseAnonKey);
}

export async function saveDesktopSetup(settings: DesktopSetup): Promise<void> {
  const response = await fetch("/api/setup/config", {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    const message =
      payload && typeof payload === "object" && "error" in payload
        ? String(payload.error)
        : `Coolie setup failed (${response.status}).`;
    throw new Error(message);
  }
  if (settings.SUPABASE_URL && settings.SUPABASE_ANON_KEY) {
    configureSupabase(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY);
  }
}

export async function getSupabaseAccessToken(): Promise<string | null> {
  if (!supabase) return null;
  const { data, error } = await supabase.auth.getSession();
  if (error) throw error;
  return data.session?.access_token ?? null;
}
