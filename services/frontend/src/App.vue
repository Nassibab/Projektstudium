<template>
  <div class="app dark-theme">
    <div class="page">
      <header class="topbar">
        <h1>Moderations-Dashboard Demo</h1>
        <button class="debug-btn" @click="triggerPublish" title="Call /demo/publish">
          Debug Publish
        </button>
      </header>

      <section v-if="currentComment" class="dashboard">
        <div class="panel score-panel">
          <div class="panel-header">
            <div>
              <h2>Aktueller Score</h2>
              <p class="subtitle">Kommentar von {{ currentComment.author }}</p>
            </div>
          </div>

          <div class="score-card" :class="scoreDetails.class">
            <span class="score-value">{{ currentComment.score.toFixed(2) }}</span>
            <span class="score-label">{{ scoreDetails.label }}</span>
          </div>

          <div class="score-meta">
            {{ commentDateTime }}
          </div>

          <div class="score-legend">
            <h4>Legende / Score-Bereiche</h4>
            <ul>
              <li>
                <span class="legend-dot dot-gruen"></span>
                <span class="legend-text">Normal</span>
                <span class="legend-range">0.00 – 0.24</span>
              </li>
              <li>
                <span class="legend-dot dot-gelb"></span>
                <span class="legend-text">Frühwarnung</span>
                <span class="legend-range">0.25 – 0.49</span>
              </li>
              <li>
                <span class="legend-dot dot-orange"></span>
                <span class="legend-text">Eskalation</span>
                <span class="legend-range">0.50 – 0.74</span>
              </li>
              <li>
                <span class="legend-dot dot-rot"></span>
                <span class="legend-text">Kritisch</span>
                <span class="legend-range">0.75 – 1.00</span>
              </li>
            </ul>
          </div>
        </div>

        <div class="panel chart-panel">
          <div class="panel-header">
            <div>
              <h2>Score-Verlauf</h2>
            </div>
          </div>

          <svg viewBox="0 0 340 180" class="line-chart-svg">
            <g class="chart-grid">
              <line x1="20" y1="20" x2="320" y2="20" />
              <line x1="20" y1="44" x2="320" y2="44" />
              <line x1="20" y1="68" x2="320" y2="68" />
              <line x1="20" y1="92" x2="320" y2="92" />
              <line x1="20" y1="116" x2="320" y2="116" />
              <line x1="20" y1="140" x2="320" y2="140" />
              
              <text x="8" y="24">1.0</text>
              <text x="8" y="48">0.8</text>
              <text x="8" y="72">0.6</text>
              <text x="8" y="96">0.4</text>
              <text x="8" y="120">0.2</text>
              <text x="8" y="144">0.0</text>
            </g>

            <polyline class="history-line" :points="linePlotPoints" />

            <g v-for="(point, index) in scoreHistory" :key="point.id">
              <circle :cx="linePointX(index)" :cy="linePointY(point.score)" r="4" class="chart-point" />
              <text :x="linePointX(index)" :y="linePointY(point.score) - 10" class="chart-label data-val">
                {{ point.score.toFixed(2) }}
              </text>
            </g>

            <g v-for="(point, index) in scoreHistory" :key="point.id + '-label'">
              <text :x="linePointX(index)" y="158" class="chart-label date-val">{{ point.date }}</text>
              <text :x="linePointX(index)" y="172" class="chart-label time-val">{{ point.time }}</text>
            </g>
          </svg>
        </div>

        <div class="panel radar-panel">
          <div class="panel-header">
            <div>
              <h2>KPI Radar</h2>
              <p class="subtitle">Kommentar-KPIs</p>
            </div>
          </div>

          <div class="radar-and-list">
            <div class="radar-wrapper">
              <svg viewBox="0 0 260 260" class="radar-chart">
                <g class="radar-grid-rings">
                  <polygon v-for="level in [0.2, 0.4, 0.6, 0.8, 1.0]" :key="level" :points="radarRingPoints(level)" />
                  <text v-for="level in [0.2, 0.4, 0.6, 0.8, 1.0]" :key="'lbl-'+level" :x="radarCenter" :y="radarCenter - (100 * level) + 12" class="radar-ring-label">
                    {{ level.toFixed(1) }}
                  </text>
                </g>

                <g>
                  <line
                    v-for="(_, index) in currentComment.kpis"
                    :key="index"
                    :x1="radarCenter"
                    :y1="radarCenter"
                    :x2="radarPoint(index, 1).x"
                    :y2="radarPoint(index, 1).y"
                    class="radar-axis"
                  />
                  <text
                    v-for="(kpi, index) in currentComment.kpis"
                    :key="kpi.name"
                    :x="radarPoint(index, 1.2).x"
                    :y="radarPoint(index, 1.2).y"
                    text-anchor="middle"
                    class="radar-axis-label"
                  >
                    {{ kpi.name }}
                  </text>
                </g>

                <polygon :points="radarPoints" class="radar-area" />
              </svg>
            </div>

            <ul class="kpi-list">
              <li v-for="kpi in currentComment.kpis" :key="kpi.name">
                <span>{{ kpi.name }}</span>
                <strong>{{ kpi.value.toFixed(2) }}</strong>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <section v-if="demoData" class="bottom-section">
        
        <div class="panel thread-panel-left">
          <h3>Aktive Threads</h3>
          <div class="thread-list">
            <div 
              v-for="(thread, index) in threadList" 
              :key="thread.id || index"
              class="thread-item"
              :class="[
                getThreadScoreClass(thread), 
                { active: currentThread && currentThread.id === thread.id }
              ]"
              :title="thread.title"
              @click="selectThread(thread)"
            >
              {{ truncateText(thread.title, 140) }}
            </div>
          </div>
        </div>

        <div class="panel thread-panel-right" v-if="currentThread">
          <h2>Originaler Beitrag</h2>
          <div class="thread-text-container">
            <p class="thread-text">{{ currentThread.text }}</p>
          </div>

          <h3>Kommentare</h3>
          <div class="comments-section">
            <div 
              class="comment-card" 
              v-for="comment in sortedComments" 
              :key="comment.id"
              :class="{ active: comment.id === selectedCommentId }"
              @click="selectedCommentId = comment.id"
            >
              <div class="comment-head">
                <strong>{{ comment.author }}</strong>
                <span>{{ formatDate(comment.time) }}</span>
              </div>
              
              <div class="comment-score" :class="getScoreDetails(comment.score).class">
                <strong>{{ getScoreDetails(comment.score).label }}:</strong> {{ comment.score.toFixed(2) }}
              </div>
              
              <p>{{ comment.text }}</p>
              <div class="moderation">
                <strong>Moderationsempfehlung:</strong> {{ comment.moderation }}
              </div>
            </div>
          </div>
        </div>
      </section>

      <div v-else class="loading">
        <p>Lade Demo-Daten…</p>
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
      demoData: null,
      selectedThreadId: null,
      selectedCommentId: null,
      eventSource: null,
    }
  },
  computed: {
    // Unterstützt sowohl ein einzelnes thread-Objekt als auch ein threads-Array (falls die API erweitert wird)
    threadList() {
      if (!this.demoData) return []

      if (Array.isArray(this.demoData)) {
        return this.demoData.map((item, index) => {
          const thread = item.thread || item
          return {
            ...thread,
            id: thread.id != null ? thread.id : index,
          }
        })
      }

      if (this.demoData.threads && Array.isArray(this.demoData.threads)) {
        return this.demoData.threads.map((thread, index) => ({
          ...thread,
          id: thread.id != null ? thread.id : index,
        }))
      }

      if (this.demoData.thread) {
        return [{
          ...this.demoData.thread,
          id: this.demoData.thread.id != null ? this.demoData.thread.id : 0,
        }]
      }

      return []
    },
    currentThread() {
      if (!this.threadList.length) return null
      if (this.selectedThreadId !== null) {
        return this.threadList.find(t => t.id === this.selectedThreadId) || this.threadList[0]
      }
      return this.threadList[0]
    },
    sortedComments() {
      if (!this.currentThread?.comments) return []
      return [...this.currentThread.comments].reverse()
    },
    currentComment() {
      if (!this.sortedComments.length) return null
      const found = this.sortedComments.find(c => c.id === this.selectedCommentId)
      return found || this.sortedComments[0]
    },
    commentDateTime() {
      if (!this.currentComment) return ''
      return new Date(this.currentComment.time).toLocaleString('de-DE', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit', second: '2-digit'
      })
    },
    scoreHistory() {
      if (!this.sortedComments.length) return []
      return this.sortedComments.map((comment, index) => {
        const dateObj = new Date(comment.time)
        return {
          id: comment.id || index,
          date: dateObj.toLocaleDateString('de-DE', { month: '2-digit', day: '2-digit' }),
          time: dateObj.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' }),
          score: comment.score
        }
      }).reverse()
    },
    linePlotPoints() {
      if (!this.scoreHistory.length) return ''
      return this.scoreHistory
        .map((point, index) => `${this.linePointX(index)},${this.linePointY(point.score)}`)
        .join(' ')
    },
    radarCenter() {
      return 130
    },
    radarPoints() {
      if (!this.currentComment?.kpis) return ''
      return this.currentComment.kpis
        .map((kpi, index) => {
          const pos = this.radarPoint(index, kpi.value)
          return `${pos.x},${pos.y}`
        })
        .join(' ')
    },
    scoreDetails() {
      if (!this.currentComment) return { class: 'score-gruen', label: 'Normal' }
      return this.getScoreDetails(this.currentComment.score)
    }
  },
  methods: {
    async triggerPublish() {
      try {
        await fetch('http://localhost:8000/demo/publish', {
          method: 'POST'
        })
        console.log('Publish endpoint triggered successfully')
      } catch (error) {
        console.error('Failed to trigger publish endpoint:', error)
      }
    },

    async fetchDemoData() {
      try {
        const response = await api.getDemoData()
        this.demoData = response.data

        if (this.threadList.length > 0) {
          this.selectedThreadId = this.threadList[0].id || null
        }
      } catch (error) {
        console.error('API Error:', error)
      }
    },
    connectDemoStream() {
      if (this.eventSource) return

      this.eventSource = new EventSource('http://localhost:8000/demo/stream')

      this.eventSource.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data)
          this.applyThreadUpdate(payload)
        } catch (error) {
          console.error('SSE parse error:', error)
        }
      }

      this.eventSource.onerror = () => {
        console.warn('SSE connection lost, retrying...')
      }
    },
    applyThreadUpdate(payload) {
      if (!payload || !this.demoData || payload.type !== 'comment_added') return

      if (!Array.isArray(this.demoData)) return

      this.demoData = this.demoData.map((item) => {
        if (!item.thread || item.thread.id !== payload.threadId) return item

        return {
          ...item,
          thread: {
            ...item.thread,
            comments: [...(item.thread.comments || []), payload.comment],
          },
        }
      })

      this.selectedThreadId = payload.threadId
      this.selectedCommentId = payload.comment?.id || null
    },
    selectThread(thread) {
      this.selectedThreadId = thread.id;
      // Bei Thread-Wechsel Kommentar-Auswahl zurücksetzen, 
      // damit stattdessen der erste Kommentar des neuen Threads geladen wird
      this.selectedCommentId = null; 
    },
    getScoreDetails(score) {
      if (score >= 0.75) return { class: 'score-rot', label: 'Kritisch' }
      if (score >= 0.50) return { class: 'score-orange', label: 'Eskalation' }
      if (score >= 0.25) return { class: 'score-gelb', label: 'Frühwarnung' }
      return { class: 'score-gruen', label: 'Normal' }
    },
    // Holt den Score des neuesten Kommentars des Threads
    getThreadScoreClass(thread) {
      if (!thread.comments || !thread.comments.length) return 'score-gruen';
      const newestComment = [...thread.comments].reduce((latest, comment) => {
        const latestTime = new Date(latest.time).getTime()
        const commentTime = new Date(comment.time).getTime()
        return commentTime > latestTime ? comment : latest
      }, thread.comments[0])
      return this.getScoreDetails(newestComment.score).class;
    },
    // Kürzt Text nach einer bestimmten Anzahl von Zeichen
    truncateText(text, length) {
      if (!text) return '';
      return text.length > length ? text.substring(0, length) + '...' : text;
    },
    radarPoint(index, value = 1) {
      const totalAxes = this.currentComment?.kpis?.length || 6
      const angle = (Math.PI * 2 * index) / totalAxes - Math.PI / 2
      const radius = 100 * value
      return {
        x: this.radarCenter + Math.cos(angle) * radius,
        y: this.radarCenter + Math.sin(angle) * radius,
      }
    },
    radarRingPoints(level) {
      const totalAxes = this.currentComment?.kpis?.length || 6
      return Array.from({ length: totalAxes }, (_, index) => {
        const pos = this.radarPoint(index, level)
        return `${pos.x},${pos.y}`
      }).join(' ')
    },
    linePointX(index) {
      const width = 300
      const count = this.scoreHistory.length
      const margin = 20
      return margin + (index * (width / Math.max(count - 1, 1)))
    },
    linePointY(score) {
      const graphHeight = 120 
      const topMargin = 20
      return topMargin + (1 - score) * graphHeight
    },
    formatDate(value) {
      if (!value) return ''
      return new Date(value).toLocaleString('de-DE', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
      })
    }
  },
  mounted() {
    this.fetchDemoData()
    this.connectDemoStream()
  },
  beforeUnmount() {
    if (this.eventSource) {
      this.eventSource.close()
      this.eventSource = null
    }
  },
}
</script>

