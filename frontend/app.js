/* ══ HEC Intelligence — App ═══════════════════════════════ */

const API = "";

/* ── State ────────────────────────────────────────────────── */
const state = {
  chats:        [],
  activeChatId: null,
  activeModel:  null,
  isStreaming:  false,
  sidebarOpen:  true,
  filterOpen:   false,
  uploadedFiles: [],   // { id, filename, chunks }
  filters:      { district: "", year: "", doc_type: "" },
};

/* ── Persisted keys ───────────────────────────────────────── */
const CHATS_KEY  = "hec_chats";
const THEME_KEY  = "hec_theme";
const MODEL_KEY  = "hec_model";

/* ── DOM ──────────────────────────────────────────────────── */
const $ = id => document.getElementById(id);
const dom = {
  app:           $("app"),
  sidebar:       $("sidebar"),
  sidebarClose:  $("sidebarClose"),
  sidebarOpen:   $("sidebarOpen"),
  brandDot:      $("brandDot"),
  newChatBtn:    $("newChatBtn"),
  pastChats:     $("pastChats"),
  modelBtn:      $("modelBtn"),
  modelBtnText:  $("modelBtnText"),
  modelDropdown: $("modelDropdown"),
  themeBtn:      $("themeBtn"),
  topbarTitle:   $("topbarTitle"),
  filterToggle:  $("filterToggle"),
  filterDot:     $("filterDot"),
  filterPanel:   $("filterPanel"),
  filterDistrict:$("filterDistrict"),
  filterYear:    $("filterYear"),
  filterType:    $("filterType"),
  clearFilters:  $("clearFilters"),
  filterBadge:   $("filterBadge"),
  conversation:  $("conversation"),
  welcome:       $("welcome"),
  statDeaths:    $("statDeaths"),
  statInjuries:  $("statInjuries"),
  statElephants: $("statElephants"),
  statIncidents: $("statIncidents"),
  districtBars:  $("districtBars"),
  chips:         $("chips"),
  uploadsBar:    $("uploadsBar"),
  attachBtn:     $("attachBtn"),
  fileInput:     $("fileInput"),
  queryInput:    $("queryInput"),
  sendBtn:       $("sendBtn"),
  sourcesPanel:  $("sourcesPanel"),
  spClose:       $("spClose"),
  spCount:       $("spCount"),
  spContext:     $("spContext"),
  spList:        $("spList"),
};

/* ══ INIT ═════════════════════════════════════════════════ */
(async function init() {
  applyTheme(localStorage.getItem(THEME_KEY) || "light");
  loadChatsFromStorage();
  renderPastChats();

  // Restore sidebar state
  const savedSidebar = localStorage.getItem("hec_sidebar");
  if (savedSidebar === "closed") closeSidebar();

  // Wire up events
  dom.sidebarClose.addEventListener("click", closeSidebar);
  dom.sidebarOpen.addEventListener("click", openSidebar);
  dom.spClose.addEventListener("click", closeSourcesPanel);
  dom.newChatBtn.addEventListener("click", newChat);
  dom.themeBtn.addEventListener("click", toggleTheme);
  dom.modelBtn.addEventListener("click", toggleModelDropdown);
  dom.filterToggle.addEventListener("click", toggleFilterPanel);
  dom.clearFilters.addEventListener("click", clearFilters);
  dom.filterDistrict.addEventListener("change", onFilterChange);
  dom.filterYear.addEventListener("change", onFilterChange);
  dom.filterType.addEventListener("change", onFilterChange);
  dom.queryInput.addEventListener("input", onInputChange);
  dom.queryInput.addEventListener("keydown", onKeyDown);
  dom.sendBtn.addEventListener("click", submitQuery);
  dom.attachBtn.addEventListener("click", () => dom.fileInput.click());
  dom.fileInput.addEventListener("change", onFilesSelected);

  // Suggestion chips
  dom.chips.querySelectorAll(".chip").forEach(btn => {
    btn.addEventListener("click", () => {
      dom.queryInput.value = btn.dataset.q;
      onInputChange();
      submitQuery();
    });
  });

  // Close model dropdown on outside click
  document.addEventListener("click", e => {
    if (!$("modelPicker").contains(e.target)) closeModelDropdown();
  });

  // Load data in parallel
  await Promise.all([loadHealth(), loadStats(), loadDistricts(), loadModels()]);
})();

/* ══ THEME ════════════════════════════════════════════════ */
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem(THEME_KEY, theme);
}

