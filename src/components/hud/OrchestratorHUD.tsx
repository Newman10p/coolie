import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import {
  Send,
  Mic,
  MicOff,
  Sparkles,
  User,
  ShieldAlert,
  Check,
  X,
  Terminal,
} from "lucide-react";
import {
  quickPrompts,
  resolveIntent,
  type Intent,
} from "../../data";
import HudFrame from "./HudFrame";
import Waveform from "./Waveform";
import CognitionPanel, { type Trace } from "./CognitionPanel";
import ContextRail from "./ContextRail";
import GenerativeCanvas from "./GenerativeCanvas";
import { SectionHeading } from "../scroll/Reveal";
import { useResearch } from "../../research/store";
import { MOCK_MODE } from "../../research/data";

interface SpeechAlternativeLike {
  transcript: string;
}

interface SpeechResultLike {
  0: SpeechAlternativeLike;
}

interface SpeechResultEventLike {
  resultIndex: number;
  results: ArrayLike<SpeechResultLike>;
}

interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: SpeechResultEventLike) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
}

type SpeechRecognitionWindow = Window & {
  SpeechRecognition?: new () => SpeechRecognitionLike;
  webkitSpeechRecognition?: new () => SpeechRecognitionLike;
};

type Msg = {
  id: number;
  role: "owner" | "coolie" | "system";
  text: string;
  intent?: string;
  memory?: string[];
  chips?: string[];
  confirm?: NonNullable<Intent["confirm"]>;
  confirmed?: boolean;
};

const intro: Msg = {
  id: 0,
  role: "coolie",
  text:
    "Good morning, Owner. This is your natural-language channel. Ask in your own words and I can bring a mission brief, evidence trail, financial handoff or decision packet into the canvas beside us. In this prototype, replies use a static demo dataset and no external action is executed.",
  intent: "orchestrator.ready",
  chips: quickPrompts.slice(0, 4),
};

let uid = 1;
const nextId = () => uid++;

