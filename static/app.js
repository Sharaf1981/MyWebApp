const I18N = {
  ar: {
    appTitle: "مساعدي الشخصي", chat: "المحادثة", tasks: "المهام", notes: "الملاحظات",
    newChat: "محادثة جديدة", send: "إرسال", chatPlaceholder: "اكتب رسالتك… مثلاً: فكّرني أشتري خبز بكرة",
    open: "الحالية", done: "المنتهية", all: "الكل", taskPlaceholder: "مهمة جديدة…",
    low: "منخفضة", medium: "متوسطة", high: "عالية", add: "إضافة",
    search: "بحث…", noteTitle: "عنوان الملاحظة", noteContent: "المحتوى (اختياري)", save: "حفظ",
    delete: "حذف", due: "الموعد", noTasks: "لا توجد مهام", noNotes: "لا توجد ملاحظات",
    thinking: "بيفكّر…", hint: "اسألني أي حاجة، أو اطلب مني أضيف مهمة أو ملاحظة.",
    errAuth: "مفتاح Claude API غير مضبوط. اضبط ANTHROPIC_API_KEY على السيرفر.",
    errRate: "طلبات كتير. استنى شوية وحاول تاني.", errGeneric: "حصل خطأ. حاول تاني.",
    switchLang: "English", pageTitle: "مساعدي الشخصي",
  },
  en: {
    appTitle: "My Assistant", chat: "Chat", tasks: "Tasks", notes: "Notes",
    newChat: "New chat", send: "Send", chatPlaceholder: "Type a message… e.g. remind me to buy bread tomorrow",
    open: "Open", done: "Done", all: "All", taskPlaceholder: "New task…",
    low: "Low", medium: "Medium", high: "High", add: "Add",
    search: "Search…", noteTitle: "Note title", noteContent: "Content (optional)", save: "Save",
    delete: "Delete", due: "Due", noTasks: "No tasks", noNotes: "No notes",
    thinking: "Thinking…", hint: "Ask me anything, or ask me to add a task or a note.",
    errAuth: "Claude API key is not set. Set ANTHROPIC_API_KEY on the server.",
    errRate: "Too many requests. Please wait and try again.", errGeneric: "Something went wrong. Please try again.",
    switchLang: "العربية", pageTitle: "My Assistant",
  },
};

const $ = (sel) => document.querySelector(sel);
const store = {
  get(key, fallback) { try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; } },
  set(key, value) { try { localStorage.setItem(key, value); } catch { /* storage unavailable */ } },
};

let lang = store.get("lang", "ar");
let conversationId = store.get("conversationId", null) || newConversationId();
const t = (key) => I18N[lang][key] ?? key;

function newConversationId() {
  const id = (crypto.randomUUID && crypto.randomUUID()) || String(Date.now());
  store.set("conversationId", id);
  return id;
}

async function api(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(data.error || res.statusText), { status: res.status, code: data.error });
  return data;
}

// --- Language ---

function applyLang() {
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  document.title = t("pageTitle");
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => { el.placeholder = t(el.dataset.i18nPlaceholder); });
  $("#langToggle").textContent = t("switchLang");
  const hint = $("#messages .hint");
  if (hint) hint.textContent = t("hint");
  renderTasks();
  renderNotes();
}

$("#langToggle").addEventListener("click", () => {
  lang = lang === "ar" ? "en" : "ar";
  store.set("lang", lang);
  applyLang();
});

// --- Tabs (mobile) ---

document.querySelectorAll(".tabs button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-selected", String(b === btn)));
    document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === `panel-${btn.dataset.tab}`));
  });
});

// --- Chat ---

function addMessage(text, cls) {
  $("#messages .hint")?.remove();
  const div = document.createElement("div");
  div.className = `msg ${cls}`;
  div.textContent = text;
  $("#messages").appendChild(div);
  $("#messages").scrollTop = $("#messages").scrollHeight;
  return div;
}

function showHint() {
  $("#messages").innerHTML = "";
  const p = document.createElement("p");
  p.className = "hint";
  p.textContent = t("hint");
  $("#messages").appendChild(p);
}