function toggleTheme() {
  const current = document.documentElement.dataset.theme;
  applyTheme(current === "dark" ? "light" : "dark");
}

/* ══ SOURCES PANEL ════════════════════════════════════════ */
let activeSrcBtn = null;

function openSourcesPanel(sources, queryText, triggerBtn = null) {
  dom.spCount.textContent = sources.length;
  dom.spContext.textContent = queryText;
  dom.spList.innerHTML = sources.map(s => {
    const typeMap = { incident: "Incident", research: "Research", prevention: "Prevention", uploaded_pdf: "PDF" };
    const tagClass = { incident: "tag-incident", research: "tag-research", prevention: "tag-prevention", uploaded_pdf: "tag-pdf" }[s.doc_type] || "tag-default";
    const typeLabel = typeMap[s.doc_type] || "";
    const tags = [
      typeLabel    ? `<span class="tag ${tagClass}">${typeLabel}</span>` : "",
      s.district   ? `<span class="tag tag-default">${esc(s.district)}</span>` : "",
      s.date       ? `<span class="tag tag-default">${esc(String(s.date))}</span>` : (s.year ? `<span class="tag tag-default">${s.year}</span>` : ""),
      s.incident_type ? `<span class="tag tag-default">${esc(s.incident_type.replace(/_/g," "))}</span>` : "",
    ].filter(Boolean).join("");
    return `
      <div class="sp-card">
        <div class="sp-card-num">${s.index}</div>
        <div class="sp-card-source">${esc(s.source || s.title || "Unknown")}</div>
        <div class="sp-card-tags">${tags}</div>
        ${s.excerpt ? `<div class="sp-card-excerpt">${esc(s.excerpt)}</div>` : ""}
      </div>`;
  }).join("");

  dom.sourcesPanel.classList.add("open");

  // Track active source button
  if (activeSrcBtn && activeSrcBtn !== triggerBtn) activeSrcBtn.classList.remove("src-active");
  if (triggerBtn) { triggerBtn.classList.add("src-active"); activeSrcBtn = triggerBtn; }
}

function closeSourcesPanel() {
  dom.sourcesPanel.classList.remove("open");
  if (activeSrcBtn) { activeSrcBtn.classList.remove("src-active"); activeSrcBtn = null; }
}

/* ══ SIDEBAR ══════════════════════════════════════════════ */
function openSidebar() {
  state.sidebarOpen = true;
  dom.sidebar.classList.remove("hidden");
  localStorage.setItem("hec_sidebar", "open");
}

function closeSidebar() {
  state.sidebarOpen = false;
  dom.sidebar.classList.add("hidden");
  localStorage.setItem("hec_sidebar", "closed");
}

/* ══ MODEL ════════════════════════════════════════════════ */
async function loadModels() {
  try {
    const { models, default: def } = await apiFetch("/api/models");
    const saved = localStorage.getItem(MODEL_KEY);
    state.activeModel = (saved && models.includes(saved)) ? saved : def;

    dom.modelBtnText.textContent = state.activeModel || def;
    dom.modelDropdown.innerHTML = models.map(m => `
      <div class="model-option ${m === state.activeModel ? "selected" : ""}" data-model="${esc(m)}">${esc(m)}</div>
    `).join("");

    dom.modelDropdown.querySelectorAll(".model-option").forEach(el => {
      el.addEventListener("click", () => selectModel(el.dataset.model));
    });
  } catch { /* fallback to default shown by health */ }
}

function selectModel(model) {
  state.activeModel = model;
  dom.modelBtnText.textContent = model;
  localStorage.setItem(MODEL_KEY, model);
  dom.modelDropdown.querySelectorAll(".model-option").forEach(el => {
    el.classList.toggle("selected", el.dataset.model === model);
  });
  closeModelDropdown();
}

function toggleModelDropdown() {
  dom.modelDropdown.classList.toggle("open");
}

function closeModelDropdown() {
  dom.modelDropdown.classList.remove("open");
}

/* ══ HEALTH ═══════════════════════════════════════════════ */
async function loadHealth() {
  dom.brandDot.className = "brand-dot loading";
  try {
    const data = await apiFetch("/api/health");
    if (!state.activeModel) {
      state.activeModel = data.model;
      dom.modelBtnText.textContent = data.model;
    }
    dom.brandDot.className = `brand-dot ${data.llm_ready ? "ready" : "error"}`;
    if (!data.llm_ready) {
      showToast("LLM not ready — make sure Ollama is running and the model is pulled.", "error");
    }
  } catch {
    dom.brandDot.className = "brand-dot error";
  }
}

