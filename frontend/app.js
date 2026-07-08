"use strict";
/* Alsamos LLM — frontend logic (vanilla JS, auth + tools). */
const $ = (id) => document.getElementById(id);
const state = { mode: "chat", models: { text: [], image: [] }, defaults: {}, hasKey: false, authOn: false, busy: false, history: [] };
let TOKEN = ""; try { TOKEN = localStorage.getItem("alsamos-token") || ""; } catch(e){}

const modeInfo = {
  chat:  { title: "\uD83D\uDCAC Chat",  hint: "Alsamos xato qilishi mumkin \u2014 muhim natijalarni tekshiring." },
  agent: { title: "\uD83E\uDDE0 Agent rejimi", hint: "Agent vazifani tugatmaguncha reasoning\u2192strategy\u2192tool\u2192validation orqali ishlaydi." },
  image: { title: "\uD83C\uDFA8 Rasm generatsiya", hint: "Bepul (Pollinations) \u2014 API kalit talab qilinmaydi." },
};

if (window.marked) marked.setOptions({ breaks: true, gfm: true,
  highlight: (c) => { try { return window.hljs ? hljs.highlightAuto(c).value : c; } catch(e){ return c; } } });

function renderMD(t){ try { return window.marked ? marked.parse(t) : escapeHtml(t); } catch(e){ return escapeHtml(t); } }
function escapeHtml(s){ const d=document.createElement("div"); d.textContent=s; return d.innerHTML; }
function authHeaders(extra){ const h = Object.assign({}, extra||{}); if (TOKEN) h["Authorization"] = "Bearer "+TOKEN; return h; }
async function api(path, opts){
  opts = opts || {}; opts.headers = authHeaders(opts.headers);
  const res = await fetch(path, opts);
  if (res.status === 401){ showLogin(); throw new Error("unauthorized"); }
  return res;
}

/* ---------- AUTH ---------- */
function showLogin(){ $("loginOverlay").style.display = "flex"; setTimeout(()=>$("loginPass").focus(), 50); }
function hideLogin(){ $("loginOverlay").style.display = "none"; }
async function doLogin(){
  const pass = $("loginPass").value; const err = $("loginErr"); err.textContent = "";
  try {
    const res = await fetch("/api/login", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({ password: pass }) });
    const d = await res.json();
    if (d.ok){ TOKEN = d.token || ""; try { localStorage.setItem("alsamos-token", TOKEN); } catch(e){} hideLogin(); boot(); }
    else { err.textContent = d.message || "Parol noto'g'ri."; }
  } catch(e){ err.textContent = "Server bilan aloqa yo'q."; }
}

/* ---------- BOOT ---------- */
async function boot(){
  let d = null;
  try { const r = await fetch("/api/models", { headers: authHeaders() }); d = await r.json(); } catch(e){}
  if (!d){ return; }
  state.models = { text: d.text || [], image: d.image || [] };
  state.defaults = d.defaults || {}; state.hasKey = !!d.has_key; state.authOn = !!d.auth;
  if (state.authOn && !TOKEN){ showLogin(); return; }
  const ks = $("keyStatus");
  if (state.hasKey){ ks.textContent = "\u25CF OpenRouter kaliti ulangan"; ks.className = "key-status ok"; }
  else { ks.textContent = "\u25CB Matn modellari uchun .env'ga OPENROUTER_API_KEY qo'ying (rasm bepul ishlaydi)"; ks.className = "key-status warn"; }
  populateModels(); refreshMetrics();
}

function populateModels(){
  const sel = $("modelSelect"); sel.innerHTML = "";
  const list = state.mode === "image" ? state.models.image : state.models.text;
  list.forEach(m => { const o = document.createElement("option"); o.value = m.id; o.textContent = m.name; o.dataset.desc = m.description || ""; sel.appendChild(o); });
  let def = state.mode === "image" ? state.defaults.image : (state.mode === "agent" ? state.defaults.agent : state.defaults.text);
  if (def && list.some(m => m.id === def)) sel.value = def;
  updateDesc();
}
function updateDesc(){ const o = $("modelSelect").selectedOptions[0]; $("modelDesc").textContent = o ? (o.dataset.desc||"") : ""; }

async function refreshMetrics(){
  try {
    const r = await api("/api/metrics"); const m = await r.json();
    $("mSuccess").textContent = m.total ? Math.round(m.success_rate*100)+"%" : "\u2013";
    $("mQuality").textContent = m.total ? m.avg_quality.toFixed(2) : "\u2013";
    const tr = { improving:"\u2197 yaxshilanmoqda", declining:"\u2198 pasaymoqda", stable:"\u2192 barqaror" };
    $("mTrend").textContent = m.total ? (tr[m.quality_trend]||m.quality_trend) : "\u2013";
    $("mTotal").textContent = m.total || "0";
  } catch(e){}
}