<style>
body, html {
  margin: 0 !important;
  padding: 0 !important;
  background-color: #0b0f19;
  font-family: 'Inter', sans-serif;
  -webkit-font-smoothing: antialiased;
}
</style>

<style scoped>
.dark-theme {
  --bg: #0b0f19;
  --surface: #131c2e;
  --surface-card: #1e293b;
  --text: #f8fafc;
  --muted: #94a3b8;
  --border: #334155;
  --accent: #38bdf8;
  --accent-soft: rgba(56, 189, 248, 0.12);
  --accent-highlight: rgba(56, 189, 248, 0.25);
  --grid-line: rgba(255, 255, 255, 0.07);
}

.app {
  background-color: var(--bg);
  min-height: 100vh;
}

.page {
  padding: 24px;
  background-color: var(--bg);
  color: var(--text);
  box-sizing: border-box;
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.topbar h1 {
  margin: 0;
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--text);
}

.debug-btn {
  background-color: transparent;
  color: var(--muted);
  border: 1px solid var(--border);
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.debug-btn:hover {
  background-color: var(--surface-card);
  color: var(--text);
  border-color: var(--muted);
}

.dashboard {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  margin-bottom: 24px;
}

.panel {
  background-color: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
}

.panel-header {
  margin-bottom: 20px;
}

.panel-header h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}

