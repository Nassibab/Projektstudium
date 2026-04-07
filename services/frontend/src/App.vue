<template>
  <div class="container">
    <h1>Hate Speech Intensity Gauge</h1>

    <div class="selector">
      <label for="website">Choose a website:</label>
      <select id="website" v-model.number="selectedWebsiteId">
        <option v-for="site in websites" :key="site.id" :value="site.id">
          {{ site.name }}
        </option>
      </select>
    </div>

    <div class="gauge-wrapper" v-if="selectedWebsite">
      <div class="gauge">
        <div class="gauge-background"></div>
        
        <div class="gauge-mask"></div>

        <div class="segment-labels">
          <span class="label-1">1</span>
          <span class="label-2">2</span>
          <span class="label-3">3</span>
          <span class="label-4">4</span>
          <span class="label-5">5</span>
          <span class="label-6">6</span>
        </div>

        <div class="pointer" :style="pointerStyle"></div>
        <div class="center-dot"></div>
      </div>
      
      <div class="status-label">
        Current level: <strong>{{ selectedWebsite.value }}</strong>
      </div>
    </div>

    <div class="loading" v-else>
      <p>Fetching website data...</p>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'IntensityGauge',
  data() {
    return {
      websites: [],
      selectedWebsiteId: null
    }
  },
  computed: {
    selectedWebsite() {
      return this.websites.find(site => site.id === this.selectedWebsiteId)
    },
    pointerStyle() {
      const val = this.selectedWebsite ? this.selectedWebsite.value : 1
      
      // Each segment is 30 degrees (180 / 6).
      // To hit the middle, we start at -90 (far left) + 15 (half a segment).
      const startAngle = -75; 
      const step = 30;
      const angle = startAngle + (val - 1) * step;
      
      return {
        transform: `translateX(-50%) rotate(${angle}deg)`
      }
    }
  },
  async mounted() {
    try {
      // Ensure your backend is running at this URL
      const response = await axios.get('http://localhost:8000/websites')
      this.websites = response.data
      
      if (this.websites.length > 0) {
        this.selectedWebsiteId = this.websites[0].id
      }
    } catch (error) {
      console.error("API Error:", error)
    }
  }
}
</script>

<style scoped>
/* Scoped ensures these styles don't leak to the rest of your app */

.container {
  max-width: 600px;
  margin: 50px auto;
  padding: 30px;
  text-align: center;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background-color: #1a1a1a;
  border-radius: 12px;
  color: #ffffff;
}

.selector {
  margin-bottom: 40px;
}

.selector label {
  display: block;
  margin-bottom: 10px;
  color: #ccc;
}

.selector select {
  padding: 10px 15px;
  border-radius: 8px;
  border: 1px solid #444;
  background: #2a2a2a;
  color: #fff;
  font-size: 1rem;
  cursor: pointer;
}

.gauge-wrapper {
  position: relative;
  display: inline-block;
}

.gauge {
  width: 300px;
  height: 150px; /* Semi-circle height */
  position: relative;
  overflow: hidden;
  border-radius: 150px 150px 0 0;
  background: #222;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
}

/* Creates the 6 colored slices using a conic gradient */
.gauge-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 200%; /* Full circle height so center is at the bottom of the gauge */
  background: conic-gradient(
    from 270deg,
    #2ecc71 0deg 30deg,    /* Green */
    #a2d149 30deg 60deg,   /* Light Green */
    #f1c40f 60deg 90deg,   /* Yellow */
    #e67e22 90deg 120deg,  /* Orange */
    #e74c3c 120deg 150deg, /* Light Red */
    #c0392b 150deg 180deg, /* Dark Red */
    transparent 180deg
  );
  opacity: 0.8;
}

/* Covers the center of the pie to make it look like a gauge track */
.gauge-mask {
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 75%;
  height: 75%;
  background: #1a1a1a; /* Matches container background */
  border-radius: 150px 150px 0 0;
  z-index: 2;
}

.pointer {
  position: absolute;
  left: 50%;
  bottom: 0;
  width: 4px;
  height: 110px;
  background: #ffffff;
  transform-origin: bottom center;
  z-index: 10;
  /* Smooth "swing" animation */
  transition: transform 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  border-radius: 4px;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
}

.center-dot {
  position: absolute;
  left: 50%;
  bottom: -10px;
  width: 24px;
  height: 24px;
  background: #ffffff;
  border-radius: 50%;
  transform: translateX(-50%);
  z-index: 11;
}

/* Label positioning around the arc */
.segment-labels span {
  position: absolute;
  z-index: 5;
  font-weight: bold;
  font-size: 1.1rem;
  color: #fff;
  text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
}

.label-1 { bottom: 20px; left: 35px; }
.label-2 { top: 55px; left: 55px; }
.label-3 { top: 25px; left: 32%; }
.label-4 { top: 25px; right: 32%; }
.label-5 { top: 55px; right: 55px; }
.label-6 { bottom: 20px; right: 35px; }

.status-label {
  margin-top: 25px;
  font-size: 1.2rem;
}

.status-label strong {
  color: #2ecc71;
  font-size: 1.5rem;
}

.loading {
  color: #888;
  font-style: italic;
}
</style>