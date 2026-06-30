import { createApp, h, shallowRef } from 'vue'
import App from './App.vue'
import SchemaView from './SchemaView.vue'

// 1. Simple routing state
const currentRoute = shallowRef(window.location.pathname)

// 2. Listen to browser navigation
window.addEventListener('popstate', () => {
  currentRoute.value = window.location.pathname
})

// 3. Create a Root component that acts as a switch
const Root = {
  setup() {
    return () => {
      // If the URL is exactly '/schema', show the new page
      if (currentRoute.value === '/schema') {
        return h(SchemaView)
      }
      // Otherwise, always show your existing, untouched App.vue
      return h(App)
    }
  }
}

// Mount the app
createApp(Root).mount('#app')