import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import PrimeVue from 'primevue/config'
import Tooltip from 'primevue/tooltip'
import './assets/main.css'
import App from './App.vue'
import { appThemePreset } from './theme'

const app = createApp(App)

const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)
app.use(pinia)
app.use(PrimeVue, {
  theme: {
    preset: appThemePreset,
    options: {
      darkModeSelector: '.dark',
      cssLayer: {
        name: 'primevue',
        order: 'theme, base, primevue',
      },
    },
  },
})
app.directive('tooltip', Tooltip)

app.mount('#app')
