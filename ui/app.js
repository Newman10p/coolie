(() => {
  "use strict";

  const API_BASE_KEY = "coolie.apiBasePath";
  const THEME_KEY = "coolie.theme";
  const routes = {
    intel: "Intel zone",
    office: "Office table",
    businesses: "Businesses",
    departments: "Departments",
    decisions: "Decisions",
    reports: "Reports",
    settings: "Settings",
  };

  const demo = {
    briefing: {
      greeting: { name: "Amina", text: "A steady start to the day." },
      reportingPeriod: "Yesterday · 28 Sep",
      companyPulse: [
        { label: "Recorded revenue", value: "$426", detail: "+8.4% vs prior day", tone: "up" },
        { label: "Active businesses", value: "3", detail: "1 awaiting approval", tone: "neutral" },
        { label: "Available wallet", value: "$8,240", detail: "$1,760 reserved", tone: "neutral" },
        { label: "Realized profit", value: "$184", detail: "Actual · recorded", tone: "up" },
      ],
      criticalAlerts: [{
        title: "Activation needs your review",
        detail: "A proposed growth test for Nuru Goods requests $350. Review its evidence, exposure, and compliance status before deciding.",
        severity: "attention",
        target: "decisions",
        action: "Review decision",
      }],
      activeBusinesses: [
        { name: "Nuru Goods", category: "Commerce · Uganda", revenue: "$268", detail: "Revenue yesterday", status: "Active", tone: "healthy", mark: "N", color: "" },
        { name: "Kawa Studio", category: "Digital products", revenue: "$112", detail: "Revenue yesterday", status: "Testing", tone: "blue", mark: "K", color: "blue" },
        { name: "Safi Home", category: "Home essentials", revenue: "$46", detail: "Revenue yesterday", status: "Researching", tone: "warning", mark: "S", color: "gold" },
      ],
      pendingDecisions: [
        { title: "Nuru Goods · paid growth test", detail: "Finance & Activation · $350 exposure", time: "Expires in 5h", risk: "Medium risk" },
      ],
      sectorHealth: [
        { id: "brain", name: "Brain", status: "healthy", detail: "Inference ready", icon: "✳" },
        { id: "research_room", name: "Research Room", status: "healthy", detail: "2 missions running", icon: "⌕" },
        { id: "sector3_enactor", name: "Enactor", status: "healthy", detail: "No live actions", icon: "↗" },
        { id: "money_calculator", name: "Finance & Activation", status: "healthy", detail: "Ledger sample only", icon: "＄" },
        { id: "evolver", name: "Evolver", status: "healthy", detail: "Idle", icon: "⤴" },
        { id: "report_collector", name: "Report Collector", status: "healthy", detail: "Updated 4m ago", icon: "▧" },
      ],
      recentChanges: [
        { name: "Weekly business pulse", type: "Executive report · 28 Sep", freshness: "Current" },
        { name: "Nuru Goods market scan", type: "Research report · 28 Sep", freshness: "Current" },
        { name: "Safi Home supplier signals", type: "Research report · 27 Sep", freshness: "Aging" },
      ],
      freshness: "Sample data · generated for preview",
    },
    officeTable: {
      moneyMatrix: [
        { label: "Wallet available", value: "$8,240", kind: "Actual" },
        { label: "Reserved funds", value: "$1,760", kind: "Pending" },
        { label: "Committed funds", value: "$920", kind: "Actual" },
        { label: "Recorded revenue", value: "$426", kind: "Actual" },
        { label: "Recorded expenses", value: "$242", kind: "Actual" },
        { label: "Realized P/L", value: "+$184", kind: "Actual" },
        { label: "Current exposure", value: "$2,110", kind: "Pending" },
        { label: "Forecast result", value: "$1,240", kind: "Forecast" },
      ],
    },
    reports: [
      { name: "Weekly business pulse", type: "Executive", period: "22–28 Sep", freshness: "Current", summary: "Portfolio activity and operating signals for the week." },
      { name: "Nuru Goods market scan", type: "Research", period: "28 Sep", freshness: "Current", summary: "Demand signals, competitor notes, and evidence gaps." },
      { name: "Safi Home supplier signals", type: "Research", period: "27 Sep", freshness: "Aging", summary: "Supplier coverage is incomplete; treat estimates cautiously." },
    ],
  };

  let state = {
    route: "intel",
    mode: "demo",
    apiBase: localStorage.getItem(API_BASE_KEY) || "",
    briefing: null,
    officeTable: null,
    departments: null,
    reports: null,
    health: null,
    apiSample: false,
    loading: false,
    error: "",
    lastUpdated: new Date(),
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const root = $("#view-root");
  let voiceRecorder = null;
  let voiceStream = null;
  let voiceChunks = [];
  let voiceState = "idle";
  let discardVoiceOnStop = false;

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[char]);
  }

  function money(value) {
    if (typeof value === "number") return `$${value.toLocaleString("en-US")}`;
    if (value && typeof value === "object" && typeof value.amount === "number") {
      return `${escapeHtml(value.currency || "")} ${value.amount.toLocaleString("en-US")}`;
    }
    return escapeHtml(value ?? "—");
  }

  function dateLabel(date = new Date()) {
    return new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric" }).format(date);
  }

  function shortTime(date) {
    return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(date);
  }

  function effectiveBriefing() {
    return state.mode === "demo" ? demo.briefing : state.briefing;
  }

  function showToast(message, timeout = 3600) {
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;
    $("#toast-region").append(toast);
    window.setTimeout(() => toast.remove(), timeout);
  }

  function validApiBase(value) {
    const path = value.trim();
    if (!path) return "";
    if (!path.startsWith("/") || path.startsWith("//") || path.includes("..") || /[?#\\]/.test(path)) {
      throw new Error("Use a same-origin path such as /api. External URLs are not accepted.");
    }
    return path.replace(/\/+$/, "");
  }

  function endpoint(path) {
    return `${state.apiBase}${path}`;
  }

  async function requestJson(path, options = {}) {
    const allowUnavailable = options.allowUnavailable === true;
    const requestOptions = { ...options };
    delete requestOptions.allowUnavailable;
    const response = await fetch(endpoint(path), {
      ...requestOptions,
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        ...(requestOptions.body && !(requestOptions.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
        ...requestOptions.headers,
      },
    });
    const text = await response.text();
    let payload;
    try { payload = text ? JSON.parse(text) : {}; }
    catch { throw new Error(`Service returned invalid JSON (${response.status}).`); }
    if (!response.ok && !(allowUnavailable && response.status === 503)) {
      throw new Error(payload.error || payload.reason || `Request failed (${response.status}).`);
    }
    return payload;
  }

  function setVoiceState(nextState, message) {
    voiceState = nextState;
    const room = $("#voice-room");
    room.classList.toggle("is-listening", nextState === "listening");
    room.classList.toggle("is-thinking", nextState === "transcribing" || nextState === "thinking");
    room.classList.toggle("is-speaking", nextState === "speaking");
    room.classList.toggle("has-error", nextState === "error");
    $("#voice-status").textContent = `${nextState[0].toUpperCase()}${nextState.slice(1)} · ${message}`;
    const active = nextState === "listening";
    $("#voice-toggle").setAttribute("aria-pressed", String(active));
    $("#voice-toggle-label").textContent = active ? "Stop & transcribe" : "Start speaking";
  }

  async function toggleVoiceCapture() {
    if (voiceRecorder?.state === "recording") {
      setVoiceState("transcribing", "Preparing your recording");
      voiceRecorder.stop();
      return;
    }
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setVoiceState("error", "Microphone capture is unavailable in this browser or context. You can type your message below.");
      return;
    }
    try {
      voiceStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      voiceChunks = [];
      voiceRecorder = new MediaRecorder(voiceStream);
      voiceRecorder.addEventListener("dataavailable", (event) => {
        if (event.data.size > 0) voiceChunks.push(event.data);
      });
      voiceRecorder.addEventListener("error", () => {
        voiceStream?.getTracks().forEach((track) => track.stop());
        voiceStream = null;
        setVoiceState("error", "Microphone recording failed. Your text draft is still available.");
      }, { once: true });
      voiceRecorder.addEventListener("stop", async () => {
        const stream = voiceStream;
        voiceStream = null;
        stream?.getTracks().forEach((track) => track.stop());
        const recording = new Blob(voiceChunks, { type: voiceRecorder?.mimeType || "application/octet-stream" });
        voiceChunks = [];
        if (discardVoiceOnStop) {
          discardVoiceOnStop = false;
          return;
        }
        if (!recording.size) {
          setVoiceState("error", "No audio was captured. Try again or type your message.");
          return;
        }
        if (state.mode !== "live" || state.apiSample || !state.apiBase) {
          setVoiceState("error", "No speech-to-text service is connected. The recording was discarded without upload.");
          return;
        }
        try {
          setVoiceState("transcribing", "Sending audio to the configured owner backend for transcription");
          const audio = new FormData();
          const audioExtension = recording.type.includes("mp4") ? "m4a"
            : recording.type.includes("ogg") ? "ogg"
              : recording.type.includes("wav") ? "wav" : "webm";
          audio.append("audio", recording, `voice-message.${audioExtension}`);
          const result = await requestJson("/orchestrator/transcribe", { method: "POST", body: audio });
          if (typeof result.transcript !== "string" || !result.transcript.trim()) {
            throw new Error("The transcription service returned no transcript.");
          }
          $("#orchestrator-prompt").value = result.transcript.trim();
          $("#voice-transcript").textContent = result.transcript.trim();
          setVoiceState("idle", "Transcript ready. Review the words, then choose Send.");
          $("#orchestrator-prompt").focus();
        } catch (error) {
          setVoiceState("error", error.message);
        }
      }, { once: true });
      voiceRecorder.start();
      $("#voice-transcript").textContent = "Listening… your transcript will appear here after transcription.";
      setVoiceState("listening", "Listening. Press Stop & transcribe when you are done.");
    } catch (error) {
      setVoiceState("error", error.name === "NotAllowedError"
        ? "Microphone permission was denied. You can still type your message."
        : `Microphone could not be started: ${error.message}`);
    }
  }

  function speakResponse(text, waitingForApproval) {
    if (!$("#spoken-response").checked || !("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) {
      setVoiceState(waitingForApproval ? "waiting for approval" : "idle", waitingForApproval
        ? "The backend says this response needs owner approval."
        : "Response received from the configured owner backend.");
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.addEventListener("end", () => {
      setVoiceState(waitingForApproval ? "waiting for approval" : "idle", waitingForApproval
        ? "Spoken response complete. Owner approval is still required."
        : "Spoken response complete.");
    }, { once: true });
    utterance.addEventListener("error", () => setVoiceState("error", "Speech output failed; the text response remains available."), { once: true });
    setVoiceState("speaking", "Speaking the backend response");
    window.speechSynthesis.speak(utterance);
  }

  async function sendOrchestratorMessage() {
    const input = $("#orchestrator-prompt");
    const message = input.value.trim();
    if (!message) {
      input.focus();
      setVoiceState("error", "Type or dictate a message first.");
      return;
    }
    if (state.mode !== "live" || state.apiSample || !state.apiBase) {
      setVoiceState("error", "Connect a real owner API to submit this draft. Nothing was sent.");
      return;
    }
    $("#voice-response").hidden = true;
    $("#orchestrator-send").disabled = true;
    setVoiceState("thinking", "Waiting for the owner backend");
    try {
      const result = await requestJson("/orchestrator/messages", {
        method: "POST",
        body: JSON.stringify({ message }),
      });
      if (typeof result.message !== "string" || !result.message.trim()) {
        throw new Error("The Orchestrator endpoint returned no text response.");
      }
      $("#voice-response").textContent = result.message;
      $("#voice-response").hidden = false;
      input.value = "";
      speakResponse(result.message, result.requiresApproval === true);
    } catch (error) {
      setVoiceState("error", `${error.message} Your draft was kept.`);
    } finally {
      $("#orchestrator-send").disabled = false;
    }
  }

  function initializeVoiceControls() {
    const captureAvailable = window.isSecureContext && Boolean(navigator.mediaDevices?.getUserMedia) && Boolean(window.MediaRecorder);
    $("#voice-toggle").disabled = !captureAvailable;
    $("#voice-capability").textContent = captureAvailable
      ? "Audio is sent only to the configured owner backend after you stop recording. Local preview recordings are discarded without upload."
      : "This browser cannot capture audio here. Text input remains available.";
    if (!("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) {
      $("#spoken-response").disabled = true;
      $("#spoken-response").parentElement.title = "Speech output is not supported in this browser.";
    }
  }

  async function connectLive() {
    state.apiBase = validApiBase(state.apiBase);
    if (!state.apiBase) throw new Error("Set the same-origin API base path in Settings first.");
    const ready = await requestJson("/health/ready", { allowUnavailable: true });
    state.health = ready;
    const [briefingResult, officeResult, reportResult] = await Promise.allSettled([
      requestJson("/ui/briefing"),
      requestJson("/ui/office-table"),
      requestJson("/ui/reports"),
    ]);
    state.apiSample = [
      ready,
      briefingResult.status === "fulfilled" ? briefingResult.value : null,
      officeResult.status === "fulfilled" ? officeResult.value : null,
      reportResult.status === "fulfilled" ? reportResult.value : null,
    ].some((payload) => payload?.dataMode === "sample");
    state.briefing = briefingResult.status === "fulfilled" ? briefingResult.value : null;
    state.officeTable = officeResult.status === "fulfilled" ? officeResult.value : null;
    if (reportResult.status === "fulfilled") {
      const reportPayload = reportResult.value;
      state.reports = Array.isArray(reportPayload)
        ? reportPayload
        : reportPayload && typeof reportPayload === "object" && Array.isArray(reportPayload.reports)
          ? reportPayload.reports
          : null;
    }
    const failures = [briefingResult, officeResult, reportResult]
      .filter((item) => item.status === "rejected")
      .map((item) => item.reason.message);
    if (reportResult.status === "fulfilled" && !state.reports) {
      failures.push("Reports endpoint returned an unexpected response shape.");
    }
    state.departments = Array.isArray(ready.services) ? ready.services : [];
    state.mode = "live";
    state.error = failures.length
      ? `Some owner views are not exposed by this backend yet: ${failures.join(" · ")}`
      : "";
    state.lastUpdated = new Date();
    render();
    if (state.error) showToast("Connected. Some live UI endpoints are not available yet.");
    else showToast("Connected to the owner API.");
  }

  async function refreshLive() {
    if (!state.apiBase) {
      showToast("Set an API path in Settings to connect live data.");
      return;
    }
    state.loading = true;
    state.error = "";
    render();
    try {
      await connectLive();
    } catch (error) {
      state.mode = "live";
      state.error = error.message;
      state.health = null;
      state.apiSample = false;
      state.briefing = null;
      state.officeTable = null;
      state.departments = null;
      state.reports = null;
      render();
      showToast("Live refresh failed. Data has not been replaced with sample values.");
    } finally {
      state.loading = false;
      updateShell();
    }
  }

  function heading(eyebrow, title, subtitle, action = "") {
    return `<div class="page-heading"><div><p class="eyebrow">${escapeHtml(eyebrow)}</p><h1>${escapeHtml(title)}</h1><p class="page-subtitle">${escapeHtml(subtitle)}</p></div>${action}</div>`;
  }

  function demoNotice() {
    return state.mode === "demo"
      ? `<div class="demo-notice"><span class="notice-icon">i</span><span><strong>Preview workspace.</strong> Everything on this screen is sample data. It does not reflect your real business, wallet, approvals, or sector health.</span><button class="notice-action" data-route-button="settings">Connect API →</button></div>`
      : state.apiSample
        ? `<div class="demo-notice"><span class="notice-icon">i</span><span><strong>Sample API data.</strong> This local preview API returns fabricated example records only. It is not connected to your business, wallet, approvals, or sector health, and it cannot perform owner actions.${state.error ? ` <strong>Some views are unavailable.</strong> ${escapeHtml(state.error)}` : ""}</span></div>`
      : state.error
        ? `<div class="demo-notice"><span class="notice-icon">!</span><span><strong>Live connection incomplete.</strong> ${escapeHtml(state.error)} No sample data is shown in live mode.</span><button class="notice-action" data-route-button="settings">Review connection →</button></div>`
        : "";
  }

  function statusPill(label, tone = "neutral") {
    return `<span class="state-pill ${escapeHtml(tone)}"><i class="pill-dot"></i>${escapeHtml(label)}</span>`;
  }

  function chartSvg() {
    return `<div class="chart-wrap" role="img" aria-label="Sample recorded revenue trend. Forecast is shown separately and is not actual revenue.">
      <svg viewBox="0 0 600 150" preserveAspectRatio="none" aria-hidden="true">
        <defs><linearGradient id="chart-fade" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#2869a8" stop-opacity=".24"/><stop offset="100%" stop-color="#2869a8" stop-opacity="0"/></linearGradient></defs>
        <line class="chart-gridline" x1="0" y1="20" x2="600" y2="20"/><line class="chart-gridline" x1="0" y1="57" x2="600" y2="57"/><line class="chart-gridline" x1="0" y1="94" x2="600" y2="94"/><line class="chart-gridline" x1="0" y1="130" x2="600" y2="130"/>
        <text class="chart-label" x="0" y="15">$600</text><text class="chart-label" x="0" y="52">$400</text><text class="chart-label" x="0" y="89">$200</text>
        <path class="chart-area" d="M48 105 C83 92 92 80 127 88 S177 71 210 79 S261 62 293 71 S346 58 379 69 S428 48 462 59 S511 35 548 49 L548 130 L48 130 Z"/>
        <path class="chart-actual" d="M48 105 C83 92 92 80 127 88 S177 71 210 79 S261 62 293 71 S346 58 379 69 S428 48 462 59 S511 35 548 49"/>
        <path class="chart-forecast" d="M548 49 C565 42 575 37 593 32"/>
        <circle cx="548" cy="49" r="3.5" fill="#428362" stroke="var(--surface)" stroke-width="2"/>
        <text class="chart-label" x="45" y="146">22 SEP</text><text class="chart-label" x="165" y="146">24 SEP</text><text class="chart-label" x="285" y="146">26 SEP</text><text class="chart-label" x="405" y="146">28 SEP</text><text class="chart-label" x="530" y="146">TODAY</text>
      </svg>
    </div>`;
  }

  function businessRows(businesses = []) {
    if (!businesses.length) return `<div class="empty-state"><span>▤</span><h2>No business records</h2><p>The owner API did not return any businesses.</p></div>`;
    return businesses.map((business) => {
      const tone = business.tone || (business.status === "active" ? "healthy" : "neutral");
      const status = business.status || "Unknown";
      return `<div class="business-row"><span class="business-logo ${escapeHtml(business.color || "")}">${escapeHtml(business.mark || business.name?.slice(0, 1) || "?")}</span><span class="business-main"><strong>${escapeHtml(business.name || "Unnamed business")}</strong><small>${escapeHtml(business.category || business.detail || "")}</small></span><span class="business-revenue"><strong>${money(business.revenue)}</strong><small>${escapeHtml(business.revenueLabel || business.detail || "Recorded revenue")}</small></span>${statusPill(status, tone)}</div>`;
    }).join("");
  }

  function decisionRows(decisions = []) {
    if (!decisions.length) return `<div class="empty-state"><span>☷</span><h2>Nothing waiting on you</h2><p>Owner decisions will appear here with their target, risk, and evidence.</p></div>`;
    return decisions.map((decision) => `<div class="decision-row"><span class="decision-marker"></span><span class="decision-content"><strong>${escapeHtml(decision.title || decision.action || "Decision requires review")}</strong><small>${escapeHtml(decision.detail || decision.target || "Evidence and approval details available")}</small></span><span class="decision-meta"><strong>${escapeHtml(decision.time || decision.expiresAt || "Pending")}</strong><small>${escapeHtml(decision.risk || decision.riskLevel || "Review required")}</small></span></div>`).join("");
  }

  function sectorItems(sectors = []) {
    return sectors.map((sector) => {
      const name = sector.name || sector.service || sector.sectorId || "Sector";
      const raw = sector.status || sector.readiness || "not_configured";
      const tone = ["healthy", "ready"].includes(String(raw).toLowerCase()) ? "healthy"
        : ["offline", "dead"].includes(String(raw).toLowerCase()) ? "offline" : "warning";
      const detail = sector.detail || sector.reason || sector.activeWorkCount !== undefined
        ? (sector.detail || sector.reason || `${sector.activeWorkCount || 0} active · ${sector.pendingAttentionCount || 0} needs attention`)
        : "No status details";
      return `<a class="sector-mini" href="#departments" data-route="departments"><span class="sector-icon">${escapeHtml(sector.icon || "⌘")}</span><span><strong>${escapeHtml(name)}</strong><small>${escapeHtml(detail)}</small></span><i class="status-dot ${tone === "healthy" ? "" : tone}"></i></a>`;
    }).join("");
  }

  function reportRows(reports = []) {
    if (!reports.length) return `<div class="empty-state"><span>▧</span><h2>No reports available</h2><p>Reports appear when the Report Collector API is connected.</p></div>`;
    return reports.slice(0, 4).map((report) => `<div class="report-row"><span class="report-icon">▧</span><span><strong>${escapeHtml(report.name || report.title || report.reportType || "Untitled report")}</strong><small>${escapeHtml(report.type || report.reportType || "Report")} · ${escapeHtml(report.period || report.generatedAt || "Period unavailable")}</small></span><span class="freshness ${(report.freshness || "").toLowerCase() === "aging" ? "stale" : ""}">● ${escapeHtml(report.freshness || "Freshness unknown")}</span></div>`).join("");
  }

  function renderIntel() {
    const data = effectiveBriefing();
    if (!data) return emptyLive("Executive briefing is not available", "The live owner briefing endpoint has not returned data. Connect an API that implements GET /api/ui/briefing.");
    const greeting = data.greeting || {};
    const pulse = data.companyPulse || [];
    const businesses = data.activeBusinesses || [];
    const decisions = data.pendingDecisions || [];
    const sectors = state.mode === "live"
      ? (state.departments || data.sectorHealth || [])
      : data.sectorHealth || [];
    const alerts = data.criticalAlerts || [];
    const metricCards = pulse.slice(0, 4).map((metric) => `<article class="card metric-card span-3"><div class="metric-top"><span class="metric-label">${escapeHtml(metric.label)}</span><span class="metric-type">${escapeHtml(metric.basis || "ACTUAL")}</span></div><div class="metric-value">${money(metric.value)}</div><div class="metric-foot">${metric.tone === "up" ? `<span class="up">↗ ${escapeHtml(metric.detail || "")}</span>` : `<span>${escapeHtml(metric.detail || "")}</span>`}</div></article>`).join("");
    const firstAlert = alerts[0];
    return `${heading(`OWNER BRIEFING · ${data.reportingPeriod || "CURRENT PERIOD"}`, greeting.text || `Good ${new Date().getHours() < 12 ? "morning" : "afternoon"}, ${greeting.name || "there"}.`, "A clear view of what is happening across your businesses.", `<span class="heading-meta"><i class="status-dot ${state.mode === "live" && state.health?.ready === false ? "warning" : ""}"></i>${escapeHtml(state.mode === "demo" ? "Sample workspace" : state.health?.status || "Connected")}</span>`)}
      ${demoNotice()}
      <div class="grid overview-grid">${metricCards}
        <article class="card card-pad pulse-card span-8">
          <div class="card-heading pulse-header"><div><h2>Company pulse</h2><p class="subheading">Recorded revenue · actuals only</p></div><div class="chart-legend"><span><i class="legend-point"></i>Actual</span><span><i class="legend-point forecast"></i>Forecast</span></div><select class="period-select" aria-label="Select pulse period"><option>7 days</option><option>30 days</option></select></div>
          ${state.mode === "demo" ? chartSvg() : `<div class="empty-state"><span>⌁</span><h2>Trend not available</h2><p>The connected briefing has not supplied a time series. No trend is inferred in the browser.</p></div>`}
          <div class="pulse-summary"><span>Reported period<strong>${escapeHtml(data.reportingPeriod || "Not provided")}</strong></span><span>Source<strong>${escapeHtml(data.source || "Owner briefing")}</strong></span><span>Freshness<strong>${escapeHtml(data.freshness || "Not provided")}</strong></span></div>
        </article>
        <article class="card card-pad span-4">
          <div class="card-heading"><div><h2>Needs your attention</h2><p class="subheading">${alerts.length} item${alerts.length === 1 ? "" : "s"} · owner review</p></div><span class="icon-soft">!</span></div>
          ${firstAlert ? `<div class="alert-title-row"><span class="alert-symbol">!</span><div><strong>${escapeHtml(firstAlert.title || firstAlert.summary || "Attention required")}</strong><p>${escapeHtml(firstAlert.detail || firstAlert.summary || "Review the related item and its evidence.")}</p></div></div><div class="alert-action"><button class="button button-secondary" data-route-button="${escapeHtml(firstAlert.target || "decisions")}">${escapeHtml(firstAlert.action || "Review item")} →</button></div>` : `<div class="empty-state"><span>✓</span><h2>No critical alerts</h2><p>Nothing urgent has been reported.</p></div>`}
        </article>
        <article class="card card-pad span-6"><div class="card-heading"><div><h2>Your businesses</h2><p class="subheading">Portfolio snapshot · recorded values</p></div><button class="quiet-link" data-route-button="businesses">View portfolio →</button></div><div class="business-list">${businessRows(businesses)}</div></article>
        <article class="card card-pad span-6"><div class="card-heading"><div><h2>Decision tray</h2><p class="subheading">Consequential actions wait for owner review</p></div><button class="quiet-link" data-route-button="decisions">All decisions →</button></div><div>${decisionRows(decisions)}</div></article>
        <article class="card card-pad span-7"><div class="card-heading"><div><h2>Department hall</h2><p class="subheading">Sector status reported by the system</p></div><button class="quiet-link" data-route-button="departments">All departments →</button></div><div class="sector-list">${sectors.length ? sectorItems(sectors.slice(0, 6)) : `<p class="field-hint">No sector health has been reported.</p>`}</div></article>
        <article class="card card-pad span-5"><div class="card-heading"><div><h2>Recent reports</h2><p class="subheading">Source and freshness stay visible</p></div><button class="quiet-link" data-route-button="reports">Report library →</button></div><div class="report-list">${reportRows(data.recentChanges || [])}</div></article>
      </div>
      <p class="field-hint" style="margin:14px 2px 0">Forecasts are not wallet balances. Recorded financial values require a source and reporting period; missing live data is shown as missing, not estimated.</p>`;
  }

  function renderOffice() {
    const office = state.mode === "demo" ? demo.officeTable : state.officeTable;
    if (!office) return emptyLive("Office table data is unavailable", "The live owner API has not returned GET /api/ui/office-table.");
    const matrix = office.moneyMatrix || [];
    const businesses = office.portfolio || (state.mode === "demo" ? demo.briefing.activeBusinesses : []);
    const decisions = office.decisions || (state.mode === "demo" ? demo.briefing.pendingDecisions : []);
    const activeWork = office.activeWork || [];
    const progress = office.researchProgress || {};
    const evolver = office.evolverProgress || {};
    return `${heading("OPERATING OVERVIEW", "Office table", "Portfolio, capital, decisions, and active work in one grounded view.", `<span class="heading-meta">Actuals, forecasts, and pending amounts are kept distinct</span>`)}${demoNotice()}
      <div class="grid overview-grid">
        <article class="card card-pad span-12"><div class="card-heading"><div><h2>Money matrix</h2><p class="subheading">${state.apiSample ? "Fabricated sample amounts · no ledger connected" : "Actual wallet state is not combined with forecasted revenue"}</p></div>${statusPill(office.reconciliationStatus || (state.mode === "demo" ? "Sample only" : "Status unavailable"), office.reconciliationStatus === "reconciled" ? "healthy" : "warning")}</div>
          <div class="money-matrix-orbit" aria-hidden="true"><span class="orbit-ring"></span><span class="orbit-core">FINANCE<br><small>LEDGER VIEW</small></span><span class="orbit-marker marker-one"></span><span class="orbit-marker marker-two"></span></div>
          ${matrix.length ? `<div class="money-grid">${matrix.map((item) => `<div class="money-cell"><small>${escapeHtml(item.label)}</small><strong>${money(item.value)}</strong><span class="metric-type">${escapeHtml(item.kind || item.basis || "BASIS UNKNOWN")}</span></div>`).join("")}</div>` : `<div class="empty-state"><span>＄</span><h2>Wallet and ledger data unavailable</h2><p>The connected API has not supplied finance balances. Do not treat forecasts as available funds.</p></div>`}
        </article>
        <article class="card card-pad span-6"><div class="card-heading"><div><h2>Business portfolio</h2><p class="subheading">Current operating stage</p></div><button class="quiet-link" data-route-button="businesses">Open portfolio →</button></div><div class="business-list">${businessRows(businesses)}</div></article>
        <article class="card card-pad span-6"><div class="card-heading"><div><h2>Decision tray</h2><p class="subheading">Backend-owned approvals and compliance gates</p></div><button class="quiet-link" data-route-button="decisions">Review queue →</button></div>${decisionRows(decisions)}</article>
        <article class="card card-pad span-6"><div class="card-heading"><div><h2>Active work</h2><p class="subheading">Running tasks and executions</p></div></div>${activeWork.length ? `<div class="report-list">${activeWork.map((item) => `<div class="report-row"><span class="report-icon">⌁</span><span><strong>${escapeHtml(item.title || item.objective || item.executionId || item.taskId)}</strong><small>${escapeHtml(item.sector || item.business || "Sector unknown")} · ${escapeHtml(item.status || "Status unknown")}</small></span>${statusPill(item.status || "Unknown", "blue")}</div>`).join("")}</div>` : `<div class="empty-state"><span>⌁</span><h2>No live work reported</h2><p>No tasks are currently available from the connected owner API.</p></div>`}</article>
        <article class="card card-pad span-6"><div class="card-heading"><div><h2>Expansion & research</h2><p class="subheading">Progress and blockers</p></div></div><div class="detail-list"><div class="detail-line"><span>Research missions</span><strong>${escapeHtml(progress.active || progress.activeCount || "—")} active</strong></div><div class="detail-line"><span>Evidence gaps</span><strong>${escapeHtml(progress.gaps || progress.gapCount || "Not reported")}</strong></div><div class="detail-line"><span>Capability proposals</span><strong>${escapeHtml(evolver.proposals || evolver.proposalCount || "Not reported")}</strong></div><div class="detail-line"><span>Current release</span><strong>${escapeHtml(evolver.releaseState || "Not reported")}</strong></div></div></article>
      </div>`;
  }

  const departments = [
    { id: "brain", name: "Brain", icon: "✳", description: "Shared intelligence, provider routing, memory, and policy.", focus: "Inference · context · routing" },
    { id: "research_room", name: "Research Room", icon: "⌕", description: "Evidence discovery, opportunity evaluation, and research handoffs.", focus: "Missions · evidence · reports" },
    { id: "sector3_enactor", name: "Enactor", icon: "↗", description: "Approval-bound execution through the controlled tool gateway.", focus: "Plans · tasks · external actions" },
    { id: "money_calculator", name: "Finance & Activation", icon: "＄", description: "Spend, margin, financial forecasts, and activation proposals.", focus: "Wallet · exposure · activation" },
    { id: "evolver", name: "Evolver", icon: "⤴", description: "Capability gaps, extension plans, testing, and release proposals.", focus: "Extensions · sandbox · review" },
    { id: "report_collector", name: "Report Collector", icon: "▧", description: "Cross-system health, reports, alerts, and source freshness.", focus: "Telemetry · reports · incidents" },
  ];

  function renderDepartments() {
    const liveStatuses = state.mode === "live" ? new Map((state.departments || []).map((item) => [item.service || item.sectorId, item])) : null;
    return `${heading("SYSTEM MAP", "Department hall", "Six specialist sectors. The Orchestrator remains the executive interface, not a department.", `<span class="heading-meta"><i class="status-dot ${state.mode === "demo" || state.apiSample ? "warning" : ""}"></i>${state.mode === "demo" || state.apiSample ? "Sample statuses" : "Live readiness view"}</span>`)}${demoNotice()}
      <div class="executive-card"><span class="orchestrator-avatar">✳</span><span><strong>Orchestrator · executive control plane</strong><small>Business authority, decisions, budgets, mandates, and escalation.</small></span><button class="button button-secondary" id="open-orchestrator-inline">Open ↗</button></div>
      <div class="section-grid">${departments.map((sector) => {
        const health = liveStatuses?.get(sector.id);
        const status = state.mode === "demo" ? "healthy" : health?.status || "not_configured";
        const tone = status === "healthy" || status === "ready" ? "healthy" : status === "offline" || status === "dead" ? "danger" : "warning";
        const active = health?.activeWorkCount ?? (state.mode === "demo" ? (sector.id === "research_room" ? 2 : 0) : "—");
        const needs = health?.pendingAttentionCount ?? (state.mode === "demo" && sector.id === "money_calculator" ? 1 : state.mode === "demo" ? 0 : "—");
        return `<article class="card department-card sector-status-${tone}"><div class="department-top"><span class="department-icon">${sector.icon}</span>${statusPill(status.replaceAll("_", " "), tone)}</div><h2>${sector.name}</h2><p>${sector.description}</p><div class="department-metrics"><span><strong>${escapeHtml(active)}</strong>Active work</span><span><strong>${escapeHtml(needs)}</strong>Needs attention</span><span><strong>${escapeHtml(sector.focus)}</strong>Scope</span></div></article>`;
      }).join("")}</div>`;
  }

  function renderBusinesses() {
    const businesses = state.mode === "demo" ? demo.briefing.activeBusinesses : state.briefing?.activeBusinesses;
    if (!businesses) return `${heading("PORTFOLIO", "Businesses", "A business workspace keeps strategy, finance, operations, and decisions together.")}${demoNotice()}${emptyLive("Portfolio data is unavailable", "The connected owner API has not supplied the businesses read model.")}`;
    const statuses = ["All", "Researching", "Awaiting approval", "Testing", "Active", "Paused", "Stopped", "Scaling"];
    return `${heading("PORTFOLIO", "Businesses", "A business workspace keeps strategy, finance, operations, and decisions together.", `<button class="button button-primary" id="add-business">＋ Add business</button>`)}${demoNotice()}
      <div class="card card-pad"><div class="card-heading"><div><h2>Portfolio</h2><p class="subheading">${businesses.length} businesses · current snapshot</p></div><select class="period-select" id="business-filter" aria-label="Filter businesses">${statuses.map((status) => `<option>${status}</option>`).join("")}</select></div><div class="section-grid" id="business-cards">${businesses.map((business) => `<article class="card business-card"><div class="business-card-head"><span class="business-logo ${escapeHtml(business.color || "")}">${escapeHtml(business.mark || business.name.slice(0, 1))}</span><div><h2>${escapeHtml(business.name)}</h2><p>${escapeHtml(business.category)}</p></div>${statusPill(business.status, business.tone)}</div><div class="business-card-foot"><span>Recorded revenue</span><strong>${money(business.revenue)}</strong></div><div class="business-card-foot"><span>Current stage</span><span>${escapeHtml(business.status)}</span></div><div class="business-card-foot"><span>Source period</span><span>${escapeHtml(state.mode === "demo" ? "Sample · 28 Sep" : business.period || "Not provided")}</span></div></article>`).join("")}</div></div>`;
  }

  function renderDecisions() {
    const decisions = (state.mode === "demo" ? demo.briefing.pendingDecisions : state.briefing?.pendingDecisions) || [];
    return `${heading("OWNER REVIEW", "Decisions", "Review exact action, target, risk, budget, compliance, evidence, and expiry.", `<span class="heading-meta">${decisions.length} waiting</span>`)}${demoNotice()}
      <div class="grid overview-grid">      <article class="card card-pad span-8 approval-document"><div class="card-heading"><div><h2>Pending approvals</h2><p class="subheading">An approval is never executed by the interface alone</p></div></div>${decisions.length ? decisions.map((decision, index) => `<article class="card card-pad detail-panel"><div class="card-heading"><div><h2>${escapeHtml(decision.title || decision.action || "Decision")}</h2><p class="subheading">${escapeHtml(decision.detail || decision.target || "Target unavailable")}</p></div>${statusPill("Pending", "warning")}</div><div class="detail-list"><div class="detail-line"><span>Target</span><strong>${escapeHtml(decision.target || "Not returned")}</strong></div><div class="detail-line"><span>Risk</span><strong>${escapeHtml(decision.risk || decision.riskLevel || "Not returned")}</strong></div><div class="detail-line"><span>Budget / exposure</span><strong>${escapeHtml(decision.budget || decision.exposure || "Not returned")}</strong></div><div class="detail-line"><span>Compliance</span><strong>${escapeHtml(decision.complianceStatus || "Not returned")}</strong></div><div class="detail-line"><span>Expires</span><strong>${escapeHtml(decision.expiresAt || decision.time || "Not returned")}</strong></div><div class="detail-line"><span>Evidence references</span><strong>${escapeHtml((decision.evidenceRefs || []).join(", ") || "Not returned")}</strong></div></div><div class="settings-actions" style="justify-content:flex-end;margin-top:14px"><button class="button button-secondary" data-review-decision="${index}">Inspect request</button><button class="button button-primary" data-review-decision="${index}">Open approval details</button></div></article>`).join("") : `<div class="empty-state"><span>✓</span><h2>No pending owner decisions</h2><p>New decisions will appear with their exact binding and supporting evidence.</p></div>`}</article>
        <aside class="card card-pad span-4"><div class="card-heading"><h2>Before you approve</h2></div><div class="detail-list"><div class="detail-line"><span>Exact action and target</span><strong>Required</strong></div><div class="detail-line"><span>Budget and exposure cap</span><strong>Required</strong></div><div class="detail-line"><span>Compliance review</span><strong>Required</strong></div><div class="detail-line"><span>Evidence and expiry</span><strong>Required</strong></div></div><p class="field-hint" style="margin-top:14px">The UI does not grant authority. Backend policy revalidates approval scope, expiry, budget, and action binding before execution.</p></aside></div>`;
  }

  function renderReports() {
    const reports = state.mode === "demo" ? demo.reports : state.reports;
    return `${heading("SYSTEM OUTPUT", "Reports", "Owner briefings and sector reports with their period, source freshness, and limitations.")}${demoNotice()}
      <div class="card card-pad"><div class="card-heading"><div><h2>Report library</h2><p class="subheading">Historical reports should remain reproducible and immutable</p></div><select class="period-select" aria-label="Filter report type"><option>All reports</option><option>Executive</option><option>Business</option><option>Financial</option><option>Execution</option><option>Research</option><option>Evolver</option></select></div>
        ${reports?.length ? `<div class="table-wrap"><table><thead><tr><th>Report</th><th>Type</th><th>Period</th><th>Freshness</th><th>Summary</th></tr></thead><tbody>${reports.map((report) => `<tr><td><strong>${escapeHtml(report.name || report.title || report.reportType)}</strong></td><td>${escapeHtml(report.type || report.reportType || "Unknown")}</td><td>${escapeHtml(report.period || report.generatedAt || "Not provided")}</td><td>${statusPill(report.freshness || "Unknown", (report.freshness || "").toLowerCase() === "current" ? "healthy" : "warning")}</td><td>${escapeHtml(report.summary || report.limitations?.join("; ") || "No summary provided")}</td></tr>`).join("")}</tbody></table></div>` : emptyLive("Reports are unavailable", "The connected owner API has not supplied the report read model.")}</div>`;
  }

  function renderSettings() {
    const paused = state.health?.paused === true || state.mode === "live" && state.health?.ready === false;
    return `${heading("OWNER CONTROLS", "Settings", "Configure a same-origin API connection and inspect the system boundary.")}${demoNotice()}
      <div class="grid overview-grid">
        <article class="card card-pad span-7"><div class="card-heading"><div><h2>Backend connection</h2><p class="subheading">${state.apiSample ? "Connected to a local sample fixture; no sector services are called" : "Live mode reads from an owner-facing BFF; sector services are not called directly"}</p></div>${statusPill(state.apiSample ? "Sample API" : state.mode === "live" ? "Live mode" : "Demo mode", state.mode === "live" && !state.apiSample ? "healthy" : "warning")}</div>
          <form class="connection-form" id="connection-form"><div class="field"><label for="api-base">Same-origin API base path</label><input id="api-base" name="api-base" type="text" value="${escapeHtml(state.apiBase)}" placeholder="/api" autocomplete="url"><span class="field-hint">Example: <code>/api</code>. This UI refuses external origins. Do not enter or store provider keys or passwords here.</span></div><div class="field-hint">Run <code>python -m ui.demo_server</code> from the repository root and use <code>/api</code> to connect to the local preview API. Its briefing, office, report, and health responses contain fabricated sample data only. It is not connected to Coolie's business state, and emergency controls are disabled. A production owner BFF must aggregate real read models and authorize controls independently.</div><div class="settings-actions"><button class="button button-primary" type="submit" id="connect-button">Connect & refresh</button><button class="button button-secondary" type="button" id="use-demo">Use preview data</button></div><div id="connection-error" class="field-error" role="status"></div></form>
        </article>
        <article class="card card-pad span-5"><div class="card-heading"><div><h2>System safety</h2><p class="subheading">Emergency controls require backend authentication</p></div><span class="icon-soft">⌑</span></div><div class="detail-list"><div class="detail-line"><span>Current mode</span><strong>${escapeHtml(state.mode === "demo" ? "Preview · no backend" : state.apiSample ? "Sample API · no real system" : "Connected owner API")}</strong></div><div class="detail-line"><span>Readiness</span><strong>${escapeHtml(state.apiSample ? "Sample only · not measured" : state.health?.status || "Not checked")}</strong></div><div class="detail-line"><span>Emergency pause</span><strong>${state.apiSample ? "Unavailable in sample mode" : state.health?.paused ? "Active" : "Not reported"}</strong></div></div><div class="settings-actions" style="margin-top:17px"><button class="button button-danger" id="pause-system" ${state.mode !== "live" || !state.apiBase || state.apiSample ? "disabled" : ""}>Pause all new work</button><button class="button button-secondary" id="resume-system" ${state.mode !== "live" || !state.apiBase || state.apiSample || !state.health?.paused ? "disabled" : ""}>Resume</button></div><p class="field-hint" style="margin-top:10px">The local sample API cannot change system state. A real backend must authenticate and authorize owner control requests.</p></article>
        <article class="card card-pad span-6"><div class="card-heading"><div><h2>UI guardrails</h2><p class="subheading">Presentation is not authority</p></div></div><div class="detail-list"><div class="detail-line"><span>Approval decisions</span><strong>Backend validated</strong></div><div class="detail-line"><span>Sharia and policy results</span><strong>Backend owned</strong></div><div class="detail-line"><span>Wallet and ledger</span><strong>Never calculated here</strong></div><div class="detail-line"><span>Provider credentials</span><strong>Never stored here</strong></div></div></article>
        <article class="card card-pad span-6"><div class="card-heading"><div><h2>Display preferences</h2><p class="subheading">Usable without animation, 3D, or blur effects</p></div></div><div class="settings-row"><span><strong>Color theme</strong><small>Saved to this browser only</small></span><button class="button button-secondary" id="theme-toggle-settings">Toggle theme</button></div><div class="settings-row"><span><strong>Reduced motion</strong><small>Honors your operating-system preference</small></span>${statusPill(window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "On" : "System", "neutral")}</div></article>
      </div>`;
  }

  function emptyLive(title, message) {
    return `<article class="card"><div class="empty-state"><span>⌁</span><h2>${escapeHtml(title)}</h2><p>${escapeHtml(message)}</p>${state.error ? `<p class="field-error">${escapeHtml(state.error)}</p>` : ""}</div></article>`;
  }

  function render() {
    const renderers = {
      intel: renderIntel,
      office: renderOffice,
      businesses: renderBusinesses,
      departments: renderDepartments,
      decisions: renderDecisions,
      reports: renderReports,
      settings: renderSettings,
    };
    root.className = `workspace-scene scene-${state.route}`;
    root.innerHTML = renderers[state.route]();
    $$(".nav-link").forEach((link) => {
      const active = link.dataset.route === state.route;
      link.classList.toggle("active", active);
      if (active) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
    $("#current-room").textContent = routes[state.route] || "Workspace";
    updateShell();
    bindViewActions();
  }

  function updateShell() {
    const live = state.mode === "live";
    const ready = state.health?.ready;
    $("#mode-chip").classList.toggle("live", live && !state.apiSample && ready !== false);
    $("#mode-chip").innerHTML = `<i class="mode-dot"></i>${state.apiSample ? "SAMPLE API" : live ? (ready === false ? "LIVE · DEGRADED" : "LIVE API") : "DEMO DATA"}`;
    const label = state.apiSample ? "Sample API preview" : live ? (ready === false ? "System degraded" : "Live connection") : "Demo workspace";
    const sublabel = state.apiSample ? "Fabricated records · no real system" : live ? (state.health?.reason || "Owner API · same origin") : "Sample data · not connected";
    $("#sidebar-status").textContent = label;
    $("#sidebar-status-sub").textContent = sublabel;
    $("#footer-status").textContent = state.apiSample ? "Sample API · not connected to Coolie" : `${live ? "Live API" : "Demo data"} · ${ready === false ? "not ready" : live ? "connected" : "not connected"}`;
    $("#sidebar-status-dot").className = `status-dot ${live && ready === false ? "warning" : ""}`;
    $("#footer-status-dot").className = `status-dot ${live && ready === false ? "warning" : ""}`;
    $("#last-updated").textContent = `Updated ${shortTime(state.lastUpdated)}`;
    $("#current-date").textContent = dateLabel();
    $("#footer-refresh").textContent = state.loading ? "Refreshing…" : "Refresh ↻";
    $("#footer-refresh").disabled = state.loading;
    $("#sidebar-refresh").disabled = state.loading;
  }

  function openDialog(title, content, eyebrow = "OWNER REVIEW") {
    $("#dialog-title").textContent = title;
    $("#dialog-eyebrow").textContent = eyebrow;
    $("#dialog-content").innerHTML = content;
    $("#overlay").hidden = false;
    $("#dialog-close").focus();
  }

  function closeDialog() {
    $("#overlay").hidden = true;
  }

  function setTheme(theme) {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_KEY, theme);
  }

  function showOrchestrator() {
    const drawer = $("#orchestrator-drawer");
    drawer.classList.add("open");
    drawer.removeAttribute("inert");
    drawer.setAttribute("aria-hidden", "false");
    $("#close-orchestrator").focus();
  }

  function hideOrchestrator() {
    if (voiceRecorder?.state === "recording") {
      discardVoiceOnStop = true;
      voiceRecorder.stop();
    }
    const drawer = $("#orchestrator-drawer");
    drawer.classList.remove("open");
    drawer.setAttribute("aria-hidden", "true");
    drawer.setAttribute("inert", "");
    $("#open-orchestrator").focus();
  }

  function bindViewActions() {
    $$("[data-route-button]").forEach((button) => button.addEventListener("click", () => navigate(button.dataset.routeButton)));
    $$("[data-review-decision]").forEach((button) => button.addEventListener("click", () => {
      const decision = (state.mode === "demo" ? demo.briefing.pendingDecisions : state.briefing?.pendingDecisions)?.[Number(button.dataset.reviewDecision)];
      openDialog("Approval details", `<p class="dialog-content">This interface only displays approval requests. The connected backend must provide an authenticated, exact-binding approval workflow before any decision can be submitted.</p><div class="detail-list">${[
        ["Action", decision?.action || decision?.title],
        ["Target", decision?.target || decision?.detail],
        ["Budget", decision?.budget || "Not provided"],
        ["Compliance", decision?.complianceStatus || "Not provided"],
        ["Expiry", decision?.expiresAt || decision?.time || "Not provided"],
        ["Evidence", (decision?.evidenceRefs || []).join(", ") || "Not provided"],
      ].map(([name, value]) => `<div class="detail-line"><span>${escapeHtml(name)}</span><strong>${escapeHtml(value || "Not returned")}</strong></div>`).join("")}</div><p class="field-hint">No approve/reject request has been sent. This backend currently exposes no approval-decision endpoint to the owner UI.</p>`);
    }));
    $("#add-business")?.addEventListener("click", () => openDialog("Business intake", `<p class="dialog-content">Business intake is collected by the Orchestrator and validated by backend policy. The current owner API does not expose an intake endpoint, so nothing has been submitted.</p><div class="dialog-actions"><button class="button button-secondary" data-close-dialog>Close</button><button class="button button-primary" data-open-orchestrator>Ask Orchestrator</button></div>`, "BUSINESS INTAKE"));
    $("#connection-form")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const error = $("#connection-error");
      error.textContent = "";
      try {
        state.apiBase = validApiBase($("#api-base").value);
        localStorage.setItem(API_BASE_KEY, state.apiBase);
        await refreshLive();
      } catch (failure) {
        error.textContent = failure.message;
      }
    });
    $("#use-demo")?.addEventListener("click", () => {
      state.mode = "demo";
      state.apiSample = false;
      state.error = "";
      state.health = null;
      state.lastUpdated = new Date();
      render();
      showToast("Preview data loaded. No backend state was changed.");
    });
    $("#pause-system")?.addEventListener("click", () => confirmPause());
    $("#resume-system")?.addEventListener("click", () => confirmResume());
    $("#theme-toggle-settings")?.addEventListener("click", toggleTheme);
    $("#business-filter")?.addEventListener("change", (event) => filterBusinesses(event.target.value));
  }

  function filterBusinesses(filter) {
    const cards = $$("#business-cards > article");
    cards.forEach((card) => {
      const text = card.textContent.toLowerCase();
      card.hidden = filter !== "All" && !text.includes(filter.toLowerCase());
    });
  }

  function toggleTheme() {
    setTheme(document.documentElement.dataset.theme === "night" ? "day" : "night");
  }

  function navigate(route) {
    if (!routes[route]) return;
    state.route = route;
    if (location.hash.slice(1) !== route) location.hash = route;
    render();
    $("#main-content").focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function confirmPause() {
    openDialog("Pause all new work?", `<p class="dialog-content">The backend will receive an emergency-pause request. This stops new business decisions, finance assessments, research execution, capability planning, Brain inference, and Enactor actions where shared failsafe wiring is active. It does not reverse an external action already in flight.</p><div class="field"><label for="pause-reason">Reason for pause</label><input id="pause-reason" type="text" maxlength="300" placeholder="Describe the safety issue"></div><div class="dialog-actions"><button class="button button-secondary" data-close-dialog>Cancel</button><button class="button button-danger" id="confirm-pause">Pause system</button></div>`, "EMERGENCY CONTROL");
    $("#confirm-pause").addEventListener("click", async () => {
      const reason = $("#pause-reason").value.trim();
      if (!reason) { $("#pause-reason").focus(); return; }
      try {
        const result = await requestJson("/system/emergency-pause", { method: "POST", body: JSON.stringify({ reason }) });
        state.health = { ...(state.health || {}), paused: result.paused, ready: false, status: "paused", reason: result.reason };
        closeDialog();
        render();
        showToast("Pause request accepted by the backend.");
      } catch (error) {
        showToast(`Pause was not confirmed: ${error.message}`);
      }
    });
  }

  function confirmResume() {
    openDialog("Resume new work?", `<p class="dialog-content">Resume only after the underlying incident is understood. The backend must revalidate readiness and owner authority.</p><div class="dialog-actions"><button class="button button-secondary" data-close-dialog>Cancel</button><button class="button button-primary" id="confirm-resume">Request resume</button></div>`, "RECOVERY CONTROL");
    $("#confirm-resume").addEventListener("click", async () => {
      try {
        await requestJson("/system/resume", { method: "POST", body: JSON.stringify({}) });
        closeDialog();
        await refreshLive();
      } catch (error) {
        showToast(`Resume was not confirmed: ${error.message}`);
      }
    });
  }

  document.addEventListener("click", (event) => {
    const routeLink = event.target.closest("[data-route]");
    if (routeLink) {
      event.preventDefault();
      navigate(routeLink.dataset.route);
      return;
    }
    if (event.target.closest("[data-close-dialog]")) closeDialog();
    if (event.target.closest("[data-open-orchestrator]")) { closeDialog(); showOrchestrator(); }
  });

  window.addEventListener("hashchange", () => {
    const route = location.hash.slice(1);
    if (routes[route] && route !== state.route) {
      state.route = route;
      render();
    }
  });
  $("#open-orchestrator").addEventListener("click", showOrchestrator);
  $("#close-orchestrator").addEventListener("click", hideOrchestrator);
  $("#voice-toggle").addEventListener("click", toggleVoiceCapture);
  $("#orchestrator-form").addEventListener("submit", (event) => {
    event.preventDefault();
    void sendOrchestratorMessage();
  });
  $("#dialog-close").addEventListener("click", closeDialog);
  $("#overlay").addEventListener("click", (event) => { if (event.target === $("#overlay")) closeDialog(); });
  $("#theme-toggle").addEventListener("click", toggleTheme);
  $("#footer-refresh").addEventListener("click", refreshLive);
  $("#sidebar-refresh").addEventListener("click", refreshLive);
  $("#search-open").addEventListener("click", () => showToast("Search will be available when the owner API exposes the search read model."));
  $$("[data-route-button]").forEach((button) => button.addEventListener("click", () => navigate(button.dataset.routeButton)));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      if (!$("#overlay").hidden) closeDialog();
      else if ($("#orchestrator-drawer").classList.contains("open")) hideOrchestrator();
    }
  });

  const savedTheme = localStorage.getItem(THEME_KEY);
  setTheme(savedTheme || "night");
  initializeVoiceControls();
  const initialRoute = location.hash.slice(1);
  if (routes[initialRoute]) state.route = initialRoute;
  render();
})();
