import axios from 'axios'
import { setupAuthInterceptor } from './authInterceptor'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 安装认证拦截器
setupAuthInterceptor(request, {
  tokenKey: 'token',
  userKey: 'user',
  refreshThreshold: 24 * 60 * 60 * 1000, // 1天
  loginPath: '/login',
  enableAutoRefresh: true,
})

// 响应拦截器：提取data
request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    // 错误已在authInterceptor中处理，这里只负责传递错误
    return Promise.reject(error)
  }
)

export default request