<template>
  <div class="app dark-theme">
    <div class="page">
      <header class="topbar">
        <h1>Moderations-Dashboard</h1>
        <div class="topbar-controls">
          <input v-model="searchThreadId" placeholder="Thread ID" class="debug-btn" style="width: 100px;">
          <select v-model="searchPlatform" class="debug-btn">
            <option value="professor">Professor</option>
            <option value="bluesky">Bluesky</option>
          </select>
          <input v-model="searchSourceFile" placeholder="Source File (optional)" class="debug-btn" style="width: 150px;">
          <button class="debug-btn" @click="fetchEvaluation" style="background: var(--accent); color: var(--bg);">
            Laden
          </button>
        </div>
      </header>

      <section v-if="threadData" class="top-section">
        <div class="panel score-panel">
          <div class="panel-header">
            <h2>Aktueller Score</h2>
            <p class="subtitle">Kommentar ID: {{ newestComment?.comment_id ?? '-' }}</p>
          </div>

          <div class="score-card" :class="scoreDetails.class">
            <span class="score-value">{{ Math.round(newestComment?.score_0_100 ?? 0) }}</span>
            <span class="score-label">{{ scoreDetails.label }}</span>
          </div>

          <div class="score-meta">
            {{ newestComment?.created_at ?? '-' }}
          </div>
        </div>

        <div class="panel chart-panel">
          <div class="panel-header">
            <h2>Score-Verlauf</h2>
          </div>

          <svg viewBox="0 0 340 220" class="line-chart-svg" preserveAspectRatio="none">
            <line
              v-for="tick in timeTicks"
              :key="tick.key"
              :x1="tick.x"
              :x2="tick.x"
              :y1="tick.major ? 18 : 28"
              :y2="190"
              :class="tick.major ? 'time-tick-major' : 'time-tick-minor'"
            />

            <text
              v-for="tick in dayLabels"
              :key="tick.key"
              :x="tick.x"
              y="206"
              text-anchor="middle"
              class="time-day-label"
            >
              {{ tick.label }}
            </text>

            <polyline class="history-line" :points="linePlotPoints" />

            <circle
              v-for="(p, i) in scoreHistory"
              :key="p.id + '-' + i"
              :cx="timeToX(p.time)"
              :cy="linePointY(p.score)"
              r="4"
              class="chart-point"
            />
          </svg>

          <div class="window-preview" v-if="currentWindow">
            <div><strong>Zeitraum:</strong> {{ formatRange(currentWindow.window_start, currentWindow.window_end) }}</div>
            <div><strong>Kommentare:</strong> {{ formatValue(currentWindow.comment_count) }}</div>
            <div><strong>Toxizität:</strong> {{ formatNumber(currentWindow.toxicity_score_mean, 2) }}</div>
            <div><strong>Attacke:</strong> {{ formatNumber(currentWindow.attack_probability_mean, 3) }}</div>
          </div>
        </div>
      </section>

      <section v-if="threadData" class="windows-panel">
        <div class="panel">
          <h2>Einzelkommentare (Neueste zuerst)</h2>
          <div class="table-container">
            <table>
              <thead>
                <tr><th>Nr</th><th>Comment ID</th><th>Zeitpunkt</th><th>Score (0-100)</th><th>Warning Level</th></tr>
              </thead>
              <tbody>
                <tr v-for="row in sortedCommentsReverse" :key="row.comment_id">
                  <td>{{ row.nr }}</td>
                  <td>{{ row.comment_id }}</td>
                  <td>{{ row.created_at }}</td>
                  <td>{{ Math.round(row.score_0_100) }}</td>
                  <td>{{ row.warning_level }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section v-if="threadData" class="windows-panel">
        <div class="panel">
          <h2>Zeitfenster-Analyse: {{ threadData.summary?.title ?? searchThreadId }}</h2>
          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th>Zeitfenster</th><th>Kommentare</th><th>Unique Users</th><th>Dominant Ratio</th><th>Multi User Ratio</th><th>Thread Users</th><th>Thread Comments</th><th>Mean Comments/User</th><th>Max Comments/User</th><th>Single Comment Users</th><th>Max User Share</th><th>Single Comment Share</th><th>Attack Count</th><th>Attack Ratio</th><th>Attack Score Mean</th><th>Attack Score Mean Norm</th><th>Attack Score Max</th><th>Attack Probability Mean</th><th>Toxic Count</th><th>Toxic Ratio</th><th>Toxicity Score Mean</th><th>Toxicity Score Mean Norm</th><th>Toxicity Score Max</th><th>Insult Comment Count</th><th>Insult Ratio</th><th>Insult Count Sum</th><th>Swearword Count</th><th>Swearword Ratio</th><th>Negative Word Mean</th><th>Recent Attack 3</th><th>Recent Attack 5</th><th>Attack Streak Max</th><th>Reply After Attack</th><th>Direct Address</th><th>Imperative</th><th>Accusation Marker</th><th>Mockery Marker</th><th>Target Recently Attacked</th><th>Counter Speech</th><th>Target Response</th><th>Deescalation</th><th>Irony</th><th>Reply Depth Mean</th><th>Reply Depth Max</th><th>Num Children Mean</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="win in sortedWindowsReverse" :key="win.window_start" :class="{ active: selectedWindowStart === win.window_start }" @click="selectedWindowStart = win.window_start">
                  <td>{{ formatRange(win.window_start, win.window_end) }}</td>
                  <td>{{ formatValue(win.comment_count) }}</td><td>{{ formatValue(win.unique_users) }}</td><td>{{ formatNumber(win.dominant_user_ratio, 2) }}</td><td>{{ formatNumber(win.multi_user_ratio, 2) }}</td><td>{{ formatValue(win.thread_user_count) }}</td><td>{{ formatValue(win.thread_comment_count) }}</td><td>{{ formatNumber(win.thread_mean_comments_per_user, 3) }}</td><td>{{ formatValue(win.thread_max_comments_by_one_user) }}</td><td>{{ formatValue(win.thread_single_comment_user_count) }}</td><td>{{ formatNumber(win.thread_max_user_share, 3) }}</td><td>{{ formatNumber(win.thread_single_comment_user_share, 3) }}</td><td>{{ formatValue(win.attack_count) }}</td><td>{{ formatNumber(win.attack_ratio, 2) }}</td><td>{{ formatNumber(win.attack_score_mean, 2) }}</td><td>{{ formatNumber(win.attack_score_mean_norm, 2) }}</td><td>{{ formatNumber(win.attack_score_max, 2) }}</td><td>{{ formatNumber(win.attack_probability_mean, 3) }}</td><td>{{ formatValue(win.toxic_count) }}</td><td>{{ formatNumber(win.toxic_ratio, 2) }}</td><td>{{ formatNumber(win.toxicity_score_mean, 2) }}</td><td>{{ formatNumber(win.toxicity_score_mean_norm, 2) }}</td><td>{{ formatNumber(win.toxicity_score_max, 2) }}</td><td>{{ formatValue(win.insult_comment_count) }}</td><td>{{ formatNumber(win.insult_ratio, 2) }}</td><td>{{ formatValue(win.insult_count_sum) }}</td><td>{{ formatValue(win.swearword_comment_count) }}</td><td>{{ formatNumber(win.swearword_ratio, 2) }}</td><td>{{ formatNumber(win.negative_word_count_mean, 2) }}</td><td>{{ formatNumber(win.recent_attack_rate_3_mean, 2) }}</td><td>{{ formatNumber(win.recent_attack_rate_5_mean, 2) }}</td><td>{{ formatValue(win.attack_streak_max) }}</td><td>{{ formatNumber(win.reply_after_attack_ratio, 2) }}</td><td>{{ formatNumber(win.direct_address_mean, 2) }}</td><td>{{ formatNumber(win.imperative_mean, 2) }}</td><td>{{ formatNumber(win.accusation_marker_mean, 2) }}</td><td>{{ formatNumber(win.mockery_marker_mean, 2) }}</td><td>{{ formatNumber(win.target_recently_attacked_ratio, 2) }}</td><td>{{ formatNumber(win.counter_speech_probability_mean, 3) }}</td><td>{{ formatNumber(win.target_response_probability_mean, 3) }}</td><td>{{ formatNumber(win.deescalation_probability_mean, 3) }}</td><td>{{ formatNumber(win.irony_mean, 2) }}</td><td>{{ formatNumber(win.reply_depth_mean, 2) }}</td><td>{{ formatValue(win.reply_depth_max) }}</td><td>{{ formatNumber(win.num_children_mean, 2) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <div v-else class="loading">
        <p v-if="loading">Lade Daten…</p>
        <p v-else>Bitte Evaluation starten.</p>
      </div>
    </div>
  </div>
</template>

<script>
import api from './services/api'

export default {
  name: 'DashboardView',
  data() {
    return {
      threadData: null,
      searchThreadId: 'SYN0001',
      searchPlatform: 'professor',
      searchSourceFile: '',
      selectedWindowStart: null,
      loading: false
    }
  },
  computed: {
    // 1. Sortierte Daten (Neueste zuerst)
    sortedCommentsReverse() {
      if (!this.threadData?.rows) return [];
      return [...this.threadData.rows].sort((a, b) => 
        new Date(b.created_at) - new Date(a.created_at)
      );
    },
    
    newestComment() {
      return this.sortedCommentsReverse[0] || null;
    },

    sortedWindowsReverse() {
      if (!this.threadData?.windows) return [];
      return [...this.threadData.windows].sort((a, b) => 
        new Date(b.window_start) - new Date(a.window_start)
      );
    },

    // 2. Bestehende Chart-Logik
    scoreHistory() {
      if (!this.threadData?.rows) return [];
      return [...this.threadData.rows]
        .map(row => ({
          id: row.comment_id,
          score: Number(row.score_0_100) / 100,
          time: new Date(row.created_at)
        }))
        .filter(p => p.time instanceof Date && !isNaN(p.time))
        .slice(-7 * 24);
    },

    scoreTimeBounds() {
      if (!this.scoreHistory.length) return { min: null, max: null };
      const times = this.scoreHistory.map(p => p.time.getTime());
      let min = new Date(Math.min(...times));
      let max = new Date(Math.max(...times));
      return { min, max };
    },

    timeTicks() {
      const { min, max } = this.scoreTimeBounds;
      if (!min || !max) return [];
      const ticks = [];
      const stepMs = 6 * 60 * 60 * 1000;
      for (let t = min.getTime(); t <= max.getTime(); t += stepMs) {
        const d = new Date(t);
        ticks.push({ key: d.toISOString(), x: this.timeToX(d), major: d.getHours() === 0 });
      }
      return ticks;
    },

    dayLabels() {
      const { min, max } = this.scoreTimeBounds;
      if (!min || !max) return [];
      const labels = [];
      let d = new Date(min);
      while (d <= max) {
        labels.push({ key: d.toISOString(), x: this.timeToX(d), label: d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' }) });
        d.setDate(d.getDate() + 1);
      }
      return labels;
    },

    linePlotPoints() {
      return this.scoreHistory
        .map(p => `${this.timeToX(p.time)},${this.linePointY(p.score)}`)
        .join(' ');
    },

    scoreDetails() {
      const score = (this.newestComment?.score_0_100 || 0) / 100;
      if (score >= 0.75) return { class: 'score-rot', label: 'Kritisch' };
      if (score >= 0.50) return { class: 'score-orange', label: 'Eskalation' };
      if (score >= 0.25) return { class: 'score-gelb', label: 'Frühwarnung' };
      return { class: 'score-gruen', label: 'Normal' };
    },

    currentWindow() {
      if (!this.threadData?.windows?.length) return null;
      return this.selectedWindowStart 
        ? this.threadData.windows.find(w => w.window_start === this.selectedWindowStart) 
        : this.threadData.windows[0];
    }
  },
  methods: {
    async fetchEvaluation() {
      this.loading = true;
      try {
        const res = await api.getEvaluation(this.searchThreadId, this.searchPlatform, this.searchSourceFile);
        this.threadData = res.data;
        this.selectedWindowStart = this.sortedWindowsReverse[0]?.window_start || null;
      } catch (e) {
        console.error('Fehler beim Laden:', e);
      } finally {
        this.loading = false;
      }
    },
    // Hilfsfunktionen für SVG & Formatierung
    timeToX(date) {
      const { min, max } = this.scoreTimeBounds;
      if (!min || !max || !date) return 20;
      const span = max.getTime() - min.getTime();
      return span <= 0 ? 20 : 20 + ((date.getTime() - min.getTime()) / span) * 300;
    },
    linePointY(s) { return 20 + (1 - s) * 120; },
    formatRange(s, e) { return s && e ? `${new Date(s).toLocaleString('de-DE')} - ${new Date(e).toLocaleString('de-DE')}` : '-'; },
    formatNumber(v, d) { return (v === null || isNaN(v)) ? '-' : Number(v).toFixed(d); },
    formatValue(v) { return (v === null || isNaN(v)) ? '-' : v; }
  }
}
</script>

<style>
body, html {
  margin: 0;
  padding: 0;
  background-color: #0b0f19;
  font-family: 'Inter', sans-serif;
}
</style>

<style scoped>
.dark-theme {
  --bg: #0b0f19;
  --surface: #131c2e;
  --text: #f8fafc;
  --muted: #94a3b8;
  --border: #334155;
  --accent: #38bdf8;
}

.app {
  background-color: var(--bg);
  min-height: 100vh;
}

.page {
  padding: 24px;
  color: var(--text);
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.topbar-controls {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.debug-btn {
  background: transparent;
  color: var(--muted);
  border: 1px solid var(--border);
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
}

.top-section {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 24px;
  margin-bottom: 24px;
}

.panel {
  background-color: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
}

.panel-header {
  margin-bottom: 16px;
}

.subtitle {
  color: var(--muted);
  margin: 4px 0 0;
}

.score-panel {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.score-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  border-radius: 12px;
  margin-top: 8px;
}

.score-value {
  font-size: 3rem;
  font-weight: 800;
  line-height: 1;
}

.score-label {
  margin-top: 8px;
  font-size: 1rem;
}

.score-meta {
  margin-top: 16px;
  color: var(--muted);
}

.chart-panel {
  min-height: 220px;
  display: flex;
  flex-direction: column;
}

.line-chart-svg {
  width: 100%;
  height: 220px;
}

.history-line {
  fill: none;
  stroke: var(--accent);
  stroke-width: 3;
}

.chart-point {
  fill: var(--bg);
  stroke: var(--accent);
  stroke-width: 2;
}

.time-tick-minor {
  stroke: rgba(255, 255, 255, 0.14);
  stroke-width: 1;
}

.time-tick-major {
  stroke: rgba(56, 189, 248, 0.65);
  stroke-width: 2.5;
}

.time-day-label {
  fill: var(--muted);
  font-size: 11px;
}

.window-preview {
  margin-top: 12px;
  color: var(--muted);
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 16px;
  font-size: 0.92rem;
}

.windows-panel {
  width: 100%;
}

.table-container {
  width: 100%;
  overflow-x: auto;
}

.table-container table {
  width: 100%;
  min-width: 2600px;
  border-collapse: collapse;
}

.table-container th,
.table-container td {
  white-space: nowrap;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  text-align: left;
}

.table-container thead th {
  position: sticky;
  top: 0;
  background: var(--surface);
  z-index: 1;
}

.table-container tbody tr:hover {
  background: rgba(56, 189, 248, 0.08);
  cursor: pointer;
}

.table-container tbody tr.active {
  background: rgba(56, 189, 248, 0.14);
}

.loading {
  color: var(--muted);
  padding: 24px 0;
}

.score-rot {
  background: #7f1d1d;
  color: #fca5a5;
}

.score-orange {
  background: #7c2d12;
  color: #fdba74;
}

.score-gelb {
  background: #713f12;
  color: #fde047;
}

.score-gruen {
  background: #064e3b;
  color: #4ade80;
}

@media (max-width: 1100px) {
  .top-section {
    grid-template-columns: 1fr;
  }

  .window-preview {
    grid-template-columns: 1fr;
  }
}
</style>