export default function OrchestratorHUD() {
  const reduce = useReducedMotion();
  const [msgs, setMsgs] = useState<Msg[]>([intro]);
  const [input, setInput] = useState("");
  const [listening, setListening] = useState(false);
  const [busy, setBusy] = useState(false);
  const [traces, setTraces] = useState<Trace[]>([]);
  const [chips, setChips] = useState<string[]>(intro.chips ?? []);
  const [memory, setMemory] = useState<string[]>([]);
  const [canvas, setCanvas] = useState<{ intent: Intent; query: string; pending: boolean; turn: number } | null>(null);
  const [voiceError, setVoiceError] = useState("");
  const [transcriptReady, setTranscriptReady] = useState(false);

  const { go } = useResearch();
  const scrollRef = useRef<HTMLDivElement>(null);
  const timers = useRef<number[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const turnRef = useRef(0);

  const clearTimers = useCallback(() => {
    timers.current.forEach((t) => clearTimeout(t));
    timers.current = [];
  }, []);
  const later = useCallback((fn: () => void, ms: number) => {
    timers.current.push(window.setTimeout(fn, ms));
  }, []);

  useEffect(() => () => clearTimers(), [clearTimers]);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: reduce ? "auto" : "smooth",
    });
  }, [msgs, traces, reduce]);

  /** Streams a reply word-by-word into the transcript. */
  const stream = useCallback(
    (intent: Intent) => {
      const id = nextId();
      setMsgs((m) => [
        ...m,
        {
          id,
          role: "coolie",
          text: "",
          intent: intent.id,
          memory: intent.memory,
          chips: intent.chips,
          confirm: intent.confirm,
        },
      ]);
      setChips(intent.chips);
      setMemory(intent.memory);

      if (reduce) {
        setMsgs((m) => m.map((x) => (x.id === id ? { ...x, text: intent.reply } : x)));
        return;
      }

      const words = intent.reply.split(" ");
      let i = 0;
      const step = () => {
        i += 1;
        const chunk = words.slice(0, i).join(" ");
        setMsgs((m) => m.map((x) => (x.id === id ? { ...x, text: chunk } : x)));
        if (i < words.length) later(step, 26);
      };
      later(step, 26);
    },
    [later, reduce]
  );

  const ask = useCallback(
    (text: string) => {
      const q = text.trim();
      if (!q || busy) return;
      clearTimers();
      setInput("");
      setTranscriptReady(false);
      setVoiceError("");
      setBusy(true);
      setTraces([]);
      setMsgs((m) => [...m, { id: nextId(), role: "owner", text: q }]);

      const intent = resolveIntent(q);
      turnRef.current += 1;
      setCanvas({ intent, query: q, pending: true, turn: turnRef.current });

      // phase 1 — reasoning
      later(() => {
        setTraces([{ kind: "thinking", text: `Resolving intent · ${intent.id}` }]);
      }, 120);

      // phase 2 — tool calls, staggered
      intent.tools.forEach((tool, i) => {
        later(() => {
          setTraces((t) => [...t, { kind: "tool", tool, state: "running" }]);
        }, 420 + i * 300);
        later(() => {
          setTraces((t) =>
            t.map((x) =>
              x.kind === "tool" && x.tool === tool ? { ...x, state: "done" } : x
            )
          );
        }, 420 + i * 300 + (reduce ? 60 : tool.ms * 2));
      });

      // phase 3 — synthesise + stream the answer
      const total = 420 + intent.tools.length * 300 + 260;
      later(() => setTraces((t) => [...t, { kind: "thinking", text: "Synthesising response" }]), total);
      later(() => {
        stream(intent);
        setCanvas((current) => (current ? { ...current, pending: false } : current));
        setBusy(false);
      }, total + (reduce ? 100 : 520));
    },
    [busy, clearTimers, later, reduce, stream]
  );

  const confirmAction = useCallback(
    (msg: Msg, approved: boolean) => {
      setMsgs((m) => m.map((x) => (x.id === msg.id ? { ...x, confirmed: approved } : x)));
      setMsgs((m) => [
        ...m,
        {
          id: nextId(),
          role: "system",
          text: approved
            ? `Demo confirmation recorded for "${msg.confirm?.label}". No external action was executed. Use the Approval Center for a backend-verified approval workflow.`
            : "Demo action cancelled. Nothing was dispatched.",
        },
      ]);
      setChips(["Show the 3 steps first", "What else needs my attention?"]);
    },
    []
  );

  // Voice transcripts are placed in the input for review; they are never sent automatically.
  const toggleVoice = () => {
    if (busy) return;
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }

    const SpeechRecognition = (window as SpeechRecognitionWindow).SpeechRecognition ??
      (window as SpeechRecognitionWindow).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setVoiceError("Browser speech recognition is unavailable here. You can type naturally instead.");
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.lang = "en-US";
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.onresult = (event) => {
        const text = Array.from(event.results)
          .slice(event.resultIndex)
          .map((result) => result[0]?.transcript ?? "")
          .join(" ")
          .trim();
        if (text) {
          setInput(text);
          setTranscriptReady(true);
          setVoiceError("");
        }
      };
      recognition.onerror = (event) => {
        setListening(false);
        setVoiceError(
          event.error === "not-allowed"
            ? "Microphone permission was denied. Type your request instead."
            : `Voice capture ended (${event.error}). You can type your request instead.`
        );
      };
      recognition.onend = () => {
        setListening(false);
        inputRef.current?.focus();
      };
      recognitionRef.current = recognition;
      setVoiceError("");
      setTranscriptReady(false);
      setListening(true);
      recognition.start();
    } catch {
      setListening(false);
      setVoiceError("Couldn't start voice capture. Type your request instead.");
    }
  };

  useEffect(
    () => () => {
      recognitionRef.current?.stop();
      clearTimers();
    },
    [clearTimers]
  );

  return (
    <div className="mx-auto w-full max-w-7xl px-4 pb-28">
      <SectionHeading
        kicker="ORCHESTRATOR HUD · NATURAL LANGUAGE"
        title="Talk naturally. See the work take shape."
        desc="Speak or type the way you would to a chief of staff. Coolie answers in natural language and composes relevant mission, evidence, financial or decision UI alongside the conversation."
      />

      <div className="grid gap-4 lg:grid-cols-[220px_minmax(0,1.2fr)_minmax(300px,0.95fr)] xl:gap-5">
        <div className="order-3 lg:order-1">
          <ContextRail />
        </div>

        {/* Conversation stage */}
        <div className="order-1 min-w-0 lg:order-2">
          <HudFrame active={busy} className="coolie-glass-blue rounded-3xl p-5 sm:p-6">
            {/* stage header */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.08] pb-4">
              <div className="flex items-center gap-2.5">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-70" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-blue-300" />
                </span>
                <p className="text-sm font-semibold text-white">Coolie Orchestrator</p>
                <span className="rounded-md bg-white/5 px-2 py-0.5 font-mono text-[10px] text-slate-400 ring-1 ring-white/10">
                  {busy ? "working…" : "ready"}
                </span>
              </div>
              <div className="flex items-center gap-2 text-[10px] font-medium tracking-wider text-slate-500">
                {MOCK_MODE && (
                  <span className="rounded bg-amber-400/10 px-1.5 py-0.5 font-bold text-amber-200 ring-1 ring-amber-400/20">
                    DEMO RESPONSES
                  </span>
                )}
                <span className="hidden items-center gap-1.5 sm:flex">
                  <Terminal className="h-3.5 w-3.5" /> NATURAL LANGUAGE
                </span>
              </div>
            </div>

            {/* transcript */}
            <div
              ref={scrollRef}
              className="max-h-[46vh] min-h-[240px] space-y-4 overflow-y-auto py-5 pr-1"
            >
              <AnimatePresence initial={false}>
                {msgs.map((m) => (
                  <motion.div
                    key={m.id}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                    className={`flex gap-3 ${m.role === "owner" ? "flex-row-reverse" : ""}`}
                  >
                    {/* avatar */}
                    <div
                      className={`mt-0.5 grid h-8 w-8 flex-none place-items-center rounded-xl ring-1 ${
                        m.role === "owner"
                          ? "bg-blue-500/20 text-blue-100 ring-blue-400/30"
                          : m.role === "system"
                            ? "bg-white/5 text-slate-400 ring-white/10"
                            : "coolie-metal text-blue-200 ring-white/10"
                      }`}
                    >
                      {m.role === "owner" ? (
                        <User className="h-4 w-4" />
                      ) : m.role === "system" ? (
                        <ShieldAlert className="h-4 w-4" />
                      ) : (
                        <Sparkles className="h-4 w-4" />
                      )}
                    </div>

                    {/* bubble */}
                    <div className={`min-w-0 max-w-[86%] ${m.role === "owner" ? "text-right" : ""}`}>
                      <div
                        className={`rounded-2xl px-4 py-3 text-[13px] leading-relaxed ${
                          m.role === "owner"
                            ? "bg-blue-500/20 text-blue-50 ring-1 ring-blue-400/25"
                            : m.role === "system"
                              ? "coolie-solid text-slate-300"
                              : "coolie-metal text-slate-100"
                        }`}
                      >
                        {m.role === "coolie" && (
                          <span className="mb-1 block text-[10px] font-semibold tracking-wider text-blue-300/70">
                            COOLIE
                          </span>
                        )}
                        <p className="whitespace-pre-wrap">{m.text}</p>
                        {m.role === "coolie" &&
                          m.text.length > 0 &&
                          m.text.length < 40 && (
                            <span className="ml-0.5 inline-block h-3.5 w-[2px] animate-pulse bg-blue-300 align-middle" />
                          )}
                      </div>

                      {/* intent tag */}
                      {m.intent && (
                        <p className="mt-1.5 font-mono text-[10px] text-slate-600">
                          response type · {m.intent}
                        </p>
                      )}

                      {/* retrieved memory */}
                      {m.memory && m.memory.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {m.memory.map((x) => (
                            <span
                              key={x}
                              className="rounded-md bg-white/[0.04] px-2 py-1 text-[10px] text-slate-400 ring-1 ring-white/[0.08]"
                            >
                              {x}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* consequential action confirmation */}
                      {m.confirm && !m.confirmed && (
                        <motion.div
                          initial={{ opacity: 0, y: 6 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="mt-2.5 rounded-xl border border-amber-400/25 bg-amber-400/10 p-3 text-left"
                        >
                          <p className="flex items-center gap-1.5 text-[11px] font-semibold text-amber-200">
                            <ShieldAlert className="h-3.5 w-3.5" /> Confirmation required
                          </p>
                          <p className="mt-1.5 text-[12px] text-amber-100/90">
                            {m.confirm.label} — {m.confirm.detail}
                          </p>
                          <div className="mt-2.5 flex gap-2">
                            <button
                              onClick={() => confirmAction(m, true)}
                              className="flex items-center gap-1.5 rounded-lg bg-emerald-500/25 px-3 py-1.5 text-[11px] font-semibold text-emerald-100 ring-1 ring-emerald-400/30 transition hover:bg-emerald-500/40"
                            >
                              <Check className="h-3.5 w-3.5" /> Confirm
                            </button>
                            <button
                              onClick={() => confirmAction(m, false)}
                              className="flex items-center gap-1.5 rounded-lg bg-white/[0.05] px-3 py-1.5 text-[11px] font-semibold text-slate-300 ring-1 ring-white/10 transition hover:bg-white/[0.1]"
                            >
                              <X className="h-3.5 w-3.5" /> Cancel
                            </button>
                          </div>
                        </motion.div>
                      )}

                      {m.confirmed && (
                        <p className="mt-1.5 text-[11px] font-medium text-amber-200">
                          Demo confirmation captured · no external action executed
                        </p>
                      )}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {/* thinking bubble */}
              {busy && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3">
                  <div className="coolie-metal mt-0.5 grid h-8 w-8 flex-none place-items-center rounded-xl text-blue-200 ring-1 ring-white/10">
                    <Sparkles className="h-4 w-4" />
                  </div>
                  <div className="coolie-metal flex items-center gap-1.5 rounded-2xl px-4 py-3">
                    {[0, 1, 2].map((i) => (
                      <motion.span
                        key={i}
                        className="h-1.5 w-1.5 rounded-full bg-blue-300"
                        animate={{ opacity: [0.25, 1, 0.25], y: [0, -3, 0] }}
                        transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }}
                      />
                    ))}
                  </div>
                </motion.div>
              )}
            </div>

            {/* suggestion chips */}
            {chips.length > 0 && !busy && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-wrap gap-2 border-t border-white/[0.08] pt-4"
              >
                {chips.map((c) => (
                  <button
                    key={c}
                    onClick={() => ask(c)}
                    className="rounded-full bg-white/[0.04] px-3 py-1.5 text-[11px] font-medium text-slate-300 ring-1 ring-white/10 transition hover:bg-blue-400/15 hover:text-blue-100"
                  >
                    {c}
                  </button>
                ))}
              </motion.div>
            )}

            {/* voice stage */}
            <AnimatePresence>
              {listening && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden"
                >
                  <div className="mt-4 rounded-2xl bg-black/30 px-4 py-3 ring-1 ring-blue-400/20">
                    <Waveform active bars={48} className="h-14" />
                    <p className="mt-1 text-center text-[11px] text-blue-200/80">
                      Listening… speak naturally. Voice is never proof of authorization.
                    </p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* command bar */}
            <div className="mt-4 flex items-center gap-2">
              <button
                onClick={toggleVoice}
                aria-label={listening ? "Stop listening" : "Start voice input"}
                className={`grid h-12 w-12 flex-none place-items-center rounded-2xl ring-1 transition ${
                  listening
                    ? "bg-rose-500/25 text-rose-200 ring-rose-400/40"
                    : "bg-blue-500/20 text-blue-200 ring-blue-400/30 hover:brightness-125"
                }`}
              >
                {listening ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
              </button>

              <div className="flex flex-1 items-center gap-2 rounded-2xl bg-black/30 px-4 ring-1 ring-white/10 transition focus-within:ring-blue-400/40">
                <input
                  ref={inputRef}
                  value={input}
                  onChange={(e) => {
                    setInput(e.target.value);
                    setTranscriptReady(false);
                    setVoiceError("");
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      ask(input);
                    }
                  }}
                  placeholder="Ask Coolie in your own words…"
                  className="h-12 flex-1 bg-transparent text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none"
                />
                <span className="hidden font-mono text-[10px] text-slate-600 sm:block">
                  ENTER
                </span>
              </div>

              <button
                onClick={() => ask(input)}
                disabled={!input.trim() || busy}
                className="grid h-12 w-12 flex-none place-items-center rounded-2xl bg-blue-500/30 text-blue-50 ring-1 ring-blue-400/30 transition hover:bg-blue-500/50 disabled:cursor-not-allowed disabled:opacity-35"
                aria-label="Send"
              >
                <Send className="h-5 w-5" />
              </button>
            </div>
            <p aria-live="polite" className="mt-2 min-h-4 px-1 text-[10px]">
              {voiceError ? (
                <span className="text-amber-200">{voiceError}</span>
              ) : transcriptReady ? (
                <span className="text-blue-200">Transcript ready. Review your words, then send when you are ready.</span>
              ) : (
                <span className="text-slate-600">Push to talk or type freely. Voice transcripts are never sent automatically.</span>
              )}
            </p>
            {MOCK_MODE && (
              <p className="mt-2 flex items-start gap-1.5 rounded-lg bg-amber-400/[0.06] px-2.5 py-2 text-[10px] leading-relaxed text-amber-100/70 ring-1 ring-amber-400/15">
                <ShieldAlert className="mt-0.5 h-3 w-3 flex-none" />
                Demo mode: replies and tool traces are illustrative static examples. No live backend or external action is connected.
              </p>
            )}
          </HudFrame>

          {/* cognition panel */}
          <div className="mt-5">
            <CognitionPanel traces={traces} busy={busy} />
          </div>

          {/* traceability spine */}
          <div className="mt-4 flex flex-wrap items-center gap-2 rounded-2xl coolie-glass p-4">
            <p className="text-[11px] text-slate-400">
              Every answer traces to the record that produced it:
            </p>
            <div className="flex flex-wrap gap-1.5">
              {(
                [
                  ["mission", "Mission"],
                  ["opportunities", "Opportunity"],
                  ["evidence", "Evidence"],
                  ["decisions", "Decision"],
                  ["history", "Outcome"],
                ] as const
              ).map(([v, label]) => (
                <button
                  key={v}
                  onClick={() => go(v)}
                  className="rounded-md bg-white/[0.05] px-2 py-1 text-[10px] font-semibold text-blue-200 ring-1 ring-white/10 transition hover:bg-blue-400/15"
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* retrieved memory footer */}
          {memory.length > 0 && (
            <div className="mt-5 flex flex-wrap items-center gap-2">
              <span className="text-[10px] font-medium uppercase tracking-wider text-slate-600">
                Recalled from memory
              </span>
              {memory.map((m) => (
                <span
                  key={m}
                  className="rounded-md bg-white/[0.04] px-2 py-1 text-[10px] text-slate-400 ring-1 ring-white/[0.08]"
                >
                  {m}
                </span>
              ))}
            </div>
          )}
        </div>
        <GenerativeCanvas
          query={canvas?.query ?? ""}
          intent={canvas?.intent ?? null}
          pending={canvas?.pending ?? false}
          turn={canvas?.turn ?? 0}
        />
      </div>
    </div>
  );
}
