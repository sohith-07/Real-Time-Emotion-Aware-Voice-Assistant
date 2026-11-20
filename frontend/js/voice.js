/* ============================================================
   Voice page: Web Speech API integration (ASR + TTS),
   live transcript, emotion display, sound-wave visualizer
   ============================================================ */
(function () {
  "use strict";

  const { API, toast, emoBadge, escapeHtml, fmtTime } = window.App;

  const els = {
    micBtn:        document.getElementById("micBtn"),
    micStatus:     document.getElementById("micStatus"),
    wave:          document.getElementById("wave"),
    transcriptLive:document.getElementById("transcriptLive"),
    transcript:    document.getElementById("transcript"),
    stopSpeak:     document.getElementById("stopSpeakBtn"),
    clear:         document.getElementById("clearBtn"),
    autoPlay:      document.getElementById("autoPlayChk"),
    browserWarn:   document.getElementById("browserWarn"),
    emoCurrent:    document.getElementById("emoCurrent"),
    emoBars:       document.getElementById("emoBars"),
  };

  // ---------- State ----------
  let recognizing = false;
  let speaking = false;
  let autoPlay = true;
  let conversationId = null;
  let interimText = "";
  let finalText = "";
  let recognition = null;
  let voices = [];
  let chosenVoice = null;
  let rate = 1.0, pitch = 1.0, lang = "en-US";

  // ---------- Settings ----------
  async function loadSettings() {
    const s = await window.App.getSettings();
    autoPlay = (s.auto_play_tts !== "false");
    els.autoPlay.checked = autoPlay;
    if (s.speech_rate) rate = parseFloat(s.speech_rate);
    if (s.speech_pitch) pitch = parseFloat(s.speech_pitch);
    if (s.language) lang = s.language;
    if (s.voice_name) {
      chosenVoice = voices.find(v => v.name === s.voice_name) || null;
    }
    if (s.microphone_enabled === "false") {
      els.micBtn.disabled = true;
      els.micStatus.textContent = "Microphone input is disabled in Settings.";
    } else {
      els.micBtn.disabled = false;
    }
  }

  // ---------- Web Speech API support ----------
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  const synth = window.speechSynthesis;

  if (!SpeechRecognition || !synth) {
    els.browserWarn.style.display = "block";
    els.micBtn.disabled = true;
    els.micStatus.textContent =
      "Web Speech API is not available in this browser. Try Chrome or Edge.";
  }

  function loadVoices() {
    if (!synth) return;
    voices = synth.getVoices() || [];
    window.App.getSettings().then((s) => {
      if (s.voice_name) chosenVoice = voices.find(v => v.name === s.voice_name) || null;
    });
  }
  if (synth) {
    loadVoices();
    synth.onvoiceschanged = loadVoices;
  }

  // ---------- Recognition ----------
  function initRecognition() {
    if (!SpeechRecognition) return null;
    const r = new SpeechRecognition();
    r.lang = lang;
    r.continuous = false;
    r.interimResults = true;
    r.maxAlternatives = 1;

    r.onstart = () => {
      recognizing = true;
      els.micBtn.classList.add("listening");
      els.micBtn.textContent = "■";
      els.wave.classList.add("active");
      els.micStatus.textContent = "Listening… speak now.";
      interimText = ""; finalText = "";
    };

    r.onresult = (event) => {
      let interim = "", finalChunk = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const res = event.results[i];
        if (res.isFinal) finalChunk += res[0].transcript;
        else interim += res[0].transcript;
      }
      if (finalChunk) { finalText += finalChunk; }
      interimText = interim;
      els.transcriptLive.textContent = (finalText + " " + interim).trim();
    };

    r.onerror = (e) => {
      let msg = "Speech recognition error.";
      if (e.error === "not-allowed") msg = "Microphone permission denied.";
      else if (e.error === "no-speech") msg = "No speech detected. Try again.";
      else if (e.error === "network") msg = "Network error during recognition.";
      else msg = "Recognition error: " + e.error;
      toast(msg, "error");
      stopListening();
    };

    r.onend = () => {
      if (recognizing) {
        // Auto-restart if user is still pressing the button but no final was captured.
        recognizing = false;
        els.micBtn.classList.remove("listening");
        els.micBtn.textContent = "🎙";
        els.wave.classList.remove("active");
        const text = (finalText || "").trim();
        if (text) {
          els.transcriptLive.textContent = "";
          sendToAssistant(text);
        } else {
          els.micStatus.textContent = "Click the microphone to start.";
        }
      }
    };

    return r;
  }

  function startListening() {
    if (!SpeechRecognition) {
      toast("Speech recognition not supported in this browser.", "error");
      return;
    }
    if (speaking) { stopSpeaking(); }
    if (!recognition) recognition = initRecognition();
    recognition.lang = lang;
    try {
      recognition.start();
    } catch {
      // Already started - restart cleanly.
      try { recognition.stop(); } catch {}
      setTimeout(() => { try { recognition.start(); } catch {} }, 200);
    }
  }

  function stopListening() {
    if (recognition && recognizing) {
      recognizing = false;
      try { recognition.stop(); } catch {}
      els.micBtn.classList.remove("listening");
      els.micBtn.textContent = "🎙";
      els.wave.classList.remove("active");
    }
  }

  // ---------- Send to backend ----------
  async function sendToAssistant(text) {
    els.micStatus.textContent = "Thinking…";
    addBubble("user", text, null, null);
    try {
      const res = await API.chat({ text, conversation_id: conversationId, mode: "voice" });
      conversationId = res.conversation_id;
      addBubble("assistant", res.reply, "neutral", 1.0);
      renderEmotion(res.emotion, res.emotion_confidence, res.emotion_scores);
      els.micStatus.textContent = autoPlay ? "Speaking…" : "Ready. Click the mic to continue.";
      if (autoPlay) speak(res.reply);
      return res;
    } catch (err) {
      toast("Assistant error: " + err.message, "error");
      els.micStatus.textContent = "Error. Try again.";
      return null;
    }
  }

  // ---------- TTS ----------
  function speak(text) {
    if (!synth) return;
    stopSpeaking();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = lang;
    u.rate = rate; u.pitch = pitch;
    if (chosenVoice) u.voice = chosenVoice;
    u.onstart = () => {
      speaking = true;
      els.stopSpeak.disabled = false;
      els.micStatus.textContent = "Speaking…";
    };
    u.onend = () => {
      speaking = false;
      els.stopSpeak.disabled = true;
      els.micStatus.textContent = "Ready. Click the mic to continue.";
    };
    u.onerror = () => {
      speaking = false;
      els.stopSpeak.disabled = true;
    };
    synth.speak(u);
  }
  function stopSpeaking() {
    if (synth) { synth.cancel(); }
    speaking = false;
    els.stopSpeak.disabled = true;
  }

  // ---------- UI rendering ----------
  function addBubble(role, content, emotion, confidence) {
    // Clear placeholder.
    const ph = els.transcript.querySelector('div[style*="text-align:center"]');
    if (ph) ph.remove();

    const div = document.createElement("div");
    div.className = "bubble " + role;
    const isUser = role === "user";
    const emo = isUser && emotion ? App.emoBadge(emotion, confidence) : "";
    const spk = !isUser ? `<span class="speaking-pill">assistant</span>` : "";
    div.innerHTML = `
      <div>${escapeHtml(content)}</div>
      <div class="meta">
        ${isUser ? '<span>you</span>' : '<span>assistant</span>'}
        ${emo}
        ${spk}
        <span>${fmtTime(new Date().toISOString())}</span>
      </div>`;
    els.transcript.appendChild(div);
    els.transcript.scrollTop = els.transcript.scrollHeight;
  }

  function renderEmotion(label, confidence, scores) {
    els.emoCurrent.innerHTML =
      `Current: ${emoBadge(label, confidence)}` +
      ` <span style="color:var(--text-mute); font-size:11px">(estimates, not diagnoses)</span>`;
    if (!scores) { els.emoBars.innerHTML = ""; return; }
    const order = ["joy","sadness","anger","fear","surprise","neutral","disgust"];
    els.emoBars.innerHTML = order.map(k => {
      const v = scores[k] || 0;
      const pct = (v * 100).toFixed(0);
      return `<div style="display:flex; align-items:center; gap:8px; margin-top:4px;">
        <span style="width:74px; font-size:11px; text-transform:capitalize; color:var(--text-dim)">${k}</span>
        <div style="flex:1; height:8px; background:var(--bg-input); border-radius:4px; overflow:hidden;">
          <div style="width:${pct}%; height:100%; background:linear-gradient(90deg, var(--brand-1), var(--brand-3)); transition:width 300ms;"></div>
        </div>
        <span style="width:34px; text-align:right; font-size:11px; color:var(--text-dim)">${pct}%</span>
      </div>`;
    }).join("");
  }

  function clearConversation() {
    conversationId = null;
    els.transcript.innerHTML =
      `<div style="color:var(--text-mute); text-align:center; padding:30px 0;">
        Conversation cleared.</div>`;
    els.emoCurrent.textContent = "No emotion detected yet.";
    els.emoBars.innerHTML = "";
    els.transcriptLive.textContent = "";
    els.micStatus.textContent = "Click the microphone to start.";
    stopSpeaking();
  }

  // ---------- Events ----------
  els.micBtn.addEventListener("click", () => {
    if (recognizing) stopListening();
    else startListening();
  });
  els.stopSpeak.addEventListener("click", stopSpeaking);
  els.clear.addEventListener("click", clearConversation);
  els.autoPlay.addEventListener("change", (e) => {
    autoPlay = e.target.checked;
    API.updateSetting("auto_play_tts", String(autoPlay)).catch(()=>{});
    window.App.clearSettingsCache();
  });

  // Init
  loadSettings().then(() => {
    if (!SpeechRecognition) return;
    els.micStatus.textContent = "Click the microphone to start.";
  });
})();
