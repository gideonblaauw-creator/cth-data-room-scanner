(function () {
  "use strict";

  const DATA = window.PLAYGROUND_DATA;
  const CFG = DATA.config;

  let lang = "en";
  let currentRoomId = "welcome";
  let findingsDoc = null;
  let selectedFindingId = null;
  let stepIndex = 0;
  let quizState = { answers: {}, passed: false, submitted: false };
  let decisions = new Map();
  let clarifications = [];

  const el = (id) => document.getElementById(id);
  const t = (key, ...args) => {
    const v = DATA.i18n[lang][key];
    return typeof v === "function" ? v(...args) : v;
  };
  const roomName = (room) => (lang === "es" ? room.nameEs : room.nameEn);

  function storageKey(suffix) {
    return CFG.storage.prefix + suffix;
  }

  function loadStorage() {
    const legacy = CFG.storage.legacy;
    lang = localStorage.getItem(legacy.lang) || localStorage.getItem(storageKey("lang")) || "en";

    try {
      const raw = localStorage.getItem(legacy.decisions) || localStorage.getItem(storageKey("decisions"));
      if (raw) decisions = new Map(Object.entries(JSON.parse(raw)));
    } catch { decisions = new Map(); }

    try {
      const raw = localStorage.getItem(legacy.quiz) || localStorage.getItem(storageKey("quiz"));
      if (raw) quizState = JSON.parse(raw);
    } catch { /* keep default */ }

    try {
      const raw = localStorage.getItem(legacy.clarifications) || localStorage.getItem(storageKey("clarifications"));
      if (raw) clarifications = JSON.parse(raw);
    } catch { clarifications = []; }

    currentRoomId = localStorage.getItem(storageKey("room")) || "welcome";
  }

  function saveDecisions() {
    const obj = Object.fromEntries(decisions);
    localStorage.setItem(CFG.storage.legacy.decisions, JSON.stringify(obj));
    localStorage.setItem(storageKey("decisions"), JSON.stringify(obj));
  }

  function saveQuizState() {
    localStorage.setItem(CFG.storage.legacy.quiz, JSON.stringify(quizState));
    localStorage.setItem(storageKey("quiz"), JSON.stringify(quizState));
  }

  function saveClarifications() {
    localStorage.setItem(CFG.storage.legacy.clarifications, JSON.stringify(clarifications));
    localStorage.setItem(storageKey("clarifications"), JSON.stringify(clarifications));
  }

  function saveRoom() {
    localStorage.setItem(storageKey("room"), currentRoomId);
  }

  function quizPassed() {
    return Boolean(quizState.passed);
  }

  function decisionRoomId(findingId) {
    return `decision-${findingId}`;
  }

  function allRooms() {
    const staticRooms = DATA.rooms.slice();
    if (!findingsDoc) return staticRooms;
    const decisionRooms = findingsDoc.findings.map((f, i) => ({
      id: decisionRoomId(f.finding_id),
      nameEn: `Door ${f.finding_id}`,
      nameEs: `Puerta ${f.finding_id}`,
      type: "decision",
      findingId: f.finding_id,
      grid: { row: 2, col: i },
      exits: ["corridor"],
      requiresQuiz: true,
    }));
    return staticRooms.concat(decisionRooms);
  }

  function getRoom(id) {
    return allRooms().find((r) => r.id === id);
  }

  async function fetchJson(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`${res.status} ${url}`);
    return res.json();
  }

  function normalizeFindings(doc) {
    const findings = doc.gate_findings || doc.findings || [];
    return {
      run_id: doc.run_id,
      company: doc.company || "VertiGreen Robotics",
      scanned_at: doc.scanned_at,
      findings,
    };
  }

  async function loadFindings() {
    const params = new URLSearchParams(window.location.search);
    const findingsParam = params.get("findings");
    const paths = findingsParam
      ? [findingsParam]
      : [
          "../../out/findings.json",
          "../out/findings.json",
          "out/findings.json",
          CFG.defaultFindingsUrl,
          "../../hitl/microworld/defaults/findings-hitl-20260908-214515.json",
        ];
    for (const p of paths) {
      try {
        findingsDoc = normalizeFindings(await fetchJson(p));
        return;
      } catch { /* next */ }
    }
    throw new Error("Could not load findings");
  }

  function decisionState(findingId) {
    const d = decisions.get(findingId);
    if (!d) return "unlocked";
    if (d.locked_at) return "locked";
    if (d.human_decision) return "decided";
    return "unlocked";
  }

  function lockedCount() {
    if (!findingsDoc) return 0;
    return findingsDoc.findings.filter((f) => decisionState(f.finding_id) === "locked").length;
  }

  function allLocked() {
    if (!findingsDoc) return false;
    const total = findingsDoc.findings.length;
    return total > 0 && lockedCount() === total;
  }

  function buildLocksDocument() {
    const locks = (findingsDoc?.findings || [])
      .map((f) => decisions.get(f.finding_id))
      .filter((d) => d && d.locked_at)
      .map((d) => ({
        finding_id: d.finding_id,
        fixture_path: d.fixture_path,
        agent_suggestion: d.agent_suggestion,
        agent_label: d.agent_label,
        human_decision: d.human_decision,
        rationale: d.rationale,
        status: d.status || "reviewed",
        locked_at: d.locked_at,
        moment: d.moment,
      }));
    return {
      version: 1,
      run_id: findingsDoc?.run_id || "unknown",
      company: findingsDoc?.company || "VertiGreen Robotics",
      quiz_passed: quizPassed(),
      quiz_source: "explainer-quiz",
      locked_at: new Date().toISOString(),
      reviewer: null,
      run_link: "hitl/out/microworld-locks.json",
      format: "lexiscan-ledger-v1",
      locks,
    };
  }

  function buildLedgerMarkdown() {
    const doc = buildLocksDocument();
    const lines = [
      "# Decisions Ledger",
      "",
      `- **Run:** ${doc.run_id}`,
      `- **Company:** ${doc.company}`,
      `- **Quiz passed:** ${doc.quiz_passed}`,
      `- **Exported:** ${doc.locked_at}`,
      "",
    ];
    if (doc.locks.length === 0) {
      lines.push("_No locked decisions yet._");
    } else {
      doc.locks.forEach((l) => {
        lines.push(`## ${l.finding_id} — ${l.fixture_path}`);
        lines.push(`- **Decision:** ${l.human_decision}`);
        lines.push(`- **Agent label:** ${l.agent_label || "—"}`);
        lines.push(`- **Moment:** ${l.moment || "—"}`);
        lines.push(`- **Rationale:** ${l.rationale}`);
        lines.push(`- **Locked at:** ${l.locked_at}`);
        lines.push("");
      });
    }
    return lines.join("\n");
  }

  function downloadBlob(content, filename, mime) {
    const blob = new Blob([content], { type: mime });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
  }

  function roomLocked(room) {
    if (room.requiresQuiz && !quizPassed()) return true;
    if (room.id === "corridor" && !quizPassed()) return true;
    if (room.type === "decision" && !quizPassed()) return true;
    return false;
  }

  function navigateTo(roomId) {
    const room = getRoom(roomId);
    if (!room) return;
    if (roomLocked(room)) {
      alert(t("corridorLocked"));
      return;
    }
    currentRoomId = roomId;
    if (room.type === "decision" && room.findingId) {
      selectedFindingId = room.findingId;
      stepIndex = 0;
    }
    saveRoom();
    render();
  }

  function renderFloorPlan() {
    const rooms = allRooms();
    const colW = 140;
    const rowH = 90;
    const pad = 24;

    const maxCol = Math.max(...rooms.map((r) => r.grid.col)) + 1;
    const maxRow = Math.max(...rooms.map((r) => r.grid.row)) + 1;
    const width = maxCol * colW + pad * 2;
    const height = maxRow * rowH + pad * 2;

    const nodes = rooms
      .map((room) => {
        const x = pad + room.grid.col * colW;
        const y = pad + room.grid.row * rowH;
        const locked = roomLocked(room);
        const active = room.id === currentRoomId;
        const cls = [
          "room-node",
          active ? "active" : "",
          locked ? "locked-room" : "",
          room.type === "decision" ? "decision-door" : "",
          room.type === "corridor" ? "type-corridor" : "",
        ]
          .filter(Boolean)
          .join(" ");
        return `<div class="${cls}" data-room="${room.id}" style="left:${x}px;top:${y}px" title="${roomName(room)}">
          <strong>${roomName(room)}</strong>
          <span class="room-type">${room.type}</span>
        </div>`;
      })
      .join("");

    const lines = [];
    rooms.forEach((room) => {
      (room.exits || []).forEach((exitId) => {
        const target = getRoom(exitId);
        if (!target) return;
        const x1 = pad + room.grid.col * colW + 60;
        const y1 = pad + room.grid.row * rowH + 36;
        const x2 = pad + target.grid.col * colW + 60;
        const y2 = pad + target.grid.row * rowH + 36;
        lines.push(`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#3d4f63" stroke-width="2"/>`);
      });
    });

    if (findingsDoc) {
      const corridor = getRoom("corridor");
      findingsDoc.findings.forEach((f) => {
        const dr = getRoom(decisionRoomId(f.finding_id));
        if (!corridor || !dr) return;
        const x1 = pad + corridor.grid.col * colW + 60;
        const y1 = pad + corridor.grid.row * rowH + 36;
        const x2 = pad + dr.grid.col * colW + 60;
        const y2 = pad + dr.grid.row * rowH + 36;
        lines.push(`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#7aab4a" stroke-width="1" stroke-dasharray="4"/>`);
      });
    }

    return `<div class="floor-plan-wrap">
      <h3 style="margin:0 0 0.5rem;font-size:0.85rem;color:var(--muted)">${t("floorPlan")} · <span style="color:var(--accent-bright)">${t("currentRoom")}: ${roomName(getRoom(currentRoomId) || { nameEn: currentRoomId, nameEs: currentRoomId })}</span></h3>
      <div class="floor-plan" style="width:${width}px;height:${height}px">
        <svg class="connectors" viewBox="0 0 ${width} ${height}">${lines.join("")}</svg>
        ${nodes}
      </div>
    </div>`;
  }

  function renderExits(room) {
    const exits = (room.exits || []).concat(
      room.type !== "corridor" && quizPassed() && findingsDoc
        ? ["corridor"]
        : []
    );
    const unique = [...new Set(exits)].filter((id) => id !== room.id && getRoom(id));
    if (unique.length === 0) return "";
    return `<div class="exits-nav">
      <span class="exit-label">${lang === "en" ? "Corridor exits" : "Salidas del pasillo"}</span>
      ${unique.map((id) => `<button type="button" data-goto="${id}">${roomName(getRoom(id))}</button>`).join("")}
    </div>`;
  }

  function renderWelcomeRoom(room) {
    return `<div class="room-view">
      <h2>${roomName(room)}</h2>
      <p>${lang === "en"
        ? "CleantechHUB Scanner Understanding Lab — LexiScan house-tour format. Walk rooms left-to-right, then enter decision doors from the corridor."
        : "Lab de comprensión Scanner CleantechHUB — formato house-tour LexiScan."}</p>
      <div class="controls">
        <button type="button" class="primary" data-goto="context">${lang === "en" ? "Start tour" : "Iniciar tour"}</button>
      </div>
      ${renderExits(room)}
    </div>`;
  }

  function renderContentRoom(room) {
    const blocks = (room.blocks || [])
      .map((b) => {
        const heading = lang === "es" ? b.headingEs : b.headingEn;
        const body = lang === "es" ? b.bodyEs : b.bodyEn;
        let inner = `<h3>${heading}</h3><p>${body || ""}</p>`;
        if (b.flowSteps) {
          inner += `<div class="flow-steps">${b.flowSteps
            .map(
              (s) =>
                `<div class="flow-step"><strong>${lang === "es" ? s.nameEs : s.nameEn}</strong>${lang === "es" ? s.descEs : s.descEn}</div>`
            )
            .join("")}</div>`;
        }
        if (b.code) {
          inner += `<pre class="mono card" style="font-size:0.78rem;overflow-x:auto">${b.code}</pre>`;
        }
        return `<div class="card">${inner}</div>`;
      })
      .join("");

    const notionLinks = CFG.notionPages
      .map(
        (p) =>
          `<li><a href="${p.url}" target="_blank" rel="noopener">${lang === "es" ? p.nameEs : p.nameEn}</a></li>`
      )
      .join("");

    return `<div class="room-view">
      <h2>${roomName(room)}</h2>
      ${blocks}
      <h3>${t("relatedNotion")}</h3>
      <ul class="path-map">${notionLinks}
        <li><a href="${CFG.notionDecisionsDb}" target="_blank" rel="noopener">Decisions DB</a></li>
      </ul>
      <p style="font-size:0.78rem;color:var(--muted)">${t("completedRun")}</p>
      ${renderExits(room)}
    </div>`;
  }

  function renderQuizRoom(room) {
    const questionsHtml = DATA.quizQuestions
      .map((q) => {
        const opts = (lang === "es" ? q.optionsEs : q.optionsEn)
          .map(
            (opt, oi) =>
              `<label><input type="radio" name="quiz_${q.id}" value="${oi}" ${quizState.answers[q.id] === oi ? "checked" : ""} ${quizState.submitted ? "disabled" : ""} /> (${String.fromCharCode(65 + oi)}) ${opt}</label>`
          )
          .join("");
        let cls = "quiz-question";
        if (quizState.submitted) {
          cls += quizState.answers[q.id] === q.answer ? " correct" : " wrong";
        }
        return `<div class="${cls}"><strong>${q.id}.</strong> ${lang === "es" ? q.questionEs : q.questionEn}<div class="quiz-options">${opts}</div></div>`;
      })
      .join("");

    const labels = (room.labelCards || [])
      .map(
        (c) =>
          `<div class="label-card ${c.id}"><strong>${c.nameEn}</strong><br>${lang === "es" ? c.descEs : c.descEn}</div>`
      )
      .join("");

    const human = (room.humanDecisions || [])
      .map((d) => `<li><strong>${d.id}</strong> — ${lang === "es" ? d.descEs : d.descEn}</li>`)
      .join("");

    const passed = quizPassed();
    const controls = passed
      ? `<span style="color:var(--accent-bright)">✓ ${t("quizPassed")} (${quizState.score}/5)</span>
         <button type="button" id="retakeQuiz">${t("retakeQuiz")}</button>
         <button type="button" class="primary" data-goto="corridor">${t("goCorridor")}</button>`
      : `<button type="button" class="primary" id="submitQuiz">${t("submitQuiz")}</button>`;

    return `<div class="room-view">
      <h2>${roomName(room)}</h2>
      <p>${lang === "en" ? "Read the concepts below, then answer all five questions. You must pass before the Decision Corridor unlocks." : "Lea los conceptos y responda las cinco preguntas para desbloquear el pasillo."}</p>
      <h3>${t("agentLabelsHeading")}</h3>
      <div class="label-grid">${labels}</div>
      <h3>${t("humanDecisionsHeading")}</h3>
      <ul>${human}</ul>
      <h3>${t("quizHeading")}</h3>
      <div id="quizForm">${questionsHtml}</div>
      <div class="controls">${controls}</div>
      ${renderExits(room)}
    </div>`;
  }

  function renderCorridorRoom(room) {
    if (!quizPassed()) {
      return `<div class="room-view"><h2>${roomName(room)}</h2><p>${t("corridorLocked")}</p>
        <button type="button" data-goto="explainer">${lang === "en" ? "Go to Explainer" : "Ir al Explicador"}</button></div>`;
    }
    const doors = (findingsDoc?.findings || [])
      .map((f) => {
        const state = decisionState(f.finding_id);
        const stateLabel = t(state === "locked" ? "locked" : state === "decided" ? "draft" : "unlocked");
        return `<button type="button" class="primary" data-goto="${decisionRoomId(f.finding_id)}">
          ${f.finding_id} · ${f.fixture_path} <span class="badge ${f.label}">${f.label}</span>
          <span style="font-size:0.68rem;color:var(--muted);display:block;margin-top:0.2rem">${stateLabel}</span>
        </button>`;
      })
      .join("");
    const total = findingsDoc?.findings.length || 0;
    return `<div class="room-view">
      <h2>${roomName(room)}</h2>
      <p>${lang === "es" ? room.descEs : room.descEn}</p>
      <div class="progress-bar"><div class="progress-fill" style="width:${total ? (lockedCount() / total) * 100 : 0}%"></div></div>
      <p style="font-size:0.78rem;color:var(--muted)">${t("progress", lockedCount(), total)}</p>
      <div class="controls" style="flex-direction:column;align-items:stretch">${doors || `<p style="color:var(--muted)">${lang === "en" ? "Load findings to see doors." : "Cargue hallazgos."}</p>`}</div>
      ${allLocked() ? `<div class="card success" style="border-color:var(--accent-bright)"><strong>${t("allLocked")}</strong> — ${t("locksHint")}</div>` : ""}
      ${renderExits(room)}
    </div>`;
  }

  function renderDecisionRoom(room) {
    const f = findingsDoc?.findings.find((x) => x.finding_id === room.findingId);
    if (!f) return `<div class="room-view"><p style="color:var(--muted)">${lang === "en" ? "Finding not loaded." : "Hallazgo no cargado."}</p></div>`;

    const steps = f.reasoning_steps || [];
    const step = steps[stepIndex] || { description: "—" };
    const d = decisions.get(f.finding_id) || {};
    const isLocked = decisionState(f.finding_id) === "locked";
    const moment = f.moment || "general";
    const momentLabel = (DATA.momentLabels[moment] || DATA.momentLabels.general)[lang === "es" ? "nameEs" : "nameEn"];

    return `<div class="room-view">
      <h2>${roomName(room)} — ${f.finding_id}</h2>
      <div class="meta-grid">
        <div class="meta-card"><label>${t("moment")}</label><span>${momentLabel}</span></div>
        <div class="meta-card"><label>${t("file")}</label><span>${f.fixture_path}</span></div>
        <div class="meta-card"><label>${t("pillar")}</label><span>${f.pillar || "—"}</span></div>
        <div class="meta-card"><label>${t("rule")}</label><span>${f.rule_fired}</span></div>
        <div class="meta-card"><label>${t("label")}</label><span class="badge ${f.label}">${f.label}</span></div>
        <div class="meta-card"><label>${t("suggestion")}</label><span>${f.agent_suggestion}</span></div>
      </div>
      <p style="font-size:0.8rem;color:var(--muted)">${f.excerpt || ""}</p>
      <div class="scrubber">
        <strong>${t("scrubber")}</strong>
        <div class="step-display">
          <div><strong>${step.rule_id || "—"}</strong> — ${step.description}</div>
          ${step.matched_text ? `<div style="margin-top:0.4rem;color:var(--warn)">${t("matched")}: "${step.matched_text}"</div>` : ""}
        </div>
        <div class="controls">
          <button type="button" id="prevStep" ${stepIndex === 0 ? "disabled" : ""}>←</button>
          <button type="button" id="nextStep" ${stepIndex >= steps.length - 1 ? "disabled" : ""}>→</button>
          <span style="color:var(--muted);font-size:0.75rem">${t("step", stepIndex + 1, steps.length)}</span>
        </div>
      </div>
      <div class="decision-panel ${isLocked ? "locked-panel" : ""}">
        <strong>${t("decision")}</strong>
        <div class="decision-options">
          ${["agree", "override", "defer"]
            .map(
              (opt) =>
                `<label><input type="radio" name="human_decision" value="${opt}" ${d.human_decision === opt ? "checked" : ""} ${isLocked ? "disabled" : ""} /> ${t(opt)}</label>`
            )
            .join("")}
        </div>
        <label for="rationale">${t("rationale")}</label>
        <textarea id="rationale" ${isLocked ? "disabled" : ""}>${d.rationale || ""}</textarea>
        <div class="controls">
          ${isLocked
            ? `<button type="button" class="danger" id="unlockBtn">${t("unlock")}</button>
               <span style="color:var(--locked);font-size:0.75rem">${t("locked")} · ${d.locked_at || ""}</span>`
            : `<button type="button" id="saveDraftBtn">${t("saveDraft")}</button>
               <button type="button" class="primary" id="lockBtn">${t("lockDecision")}</button>`}
        </div>
      </div>
      ${renderExits(room)}
    </div>`;
  }

  function renderGhRoom(room) {
    const repo = CFG.repoUrl;
    const links = DATA.ghLinks
      .map(
        (l) =>
          `<li><a href="${repo}/tree/main/${l.path.replace(/\/$/, "")}" target="_blank" rel="noopener"><code>${l.path}</code></a> — ${lang === "es" ? l.descEs : l.descEn}</li>`
      )
      .join("");
    const fixtureMap = findingsDoc
      ? findingsDoc.findings
          .map(
            (f) =>
              `<li><code>${f.finding_id}</code> → <code>fixtures/sample-dataroom/${f.fixture_path}</code> <span class="badge ${f.label}">${f.label}</span></li>`
          )
          .join("")
      : `<li style="color:var(--muted)">${lang === "en" ? "Load findings to see map" : "Cargue hallazgos"}</li>`;

    return `<div class="room-view">
      <h2>${roomName(room)}</h2>
      <p><a href="${repo}" target="_blank" rel="noopener">${repo}</a></p>
      <h3>${t("ghPaths")}</h3>
      <ul class="path-map">${links}</ul>
      <h3>${t("fixtureMap")}</h3>
      <ul class="path-map">${fixtureMap}</ul>
      ${renderExits(room)}
    </div>`;
  }

  function renderClarificationsRoom(room) {
    const items = clarifications.length
      ? clarifications
          .map(
            (c, i) =>
              `<div class="clarification-item"><strong>${c.finding_id}</strong> · <span style="color:var(--muted)">${c.created_at}</span>
                <p style="margin:0.4rem 0 0">${c.note}</p>
                <button type="button" class="danger" style="margin-top:0.4rem;font-size:0.68rem" data-del-clar="${i}">${t("remove")}</button></div>`
          )
          .join("")
      : `<p style="color:var(--muted)">${t("noClarifications")}</p>`;

    const findingOptions = findingsDoc
      ? findingsDoc.findings.map((f) => `<option value="${f.finding_id}">${f.finding_id} — ${f.fixture_path}</option>`).join("")
      : '<option value="F000">F000 — general</option>';

    return `<div class="room-view">
      <h2>${roomName(room)}</h2>
      <p>${lang === "en" ? "Capture open questions, deferrals, and needs-clarification notes tied to a finding." : "Capture notas de aplazamiento y aclaraciones por hallazgo."}</p>
      <div class="card">
        <label>${t("findingId")}</label>
        <select id="clarFinding">${findingOptions}</select>
        <label style="margin-top:0.6rem;display:block">${t("note")}</label>
        <textarea id="clarNote" placeholder="${lang === "en" ? "What needs clarification?" : "¿Qué necesita aclaración?"}"></textarea>
        <div class="controls"><button type="button" class="primary" id="addClar">${t("addClarification")}</button></div>
      </div>
      <div id="clarList">${items}</div>
      <div class="controls"><button type="button" id="exportClar">${t("exportClarifications")}</button></div>
      ${renderExits(room)}
    </div>`;
  }

  function renderRoomContent() {
    const room = getRoom(currentRoomId);
    if (!room) return `<p style="color:var(--muted)">Unknown room: ${currentRoomId}</p>`;
    switch (room.type) {
      case "welcome":
        return renderWelcomeRoom(room);
      case "content":
        return renderContentRoom(room);
      case "quiz":
        return renderQuizRoom(room);
      case "corridor":
        return renderCorridorRoom(room);
      case "decision":
        return renderDecisionRoom(room);
      case "link":
        return renderGhRoom(room);
      case "clarifications":
        return renderClarificationsRoom(room);
      default:
        return `<p>Unknown room type: ${room.type}</p>`;
    }
  }

  function renderLedger() {
    const doc = buildLocksDocument();
    const items =
      doc.locks.length > 0
        ? doc.locks
            .map((l) => {
              const cls = l.status === "reviewed" ? "locked" : "draft";
              return `<div class="ledger-item ${cls}"><strong>${l.finding_id}</strong> · ${l.human_decision}<br><span style="color:var(--muted)">${l.rationale.slice(0, 48)}…</span></div>`;
            })
            .join("")
        : `<p style="font-size:0.78rem;color:var(--muted)">${t("ledgerEmpty")}</p>`;

    el("ledgerPanel").innerHTML = `
      <h2>${t("ledger")}</h2>
      <p style="font-size:0.72rem;color:var(--muted)">${findingsDoc ? t("progress", lockedCount(), findingsDoc.findings.length) : ""}</p>
      ${items}
      <div class="ledger-actions">
        <button type="button" id="ledgerJson">${t("downloadJson")}</button>
        <button type="button" id="ledgerMd">${t("downloadMd")}</button>
        <button type="button" id="ledgerCopyJson">${t("copyJson")}</button>
        <button type="button" id="ledgerCopyMd">${t("copyMd")}</button>
        <a href="${CFG.notionDecisionsDb}" target="_blank" rel="noopener"><button type="button">${t("openNotion")}</button></a>
      </div>
      <div class="card" style="margin-top:0.75rem;font-size:0.72rem">
        <strong>${t("pushRecipe")}</strong>
        <pre class="mono" style="font-size:0.68rem;margin:0.4rem 0 0">python scripts/push_microworld_to_notion.py --dry-run
python scripts/push_microworld_to_notion.py</pre>
      </div>`;
  }

  function updateBanners() {
    const banner = el("statusBanner");
    if (!quizPassed()) {
      banner.textContent = t("quizGate");
      banner.className = "banner";
    } else if (allLocked()) {
      banner.innerHTML = `<strong>${t("locksReady")}</strong> — ${t("locksHint")}`;
      banner.className = "banner success";
    } else {
      banner.textContent = t("quizPassed");
      banner.className = "banner success";
    }
  }

  function updateHeader() {
    el("titleMain").textContent = lang === "es" ? DATA.meta.titleEs : DATA.meta.titleEn;
    el("subtitleMain").textContent = lang === "es" ? DATA.meta.subtitleEs : DATA.meta.subtitleEn;
    el("runMeta").textContent = findingsDoc ? `${findingsDoc.company} · ${findingsDoc.run_id}` : "";
    el("langEn").classList.toggle("active", lang === "en");
    el("langEs").classList.toggle("active", lang === "es");
  }

  function bindRoomEvents() {
    document.querySelectorAll("[data-goto]").forEach((btn) => {
      btn.onclick = () => navigateTo(btn.dataset.goto);
    });
    document.querySelectorAll(".room-node:not(.locked-room)").forEach((node) => {
      node.onclick = () => navigateTo(node.dataset.room);
    });

    const submitQuiz = el("submitQuiz");
    if (submitQuiz) submitQuiz.onclick = handleSubmitQuiz;
    const retake = el("retakeQuiz");
    if (retake) {
      retake.onclick = () => {
        quizState = { answers: {}, passed: false, submitted: false };
        saveQuizState();
        render();
      };
    }

    el("prevStep")?.addEventListener("click", () => {
      stepIndex--;
      render();
    });
    el("nextStep")?.addEventListener("click", () => {
      stepIndex++;
      render();
    });
    el("saveDraftBtn")?.addEventListener("click", saveDraft);
    el("lockBtn")?.addEventListener("click", lockDecision);
    el("unlockBtn")?.addEventListener("click", unlockDecision);

    el("addClar")?.addEventListener("click", () => {
      const note = el("clarNote").value.trim();
      if (note.length < 4) return;
      clarifications.push({
        finding_id: el("clarFinding").value,
        note,
        created_at: new Date().toISOString(),
      });
      saveClarifications();
      render();
    });
    document.querySelectorAll("[data-del-clar]").forEach((btn) => {
      btn.onclick = () => {
        clarifications.splice(parseInt(btn.dataset.delClar, 10), 1);
        saveClarifications();
        render();
      };
    });
    el("exportClar")?.addEventListener("click", () => {
      downloadBlob(
        JSON.stringify({ version: 1, run_id: findingsDoc?.run_id, clarifications }, null, 2),
        "clarifications.json",
        "application/json"
      );
    });

    el("ledgerJson")?.addEventListener("click", () => {
      downloadBlob(JSON.stringify(buildLocksDocument(), null, 2), "microworld-locks.json", "application/json");
    });
    el("ledgerMd")?.addEventListener("click", () => {
      downloadBlob(buildLedgerMarkdown(), "decisions-ledger.md", "text/markdown");
    });
    el("ledgerCopyJson")?.addEventListener("click", () => {
      navigator.clipboard.writeText(JSON.stringify(buildLocksDocument(), null, 2));
    });
    el("ledgerCopyMd")?.addEventListener("click", () => {
      navigator.clipboard.writeText(buildLedgerMarkdown());
    });
  }

  function readDecisionForm() {
    const decision = document.querySelector('input[name="human_decision"]:checked');
    return {
      finding_id: selectedFindingId,
      human_decision: decision ? decision.value : null,
      rationale: el("rationale")?.value.trim() || "",
    };
  }

  function saveDraft() {
    const f = findingsDoc.findings.find((x) => x.finding_id === selectedFindingId);
    const form = readDecisionForm();
    decisions.set(selectedFindingId, {
      ...decisions.get(selectedFindingId),
      ...form,
      fixture_path: f.fixture_path,
      agent_suggestion: f.agent_suggestion,
      agent_label: f.label,
      moment: f.moment,
      status: "pending",
    });
    saveDecisions();
    render();
  }

  function lockDecision() {
    const form = readDecisionForm();
    if (!form.human_decision) {
      alert(t("pickDecision"));
      return;
    }
    if (form.rationale.length < 8) {
      alert(t("rationaleShort"));
      return;
    }
    if (!confirm(t("lockConfirm"))) return;
    const f = findingsDoc.findings.find((x) => x.finding_id === selectedFindingId);
    decisions.set(selectedFindingId, {
      ...form,
      fixture_path: f.fixture_path,
      agent_suggestion: f.agent_suggestion,
      agent_label: f.label,
      moment: f.moment,
      status: "reviewed",
      locked_at: new Date().toISOString(),
    });
    saveDecisions();
    const next = findingsDoc.findings.find(
      (x) => decisionState(x.finding_id) !== "locked" && x.finding_id !== selectedFindingId
    );
    if (next) {
      selectedFindingId = next.finding_id;
      currentRoomId = decisionRoomId(next.finding_id);
      stepIndex = 0;
      saveRoom();
    }
    render();
  }

  function unlockDecision() {
    if (!confirm(t("unlockConfirm"))) return;
    const d = decisions.get(selectedFindingId);
    if (d) {
      delete d.locked_at;
      d.status = "pending";
      saveDecisions();
    }
    render();
  }

  function handleSubmitQuiz() {
    let score = 0;
    DATA.quizQuestions.forEach((q) => {
      const sel = document.querySelector(`input[name="quiz_${q.id}"]:checked`);
      if (sel) quizState.answers[q.id] = parseInt(sel.value, 10);
      if (quizState.answers[q.id] === q.answer) score++;
    });
    const allAnswered = DATA.quizQuestions.every((q) => quizState.answers[q.id] !== undefined);
    if (!allAnswered) {
      alert(t("allAnswered"));
      return;
    }
    quizState.submitted = true;
    quizState.score = score;
    quizState.passed = score === DATA.quizQuestions.length;
    saveQuizState();
    render();
    if (quizState.passed) navigateTo("corridor");
    else alert(`${t("quizScore", score, DATA.quizQuestions.length)} — ${t("reviewRetake")}`);
  }

  function showWelcomeIfNeeded() {
    const seen = localStorage.getItem(CFG.storage.legacy.welcome) || localStorage.getItem(storageKey("welcome"));
    const overlay = el("welcomeOverlay");
    if (!seen) overlay.classList.remove("hidden");
    else overlay.classList.add("hidden");
  }

  function dismissWelcome(startTour) {
    localStorage.setItem(CFG.storage.legacy.welcome, "1");
    localStorage.setItem(storageKey("welcome"), "1");
    el("welcomeOverlay").classList.add("hidden");
    if (startTour) navigateTo("context");
  }

  function resetProgress() {
    if (!confirm(t("resetConfirm"))) return;
    decisions = new Map();
    quizState = { answers: {}, passed: false, submitted: false };
    clarifications = [];
    currentRoomId = "welcome";
    saveDecisions();
    saveQuizState();
    saveClarifications();
    saveRoom();
    localStorage.removeItem(CFG.storage.legacy.welcome);
    localStorage.removeItem(storageKey("welcome"));
    render();
    showWelcomeIfNeeded();
  }

  function render() {
    updateHeader();
    updateBanners();
    el("mainContent").innerHTML = renderFloorPlan() + renderRoomContent();
    renderLedger();
    bindRoomEvents();
  }

  function bindGlobalEvents() {
    el("langEn").onclick = () => {
      lang = "en";
      localStorage.setItem(CFG.storage.legacy.lang, lang);
      localStorage.setItem(storageKey("lang"), lang);
      render();
    };
    el("langEs").onclick = () => {
      lang = "es";
      localStorage.setItem(CFG.storage.legacy.lang, lang);
      localStorage.setItem(storageKey("lang"), lang);
      render();
    };
    el("resetBtn").onclick = resetProgress;
    el("welcomeStart").onclick = () => dismissWelcome(true);
    el("welcomeSkip").onclick = () => dismissWelcome(false);
    el("findingsInput").addEventListener("change", async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      try {
        findingsDoc = normalizeFindings(JSON.parse(await file.text()));
        selectedFindingId = findingsDoc.findings[0]?.finding_id || null;
        render();
      } catch (err) {
        alert(err.message);
      }
    });
  }

  async function init() {
    loadStorage();
    bindGlobalEvents();
    showWelcomeIfNeeded();
    try {
      await loadFindings();
      selectedFindingId = findingsDoc.findings[0]?.finding_id || null;
    } catch (err) {
      el("statusBanner").textContent = "Failed to load findings: " + err.message;
      el("statusBanner").className = "banner";
    }
    render();
  }

  init();
})();