function setMode(mode){
  state.mode = mode;
  document.querySelectorAll(".mode-btn").forEach(b => b.classList.toggle("active", b.dataset.mode === mode));
  $("topbarTitle").textContent = modeInfo[mode].title;
  $("composerHint").textContent = modeInfo[mode].hint;
  populateModels();
}

function hideWelcome(){ $("welcome").classList.add("hidden"); }
function scrollDown(){ const c = $("chat"); c.scrollTop = c.scrollHeight; }

function addMsg(role, html){
  hideWelcome();
  const wrap = document.createElement("div"); wrap.className = "msg " + role;
  wrap.innerHTML = `<div class="avatar">${role==="user"?"\uD83D\uDC64":"A"}</div>`+
    `<div class="body"><div class="role">${role==="user"?"Siz":"Alsamos"}</div>`+
    `<div class="content"></div></div>`;
  wrap.querySelector(".content").innerHTML = html;
  $("messages").appendChild(wrap); scrollDown();
  return wrap.querySelector(".content");
}
function typingBubble(){ return addMsg("assistant", `<div class="typing"><span></span><span></span><span></span></div>`); }

async function sendChat(text, contentEl){
  const messages = state.history.concat([{ role:"user", content:text }]);
  const res = await api("/api/chat", { method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({ model: $("modelSelect").value, messages }) });
  let acc = "";
  await readSSE(res, (ev) => {
    if (ev.type === "token"){ acc += ev.text; contentEl.innerHTML = renderMD(acc) + `<span class="cursor"></span>`; scrollDown(); }
    else if (ev.type === "error"){ contentEl.innerHTML = `<div class="badge red">Xato</div> ${escapeHtml(ev.message)}`; }
  });
  contentEl.innerHTML = renderMD(acc);
  state.history.push({ role:"user", content:text }); state.history.push({ role:"assistant", content:acc });
}

async function sendAgent(text, contentEl){
  const trace = document.createElement("div"); trace.className = "trace";
  trace.innerHTML = `<div class="trace-head"><span class="spin"></span><span class="trace-title">Ishlanmoqda\u2026</span><span class="chev">\u25BE</span></div><div class="trace-body"></div>`;
  contentEl.appendChild(trace);
  const head = trace.querySelector(".trace-title");
  const body = trace.querySelector(".trace-body");
  trace.querySelector(".trace-head").onclick = () => trace.classList.toggle("collapsed");
  const answer = document.createElement("div"); contentEl.appendChild(answer);

  const step = (cls, html) => { const s = document.createElement("div"); s.className = "step "+(cls||""); s.innerHTML = `<span class="dot"></span><span>${html}</span>`; body.appendChild(s); scrollDown(); return s; };
  const res = await api("/api/agent", { method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({ model: $("modelSelect").value, task:text, history: state.history }) });

  let acc = "";
  await readSSE(res, (ev) => {
    switch(ev.type){
      case "stage": step("", ev.label); break;
      case "reasoning": {
        const d = ev.data;
        step("ok", `<b>Tahlil:</b> murakkablik <span class="badge blue">${d.complexity}</span>`+
          (d.deep_reasoning?` <span class="badge">4-bosqichli deep reasoning</span>`:"")+
          (d.dependencies&&d.dependencies.length?`<br>Bog'liqliklar: ${d.dependencies.join(", ")}`:""));
        break; }
      case "strategy": step("ok", `<b>Strategiya:</b> <span class="badge blue">${ev.data.name}</span> \u2014 ${escapeHtml(ev.data.rationale)}`); break;
      case "iteration": acc=""; step("", ev.label); break;
      case "token": acc += ev.text; break;
      case "tool": {
        if (ev.phase === "call") step("tool", `\uD83D\uDD27 <b>Tool:</b> <span class="badge blue">${escapeHtml(ev.name)}</span> <code>${escapeHtml(JSON.stringify(ev.args||{}).slice(0,120))}</code>`);
        else { const ok = ev.ok; const dl = ev.data && ev.data.result && ev.data.result.download_url;
          step(ok?"ok":"warn", `\uD83D\uDD27 Natija: <span class="badge ${ok?"green":"red"}">${ok?"ok":"xato"}</span>`+(dl?` <a href="${dl}" target="_blank">\u2B07 Yuklab olish</a>`:"")); }
        break; }
      case "validation": {
        const v = ev.data; const cls = v.passed?"ok":"warn";
        const bd = v.passed?`<span class="badge green">o'tdi \u00B7 ${v.score}</span>`:`<span class="badge red">qayta ishlash \u00B7 ${v.score}</span>`;
        step(cls, `<b>Self-validation</b> (${v.level}): ${bd}`); break; }
      case "final": {
        answer.innerHTML = renderMD(ev.output || "");
        const k = ev.knowledge||{};
        head.innerHTML = (ev.success?`\u2714 Yakunlandi`:`\u26A0 Qisman`)+` \u2014 `+
          `<span class="badge ${ev.success?"green":"red"}">${ev.success?"muvaffaqiyatli":"to'liq emas"}</span>`+
          ` <span class="badge">sifat ${ev.quality}</span> <span class="badge">${ev.iterations} urinish</span>`+
          (ev.tool_calls?` <span class="badge blue">${ev.tool_calls} tool</span>`:"")+
          (k.domain?` <span class="badge blue">${k.domain}: ${k.level}</span>`:"");
        const spin = trace.querySelector(".spin"); if (spin) spin.outerHTML = `<span class="done">\u2714</span>`;
        trace.classList.add("collapsed");
        break; }
      case "error": answer.innerHTML = `<div class="badge red">Xato</div> ${escapeHtml(ev.message)}`; break;
    }
  });
  if (answer.innerHTML.trim()){ state.history.push({ role:"user", content:text }); state.history.push({ role:"assistant", content: answer.textContent }); }
  refreshMetrics();
}

