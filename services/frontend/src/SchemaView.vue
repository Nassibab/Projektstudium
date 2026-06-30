<template>
  <div class="app dark-theme">
    <div class="page">
      <header class="topbar">
        <div>
          <h1>Live Shitstorm Evaluation</h1>
          <p class="subtitle">Thread: {{ data?.current_window_metrics?.thread_id ?? '-' }}</p>
        </div>
        <div class="status-badge" :class="{'connected': status.includes('Verbunden') || status.includes('Geladen')}">
          {{ status }}
        </div>
      </header>

      <section class="top-section">
        <div class="panel score-panel">
          <div class="panel-header">
            <h2>Aktuelle Metriken</h2>
            <p class="subtitle">
              Zeitraum: {{ formatTime(data?.current_window_metrics?.window_start) }} - 
              {{ formatTime(data?.current_window_metrics?.window_end) }}
            </p>
          </div>
          <div class="metrics-grid">
            <div class="metric-box">
              <span class="label">Kommentare</span>
              <span class="value">{{ data?.current_window_metrics?.comment_count ?? '-' }}</span>
            </div>
            <div class="metric-box">
              <span class="label">Unique Users</span>
              <span class="value">{{ data?.current_window_metrics?.unique_users ?? '-' }}</span>
            </div>
          </div>
        </div>

        <div class="panel prediction-panel">
          <div class="panel-header">
            <h2>Vorhersage & Status</h2>
          </div>
          <div class="score-card" :class="'level-' + (data?.shitstorm_prediction?.warning_level ?? 'none')">
            <span class="score-value">{{ data?.shitstorm_prediction?.shitstorm_barometer ?? '-' }}</span>
            <span class="score-label">Barometer Score</span>
          </div>
          <div class="meta-list">
            <div><strong>Warning Level:</strong> {{ data?.shitstorm_prediction?.warning_level ?? '-' }}</div>
            <div><strong>Status:</strong> {{ data?.shitstorm_prediction?.evaluation_status ?? '-' }}</div>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <h2>Dimensionen & Indikatoren</h2>
        </div>
        
        <div class="dimensions-grid">
          <div 
            class="dimension-card" 
            v-for="(dim, key) in data?.shitstorm_prediction?.dimension_results || {}" 
            :key="key"
          >
            <div class="dim-header">
              <h3>{{ dim.label }}</h3>
              <span class="evidence-badge" :title="'Evidence Score'">
                {{ formatNumber(dim.evidence_score) }}
              </span>
            </div>
            
            <ul class="indicator-list">
                <li v-for="(indicator, iKey) in dim.indicator_results" :key="iKey">
                    <span class="ind-name">{{ iKey }}</span>
                    <span class="ind-score">Wert: 
                    <strong :class="{ 'red-zero': indicator.current_value === 0 }">
                        {{ formatPrecise(indicator.current_value) }}
                    </strong>
                    </span>
                </li>
                <li v-if="!dim.indicator_results || Object.keys(dim.indicator_results).length === 0" class="empty-list">
                    Keine Indikatoren
                </li>
            </ul>
          </div>
          
          <div v-if="!data?.shitstorm_prediction?.dimension_results" class="empty-list">
            Warte auf Dimensionsdaten...
          </div>
        </div>
      </section>

      <section class="bottom-section">
        <div class="panel">
          <div class="panel-header"><h2>Countermeasures</h2></div>
          <div class="meta-list">
            <div><strong>Level:</strong> {{ data?.countermeasures?.level ?? '-' }}</div>
            <div><strong>Actions:</strong> {{ data?.countermeasures?.actions?.length ? data.countermeasures.actions.join(', ') : 'Keine' }}</div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-header"><h2>Counter Speech</h2></div>
          <div class="meta-list">
            <div><strong>Soll generieren:</strong> {{ data?.counter_speech?.should_generate ?? '-' }}</div>
            <div><strong>Grund:</strong> {{ data?.counter_speech?.reason ?? '-' }}</div>
            <div v-if="data?.counter_speech?.generated_text"><strong>Text:</strong> {{ data.counter_speech.generated_text }}</div>
            <div v-if="data?.counter_speech?.error" class="error-text"><strong>Fehler:</strong> {{ data.counter_speech.error }}</div>
          </div>
        </div>
      </section>

      <section class="panel method-panel">
        <div class="panel-header">
          <h2>Methodik (Konfiguration)</h2>
        </div>
        <div class="method-grid">
          <div v-for="(val, key) in data?.shitstorm_prediction?.method || {}" :key="key" class="method-item">
            <strong>{{ formatKeyName(key) }}:</strong>
            <p>{{ val }}</p>
          </div>
          <div v-if="!data?.shitstorm_prediction?.method" class="empty-list">Keine Methodik-Daten verfügbar.</div>
        </div>
      </section>

    </div>
  </div>
</template>

