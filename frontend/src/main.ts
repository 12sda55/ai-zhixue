import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import App from './App.vue'
import router from './router'
import './shared/styles/global.less'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(Antd)

// 全局错误处理：防止未捕获的异常导致页面空白
app.config.errorHandler = (err, _instance, info) => {
  console.error('[Vue Error]', err, '\nInfo:', info)
}

// 全局未处理的 Promise rejection
window.addEventListener('unhandledrejection', (event) => {
  console.error('[Unhandled Promise Rejection]', event.reason)
})

app.mount('#app')