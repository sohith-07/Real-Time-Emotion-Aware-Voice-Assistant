/* ============================================================
   Analytics dashboard: KPIs + emotion distribution + trend
   ============================================================ */
(function () {
  "use strict";

  const { API, toast, emoBadge, escapeHtml, fmtTime } = window.App;

  const els = {
    kpiConv:   document.getElementById("kpiConv"),
    kpiMsg:    document.getElementById("kpiMsg"),
    kpiUser:   document.getElementById("kpiUser"),
    kpiAssist: document.getElementById("kpiAssist"),
    kpiEmo:    document.getElementById("kpiEmo"),
    recent:    document.getElementById("recentList"),
    breakdown: document.getElementById("emoBreakdown"),
    refresh:   document.getElementById("refreshBtn"),
    dist:      document.getElementById("distChart"),
    trend:     document.getElementById("trendChart"),
  };

  let distChart = null, trendChart = null;

  const EMO_COLORS = {
    joy: "#2f80ed", sadness: "#64748b", anger: "#dc5a67",
    fear: "#8466c8", surprise: "#d5a12a", neutral: "#94a3b8", disgust: "#b7793f",
  };

  async function load() {
    els.refresh.disabled = true;
    try {
      const d = await API.analytics();
      els.kpiConv.textContent = d.total_conversations;
      els.kpiMsg.textContent = d.total_messages;
      els.kpiUser.textContent = d.total_user_messages;
      els.kpiAssist.textContent = d.total_assistant_messages;
      els.kpiEmo.textContent = d.most_frequent_emotion || "—";

      renderRecent(d.recent_messages || []);
      renderBreakdown(d.emotion_distribution || []);
      renderDistChart(d.emotion_distribution || []);
      renderTrendChart(d.daily_counts || []);
    } catch (err) {
      toast("Could not load analytics: " + err.message, "error");
    } finally {
      els.refresh.disabled = false;
    }
  }

  function renderRecent(rows) {
    if (!rows.length) {
      els.recent.innerHTML = '<div style="color:var(--text-mute); padding:8px;">No messages yet.</div>';
      return;
    }
    els.recent.innerHTML = rows.map(r => {
      const who = r.role === "user" ? "user" : "assistant";
      const emo = r.emotion && r.role === "user"
        ? `<span class="emo-badge emo-${r.emotion}" style="margin-left:6px"><span class="emo-dot"></span>${r.emotion}</span>`
        : "";
      return `<div class="recent-row">
        <span class="who ${who}">${who === "user" ? "U" : "A"}</span>
        <span class="text">${escapeHtml(r.content)}</span>
        ${emo}
        <span class="time">${fmtTime(r.created_at)}</span>
      </div>`;
    }).join("");
  }

  function renderBreakdown(dist) {
    if (!dist.length) {
      els.breakdown.innerHTML = '<div style="color:var(--text-mute); padding:8px;">No emotion data yet.</div>';
      return;
    }
    const sorted = [...dist].sort((a,b) => b.count - a.count);
    els.breakdown.innerHTML = sorted.map(d => `
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
        <span class="emo-badge emo-${d.label}"><span class="emo-dot"></span>${d.label}</span>
        <div style="flex:1; height:10px; background:var(--bg-input); border-radius:5px; overflow:hidden;">
          <div style="width:${d.percentage}%; height:100%; background:${EMO_COLORS[d.label] || "#888"}; transition:width 400ms;"></div>
        </div>
        <span style="width:80px; text-align:right; font-size:12px; color:var(--text-dim)">${d.count} · ${d.percentage}%</span>
      </div>`).join("");
  }

  function renderDistChart(dist) {
    if (!els.dist) return;
    const ctx = els.dist.getContext("2d");
    const width = els.dist.clientWidth || 400;
    const height = els.dist.clientHeight || 240;
    els.dist.width = width * devicePixelRatio;
    els.dist.height = height * devicePixelRatio;
    ctx.scale(devicePixelRatio, devicePixelRatio);
    ctx.clearRect(0, 0, width, height);
    if (!dist.length) {
      ctx.fillStyle = getCssVar("--text-mute");
      ctx.font = "13px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("No emotion data yet", width / 2, height / 2);
      return;
    }
    let start = -Math.PI / 2;
    const cx = width / 2, cy = height / 2, radius = Math.min(width, height) * 0.32;
    dist.forEach((d) => {
      const angle = (d.count / Math.max(dist.reduce((sum, x) => sum + x.count, 0), 1)) * Math.PI * 2;
      ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, radius, start, start + angle); ctx.closePath();
      ctx.fillStyle = EMO_COLORS[d.label] || "#94a3b8"; ctx.fill(); start += angle;
    });
  }

  function renderTrendChart(daily) {
    if (!els.trend) return;
    const ctx = els.trend.getContext("2d");
    const width = els.trend.clientWidth || 400;
    const height = els.trend.clientHeight || 240;
    els.trend.width = width * devicePixelRatio;
    els.trend.height = height * devicePixelRatio;
    ctx.scale(devicePixelRatio, devicePixelRatio);
    ctx.clearRect(0, 0, width, height);
    if (!daily.length) {
      ctx.fillStyle = getCssVar("--text-mute"); ctx.font = "13px sans-serif"; ctx.textAlign = "center";
      ctx.fillText("No daily activity yet", width / 2, height / 2); return;
    }
    const max = Math.max(...daily.map(d => d.count), 1);
    const left = 32, bottom = 28, top = 15, chartW = width - left - 12, chartH = height - bottom - top;
    const barW = chartW / daily.length;
    ctx.fillStyle = getCssVar("--brand-1");
    daily.forEach((d, i) => {
      const barH = (d.count / max) * chartH;
      ctx.fillRect(left + i * barW + barW * 0.18, height - bottom - barH, barW * 0.64, barH);
      ctx.fillStyle = getCssVar("--text-mute"); ctx.font = "9px sans-serif"; ctx.textAlign = "center";
      ctx.fillText(d.date.slice(5), left + i * barW + barW / 2, height - 8);
      ctx.fillStyle = getCssVar("--brand-1");
    });
  }

  function getCssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#94a3b8";
  }

  els.refresh.addEventListener("click", load);
  load();
})();
