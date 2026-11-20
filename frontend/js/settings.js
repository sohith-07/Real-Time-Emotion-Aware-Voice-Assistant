/* ============================================================
   Settings page: load/save all settings, voice picker, theme
   ============================================================ */
(function () {
  "use strict";

  const { API, toast, escapeHtml } = window.App;

  const ids = [
    "auto_play_tts", "microphone_enabled", "interrupt_enabled",
    "sound_wave_visualizer", "emotion_detection_enabled",
    "voice_name", "speech_rate", "speech_pitch", "language", "theme",
  ];

  const BOOL = ["auto_play_tts", "microphone_enabled", "interrupt_enabled",
                "sound_wave_visualizer", "emotion_detection_enabled"];

  const els = {};
  ids.forEach((id) => { els[id] = document.getElementById("set_" + id); });
  els.rateVal = document.getElementById("rateVal");
  els.pitchVal = document.getElementById("pitchVal");
  els.save = document.getElementById("saveBtn");
  els.reset = document.getElementById("resetBtn");
  els.testVoice = document.getElementById("testVoiceBtn");
  els.openaiKey = document.getElementById("set_openai_key");

  let synth = window.speechSynthesis;
  let voices = [];

  function loadVoices() {
    if (!synth) return;
    voices = synth.getVoices() || [];
    const sel = els.voice_name;
    const cur = sel.value;
    sel.innerHTML = '<option value="">Default (browser)</option>' +
      voices.map(v => `<option value="${escapeHtml(v.name)}">${escapeHtml(v.name)} (${v.lang})</option>`).join("");
    if (cur) sel.value = cur;
  }
  if (synth) {
    loadVoices();
    synth.onvoiceschanged = loadVoices;
  }

  async function loadSettings() {
    try {
      const data = await API.settings();
      const map = {};
      (data.settings || []).forEach((s) => (map[s.key] = s.value));
      ids.forEach((id) => {
        const el = els[id];
        if (!el) return;
        const v = map[id];
        if (BOOL.includes(id)) el.checked = (v === "true");
        else el.value = v ?? "";
      });
      els.rateVal.textContent = parseFloat(els.speech_rate.value || 1).toFixed(1);
      els.pitchVal.textContent = parseFloat(els.speech_pitch.value || 1).toFixed(1);
      // Reflect theme on this page immediately.
      if (map.theme) {
        document.documentElement.setAttribute("data-theme", map.theme);
      }
    } catch (err) {
      toast("Could not load settings: " + err.message, "error");
    }
  }

  async function saveSettings() {
    els.save.disabled = true;
    els.save.textContent = "Saving…";
    try {
      const arr = ids.map((id) => {
        const el = els[id];
        const value = BOOL.includes(id) ? String(el.checked) : el.value;
        return { key: id, value };
      });
      await API.updateSettingsBulk(arr);

      // Apply theme immediately.
      document.documentElement.setAttribute("data-theme", els.theme.value);
      localStorage.setItem("theme", els.theme.value);

      // Optional: write OpenAI key into backend .env (server-side handled).
      const key = els.openaiKey.value.trim();
      if (key) {
        try {
          await App.API.updateSetting("openai_api_key", key);
          toast("OpenAI key saved to backend settings.", "success");
          els.openaiKey.value = "";
        } catch {
          toast("Could not save OpenAI key.", "error");
        }
      }
      window.App.clearSettingsCache();
      toast("Settings saved.", "success");
    } catch (err) {
      toast("Save failed: " + err.message, "error");
    } finally {
      els.save.disabled = false;
      els.save.textContent = "Save settings";
    }
  }

  async function resetSettings() {
    if (!confirm("Reset all settings to defaults?")) return;
    try {
      await API.resetSettings();
      window.App.clearSettingsCache();
      await loadSettings();
      toast("Settings reset to defaults.", "success");
    } catch (err) {
      toast("Reset failed: " + err.message, "error");
    }
  }

  function testVoice() {
    if (!synth) { toast("Speech synthesis not supported.", "error"); return; }
    synth.cancel();
    const u = new SpeechSynthesisUtterance(
      "Hello! I'm your emotion-aware voice assistant. How are you feeling today?"
    );
    u.rate = parseFloat(els.speech_rate.value || 1);
    u.pitch = parseFloat(els.speech_pitch.value || 1);
    const name = els.voice_name.value;
    if (name) {
      const v = voices.find((x) => x.name === name);
      if (v) u.voice = v;
    }
    synth.speak(u);
  }

  // Wire events
  els.speech_rate.addEventListener("input", (e) => {
    els.rateVal.textContent = parseFloat(e.target.value).toFixed(1);
  });
  els.speech_pitch.addEventListener("input", (e) => {
    els.pitchVal.textContent = parseFloat(e.target.value).toFixed(1);
  });
  els.theme.addEventListener("change", (e) => {
    document.documentElement.setAttribute("data-theme", e.target.value);
  });
  els.save.addEventListener("click", saveSettings);
  els.reset.addEventListener("click", resetSettings);
  els.testVoice.addEventListener("click", testVoice);

  // Initial load
  loadSettings();
  loadVoices();
})();
