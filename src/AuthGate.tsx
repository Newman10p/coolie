import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import type { Session } from "@supabase/supabase-js";
import { KeyRound, LogOut, ShieldCheck } from "lucide-react";
import {
  initializeSupabaseAuth,
  saveDesktopSetup,
  supabase,
  supabaseAuthConfigured,
  type DesktopSetup,
} from "./auth";

const EMPTY_SETUP: DesktopSetup = {
  SUPABASE_URL: "",
  SUPABASE_REGION: "us-east-1",
  SUPABASE_ANON_KEY: "",
  SUPABASE_DB_PASSWORD: "",
  COOLIE_WORKSPACE_ID: "",
  FIRECRAWL_API_KEY: "",
  OPENSEARCH_URL: "",
  OPENSEARCH_INDEX: "",
  OPENSEARCH_USERNAME: "",
  OPENSEARCH_PASSWORD: "",
  COOLIE_RESEARCH_BROWSER_ALLOWED_HOSTS: "",
};

export default function AuthGate({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [configured, setConfigured] = useState(supabaseAuthConfigured);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [setup, setSetup] = useState<DesktopSetup>(EMPTY_SETUP);
  const [setupMode, setSetupMode] = useState(false);
  const [recoveryMode, setRecoveryMode] = useState(false);
  const [recoverySent, setRecoverySent] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let active = true;
    let unsubscribe: (() => void) | undefined;
    void initializeSupabaseAuth().then((isConfigured) => {
      if (!active) return;
      setConfigured(isConfigured);
      if (!isConfigured || !supabase) {
        setLoading(false);
        return;
      }
      const client = supabase;
      const { data: listener } = client.auth.onAuthStateChange((event, nextSession) => {
        setSession(nextSession);
        if (event === "PASSWORD_RECOVERY") setRecoveryMode(true);
        setLoading(false);
        setErrorMessage(null);
      });
      unsubscribe = () => listener.subscription.unsubscribe();
      void client.auth.getSession().then(({ data, error }) => {
        if (!active) return;
        if (error) setErrorMessage(error.message);
        setSession(data.session);
        setLoading(false);
      }).catch((error: unknown) => {
        if (!active) return;
        setErrorMessage(error instanceof Error ? error.message : "Could not check the owner session.");
        setLoading(false);
      });
    }).catch((error: unknown) => {
      if (!active) return;
      setErrorMessage(error instanceof Error ? error.message : "Could not load Coolie setup.");
      setLoading(false);
    });
    return () => {
      active = false;
      unsubscribe?.();
    };
  }, []);

  async function submitSetup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setErrorMessage(null);
    try {
      await saveDesktopSetup(setup);
      window.location.reload();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not save Coolie setup.");
    } finally {
      setSubmitting(false);
    }
  }

  async function sendPasswordRecovery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!supabase) return;
    setSubmitting(true);
    setErrorMessage(null);
    setNotice(null);
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: window.location.origin,
      });
      if (error) throw error;
      setRecoverySent(true);
      setNotice("If this email belongs to an invited Coolie owner, Supabase will send a secure password setup link.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not request a password setup email.");
    } finally {
      setSubmitting(false);
    }
  }

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!supabase) return;
    setSubmitting(true);
    setErrorMessage(null);
    try {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) setErrorMessage(error.message);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Sign-in request failed.");
    } finally {
      setSubmitting(false);
    }
  }

  async function signOut() {
    if (!supabase) return;
    try {
      const { error } = await supabase.auth.signOut();
      if (error) setErrorMessage(error.message);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Sign-out request failed.");
    }
  }

  async function updatePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!supabase) return;
    if (password.length < 12) {
      setErrorMessage("Choose a password with at least 12 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setErrorMessage("The passwords do not match.");
      return;
    }
    setSubmitting(true);
    setErrorMessage(null);
    try {
      const { error } = await supabase.auth.updateUser({ password });
      if (error) throw error;
      setRecoveryMode(false);
      setRecoverySent(false);
      setPassword("");
      setConfirmPassword("");
      setNotice("Your owner password has been set.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not update the password.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="coolie-room flex min-h-screen items-center justify-center text-sm text-slate-300">
        Checking secure owner session…
      </div>
    );
  }

  if (!configured || setupMode) {
    return (
      <main className="coolie-room flex min-h-screen items-center justify-center px-5 py-12">
        <form onSubmit={(event) => void submitSetup(event)} className="coolie-glass-blue w-full max-w-2xl rounded-2xl p-7 shadow-2xl sm:p-9">
          <Header title="Connect Coolie" />
          <p className="mb-6 text-xs leading-relaxed text-slate-400">
            Required values connect this installation to your existing Supabase project. Private values are sent only to this loopback-only setup service and stored in your local user profile; they are never returned to the browser. Only the public anon key is exposed to the sign-in client. Do not enter a service-role key.
          </p>
          <p className="mb-5 text-xs leading-relaxed text-slate-500">
            Find the project URL and publishable/anon key in Supabase project settings. Use the database password set for the project (not your Supabase account password); the workspace UUID is the existing Coolie workspace ID.
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            <SetupField label="Supabase project URL" value={setup.SUPABASE_URL} required onChange={(value) => updateSetup("SUPABASE_URL", value)} placeholder="https://your-project.supabase.co" />
            <SetupField label="Project region" value={setup.SUPABASE_REGION} required onChange={(value) => updateSetup("SUPABASE_REGION", value)} placeholder="us-east-1" />
            <SetupField label="Supabase publishable / anon key" value={setup.SUPABASE_ANON_KEY} required secret onChange={(value) => updateSetup("SUPABASE_ANON_KEY", value)} />
            <SetupField label="Supabase database password" value={setup.SUPABASE_DB_PASSWORD} required secret onChange={(value) => updateSetup("SUPABASE_DB_PASSWORD", value)} />
            <SetupField label="Coolie workspace UUID" value={setup.COOLIE_WORKSPACE_ID} required onChange={(value) => updateSetup("COOLIE_WORKSPACE_ID", value)} />
          </div>
          <details className="mt-6 rounded-xl border border-white/10 bg-slate-950/30 p-4">
            <summary className="cursor-pointer text-xs font-semibold text-blue-100">Optional research provider setup</summary>
            <p className="my-3 text-xs leading-relaxed text-slate-400">These provider credentials stay on this computer. The research MCP tools are not activated unless an operator-configured service factory enables them.</p>
            <div className="grid gap-4 sm:grid-cols-2">
              <SetupField label="Firecrawl API key" value={setup.FIRECRAWL_API_KEY} secret onChange={(value) => updateSetup("FIRECRAWL_API_KEY", value)} />
              <SetupField label="OpenSearch HTTPS URL" value={setup.OPENSEARCH_URL} onChange={(value) => updateSetup("OPENSEARCH_URL", value)} />
              <SetupField label="OpenSearch index" value={setup.OPENSEARCH_INDEX} onChange={(value) => updateSetup("OPENSEARCH_INDEX", value)} />
              <SetupField label="OpenSearch username (optional)" value={setup.OPENSEARCH_USERNAME} onChange={(value) => updateSetup("OPENSEARCH_USERNAME", value)} />
              <SetupField label="OpenSearch password (optional)" value={setup.OPENSEARCH_PASSWORD} secret onChange={(value) => updateSetup("OPENSEARCH_PASSWORD", value)} />
              <SetupField label="Browser host allowlist" value={setup.COOLIE_RESEARCH_BROWSER_ALLOWED_HOSTS} onChange={(value) => updateSetup("COOLIE_RESEARCH_BROWSER_ALLOWED_HOSTS", value)} placeholder="www.example.com, *.example.org" />
            </div>
          </details>
          {errorMessage && <ErrorMessage>{errorMessage}</ErrorMessage>}
          <button className="mt-6 w-full rounded-lg bg-blue-300 px-4 py-3 text-sm font-semibold text-slate-950 disabled:opacity-60" type="submit" disabled={submitting}>
            {submitting ? "Saving securely…" : "Save local setup"}
          </button>
        </form>
      </main>
    );
  }

  if (recoveryMode && session) {
    return (
      <main className="coolie-room flex min-h-screen items-center justify-center px-5 py-12">
        <form onSubmit={(event) => void updatePassword(event)} className="coolie-glass-blue w-full max-w-md rounded-2xl p-7 shadow-2xl sm:p-9">
          <Header title="Create your owner password" />
          <p className="mb-5 text-xs leading-relaxed text-slate-400">The secure Supabase recovery link verifies your identity. Choose your actual password here; Coolie does not generate or store a temporary password.</p>
          <PasswordFields password={password} setPassword={setPassword} confirmPassword={confirmPassword} setConfirmPassword={setConfirmPassword} />
          {errorMessage && <ErrorMessage>{errorMessage}</ErrorMessage>}
          <button className="mt-5 w-full rounded-lg bg-blue-300 px-4 py-3 text-sm font-semibold text-slate-950 disabled:opacity-60" type="submit" disabled={submitting}>
            {submitting ? "Updating…" : "Set owner password"}
          </button>
        </form>
      </main>
    );
  }

  if (!session) {
    if (recoverySent) {
      return (
        <main className="coolie-room flex min-h-screen items-center justify-center px-5 py-12">
          <div className="coolie-glass-blue w-full max-w-md rounded-2xl p-7 shadow-2xl sm:p-9">
            <Header title="Check your email" />
            <p className="text-xs leading-relaxed text-slate-300">{notice}</p>
            <button className="mt-5 text-xs text-blue-200 underline" onClick={() => { setRecoverySent(false); setNotice(null); }} type="button">Back to sign in</button>
          </div>
        </main>
      );
    }
    return (
      <main className="coolie-room flex min-h-screen items-center justify-center px-5 py-12">
        <form onSubmit={(event) => void (recoveryMode ? sendPasswordRecovery(event) : signIn(event))} className="coolie-glass-blue w-full max-w-md rounded-2xl p-7 shadow-2xl sm:p-9">
          <Header title={recoveryMode ? "Set or reset password" : "Owner sign in"} />
          <label className="mb-4 block text-xs font-medium text-slate-300">
            Email
            <input autoComplete="username" className="mt-2 w-full rounded-lg border border-white/10 bg-slate-950/50 px-3 py-3 text-sm text-white outline-none focus:border-blue-300/60" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </label>
          {!recoveryMode && (
            <label className="mb-5 block text-xs font-medium text-slate-300">
              Password
              <input autoComplete="current-password" className="mt-2 w-full rounded-lg border border-white/10 bg-slate-950/50 px-3 py-3 text-sm text-white outline-none focus:border-blue-300/60" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
            </label>
          )}
          {errorMessage && <ErrorMessage>{errorMessage}</ErrorMessage>}
          {notice && <p role="status" className="mb-4 text-xs text-emerald-200">{notice}</p>}
          <button className="w-full rounded-lg bg-blue-300 px-4 py-3 text-sm font-semibold text-slate-950 disabled:opacity-60" type="submit" disabled={submitting}>
            {submitting ? "Please wait…" : recoveryMode ? "Email secure password link" : "Sign in securely"}
          </button>
          <button className="mt-4 w-full text-center text-xs text-blue-200 hover:text-white" onClick={() => { setRecoveryMode(!recoveryMode); setErrorMessage(null); setNotice(null); }} type="button">
            {recoveryMode ? "Back to sign in" : "Set first password / Forgot password"}
          </button>
          <p className="mt-4 text-center text-[11px] leading-relaxed text-slate-500">Access is restricted to active members of the configured Coolie workspace. In Supabase Auth URL Configuration, allow the redirect URL <code className="text-slate-300">http://127.0.0.1:4173</code> for password setup links.</p>
          <button className="mt-3 w-full text-center text-[11px] text-slate-500 hover:text-slate-300" onClick={() => { setSetupMode(true); setErrorMessage(null); }} type="button">Change local connection setup</button>
        </form>
      </main>
    );
  }

  return (
    <>
      {children}
      <button
        className="fixed right-4 top-4 z-[60] flex items-center gap-2 rounded-full border border-white/10 bg-slate-950/80 px-3 py-2 text-xs text-slate-300 shadow-lg backdrop-blur transition hover:border-white/20 hover:text-white"
        onClick={() => void signOut()}
        type="button"
      >
        <LogOut className="h-3.5 w-3.5" />
        Sign out
      </button>
      {errorMessage && (
        <p role="alert" className="fixed right-4 top-16 z-[60] rounded-lg border border-red-300/20 bg-red-950/90 px-3 py-2 text-xs text-red-100">
          {errorMessage}
        </p>
      )}
    </>
  );

  function updateSetup<Key extends keyof DesktopSetup>(key: Key, value: DesktopSetup[Key]) {
    setSetup((current) => ({ ...current, [key]: value }));
  }
}

