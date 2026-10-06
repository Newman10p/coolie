import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import type { Session } from "@supabase/supabase-js";
import { ArrowLeft, ArrowRight, KeyRound, LogOut, Sparkles } from "lucide-react";
import { checkForDesktopUpdate, getCurrentDesktopBuild, type DesktopUpdate } from "./updates";
import {
  initializeSupabaseAuth,
  saveDesktopAuthSettings,
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
  COOLIE_AI_API_KEY: "",
  CLEAR_COOLIE_AI_API_KEY: false,
  FIRECRAWL_API_KEY: "",
  OPENSEARCH_URL: "",
  OPENSEARCH_INDEX: "",
  OPENSEARCH_USERNAME: "",
  OPENSEARCH_PASSWORD: "",
  COOLIE_RESEARCH_BROWSER_ALLOWED_HOSTS: "",
};

type OnboardingStep =
  | "welcome"
  | "email"
  | "connect"
  | "credentials"
  | "recovery-sent"
  | "recovery-invalid"
  | "password"
  | "preferences"
  | "configuration"
  | "ready";

function hasRecoveryMarker(): boolean {
  return new URLSearchParams(window.location.search).get("coolie_recovery") === "1";
}

function hasCompletedOnboarding(session: Session | null): boolean {
  return session?.user.user_metadata?.coolie_onboarding_complete === true;
}