.subtitle {
  margin: 4px 0 0 0;
  color: var(--muted);
  font-size: 0.875rem;
}

/* =========================================
   DYNAMISCHE SCORE-FARBEN & TEXT (AMPELSYSTEM)
========================================= */

.score-card {
  display: flex;
  flex-direction: column;
  padding: 24px;
  border-radius: 12px;
  margin-bottom: 16px;
  align-items: center;
  transition: all 0.3s ease;
}

.score-value {
  font-size: 3.5rem;
  font-weight: 800;
  line-height: 1;
  margin-bottom: 8px;
}
.score-label {
  font-size: 1.1rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Grün (< 0.25) */
.score-card.score-gruen { background: linear-gradient(135deg, rgba(34, 197, 94, 0.15), transparent); border: 1px solid rgba(34, 197, 94, 0.4); }
.score-card.score-gruen .score-value, .score-card.score-gruen .score-label { color: #4ade80; }
.comment-score.score-gruen { background-color: rgba(34, 197, 94, 0.15); color: #4ade80; border-color: rgba(34, 197, 94, 0.3); }

/* Gelb / Frühwarnung (0.25 - 0.49) */
.score-card.score-gelb { background: linear-gradient(135deg, rgba(234, 179, 8, 0.15), transparent); border: 1px solid rgba(234, 179, 8, 0.4); }
.score-card.score-gelb .score-value, .score-card.score-gelb .score-label { color: #fde047; }
.comment-score.score-gelb { background-color: rgba(234, 179, 8, 0.15); color: #fde047; border-color: rgba(234, 179, 8, 0.3); }

/* Orange / Eskalation (0.50 - 0.74) */
.score-card.score-orange { background: linear-gradient(135deg, rgba(249, 115, 22, 0.15), transparent); border: 1px solid rgba(249, 115, 22, 0.4); }
.score-card.score-orange .score-value, .score-card.score-orange .score-label { color: #ffedd5; text-shadow: 0 0 10px rgba(249, 115, 22, 0.5); }
.comment-score.score-orange { background-color: rgba(249, 115, 22, 0.15); color: #fdba74; border-color: rgba(249, 115, 22, 0.3); }

/* Rot / Kritisch (>= 0.75) */
.score-card.score-rot { background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), transparent); border: 1px solid rgba(239, 68, 68, 0.5); box-shadow: inset 0 0 15px rgba(239, 68, 68, 0.1); }
.score-card.score-rot .score-value, .score-card.score-rot .score-label { color: #fca5a5; text-shadow: 0 0 12px rgba(239, 68, 68, 0.6); }
.comment-score.score-rot { background-color: rgba(239, 68, 68, 0.2); color: #fca5a5; border-color: rgba(239, 68, 68, 0.4); }


/* =========================================
   LEGENDE STYLING
========================================= */
.score-legend {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--grid-line);
}

.score-legend h4 {
  margin: 0 0 12px 0;
  font-size: 0.8rem;
  text-transform: uppercase;
  color: var(--muted);
  letter-spacing: 0.05em;
}

.score-legend ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.score-legend li {
  display: flex;
  align-items: center;
  font-size: 0.875rem;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 12px;
  flex-shrink: 0;
}

.legend-text {
  color: var(--text);
  flex-grow: 1;
}

.legend-range {
  color: var(--muted);
  font-family: monospace;
  font-size: 0.8rem;
}

.dot-gruen { background-color: #4ade80; box-shadow: 0 0 8px rgba(74, 222, 128, 0.4); }
.dot-gelb { background-color: #fde047; box-shadow: 0 0 8px rgba(253, 224, 71, 0.4); }
.dot-orange { background-color: #fb923c; box-shadow: 0 0 8px rgba(251, 146, 60, 0.4); }
.dot-rot { background-color: #f87171; box-shadow: 0 0 8px rgba(248, 113, 113, 0.4); }


/* =========================================
   RESTLICHES STYLING
========================================= */
.score-meta {
  color: var(--muted);
  font-size: 0.85rem;
  text-align: center;
}

.line-chart-svg {
  width: 100%;
  height: auto;
  overflow: visible;
}

.chart-grid line {
  stroke: var(--grid-line);
  stroke-dasharray: 3 3;
  stroke-width: 1;
}

.chart-grid text {
  fill: var(--muted);
  font-size: 0.7rem;
  text-anchor: end;
}

.history-line {
  fill: none;
  stroke: var(--accent);
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.chart-point {
  fill: var(--surface);
  stroke: var(--accent);
  stroke-width: 2.5;
}

.chart-label.data-val {
  fill: var(--accent);
  font-size: 0.75rem;
  font-weight: 600;
  text-anchor: middle;
}

.chart-label.date-val {
  fill: var(--muted);
  font-size: 0.7rem;
  text-anchor: middle;
}

.chart-label.time-val {
  fill: var(--muted);
  font-size: 0.62rem;
  text-anchor: middle;
  opacity: 0.7;
}

.radar-and-list {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 16px;
  align-items: center;
}

.radar-wrapper {
  display: flex;
  justify-content: center;
}

.radar-chart {
  width: 100%;
  max-width: 220px;
  height: auto;
  overflow: visible;
}

.radar-grid-rings polygon {
  fill: none;
  stroke: var(--grid-line);
  stroke-width: 1;
}

.radar-ring-label {
  fill: rgba(255, 255, 255, 0.25);
  font-size: 0.65rem;
  text-anchor: middle;
}

.radar-axis {
  stroke: var(--grid-line);
  stroke-width: 1.5;
}

.radar-axis-label {
  fill: var(--text);
  font-size: 0.7rem;
  font-weight: 500;
}

.radar-area {
  fill: var(--accent-highlight);
  stroke: var(--accent);
  stroke-width: 2;
  stroke-linejoin: round;
}

.kpi-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.kpi-list li {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--grid-line);
  font-size: 0.875rem;
}

.kpi-list li:last-child {
  border-bottom: none;
}

.kpi-list span {
  color: var(--muted);
}

.kpi-list strong {
  color: var(--accent);
}

.bottom-section {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 24px;
}

/* =========================================
   NEU: THREAD-LISTE & TEXT LAYOUT
========================================= */

.thread-panel-left {
  position: sticky;
  top: 24px;
  height: fit-content;
}

.thread-panel-left h3 {
  margin: 0 0 16px 0;
  font-size: 1.1rem;
}

.thread-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* Warnstufen Framing der Titel-Karten */
.thread-item {
  padding: 14px;
  border-radius: 8px;
  background-color: var(--surface-card);
  border: 2px solid var(--border);
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
  line-height: 1.4;
  color: var(--text);
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.thread-item:hover {
  transform: translateX(4px);
}

.thread-item.active {
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

/* Farben basierend auf der maximalen Warnstufe des Threads */
.thread-item.score-gruen { border-color: rgba(34, 197, 94, 0.4); background-color: rgba(34, 197, 94, 0.05); }
.thread-item.score-gruen.active { border-color: #4ade80; }

.thread-item.score-gelb { border-color: rgba(234, 179, 8, 0.4); background-color: rgba(234, 179, 8, 0.05); }
.thread-item.score-gelb.active { border-color: #fde047; }

.thread-item.score-orange { border-color: rgba(249, 115, 22, 0.4); background-color: rgba(249, 115, 22, 0.05); }
.thread-item.score-orange.active { border-color: #fb923c; }

.thread-item.score-rot { border-color: rgba(239, 68, 68, 0.5); background-color: rgba(239, 68, 68, 0.1); }
.thread-item.score-rot.active { border-color: #f87171; box-shadow: 0 0 10px rgba(239, 68, 68, 0.2); }

/* Text & Kommentar Layout rechts */
.thread-panel-right h2 {
  margin: 0 0 12px 0;
  font-size: 1.4rem;
  color: var(--accent);
}

.thread-panel-right h3 {
  margin: 32px 0 16px 0;
  font-size: 1.2rem;
  border-bottom: 1px solid var(--grid-line);
  padding-bottom: 8px;
}

.thread-text-container {
  background-color: var(--surface-card);
  padding: 20px;
  border-radius: 12px;
  border-left: 4px solid var(--accent);
}

.thread-text {
  margin: 0;
  color: #e2e8f0;
  line-height: 1.6;
  font-size: 1rem;
  white-space: pre-wrap;
}

.comments-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.comment-card {
  background-color: var(--surface-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: border-color 0.2s ease, transform 0.2s ease;
}

.comment-card:hover {
  border-color: rgba(56, 189, 248, 0.5);
  transform: translateY(-1px);
}

.comment-card.active {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent-soft);
  background-color: rgba(30, 41, 59, 0.7);
}

.comment-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  font-size: 0.9rem;
}

.comment-head strong {
  color: var(--text);
}

.comment-head span {
  color: var(--muted);
}

.comment-score {
  display: inline-block;
  font-size: 0.85rem;
  padding: 4px 10px;
  border-radius: 6px;
  margin-bottom: 12px;
  border-style: solid;
  border-width: 1px;
}

.comment-card p {
  margin: 0 0 16px 0;
  font-size: 0.95rem;
  line-height: 1.5;
  color: #e2e8f0;
}

.comment-card .moderation {
  background-color: rgba(255, 255, 255, 0.03);
  border-left: 3px solid var(--accent);
  padding: 10px 14px;
  border-radius: 0 8px 8px 0;
  font-size: 0.9rem;
  color: var(--muted);
}

.comment-card .moderation strong {
  color: var(--text);
}

.loading {
  text-align: center;
  padding: 40px;
  color: var(--muted);
}

@media (max-width: 1100px) {
  .dashboard {
    grid-template-columns: 1fr;
  }
  .bottom-section {
    grid-template-columns: 1fr;
  }
  .thread-panel-left {
    position: static;
  }
}

@media (max-width: 600px) {
  .radar-and-list {
    grid-template-columns: 1fr;
  }
  .page {
    padding: 16px;
  }
}
</style>