function Header({ title }: { title: string }) {
  return (
    <div className="mb-6 flex items-center gap-3">
      <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-400/10 text-blue-200 ring-1 ring-blue-200/20"><KeyRound className="h-5 w-5" /></span>
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-blue-200/70">Coolie Intel Zone</p>
        <h1 className="mt-1 text-xl font-semibold text-slate-50">{title}</h1>
      </div>
    </div>
  );
}

function SetupField({ label, value, onChange, required, secret, placeholder }: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  secret?: boolean;
  placeholder?: string;
}) {
  return (
    <label className="block text-xs font-medium text-slate-300">
      {label}{required ? " *" : ""}
      <input
        autoComplete="off"
        className="mt-2 w-full rounded-lg border border-white/10 bg-slate-950/50 px-3 py-3 text-sm text-white outline-none focus:border-blue-300/60"
        type={secret ? "password" : "text"}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        required={required}
      />
    </label>
  );
}

function PasswordFields({ password, setPassword, confirmPassword, setConfirmPassword }: {
  password: string;
  setPassword: (value: string) => void;
  confirmPassword: string;
  setConfirmPassword: (value: string) => void;
}) {
  return (
    <>
      <label className="mb-4 block text-xs font-medium text-slate-300">New password
        <input autoComplete="new-password" className="mt-2 w-full rounded-lg border border-white/10 bg-slate-950/50 px-3 py-3 text-sm text-white outline-none focus:border-blue-300/60" type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={12} required />
      </label>
      <label className="mb-4 block text-xs font-medium text-slate-300">Confirm password
        <input autoComplete="new-password" className="mt-2 w-full rounded-lg border border-white/10 bg-slate-950/50 px-3 py-3 text-sm text-white outline-none focus:border-blue-300/60" type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} minLength={12} required />
      </label>
    </>
  );
}

function ErrorMessage({ children }: { children: string }) {
  return <p role="alert" className="mb-4 rounded-lg border border-red-300/20 bg-red-950/30 px-3 py-2 text-xs text-red-200">{children}</p>;
}