/* ══ STATS ════════════════════════════════════════════════ */
async function loadStats() {
  try {
    const d = await apiFetch("/api/stats");
    dom.statDeaths.textContent    = d.total_human_deaths ?? "—";
    dom.statInjuries.textContent  = d.total_human_injuries ?? "—";
    dom.statElephants.textContent = d.total_elephant_deaths ?? "—";
    dom.statIncidents.textContent = d.total_incidents ?? "—";

    const top = d.top_districts || [];
    const max = top[0]?.count || 1;
    dom.districtBars.innerHTML = top.map(t => `
      <div class="district-row">
        <span class="district-name">${esc(t.district)}</span>
        <div class="district-track"><div class="district-fill" style="width:${Math.round(t.count/max*100)}%"></div></div>
        <span class="district-count">${t.count}</span>
      </div>`).join("") || "<p style='font-size:12px;color:var(--text-3)'>No data loaded yet.</p>";
  } catch {
    dom.districtBars.innerHTML = "<p style='font-size:12px;color:var(--text-3)'>Failed to load stats.</p>";
  }
}

/* ══ DISTRICTS ════════════════════════════════════════════ */
async function loadDistricts() {
  try {
    const { districts } = await apiFetch("/api/districts");
    districts.forEach(d => {
      const opt = document.createElement("option");
      opt.value = d; opt.textContent = d;
      dom.filterDistrict.appendChild(opt);
    });
  } catch { /* silent */ }
}

/* ══ FILTERS ══════════════════════════════════════════════ */
function toggleFilterPanel() {
  state.filterOpen = !state.filterOpen;
  dom.filterPanel.classList.toggle("open", state.filterOpen);
}

function onFilterChange() {
  state.filters.district = dom.filterDistrict.value;
  state.filters.year     = dom.filterYear.value;
  state.filters.doc_type = dom.filterType.value;
  updateFilterUI();
}

function clearFilters() {
  dom.filterDistrict.value = "";
  dom.filterYear.value     = "";
  dom.filterType.value     = "";
  onFilterChange();
}

function updateFilterUI() {
  const parts = [];
  if (state.filters.district) parts.push(state.filters.district);
  if (state.filters.year)     parts.push(state.filters.year);
  if (state.filters.doc_type) parts.push(dom.filterType.options[dom.filterType.selectedIndex].text);
  const active = parts.length > 0;
  dom.filterBadge.textContent = active ? `Filtering: ${parts.join(" · ")}` : "";
  dom.filterDot.style.display = active ? "block" : "none";
}

/* ══ CHAT MANAGEMENT ══════════════════════════════════════ */
function loadChatsFromStorage() {
  try { state.chats = JSON.parse(localStorage.getItem(CHATS_KEY) || "[]"); }
  catch { state.chats = []; }
}

function saveChatsToStorage() {
  localStorage.setItem(CHATS_KEY, JSON.stringify(state.chats));
}

function newChat() {
  state.activeChatId = null;
  dom.topbarTitle.textContent = "HEC Intelligence";
  showWelcome();
}

function showWelcome() {
  const existing = dom.conversation.querySelector(".chat-wrapper");
  if (existing) existing.remove();
  dom.welcome.style.display = "";
}

function hideWelcome() {
  dom.welcome.style.display = "none";
}

function getOrCreateChat(firstQuery) {
  if (state.activeChatId) {
    return state.chats.find(c => c.id === state.activeChatId);
  }
  const chat = {
    id:        `chat_${Date.now()}`,
    title:     firstQuery.slice(0, 48),
    messages:  [],
    createdAt: Date.now(),
  };
  state.chats.unshift(chat);
  state.activeChatId = chat.id;
  saveChatsToStorage();
  renderPastChats();
  dom.topbarTitle.textContent = chat.title;
  return chat;
}

function addMessageToChat(role, content, sources = null) {
  const chat = state.chats.find(c => c.id === state.activeChatId);
  if (!chat) return;
  const msg = { role, content };
  if (sources) msg.sources = sources;
  chat.messages.push(msg);
  saveChatsToStorage();
}

