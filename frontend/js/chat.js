/* ============================================================
   Text chat page: conversation list, message bubbles, send
   ============================================================ */
(function () {
  "use strict";

  const { API, toast, emoBadge, escapeHtml, fmtTime } = window.App;

  const els = {
    convList:    document.getElementById("convList"),
    newChat:     document.getElementById("newChatBtn"),
    clearAll:    document.getElementById("clearAllBtn"),
    messages:    document.getElementById("messages"),
    input:       document.getElementById("msgInput"),
    send:        document.getElementById("sendBtn"),
    speakLast:   document.getElementById("speakLastBtn"),
  };

  let currentId = null;
  let sending = false;
  let synth = window.speechSynthesis;
  let lastAssistantText = "";

  // ---------- Conversations list ----------
  async function loadConversations() {
    try {
      const data = await API.conversations();
      els.convList.innerHTML = (data.conversations || [])
        .map(c => `<div class="conv-item ${c.id === currentId ? "active" : ""}" data-id="${c.id}" title="${escapeHtml(c.title)}">
          ${escapeHtml(c.title || "Untitled")}
        </div>`).join("") || '<div style="color:var(--text-mute); font-size:12px; padding:8px;">No conversations yet.</div>';
      els.convList.querySelectorAll(".conv-item").forEach(el => {
        el.addEventListener("click", () => openConversation(el.dataset.id));
      });
    } catch (err) {
      els.convList.innerHTML = `<div style="color:var(--danger); font-size:12px; padding:8px;">${escapeHtml(err.message)}</div>`;
    }
  }

  async function openConversation(id) {
    currentId = id;
    try {
      const conv = await API.conversation(id);
      renderMessages(conv.messages || []);
      loadConversations();
    } catch (err) {
      toast("Could not open conversation: " + err.message, "error");
    }
  }

  function renderMessages(messages) {
    if (!messages.length) {
      els.messages.innerHTML =
        `<div style="color:var(--text-mute); text-align:center; padding:40px 0;">This conversation is empty.</div>`;
      return;
    }
    els.messages.innerHTML = messages.map(m => bubbleHtml(m)).join("");
    els.messages.scrollTop = els.messages.scrollHeight;
    const last = messages[messages.length - 1];
    if (last.role === "assistant") lastAssistantText = last.content;
  }

  function bubbleHtml(m) {
    const isUser = m.role === "user";
    const emo = isUser && m.emotion ? emoBadge(m.emotion, m.emotion_confidence) : "";
    const spk = !isUser ? `<span class="speaking-pill">assistant</span>` : "";
    return `<div class="bubble ${m.role}">
      <div>${escapeHtml(m.content)}</div>
      <div class="meta">
        ${isUser ? '<span>you</span>' : '<span>assistant</span>'}
        ${emo} ${spk}
        <span>${fmtTime(m.created_at)}</span>
      </div></div>`;
  }

  function addBubble(role, content, emotion, confidence) {
    const ph = els.messages.querySelector('div[style*="text-align:center"]');
    if (ph) ph.remove();
    const m = { role, content, emotion, emotion_confidence: confidence, created_at: new Date().toISOString() };
    els.messages.insertAdjacentHTML("beforeend", bubbleHtml(m));
    els.messages.scrollTop = els.messages.scrollHeight;
    if (role === "assistant") lastAssistantText = content;
  }

  // ---------- Send ----------
  async function send() {
    const text = els.input.value.trim();
    if (!text || sending) return;
    sending = true;
    els.send.disabled = true;
    els.send.innerHTML = '<span class="spinner"></span> Sending';
    els.input.value = "";
    autoGrow();

    addBubble("user", text, null, null);
    try {
      const res = await API.chat({ text, conversation_id: currentId, mode: "text" });
      currentId = res.conversation_id;
      // Patch the user bubble with emotion now we know it.
      const bubbles = els.messages.querySelectorAll(".bubble.user");
      const lastUser = bubbles[bubbles.length - 1];
      if (lastUser) {
        const meta = lastUser.querySelector(".meta");
        if (meta) meta.insertAdjacentHTML("afterbegin", emoBadge(res.emotion, res.emotion_confidence));
      }
      addBubble("assistant", res.reply, "neutral", 1.0);
      loadConversations();
    } catch (err) {
      addBubble("assistant", "⚠ Sorry, I couldn't process that. " + err.message, null, null);
      toast(err.message, "error");
    } finally {
      sending = false;
      els.send.disabled = false;
      els.send.textContent = "Send";
      els.input.focus();
    }
  }

  // ---------- Auto-grow textarea ----------
  function autoGrow() {
    els.input.style.height = "auto";
    els.input.style.height = Math.min(120, els.input.scrollHeight) + "px";
  }

  // ---------- Speak last ----------
  function speakLast() {
    if (!synth || !lastAssistantText) {
      toast("Nothing to speak yet.", "info");
      return;
    }
    if (synth.speaking) { synth.cancel(); return; }
    const u = new SpeechSynthesisUtterance(lastAssistantText);
    synth.speak(u);
  }

  // ---------- Events ----------
  els.send.addEventListener("click", send);
  els.input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  });
  els.input.addEventListener("input", autoGrow);
  els.newChat.addEventListener("click", () => {
    currentId = null;
    els.messages.innerHTML =
      `<div style="color:var(--text-mute); text-align:center; padding:40px 0;">
        Start a conversation by typing below.</div>`;
    loadConversations();
    els.input.focus();
  });
  els.clearAll.addEventListener("click", async () => {
    if (!confirm("Delete ALL conversations? This cannot be undone.")) return;
    try {
      await API.clearAll();
      currentId = null;
      els.messages.innerHTML =
        `<div style="color:var(--text-mute); text-align:center; padding:40px 0;">
          All conversations cleared.</div>`;
      loadConversations();
      toast("All conversations cleared.", "success");
    } catch (err) {
      toast("Could not clear: " + err.message, "error");
    }
  });
  els.speakLast.addEventListener("click", speakLast);

  // Init
  loadConversations();
})();