export default function AuthGate({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [configured, setConfigured] = useState(false);
  const [aiKeyConfigured, setAiKeyConfigured] = useState(false);
  const [authConfigured, setAuthConfigured] = useState(supabaseAuthConfigured);
  const [supabaseUrl, setSupabaseUrl] = useState("");
  const [supabaseAnonKey, setSupabaseAnonKey] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [preferredName, setPreferredName] = useState("");
  const [setup, setSetup] = useState<DesktopSetup>(EMPTY_SETUP);
  const [step, setStep] = useState<OnboardingStep>("welcome");
  const [requestingRecovery, setRequestingRecovery] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [updateChecking, setUpdateChecking] = useState(false);
  const [updateChecked, setUpdateChecked] = useState(false);
  const [availableUpdate, setAvailableUpdate] = useState<DesktopUpdate | null>(null);
  const [updateError, setUpdateError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    void initializeSupabaseAuth().then(async (bootstrap) => {
      if (!active) return;
      setAuthConfigured(bootstrap.authConfigured);
      setConfigured(bootstrap.configured);
      setAiKeyConfigured(bootstrap.aiKeyConfigured);
      setSupabaseUrl(bootstrap.supabaseUrl);
      setSupabaseAnonKey(bootstrap.supabaseAnonKey);
      if (bootstrap.configured) {
        setSetup((current) => ({ ...current, SUPABASE_REGION: "" }));
      }

      if (!bootstrap.authConfigured || !supabase) {
        setStep("welcome");
        setLoading(false);
        return;
      }

      const client = supabase;
      try {
        const { data, error } = await client.auth.getSession();
        if (!active) return;
        if (error) {
          setErrorMessage(error.message);
          if (hasRecoveryMarker()) setStep("recovery-invalid");
          else setStep("credentials");
        } else {
          setSession(data.session);
          if (data.session) loadPreferences(data.session);
          if (hasRecoveryMarker()) {
            setStep(data.session ? "password" : "recovery-invalid");
          } else if (!data.session) {
            setStep("welcome");
          } else if (!hasCompletedOnboarding(data.session)) {
            setStep("password");
          } else {
            setStep(bootstrap.configured ? "ready" : "configuration");
          }
        }
      } catch (error) {
        if (!active) return;
        setErrorMessage(error instanceof Error ? error.message : "Could not check the owner session.");
        setStep(hasRecoveryMarker() ? "recovery-invalid" : "credentials");
      } finally {
        if (active) setLoading(false);
      }
    }).catch((error: unknown) => {
      if (!active) return;
      setErrorMessage(error instanceof Error ? error.message : "Could not load Coolie setup.");
      setLoading(false);
    });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!authConfigured || !supabase) return;
    const client = supabase;
    const { data: listener } = client.auth.onAuthStateChange((event, nextSession) => {
      setSession(nextSession);
      if (nextSession) loadPreferences(nextSession);
      setErrorMessage(null);
      if (event === "PASSWORD_RECOVERY") {
        setStep(nextSession ? "password" : "recovery-invalid");
      } else if (event === "SIGNED_IN" && nextSession) {
        setStep(
          hasCompletedOnboarding(nextSession)
            ? (configured ? "ready" : "configuration")
            : "password",
        );
      } else if (event === "SIGNED_OUT") {
        setStep("email");
      }
    });
    return () => listener.subscription.unsubscribe();
  }, [authConfigured, configured]);

  async function saveAuthConnection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setErrorMessage(null);
    try {
      await saveDesktopAuthSettings(supabaseUrl, supabaseAnonKey);
      setAuthConfigured(true);
      setStep("credentials");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not save the Supabase connection.");
    } finally {
      setSubmitting(false);
    }
  }

  async function submitSetup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setErrorMessage(null);
    try {
      await saveDesktopSetup(setup);
      setConfigured(true);
      setAiKeyConfigured(
        setup.CLEAR_COOLIE_AI_API_KEY
          ? false
          : Boolean(setup.COOLIE_AI_API_KEY.trim()) || aiKeyConfigured,
      );
      setSetup((current) => ({ ...current, COOLIE_AI_API_KEY: "", CLEAR_COOLIE_AI_API_KEY: false }));
      setNotice("Local settings saved.");
      await completeOnboarding();
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
        redirectTo: `${window.location.origin}/?coolie_recovery=1`,
      });
      if (error) throw error;
      setStep("recovery-sent");
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
      const { data, error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw error;
      setSession(data.session);
      loadPreferences(data.session);
      setPassword("");
      setStep(
        hasCompletedOnboarding(data.session)
          ? (configured ? "ready" : "configuration")
          : "password",
      );
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Sign-in request failed.");
    } finally {
      setSubmitting(false);
    }
  }

  async function updatePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!supabase || !session) {
      setStep(hasRecoveryMarker() ? "recovery-invalid" : "credentials");
      return;
    }
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
      setPassword("");
      setConfirmPassword("");
      window.history.replaceState({}, document.title, window.location.pathname);
      if (hasCompletedOnboarding(session)) {
        setStep(configured ? "ready" : "configuration");
      } else {
        setStep("preferences");
        setNotice("Password updated. Next, tell Coolie how to address you.");
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not update the password.");
    } finally {
      setSubmitting(false);
    }
  }

  async function savePreferences(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!supabase) return;
    setSubmitting(true);
    setErrorMessage(null);
    try {
      const { error } = await supabase.auth.updateUser({
        data: {
          coolie_full_name: fullName.trim(),
          coolie_preferred_name: preferredName.trim(),
        },
      });
      if (error) throw error;
      if (configured) await completeOnboarding();
      else setStep("configuration");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not save your preferences.");
    } finally {
      setSubmitting(false);
    }
  }

  async function completeOnboarding() {
    if (!supabase) throw new Error("Supabase authentication is not configured.");
    const { error } = await supabase.auth.updateUser({
      data: {
        coolie_full_name: fullName.trim(),
        coolie_preferred_name: preferredName.trim(),
        coolie_onboarding_complete: true,
      },
    });
    if (error) throw error;
    const { data, error: sessionError } = await supabase.auth.getSession();
    if (sessionError) throw sessionError;
    setSession(data.session);
    setStep("ready");
    setNotice(null);
  }

  async function signOut() {
    if (!supabase) return;
    try {
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
      setSession(null);
      setStep("email");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Sign-out request failed.");
    }
  }

  async function checkUpdates() {
    setUpdateChecking(true);
    setUpdateError(null);
    try {
      setAvailableUpdate(await checkForDesktopUpdate());
      setUpdateChecked(true);
    } catch (error) {
      setUpdateError(error instanceof Error ? error.message : "Could not check for updates.");
    } finally {
      setUpdateChecking(false);
    }
  }

  function loadPreferences(ownerSession: Session) {
    const metadata = ownerSession.user.user_metadata;
    setFullName(typeof metadata?.coolie_full_name === "string" ? metadata.coolie_full_name : "");
    setPreferredName(typeof metadata?.coolie_preferred_name === "string" ? metadata.coolie_preferred_name : "");
  }

  if (loading) {
    return (
      <div className="coolie-room flex min-h-screen items-center justify-center text-sm text-slate-300">
        Checking secure owner session…
      </div>
    );
  }

  if (step === "ready" && session && configured) {
    return (
      <>
        {children}
        <div className={`fixed left-4 top-4 z-[60] max-w-[calc(100%-12rem)] rounded-full border px-3 py-2 text-xs shadow-lg backdrop-blur ${
          aiKeyConfigured
            ? "border-amber-200/20 bg-amber-950/80 text-amber-100"
            : "border-white/10 bg-slate-950/80 text-slate-300"
        }`}>
          {aiKeyConfigured ? "AI key saved · provider integration pending" : "Awaiting AI provider API key"}
        </div>
        <button
          className="fixed right-4 top-4 z-[60] flex items-center gap-2 rounded-full border border-white/10 bg-slate-950/80 px-3 py-2 text-xs text-slate-300 shadow-lg backdrop-blur transition hover:border-white/20 hover:text-white"
          onClick={() => void signOut()}
          type="button"
        >
          <LogOut className="h-3.5 w-3.5" />
          Sign out
        </button>
        <button
          className="fixed right-4 top-14 z-[60] rounded-full border border-white/10 bg-slate-950/80 px-3 py-2 text-xs text-slate-300 shadow-lg backdrop-blur transition hover:border-white/20 hover:text-white"
          onClick={() => { setErrorMessage(null); setStep("configuration"); }}
          type="button"
        >
          Local settings
        </button>
        <button
          className="fixed right-4 top-24 z-[60] rounded-full border border-white/10 bg-slate-950/80 px-3 py-2 text-xs text-slate-300 shadow-lg backdrop-blur transition hover:border-white/20 hover:text-white disabled:opacity-60"
          onClick={() => void checkUpdates()}
          type="button"
          disabled={updateChecking}
        >
          {updateChecking ? "Checking updates…" : "Check for updates"}
        </button>
        {updateError && (
          <p role="alert" className="fixed right-4 top-36 z-[60] max-w-sm rounded-lg border border-red-300/20 bg-red-950/90 px-3 py-2 text-xs text-red-100">
            {updateError}
          </p>
        )}
        {updateChecked && !availableUpdate && (
          <p role="status" className="fixed right-4 top-36 z-[60] rounded-lg border border-white/10 bg-slate-950/90 px-3 py-2 text-xs text-slate-300">
            Coolie is up to date ({getCurrentDesktopBuild().slice(0, 7)}).
          </p>
        )}
        {availableUpdate && (
          <section className="fixed right-4 top-36 z-[60] w-[min(24rem,calc(100vw-2rem))] rounded-xl border border-blue-200/20 bg-slate-950/95 p-4 text-xs text-slate-200 shadow-2xl">
            <h2 className="font-semibold text-blue-100">A Coolie update is available</h2>
            <p className="my-2 text-slate-400">Build {availableUpdate.commit.slice(0, 7)}. Download the installer for your device, close Coolie, and run it to update.</p>
            <ul className="space-y-2">
              {availableUpdate.assets.map((asset) => (
                <li key={asset.name}>
                  <a className="text-blue-200 underline hover:text-white" href={asset.url} target="_blank" rel="noreferrer">
                    {asset.name}
                  </a>
                </li>
              ))}
            </ul>
          </section>
        )}
        {errorMessage && (
          <p role="alert" className="fixed right-4 top-16 z-[60] rounded-lg border border-red-300/20 bg-red-950/90 px-3 py-2 text-xs text-red-100">
            {errorMessage}
          </p>
        )}
      </>
    );
  }

  if (step === "welcome") {
    return (
      <WizardCard step={1} title="A clearer way to run your workroom">
        <div className="mb-7 flex justify-center">
          <div className="relative flex h-28 w-28 items-center justify-center">
            <span className="absolute inset-0 animate-ping rounded-full border border-blue-300/20" />
            <span className="absolute inset-2 animate-pulse rounded-full border border-blue-200/40" />
            <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-300/10 text-blue-100 ring-1 ring-blue-200/30">
              <Sparkles className="h-8 w-8" />
            </span>
          </div>
        </div>
        <p className="mb-7 text-center text-sm leading-relaxed text-slate-300">
          Set up your owner access, choose how Coolie addresses you, then connect the workspace. Your setup is saved locally and can be changed later.
        </p>
        <button className={primaryButton} onClick={() => setStep("email")} type="button">
          Begin onboarding <ArrowRight className="inline h-4 w-4" />
        </button>
        <p className="mt-4 text-center text-[11px] leading-relaxed text-slate-500">
          Your temporary password is verified by Supabase and is never bundled with this installer.
        </p>
      </WizardCard>
    );
  }

  if (step === "email") {
    return (
      <WizardCard step={2} title="Start with your owner email">
        <p className="mb-5 text-xs leading-relaxed text-slate-400">
          Use the email address associated with your invited Coolie owner account.
        </p>
        <form onSubmit={(event) => {
          event.preventDefault();
          setErrorMessage(null);
          setStep(authConfigured ? "credentials" : "connect");
        }}>
          <SetupField label="Owner email" value={email} required onChange={setEmail} type="email" autoComplete="username" />
          {errorMessage && <ErrorMessage>{errorMessage}</ErrorMessage>}
          <button className={primaryButton} type="submit">
            Continue <ArrowRight className="inline h-4 w-4" />
          </button>
        </form>
      </WizardCard>
    );
  }

  if (step === "connect") {
    return (
      <WizardCard step={3} title="Connect your Supabase project">
        <p className="mb-5 text-xs leading-relaxed text-slate-400">
          Only the project URL and public anon/publishable key are needed for owner sign-in. Database credentials and workspace settings come later and stay on this computer.
        </p>
        <form onSubmit={(event) => void saveAuthConnection(event)}>
          <SetupField label="Supabase project URL" value={supabaseUrl} required onChange={setSupabaseUrl} placeholder="https://your-project.supabase.co" />
          <SetupField label="Supabase publishable / anon key" value={supabaseAnonKey} required secret onChange={setSupabaseAnonKey} />
          {errorMessage && <ErrorMessage>{errorMessage}</ErrorMessage>}
          <button className={`${primaryButton} mt-5`} type="submit" disabled={submitting}>
            {submitting ? "Saving connection…" : "Continue to owner sign-in"}
          </button>
        </form>
        <button className={secondaryButton} onClick={() => setStep("email")} type="button">
          <ArrowLeft className="inline h-4 w-4" /> Change owner email
        </button>
      </WizardCard>
    );
  }

  if (step === "credentials" || requestingRecovery) {
    if (step === "recovery-sent") {
      return (
        <WizardCard step={3} title="Check your email">
          <p role="status" className="text-xs leading-relaxed text-slate-300">{notice}</p>
          <button className={`${secondaryButton} mt-5`} onClick={() => { setRequestingRecovery(false); setStep("credentials"); setNotice(null); }} type="button">
            Back to sign in
          </button>
        </WizardCard>
      );
    }
    return (
      <WizardCard step={3} title={requestingRecovery ? "Request a secure password link" : "Sign in to Coolie"}>
        <form onSubmit={(event) => void (requestingRecovery ? sendPasswordRecovery(event) : signIn(event))}>
          {requestingRecovery ? (
            <SetupField label="Owner email" value={email} required onChange={setEmail} type="email" autoComplete="username" />
          ) : (
            <p className="mb-5 text-xs text-slate-400">
              Signing in as <span className="text-slate-200">{email}</span>
              <button className="ml-2 text-blue-200 underline" onClick={() => setStep("email")} type="button">Change</button>
            </p>
          )}
          {!requestingRecovery && (
            <>
              <SetupField
                label="Temporary password"
                value={password}
                required
                secret
                onChange={setPassword}
                autoComplete="current-password"
              />
              <p className="mb-5 text-[11px] leading-relaxed text-slate-500">
                Enter the temporary password from your private password.env file. It must already be the current password for this Supabase account. Coolie sends it only to Supabase for verification; the file is not read, saved, or included in the installer. If it is not set on the account, request a secure password link instead.
              </p>
            </>
          )}
          {errorMessage && <ErrorMessage>{errorMessage}</ErrorMessage>}
          <button className={primaryButton} type="submit" disabled={submitting}>
            {submitting ? "Please wait…" : requestingRecovery ? "Email secure setup link" : "Verify and continue"}
          </button>
        </form>
        <button className={secondaryButton} onClick={() => { setRequestingRecovery(!requestingRecovery); setErrorMessage(null); }} type="button">
          {requestingRecovery ? "Back to temporary-password sign in" : "Need a password setup link?"}
        </button>
        <p className="mt-4 text-center text-[11px] leading-relaxed text-slate-500">
          Allow <code className="text-slate-300">{window.location.origin}/?coolie_recovery=1</code> in Supabase Auth URL Configuration.
        </p>
      </WizardCard>
    );
  }

  if (step === "recovery-invalid") {
    return (
      <WizardCard step={3} title="This password link is not active">
        <p className="mb-5 text-xs leading-relaxed text-slate-300">
          Supabase did not establish a verified recovery session. The link may be expired or already used. No new email was sent automatically.
        </p>
        {errorMessage && <ErrorMessage>{errorMessage}</ErrorMessage>}
        <button className={primaryButton} onClick={() => { window.history.replaceState({}, document.title, window.location.pathname); setErrorMessage(null); setRequestingRecovery(true); setStep("credentials"); }} type="button">
          Request a fresh password link
        </button>
        <button className={secondaryButton} onClick={() => { window.history.replaceState({}, document.title, window.location.pathname); setErrorMessage(null); setRequestingRecovery(false); setStep("email"); }} type="button">
          <ArrowLeft className="inline h-4 w-4" /> Back to email
        </button>
      </WizardCard>
    );
  }

  if (step === "password") {
    return (
      <WizardCard step={4} title="Create your permanent password">
        <p className="mb-5 text-xs leading-relaxed text-slate-400">
          Your identity has been verified by Supabase. Choose a new password of at least 12 characters. Coolie never stores your password.
        </p>
        <form onSubmit={(event) => void updatePassword(event)}>
          <PasswordFields password={password} setPassword={setPassword} confirmPassword={confirmPassword} setConfirmPassword={setConfirmPassword} />
          {errorMessage && <ErrorMessage>{errorMessage}</ErrorMessage>}
          <button className={primaryButton} type="submit" disabled={submitting}>
            {submitting ? "Updating password…" : "Set my password"}
          </button>
        </form>
      </WizardCard>
    );
  }

  if (step === "preferences") {
    return (
      <WizardCard step={5} title="Make Coolie yours">
        <p className="mb-5 text-xs leading-relaxed text-slate-400">
          These preferences are saved to your Supabase Auth profile and can be changed later.
        </p>
        <form onSubmit={(event) => void savePreferences(event)}>
          <SetupField label="Your name" value={fullName} required onChange={setFullName} autoComplete="name" />
          <SetupField label="What should Coolie call you?" value={preferredName} required onChange={setPreferredName} autoComplete="nickname" />
          {errorMessage && <ErrorMessage>{errorMessage}</ErrorMessage>}
          <button className={primaryButton} type="submit" disabled={submitting}>
            {submitting ? "Saving preferences…" : "Continue"}
          </button>
        </form>
      </WizardCard>
    );
  }

  return (
    <WizardCard step={6} title="Connect workspace data">
      <p className="mb-5 text-xs leading-relaxed text-slate-400">
        Database values stay in this computer’s local settings file; only the public anon key is sent to the browser. Do not enter a service-role key. Leave fields blank when editing to keep the saved value.
      </p>
      <p className="mb-5 text-[11px] leading-relaxed text-slate-500">
        Find the database password in Supabase project settings. Use the existing Coolie workspace UUID. Add your AI provider key below when ready; provider integration must also be configured to enable AI features.
      </p>
      <form onSubmit={(event) => void submitSetup(event)}>
        <div className="grid gap-4 sm:grid-cols-2">
          <SetupField label="Project region" value={setup.SUPABASE_REGION} required={!configured} onChange={(value) => updateSetup("SUPABASE_REGION", value)} placeholder={configured ? "Leave blank to keep current value" : "us-east-1"} />
          <SetupField label="Supabase database password" value={setup.SUPABASE_DB_PASSWORD} required={!configured} secret onChange={(value) => updateSetup("SUPABASE_DB_PASSWORD", value)} placeholder={configured ? "Leave blank to keep current value" : undefined} />
          <SetupField label="Coolie workspace UUID" value={setup.COOLIE_WORKSPACE_ID} required={!configured} onChange={(value) => updateSetup("COOLIE_WORKSPACE_ID", value)} placeholder={configured ? "Leave blank to keep current value" : undefined} />
        </div>
        <section className="mb-5 rounded-xl border border-blue-200/15 bg-blue-950/20 p-4">
          <h2 className="text-sm font-semibold text-slate-100">AI provider API key</h2>
          <p className="my-2 text-xs leading-relaxed text-slate-400">
            {aiKeyConfigured
              ? "A key is saved on this computer. Leave the field empty to keep it, or replace it below."
              : "Coolie is ready for provider setup. Add your provider key here; it is stored locally and never returned to the browser."}
            {" "}Saving a key stores it securely for development but does not activate AI features until a compatible provider service is configured.
          </p>
          <SetupField
            label="AI provider API key"
            value={setup.COOLIE_AI_API_KEY}
            secret
            onChange={(value) => updateSetup("COOLIE_AI_API_KEY", value)}
            placeholder={aiKeyConfigured ? "Leave blank to keep current key" : "Paste provider API key"}
          />
          {aiKeyConfigured && (
            <label className="flex items-center gap-2 text-xs text-slate-300">
              <input
                type="checkbox"
                checked={setup.CLEAR_COOLIE_AI_API_KEY}
                onChange={(event) => {
                  const clear = event.target.checked;
                  setSetup((current) => ({
                    ...current,
                    COOLIE_AI_API_KEY: "",
                    CLEAR_COOLIE_AI_API_KEY: clear,
                  }));
                }}
              />
              Remove the saved AI key
            </label>
          )}
        </section>
        <details className="mt-5 rounded-xl border border-white/10 bg-slate-950/30 p-4">
          <summary className="cursor-pointer text-xs font-semibold text-blue-100">Optional research provider settings</summary>
          <p className="my-3 text-xs leading-relaxed text-slate-400">Provider credentials stay on this computer. They do not activate integrations unless an operator-configured service factory enables them.</p>
          <div className="grid gap-4 sm:grid-cols-2">
            <SetupField label="Firecrawl API key" value={setup.FIRECRAWL_API_KEY} secret onChange={(value) => updateSetup("FIRECRAWL_API_KEY", value)} placeholder="Leave blank to keep current value" />
            <SetupField label="OpenSearch HTTPS URL" value={setup.OPENSEARCH_URL} onChange={(value) => updateSetup("OPENSEARCH_URL", value)} placeholder="Leave blank to keep current value" />
            <SetupField label="OpenSearch index" value={setup.OPENSEARCH_INDEX} onChange={(value) => updateSetup("OPENSEARCH_INDEX", value)} placeholder="Leave blank to keep current value" />
            <SetupField label="OpenSearch username" value={setup.OPENSEARCH_USERNAME} onChange={(value) => updateSetup("OPENSEARCH_USERNAME", value)} placeholder="Leave blank to keep current value" />
            <SetupField label="OpenSearch password" value={setup.OPENSEARCH_PASSWORD} secret onChange={(value) => updateSetup("OPENSEARCH_PASSWORD", value)} placeholder="Leave blank to keep current value" />
            <SetupField label="Browser host allowlist" value={setup.COOLIE_RESEARCH_BROWSER_ALLOWED_HOSTS} onChange={(value) => updateSetup("COOLIE_RESEARCH_BROWSER_ALLOWED_HOSTS", value)} placeholder="Leave blank to keep current value" />
          </div>
        </details>
        {errorMessage && <ErrorMessage>{errorMessage}</ErrorMessage>}
        <button className={`${primaryButton} mt-5`} type="submit" disabled={submitting}>
          {submitting ? "Saving securely…" : configured ? "Save local settings" : "Finish setup"}
        </button>
      </form>
      {notice && <p role="status" className="mt-4 text-xs text-emerald-200">{notice}</p>}
    </WizardCard>
  );

  function updateSetup<Key extends keyof DesktopSetup>(key: Key, value: DesktopSetup[Key]) {
    setSetup((current) => ({
      ...current,
      SUPABASE_URL: supabaseUrl,
      SUPABASE_ANON_KEY: supabaseAnonKey,
      ...(key === "COOLIE_AI_API_KEY" ? { CLEAR_COOLIE_AI_API_KEY: false } : {}),
      [key]: value,
    }));
  }
}