function loadChat(chatId) {
  const chat = state.chats.find(c => c.id === chatId);
  if (!chat) return;
  state.activeChatId = chatId;
  dom.topbarTitle.textContent = chat.title;
  hideWelcome();

  const existing = dom.conversation.querySelector(".chat-wrapper");
  if (existing) existing.remove();

  const wrapper = document.createElement("div");
  wrapper.className = "chat-wrapper";
  dom.conversation.appendChild(wrapper);

  const msgs = chat.messages;
  let i = 0;
  while (i < msgs.length) {
    const msg = msgs[i];
    if (msg.role === "user") {
      const userRow = buildUserBubble(msg.content);
      userRow.style.animation = "none";
      wrapper.appendChild(userRow);

      const nextMsg = msgs[i + 1];
      if (nextMsg && nextMsg.role === "assistant") {
        const botRow = buildBotRow();
        botRow.style.animation = "none";
        const typingEl  = botRow.querySelector(".typing-indicator");
        const contentEl = botRow.querySelector(".bot-content");
        const actionBar = botRow.querySelector(".action-bar");
        typingEl.style.display = "none";
        contentEl.removeAttribute("hidden");
        contentEl.innerHTML = renderMarkdown(nextMsg.content);
        buildActionBar(actionBar, contentEl, nextMsg.sources || [], msg.content);
        wrapper.appendChild(botRow);
        i += 2;
        continue;
      }
    }
    i++;
  }

  scrollToBottom();
  renderPastChats();
}

function deleteChat(chatId, e) {
  e.stopPropagation();
  state.chats = state.chats.filter(c => c.id !== chatId);
  saveChatsToStorage();
  if (state.activeChatId === chatId) newChat();
  renderPastChats();
}

/* ── Render past chats sidebar ───────────────────────────── */
function renderPastChats() {
  if (!state.chats.length) {
    dom.pastChats.innerHTML = "<p class='no-chats'>No conversations yet.</p>";
    return;
  }

  const now = Date.now();
  const groups = { today: [], yesterday: [], earlier: [] };
  state.chats.forEach(c => {
    const age = now - c.createdAt;
    if (age < 86400000)       groups.today.push(c);
    else if (age < 172800000) groups.yesterday.push(c);
    else                       groups.earlier.push(c);
  });

  let html = "";
  const addGroup = (label, chats) => {
    if (!chats.length) return;
    html += `<div class="chat-group-label">${label}</div>`;
    chats.forEach(c => {
      html += `
        <div class="chat-item ${c.id === state.activeChatId ? "active" : ""}" data-id="${esc(c.id)}">
          <span class="chat-item-title">${esc(c.title)}</span>
          <button class="chat-delete" data-del="${esc(c.id)}" title="Delete">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6 6 18M6 6l12 12"/></svg>
          </button>
        </div>`;
    });
  };

  addGroup("Today",     groups.today);
  addGroup("Yesterday", groups.yesterday);
  addGroup("Earlier",   groups.earlier);

  dom.pastChats.innerHTML = html;

  dom.pastChats.querySelectorAll(".chat-item").forEach(el => {
    el.addEventListener("click", () => loadChat(el.dataset.id));
  });

  dom.pastChats.querySelectorAll(".chat-delete").forEach(btn => {
    btn.addEventListener("click", e => deleteChat(btn.dataset.del, e));
  });
}

/* ══ FILE UPLOAD ══════════════════════════════════════════ */
async function onFilesSelected() {
  const files = [...dom.fileInput.files];
  dom.fileInput.value = "";
  for (const file of files) await uploadFile(file);
}

async function uploadFile(file) {
  const tempId = `upload_${Date.now()}`;
  addFileChip(tempId, file.name, true);

  try {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API}/api/upload`, { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Upload failed (${res.status})`);
    }
    const data = await res.json();
    updateFileChip(tempId, data.upload_id, file.name, data.chunks_added);
    state.uploadedFiles.push({ id: data.upload_id, filename: file.name, chunks: data.chunks_added });
    showToast(`"${file.name}" added — ${data.chunks_added} chunks indexed.`, "success");
  } catch (err) {
    removeFileChip(tempId);
    showToast(`Upload failed: ${err.message}`, "error");
  }
}

function addFileChip(id, filename, loading = false) {
  const chip = document.createElement("div");
  chip.className = `file-chip ${loading ? "uploading" : ""}`;
  chip.dataset.chipId = id;
  chip.innerHTML = `
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
    <span class="file-chip-name">${esc(filename)}</span>
    ${loading ? '<span style="font-size:10px;opacity:.6">uploading…</span>' : ''}
    <button class="file-chip-remove" data-remove="${esc(id)}" title="Remove">
      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6 6 18M6 6l12 12"/></svg>
    </button>`;
  chip.querySelector(".file-chip-remove").addEventListener("click", () => removeFileChip(id));
  dom.uploadsBar.appendChild(chip);
}

