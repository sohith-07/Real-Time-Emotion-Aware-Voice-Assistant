/* ============================================================
   Shared utilities: API client, sidebar, theme, toasts
   ============================================================ */
(function (global) {
  "use strict";

  // API base - same origin when served by FastAPI, override via ?api=
  const API_BASE = (function () {
    const p = new URLSearchParams(location.search);
    if (p.get("api")) return p.get("api").replace(/\/$/, "");
    return ""; // same origin
  })();

  async function api(path, options = {}) {
    const opts = Object.assign(
      {
        headers: { "Content-Type": "application/json" },
      },
      options
    );
    if (opts.body && typeof opts.body !== "string") {
      opts.body = JSON.stringify(opts.body);
    }
    try {
      const res = await fetch(API_BASE + path, opts);
      const text = await res.text();
      const data = text ? JSON.parse(text) : null;
      if (!res.ok) {
        const msg = (data && (data.detail || data.message)) || res.statusText;
        throw new Error(msg);
      }
      return data;
    } catch (err) {
      // Network or parse error - surface a clean message.
      throw err;
    }
  }

  const API = {
    health: () => api("/api/health"),
    chat: (body) => api("/api/chat", { method: "POST", body }),
    emotion: (text) =>
      api("/api/emotion", { method: "POST", body: { text } }),
    emotionLabels: () => api("/api/emotion/labels"),
    conversations: () => api("/api/conversations"),
    conversation: (id) => api(`/api/conversations/${id}`),
    deleteConversation: (id) =>
      api(`/api/conversations/${id}`, { method: "DELETE" }),
    clearAll: () => api("/api/conversations/clear", { method: "POST" }),
    analytics: () => api("/api/analytics"),
    settings: () => api("/api/settings"),
    updateSetting: (key, value) =>
      api(`/api/settings/${key}`, { method: "PUT", body: { key, value } }),
    updateSettingsBulk: (arr) =>
      api("/api/settings", { method: "POST", body: { settings: arr } }),
    resetSettings: () => api("/api/settings/reset", { method: "POST" }),
    voiceInfo: () => api("/api/voice/info"),
    voices: () => api("/api/voice/voices"),
    engines: () => api("/api/chat/engines"),
  };

  /* ---------- Theme ---------- */
  function loadTheme() {
    const saved = localStorage.getItem("theme");
    document.documentElement.setAttribute("data-theme", saved || "light");
  }
  function toggleTheme() {
    const cur = document.documentElement.getAttribute("data-theme") || "light";
    const next = cur === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
    // Persist server-side so analytics / settings reflect choice.
    API.updateSetting("theme", next).catch(() => {});
    // Update icon if present.
    document.querySelectorAll(".theme-toggle").forEach((el) => {
      el.textContent = next === "dark" ? "☀" : "☾";
    });
  }

  /* ---------- Sidebar ---------- */
  function buildSidebar(active) {
    const links = [
      { key: "index",     href: "index.html",     ico: "🏠", label: "Home" },
      { key: "voice",     href: "voice.html",     ico: "🎙", label: "Voice Assistant" },
      { key: "chat",      href: "chat.html",      ico: "💬", label: "Text Chat" },
      { key: "analytics", href: "analytics.html", ico: "📊", label: "Analytics" },
      { key: "settings",  href: "settings.html",  ico: "⚙", label: "Settings" },
    ];
    return `
      <aside class="sidebar" id="sidebar">
        <div class="brand">
          <div class="brand-logo">E</div>
          <div>
            <div class="brand-name">EmotiVoice</div>
            <div class="brand-sub">Emotion-aware AI</div>
          </div>
        </div>
        <nav class="nav">
          ${links
            .map(
              (l) =>
                `<a class="nav-link ${active === l.key ? "active" : ""}" href="${l.href}">
                   <span class="ico">${l.ico}</span><span>${l.label}</span>
                 </a>`
            )
            .join("")}
        </nav>
        <div class="sidebar-footer">v1.0.0 · Web Speech + FastAPI</div>
      </aside>
      <div class="scrim" id="scrim"></div>
    `;
  }

  function mountShell(active) {
    loadTheme();
    const host = document.getElementById("shell");
    if (!host) return;
    host.innerHTML = buildSidebar(active);
    const sidebar = document.getElementById("sidebar");
    const scrim = document.getElementById("scrim");
    document.addEventListener("click", (e) => {
      if (e.target.closest("#menuBtn")) {
        sidebar.classList.add("open");
        scrim.classList.add("show");
      } else if (e.target.id === "scrim" || e.target.closest("#scrim")) {
        sidebar.classList.remove("open");
        scrim.classList.remove("show");
      }
    });
  }

  /* ---------- Toasts ---------- */
  function ensureToastHost() {
    let host = document.querySelector(".toast-host");
    if (!host) {
      host = document.createElement("div");
      host.className = "toast-host";
      document.body.appendChild(host);
    }
    return host;
  }
  function toast(message, kind = "info", ms = 3200) {
    const host = ensureToastHost();
    const el = document.createElement("div");
    el.className = `toast ${kind}`;
    el.textContent = message;
    host.appendChild(el);
    setTimeout(() => {
      el.style.opacity = "0";
      el.style.transform = "translateX(20px)";
      setTimeout(() => el.remove(), 240);
    }, ms);
  }

  /* ---------- Helpers ---------- */
  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }
  function emoBadge(label, confidence) {
    const cls = `emo-badge emo-${label || "neutral"}`;
    const pct = confidence != null ? ` · ${(confidence * 100).toFixed(0)}%` : "";
    return `<span class="${cls}"><span class="emo-dot"></span>${label || "neutral"}${pct}</span>`;
  }
  function fmtTime(iso) {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      return d.toLocaleString(undefined, {
        month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit",
      });
    } catch { return ""; }
  }

  /* ---------- Settings cache ---------- */
  let _settingsCache = null;
  async function getSettings() {
    if (_settingsCache) return _settingsCache;
    try {
      const data = await API.settings();
      _settingsCache = {};
      (data.settings || []).forEach((s) => (_settingsCache[s.key] = s.value));
    } catch {
      _settingsCache = {};
    }
    return _settingsCache;
  }
  function clearSettingsCache() { _settingsCache = null; }

  global.App = {
    API,
    mountShell,
    loadTheme,
    toggleTheme,
    toast,
    escapeHtml,
    emoBadge,
    fmtTime,
    getSettings,
    clearSettingsCache,
    API_BASE,
  };
})(window);
