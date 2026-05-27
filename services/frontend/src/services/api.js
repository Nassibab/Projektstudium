import axios from 'axios'

// Basis-Konfiguration für unser Backend
const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000 // Timeout nach 10 Sekunden
})

// Hier exportieren wir alle unsere API-Aufrufe
export default {
  getDemoData() {
    return apiClient.get('/demo-data')
  }
}