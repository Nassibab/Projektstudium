import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api', // Nutzt den Proxy aus der vite.config.js
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000
})

export default {
  // Lade die ECHTEN letzten 2 Threads aus der DB
  getLatestThreads() {
    return apiClient.get('/threads/latest')
  }
}