const primaryButton = "w-full rounded-lg bg-blue-300 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-blue-200 disabled:opacity-60";
const secondaryButton = "mt-4 w-full text-center text-xs text-blue-200 hover:text-white";

function WizardCard({ step, title, children }: { step: number; title: string; children: ReactNode }) {
  return (
    <main className="coolie-room flex min-h-screen items-center justify-center px-5 py-12">
      <section className="coolie-glass-blue w-full max-w-2xl rounded-2xl p-7 shadow-2xl sm:p-9">
        <header className="mb-6 flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-400/10 text-blue-200 ring-1 ring-blue-200/20">
            <KeyRound className="h-5 w-5" />
          </span>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-blue-200/70">Coolie Owner Onboarding · {step}/6</p>
            <h1 className="mt-1 text-xl font-semibold text-slate-50">{title}</h1>
          </div>
        </header>
        {children}
      </section>
    </main>
  );
}

function SetupField({ label, value, onChange, required, secret, placeholder, type = "text", autoComplete = "off" }: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  secret?: boolean;
  placeholder?: string;
  type?: string;
  autoComplete?: string;
}) {
  return (
    <label className="mb-4 block text-xs font-medium text-slate-300">
      {label}{required ? " *" : ""}
      <input
        autoComplete={autoComplete}
        className="mt-2 w-full rounded-lg border border-white/10 bg-slate-950/50 px-3 py-3 text-sm text-white outline-none focus:border-blue-300/60"
        type={secret ? "password" : type}
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
      <SetupField label="New password" value={password} onChange={setPassword} required secret autoComplete="new-password" />
      <SetupField label="Confirm new password" value={confirmPassword} onChange={setConfirmPassword} required secret autoComplete="new-password" />
    </>
  );
}

function ErrorMessage({ children }: { children: string }) {
  return <p role="alert" className="mb-4 rounded-lg border border-red-300/20 bg-red-950/30 px-3 py-2 text-xs text-red-200">{children}</p>;
}