<script>
export default {
  name: 'SchemaView',
  data() {
    return {
      data: null,
      status: 'Initialisiere...',
      eventSource: null
    }
  },
  async mounted() {
    // 1. Setze initial den Status für die Platzhalter
    this.status = 'Warte auf Live-Daten vom Backend...';

    // 2. Versuche die test.json zur Laufzeit aus dem public-Ordner zu laden
    try {
      const response = await fetch('/test.json');
      if (response.ok) {
        const testData = await response.json();
        this.data = testData;
        this.status = 'Lokale test.json geladen (Warte auf Live-Updates...)';
      } else {
        console.log('Keine lokale test.json gefunden (HTTP ' + response.status + '). Starte mit Platzhaltern.');
      }
    } catch (e) {
      console.log('Fehler beim Abrufen der test.json. Starte mit Platzhaltern.');
    }

    // 3. Starte SSE Verbindung für Live Updates aus Redis
    this.connectSSE();
  },
  beforeUnmount() {
    if (this.eventSource) {
      this.eventSource.close();
    }
  },
  methods: {
    connectSSE() {
      this.eventSource = new EventSource('/api/schema-stream');

      this.eventSource.onopen = () => {
        this.status = 'Verbunden via SSE. Empfange Live-Daten...';
      };

      this.eventSource.onmessage = (event) => {
        try {
          this.data = JSON.parse(event.data);
          this.status = 'Daten zuletzt aktualisiert: ' + new Date().toLocaleTimeString();
        } catch (e) {
          console.error("Fehler beim Parsen der JSON-Daten:", e);
        }
      };

      this.eventSource.onerror = (err) => {
        console.error("SSE Fehler:", err);
        this.status = 'Verbindung unterbrochen. Reconnect läuft...';
      };
    },
    
    // Hilfsfunktionen für die Formatierung
    formatTime(isoString) {
      if (!isoString) return '-';
      const d = new Date(isoString);
      return isNaN(d.getTime()) ? isoString : d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
    },
    formatNumber(val) {
      if (val === null || val === undefined || isNaN(val)) return '-';
      return Number(val).toFixed(2);
    },
    formatPrecise(val) {
      if (val === null || val === undefined || isNaN(val)) return '-';
      // parseFloat entfernt die anhängenden Nullen, toFixed(4) limitiert auf max 4 Stellen
      return parseFloat(Number(val).toFixed(4));
    },
    formatKeyName(key) {
      return key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
    }
  }
}
</script>

<style scoped>
/* Theme & Grundstruktur (analog zu App.vue) */
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
  color: var(--text);
  font-family: 'Inter', sans-serif;
}

.page { padding: 24px; }
.topbar { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.topbar h1 { margin: 0 0 4px 0; }
.subtitle { color: var(--muted); margin: 0; font-size: 0.9rem; }

.status-badge { 
  padding: 6px 12px; 
  border-radius: 20px; 
  font-size: 0.85rem; 
  border: 1px solid var(--border); 
  color: var(--muted); 
}
.status-badge.connected { 
  color: #4ade80; 
  border-color: #064e3b; 
  background: rgba(6, 78, 59, 0.3); 
}

/* Layout Panels */
.top-section, .bottom-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
}

.panel {
  background-color: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
}
.panel-header h2 { margin: 0 0 8px 0; font-size: 1.25rem; }

/* Score Card */
.score-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  border-radius: 12px;
  margin: 16px 0;
  border: 1px solid var(--border);
}
.score-value { font-size: 2.5rem; font-weight: 800; line-height: 1; }
.score-label { margin-top: 8px; font-size: 0.9rem; color: var(--muted); }

/* Warning Level Colors */
.level-normal { background: rgba(6, 78, 59, 0.3); border-color: #064e3b; color: #4ade80; }
.level-watch { background: rgba(113, 63, 18, 0.3); border-color: #713f12; color: #fde047; }
.level-warning { background: rgba(124, 45, 18, 0.3); border-color: #7c2d12; color: #fdba74; }
.level-critical { background: rgba(127, 29, 29, 0.3); border-color: #7f1d1d; color: #fca5a5; }

/* Metrics Grid */
.metrics-grid {
  display: flex;
  gap: 24px;
  margin-top: 16px;
}
.metric-box {
  display: flex;
  flex-direction: column;
}
.metric-box .label { font-size: 0.85rem; color: var(--muted); margin-bottom: 4px; }
.metric-box .value { font-size: 1.5rem; font-weight: bold; }

.red-zero {
  color: #fca5a5 !important;
}

/* Lists & Text */
.meta-list > div {
  margin-bottom: 8px;
  font-size: 0.95rem;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  padding-bottom: 8px;
}
.error-text { color: #fca5a5; }

/* Dimensions Grid */
.dimensions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-top: 16px;
}
.dimension-card {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
}
.dim-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border);
  padding-bottom: 12px;
}
.dim-header h3 { margin: 0; font-size: 1.1rem; color: var(--accent); }
.evidence-badge {
  background: var(--border);
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: bold;
}
.indicator-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.indicator-list li {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  padding: 8px 0;
  border-bottom: 1px dashed var(--border);
}
.indicator-list li:last-child { border-bottom: none; }
.ind-name { color: #e2e8f0; font-family: monospace;}
.ind-score { color: var(--muted); }
.ind-score strong { color: #f8fafc; }

/* Method Grid */
.method-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}
.method-item {
  background: rgba(0,0,0,0.15);
  padding: 12px;
  border-radius: 8px;
  border-left: 3px solid var(--accent);
}
.method-item strong { display: block; margin-bottom: 6px; color: var(--accent); font-size: 0.9rem; }
.method-item p { margin: 0; font-size: 0.85rem; color: var(--muted); line-height: 1.4; }

.empty-list { color: var(--muted); font-style: italic; font-size: 0.9rem; padding: 10px 0; }

@media (max-width: 900px) {
  .top-section, .bottom-section { grid-template-columns: 1fr; }
}
</style>