function updateFileChip(tempId, realId, filename, chunks) {
  const chip = dom.uploadsBar.querySelector(`[data-chip-id="${tempId}"]`);
  if (!chip) return;
  chip.dataset.chipId = realId;
  chip.classList.remove("uploading");
  chip.innerHTML = `
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
    <span class="file-chip-name">${esc(filename)}</span>
    <button class="file-chip-remove" data-remove="${esc(realId)}" title="Remove">
      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6 6 18M6 6l12 12"/></svg>
    </button>`;
  chip.querySelector(".file-chip-remove").addEventListener("click", () => removeFileChip(realId));
}

function removeFileChip(id) {
  const chip = dom.uploadsBar.querySelector(`[data-chip-id="${id}"]`);
  if (chip) chip.remove();
  state.uploadedFiles = state.uploadedFiles.filter(f => f.id !== id);
}

/* ══ INPUT ════════════════════════════════════════════════ */
function onInputChange() {
  const val = dom.queryInput.value.trim();
  dom.sendBtn.disabled = !val || state.isStreaming;
  autoResize();
}

function autoResize() {
  dom.queryInput.style.height = "auto";
  dom.queryInput.style.height = Math.min(dom.queryInput.scrollHeight, 140) + "px";
}

function onKeyDown(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    if (!dom.sendBtn.disabled) submitQuery();
  }
}

/* ══ SUBMIT QUERY ═════════════════════════════════════════ */
async function submitQuery() {
  const query = dom.queryInput.value.trim();
  if (!query || state.isStreaming) return;

  state.isStreaming = true;
  dom.sendBtn.disabled = true;
  dom.queryInput.value = "";
  dom.queryInput.style.height = "auto";

  hideWelcome();

  // Ensure chat wrapper exists
  let wrapper = dom.conversation.querySelector(".chat-wrapper");
  if (!wrapper) {
    wrapper = document.createElement("div");
    wrapper.className = "chat-wrapper";
    dom.conversation.appendChild(wrapper);
  }

  getOrCreateChat(query);
  addMessageToChat("user", query);

  // User bubble
  const userRow = buildUserBubble(query);
  wrapper.appendChild(userRow);
  scrollToBottom();

  // Bot row with typing indicator
  const botRow = buildBotRow();
  wrapper.appendChild(botRow);
  scrollToBottom();

  const typingEl  = botRow.querySelector(".typing-indicator");
  const contentEl = botRow.querySelector(".bot-content");
  const actionBar = botRow.querySelector(".action-bar");

  const reqBody = {
    query,
    district: state.filters.district || null,
    year:     state.filters.year     ? parseInt(state.filters.year) : null,
    doc_type: state.filters.doc_type || null,
    model:    state.activeModel || null,
  };

  let fullText = "";
  let sources  = [];

  try {
    const resp = await fetch(`${API}/api/chat`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(reqBody),
    });

    if (!resp.ok) throw new Error(`Server error (${resp.status})`);

    const reader  = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    let cursorEl = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop();

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        let evt;
        try { evt = JSON.parse(line.slice(6)); } catch { continue; }

        if (evt.type === "token") {
          fullText += evt.content;
          if (typingEl.style.display !== "none") {
            typingEl.style.display = "none";
            contentEl.removeAttribute("hidden");
          }
          cursorEl?.remove();
          contentEl.innerHTML = renderMarkdown(fullText);
          cursorEl = appendCursor(contentEl);
          scrollToBottom();

        } else if (evt.type === "sources") {
          sources = evt.sources || [];

        } else if (evt.type === "error") {
          cursorEl?.remove();
          typingEl.style.display = "none";
          contentEl.removeAttribute("hidden");
          contentEl.innerHTML = `<div class="error-msg">${esc(evt.message)}</div>`;

        } else if (evt.type === "done") {
          cursorEl?.remove();
          buildActionBar(actionBar, contentEl, sources, query);
        }
      }
    }
  } catch (err) {
    typingEl.style.display = "none";
    contentEl.removeAttribute("hidden");
    contentEl.innerHTML = `<div class="error-msg">Request failed: ${esc(err.message)}</div>`;
  } finally {
    addMessageToChat("assistant", fullText, sources.length ? sources : null);
    state.isStreaming = false;
    dom.sendBtn.disabled = !dom.queryInput.value.trim();
    scrollToBottom();
  }
}

