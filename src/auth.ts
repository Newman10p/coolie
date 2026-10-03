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
}

export let supabaseAuthConfigured = false;
export let supabase: ReturnType<typeof createClient> | null = null;

function configureSupabase(url: string, anonKey: string) {
  supabase = createClient(url, anonKey, {
    auth: {
      storage: window.sessionStorage,
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
      flowType: "pkce",
    },
  });
  supabaseAuthConfigured = true;
}

export async function initializeSupabaseAuth(): Promise<boolean> {
  const response = await fetch("/api/setup/config", { headers: { Accept: "application/json" } });
  if (response.ok) {
    const settings: unknown = await response.json();
    if (
      settings &&
      typeof settings === "object" &&
      "configured" in settings &&
      settings.configured === true &&
      "supabaseUrl" in settings &&
      typeof settings.supabaseUrl === "string" &&
      "supabaseAnonKey" in settings &&
      typeof settings.supabaseAnonKey === "string"
    ) {
      configureSupabase(settings.supabaseUrl, settings.supabaseAnonKey);
      return true;
    }
    return false;
  }

  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
  const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
  if (supabaseUrl && supabaseAnonKey) {
    configureSupabase(supabaseUrl, supabaseAnonKey);
    return true;
  }
  throw new Error(`Coolie configuration could not be loaded (${response.status}).`);
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
  configureSupabase(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY);
}

export async function getSupabaseAccessToken(): Promise<string | null> {
  if (!supabase) return null;
  const { data, error } = await supabase.auth.getSession();
  if (error) throw error;
  return data.session?.access_token ?? null;
}