$("#chatForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = $("#chatInput");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  addMessage(text, "user");
  const typing = addMessage(t("thinking"), "bot typing");
  const submit = $("#chatForm button");
  submit.disabled = true;
  try {
    const { reply, changed } = await api("POST", "/api/chat", { message: text, conversation_id: conversationId });
    typing.remove();
    addMessage(reply, "bot");
    if (changed) { loadTasks(); loadNotes(); }
  } catch (err) {
    typing.remove();
    const key = err.status === 401 ? "errAuth" : err.status === 429 ? "errRate" : "errGeneric";
    addMessage(t(key), "bot error");
  } finally {
    submit.disabled = false;
    input.focus();
  }
});

$("#newChat").addEventListener("click", async () => {
  await api("POST", "/api/chat/reset", { conversation_id: conversationId }).catch(() => {});
  conversationId = newConversationId();
  showHint();
});

// --- Tasks ---

let tasks = [];

async function loadTasks() {
  tasks = await api("GET", `/api/tasks?status=${$("#taskFilter").value}`);
  renderTasks();
}

function renderTasks() {
  const list = $("#taskList");
  list.innerHTML = "";
  if (!tasks.length) {
    list.innerHTML = `<li class="empty"></li>`;
    list.firstChild.textContent = t("noTasks");
    return;
  }
  for (const task of tasks) {
    const li = document.createElement("li");
    if (task.done) li.classList.add("done");

    const check = document.createElement("input");
    check.type = "checkbox";
    check.checked = !!task.done;
    check.setAttribute("aria-label", task.title);
    check.addEventListener("change", async () => {
      await api("PATCH", `/api/tasks/${task.id}`, { done: check.checked });
      loadTasks();
    });

    const body = document.createElement("div");
    body.className = "body";
    const title = document.createElement("div");
    title.className = "title";
    title.textContent = task.title;
    const meta = document.createElement("div");
    meta.className = "meta";
    const badge = document.createElement("span");
    badge.className = `badge ${task.priority}`;
    badge.textContent = t(task.priority);
    meta.appendChild(badge);
    if (task.due_date) meta.append(` · ${t("due")}: ${task.due_date}`);
    body.append(title, meta);

    const del = document.createElement("button");
    del.className = "icon";
    del.type = "button";
    del.textContent = "✕";
    del.setAttribute("aria-label", t("delete"));
    del.addEventListener("click", async () => {
      await api("DELETE", `/api/tasks/${task.id}`);
      loadTasks();
    });

    li.append(check, body, del);
    list.appendChild(li);
  }
}

$("#taskFilter").addEventListener("change", loadTasks);
$("#taskForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  await api("POST", "/api/tasks", {
    title: $("#taskTitle").value,
    due_date: $("#taskDue").value || null,
    priority: $("#taskPriority").value,
  });
  e.target.reset();
  loadTasks();
});

// --- Notes ---

let notes = [];
let searchTimer;

async function loadNotes() {
  const q = $("#noteSearch").value.trim();
  notes = await api("GET", `/api/notes${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  renderNotes();
}

function renderNotes() {
  const list = $("#noteList");
  list.innerHTML = "";
  if (!notes.length) {
    list.innerHTML = `<li class="empty"></li>`;
    list.firstChild.textContent = t("noNotes");
    return;
  }
  for (const note of notes) {
    const li = document.createElement("li");
    const body = document.createElement("div");
    body.className = "body";
    const title = document.createElement("div");
    title.className = "title";
    title.textContent = note.title;
    body.appendChild(title);
    if (note.content) {
      const content = document.createElement("div");
      content.className = "note-content";
      content.textContent = note.content;
      body.appendChild(content);
    }
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = note.created_at;
    body.appendChild(meta);

    const del = document.createElement("button");
    del.className = "icon";
    del.type = "button";
    del.textContent = "✕";
    del.setAttribute("aria-label", t("delete"));
    del.addEventListener("click", async () => {
      await api("DELETE", `/api/notes/${note.id}`);
      loadNotes();
    });

    li.append(body, del);
    list.appendChild(li);
  }
}

$("#noteSearch").addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadNotes, 250);
});
$("#noteForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  await api("POST", "/api/notes", { title: $("#noteTitle").value, content: $("#noteContent").value });
  e.target.reset();
  loadNotes();
});

// --- Init ---

showHint();
applyLang();
loadTasks();
loadNotes();
