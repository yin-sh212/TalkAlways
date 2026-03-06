import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

// ú”(ž‹
const app = createApp(App)

// ( Pinia
app.use(createPinia())

// (ï1
app.use(router)

// }”(
app.mount('#app')