/* ══ DOM BUILDERS ═════════════════════════════════════════ */
function buildUserBubble(content) {
  const row = document.createElement("div");
  row.className = "msg-row user-row";
  row.innerHTML = `<div class="user-bubble">${esc(content)}</div>`;
  return row;
}

function buildBotRow() {
  const row = document.createElement("div");
  row.className = "msg-row bot-row";
  row.innerHTML = `
    <div class="bot-avatar">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
    </div>
    <div class="bot-bubble-wrap">
      <div class="bot-bubble">
        <div class="typing-indicator">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
        <div class="bot-content" hidden></div>
      </div>
      <div class="action-bar" hidden></div>
    </div>`;
  return row;
}

function buildActionBar(barEl, contentEl, sources, query) {
  const n = sources.length;
  barEl.innerHTML = `
    <button class="action-btn copy-btn" title="Copy response">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
    </button>
    ${n ? `
    <button class="action-btn src-btn" title="View sources">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      <span class="src-badge">${n}</span>
    </button>` : ""}
    <button class="action-btn regen-btn" title="Regenerate response">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-4.95"/></svg>
    </button>`;

  barEl.removeAttribute("hidden");

  barEl.querySelector(".copy-btn").addEventListener("click", () => copyResponse(contentEl, barEl.querySelector(".copy-btn")));
  if (n) {
    const srcBtn = barEl.querySelector(".src-btn");
    srcBtn.addEventListener("click", () => {
      if (srcBtn.classList.contains("src-active")) {
        closeSourcesPanel();
      } else {
        openSourcesPanel(sources, query, srcBtn);
      }
    });
  }
  barEl.querySelector(".regen-btn").addEventListener("click", () => regenerateQuery(query));
}

function copyResponse(contentEl, btn) {
  const text = contentEl.innerText || contentEl.textContent || "";
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.innerHTML;
    btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>`;
    btn.style.color = "var(--accent-mid)";
    setTimeout(() => { btn.innerHTML = orig; btn.style.color = ""; }, 1800);
  }).catch(() => showToast("Copy failed — select the text manually.", "error"));
}

function regenerateQuery(query) {
  if (state.isStreaming) return;
  dom.queryInput.value = query;
  onInputChange();
  submitQuery();
}

function appendCursor(el) {
  const span = document.createElement("span");
  span.className = "cursor";
  el.appendChild(span);
  return span;
}

function scrollToBottom() {
  dom.conversation.scrollTop = dom.conversation.scrollHeight;
}


/* ══ MARKDOWN RENDERER (lightweight) ══════════════════════ */
function renderMarkdown(text) {
  let html = esc(text);
  // Bold / italic
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
  // Headings → bold paragraph
  html = html.replace(/^#{1,3}\s+(.+)$/gm, "<strong>$1</strong>");
  // Unordered list items
  html = html.replace(/^[-•]\s+(.+)$/gm, "<li>$1</li>");
  // Wrap consecutive li in ul
  html = html.replace(/(<li>[\s\S]*?<\/li>(?:\n<li>[\s\S]*?<\/li>)*)/g, "<ul>$1</ul>");
  // Paragraphs
  html = html.split(/\n{2,}/).map(p => {
    p = p.trim();
    if (!p) return "";
    if (p.startsWith("<ul>") || p.startsWith("<li>")) return p;
    return `<p>${p.replace(/\n/g, " ")}</p>`;
  }).join("\n");
  return html;
}

/* ══ UTILITIES ════════════════════════════════════════════ */
function esc(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function apiFetch(path, options = {}) {
  const res = await fetch(`${API}${path}`, options);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/* ── Toast ────────────────────────────────────────────────── */
function showToast(msg, type = "info") {
  const el = document.createElement("div");
  const colors = { success: "#166534", error: "#991b1b", info: "#1e3a8a" };
  const bgs    = { success: "#dcfce7", error: "#fee2e2", info: "#dbeafe" };
  el.style.cssText = `
    position:fixed; bottom:20px; right:20px; max-width:320px; z-index:9999;
    padding:10px 14px; border-radius:9px; font-size:13px; line-height:1.4;
    color:${colors[type] || "#1a1a1a"};
    background:${bgs[type] || "#f5f5f5"};
    box-shadow:0 4px 16px rgba(0,0,0,.15);
    animation: fadein .2s ease;`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.style.opacity = "0", 3500);
  setTimeout(() => el.remove(), 3800);
}