async function sendImage(text, contentEl){
  contentEl.innerHTML = `<div class="img-result"><div class="img-skeleton"></div></div>`;
  try {
    const res = await api("/api/image", { method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ model: $("modelSelect").value, prompt:text }) });
    const d = await res.json();
    const img = new Image(); img.alt = text; img.src = d.url;
    img.onload = () => { contentEl.innerHTML = `<div class="img-result"></div>`; contentEl.firstChild.appendChild(img); scrollDown(); };
    img.onerror = () => { contentEl.innerHTML = `<div class="badge red">Rasm yuklanmadi</div> <a href="${d.url}" target="_blank">Havola</a>`; };
  } catch(e){ contentEl.innerHTML = `<div class="badge red">Xato</div> ${escapeHtml(String(e))}`; }
}

async function readSSE(res, onEvent){
  if (!res.body){ onEvent({ type:"error", message:"Server bilan aloqa yo'q ("+res.status+")" }); return; }
  const reader = res.body.getReader(); const dec = new TextDecoder(); let buf = "";
  while(true){
    const { value, done } = await reader.read(); if (done) break;
    buf += dec.decode(value, { stream:true }); const parts = buf.split("\n\n"); buf = parts.pop();
    for (const p of parts){
      const line = p.split("\n").find(l => l.startsWith("data:")); if (!line) continue;
      try { onEvent(JSON.parse(line.slice(5).trim())); } catch(e){}
    }
  }
}

async function submit(){
  const input = $("input"); const text = input.value.trim();
  if (!text || state.busy) return;
  state.busy = true; $("send").disabled = true;
  addMsg("user", escapeHtml(text)); input.value = ""; input.style.height = "auto";
  const contentEl = typingBubble();
  try {
    if (state.mode === "chat") await sendChat(text, contentEl);
    else if (state.mode === "agent"){ contentEl.innerHTML = ""; await sendAgent(text, contentEl); }
    else await sendImage(text, contentEl);
  } catch(e){ if (String(e).indexOf("unauthorized")===-1) contentEl.innerHTML = `<div class="badge red">Xato</div> ${escapeHtml(String(e))}`; }
  finally { state.busy = false; $("send").disabled = false; input.focus(); }
}

function autoGrow(el){ el.style.height = "auto"; el.style.height = Math.min(el.scrollHeight, 200) + "px"; }

$("send").onclick = submit;
$("input").addEventListener("keydown", (e) => { if (e.key==="Enter" && !e.shiftKey){ e.preventDefault(); submit(); } });
$("input").addEventListener("input", (e) => autoGrow(e.target));
$("modelSelect").addEventListener("change", updateDesc);
document.querySelectorAll(".mode-btn").forEach(b => b.onclick = () => setMode(b.dataset.mode));
$("newChat").onclick = () => { state.history=[]; $("messages").innerHTML=""; $("welcome").classList.remove("hidden"); };
document.querySelectorAll(".suggestion").forEach(b => b.onclick = () => { $("input").value = b.textContent; autoGrow($("input")); submit(); });
$("themeToggle").onclick = () => {
  const cur = document.documentElement.getAttribute("data-theme")==="light"?"dark":"light";
  document.documentElement.setAttribute("data-theme", cur);
  $("themeToggle").textContent = cur==="light"?"\u2600":"\u263E";
  try { localStorage.setItem("alsamos-theme", cur); } catch(e){}
};
$("hamburger").onclick = () => { $("sidebar").classList.toggle("open"); };
if ($("loginBtn")){ $("loginBtn").onclick = doLogin;
  $("loginPass").addEventListener("keydown", (e)=>{ if(e.key==="Enter") doLogin(); }); }

(function initTheme(){ let t="dark"; try { t = localStorage.getItem("alsamos-theme")||"dark"; } catch(e){}
  document.documentElement.setAttribute("data-theme", t); $("themeToggle").textContent = t==="light"?"\u2600":"\u263E"; })();
boot();
setInterval(refreshMetrics, 15000);
