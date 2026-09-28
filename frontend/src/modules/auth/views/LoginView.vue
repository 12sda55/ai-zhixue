<template>
  <div class="auth-landing-page">
    <!-- 背景图片 -->
    <div class="login-bg-image"></div>
    <!-- 粒子系统 -->
    <canvas ref="canvasRef" class="particle-canvas" />
    <!-- 渐变遮罩 -->
    <div class="login-bg-grad"></div>

    <nav class="login-nav">
      <div class="login-nav-pill liquid-glass">
        <div class="nav-brand">
          <div class="nav-brand-icon">AI</div>
          <span>智学</span>
        </div>
        <router-link to="/landing" class="nav-back">← 返回首页</router-link>
      </div>
    </nav>

    <div class="auth-card liquid-glass">
      <div class="auth-card-inner">
        <div class="auth-header">
          <div class="auth-logo">AI</div>
          <h1 class="auth-title serif">{{ mode === 'login' ? '欢迎回来' : '创建账户' }}</h1>
          <p class="auth-subtitle">{{ mode === 'login' ? '登录你的账户，继续学习之旅' : '注册后即可开启个性化学习' }}</p>
        </div>

        <div class="tab-row">
          <button class="tab-btn" :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
          <button class="tab-btn" :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button>
        </div>

        <!-- 登录表单 -->
        <form v-if="mode === 'login'" class="auth-form active" @submit.prevent="handleLogin" novalidate>
          <div class="form-group">
            <label class="form-label">用户名</label>
            <div class="form-input-wrap" :class="{ 'input-error': loginErrors.username }">
              <input type="text" v-model="loginForm.username" placeholder="请输入你的用户名" required @input="validateLoginUsername" />
            </div>
            <div v-if="loginErrors.username" class="field-error">{{ loginErrors.username }}</div>
          </div>
          <div class="form-group">
            <label class="form-label">密码</label>
            <div class="form-input-wrap password-wrap" :class="{ 'input-error': loginErrors.password }">
              <input :type="showLoginPassword ? 'text' : 'password'" v-model="loginForm.password" placeholder="请输入密码" required @input="validateLoginPassword" />
              <button type="button" class="password-toggle" @click="showLoginPassword = !showLoginPassword" aria-label="显示密码">
                <svg v-if="!showLoginPassword" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
              </button>
            </div>
            <div v-if="loginErrors.password" class="field-error">{{ loginErrors.password }}</div>
          </div>
          <div class="form-options">
            <label class="checkbox-wrap">
              <input type="checkbox" v-model="rememberMe" />
              <span>记住我</span>
            </label>
            <button type="button" class="forgot-link" @click="showForgotModal = true">忘记密码？</button>
          </div>
          <button type="submit" class="submit-btn" :class="submitClass" :disabled="loading">
            <span v-if="loading" class="btn-loading">
              <svg class="spinner" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" stroke-dasharray="31.4 31.4" /></svg>
              登录中…
            </span>
            <span v-else-if="submitSuccess" class="btn-success">✓ 成功</span>
            <span v-else>登录</span>
          </button>
          <div v-if="errorMsg" class="error-msg" :class="{ shake: errorMsgShake }">{{ errorMsg }}</div>
        </form>

        <!-- 注册表单 -->
        <form v-if="mode === 'register'" class="auth-form active" @submit.prevent="handleRegister" novalidate>
          <div class="form-group">
            <label class="form-label">角色类型</label>
            <div class="form-input-wrap">
              <select v-model="registerForm.role" @change="onRoleChange">
                <option value="student">学生</option>
                <option value="admin">管理员</option>
              </select>
            </div>
          </div>
          <!-- 管理员邀请码 -->
          <div v-if="registerForm.role === 'admin'" class="form-group">
            <label class="form-label">管理员邀请码</label>
            <div class="form-input-wrap" :class="{ 'input-error': registerErrors.inviteCode }">
              <input type="text" v-model="registerForm.inviteCode" placeholder="请输入管理员邀请码" required @input="validateInviteCode" />
            </div>
            <div v-if="registerErrors.inviteCode" class="field-error">{{ registerErrors.inviteCode }}</div>
          </div>
          <div class="form-group">
            <label class="form-label">用户名</label>
            <div class="form-input-wrap" :class="{ 'input-error': registerErrors.username }">
              <input type="text" v-model="registerForm.username" placeholder="设置你的用户名" required @input="validateRegisterUsername" />
            </div>
            <div v-if="registerErrors.username" class="field-error">{{ registerErrors.username }}</div>
          </div>
          <div class="form-group">
            <label class="form-label">邮箱（可选）</label>
            <div class="form-input-wrap" :class="{ 'input-error': registerErrors.email }">
              <input type="email" v-model="registerForm.email" placeholder="your@email.com" @input="validateRegisterEmail" />
            </div>
            <div v-if="registerErrors.email" class="field-error">{{ registerErrors.email }}</div>
          </div>
          <div class="form-group">
            <label class="form-label">密码</label>
            <div class="form-input-wrap password-wrap" :class="{ 'input-error': registerErrors.password }">
              <input :type="showRegPassword ? 'text' : 'password'" v-model="registerForm.password" placeholder="设置你的密码（至少6位）" required @input="validateRegisterPassword" />
              <button type="button" class="password-toggle" @click="showRegPassword = !showRegPassword" aria-label="显示密码">
                <svg v-if="!showRegPassword" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
              </button>
            </div>
            <div v-if="registerErrors.password" class="field-error">{{ registerErrors.password }}</div>
            <!-- 密码强度指示器 -->
            <div v-if="registerForm.password" class="password-strength">
              <div class="strength-bar">
                <div class="strength-fill" :class="passwordStrengthClass" :style="{ width: passwordStrengthWidth }"></div>
              </div>
              <span class="strength-text" :class="passwordStrengthClass">{{ passwordStrengthText }}</span>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">确认密码</label>
            <div class="form-input-wrap" :class="{ 'input-error': registerErrors.confirmPassword }">
              <input type="password" v-model="registerForm.confirmPassword" placeholder="再次输入密码" required @input="validateConfirmPassword" />
            </div>
            <div v-if="registerErrors.confirmPassword" class="field-error">{{ registerErrors.confirmPassword }}</div>
          </div>
          <button type="submit" class="submit-btn" :class="submitClass" :disabled="loading || !isRegisterValid">
            <span v-if="loading" class="btn-loading">
              <svg class="spinner" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" stroke-dasharray="31.4 31.4" /></svg>
              注册中…
            </span>
            <span v-else-if="submitSuccess" class="btn-success">✓ 成功</span>
            <span v-else>创建账户</span>
          </button>
          <div v-if="errorMsg" class="error-msg" :class="{ shake: errorMsgShake }">{{ errorMsg }}</div>
        </form>

        <div class="auth-footer">
          <router-link to="/landing">← 返回产品首页</router-link>
        </div>
      </div>
    </div>

    <!-- 忘记密码模态框 -->
    <div v-if="showForgotModal" class="modal-overlay" @click.self="closeForgotModal">
      <div class="modal-content liquid-glass">
        <button class="modal-close" @click="closeForgotModal">✕</button>
        <h2 class="modal-title">重置密码</h2>

        <!-- 步骤指示器 -->
        <div class="step-indicator">
          <div class="step" :class="{ active: forgotStep >= 1, done: forgotStep > 1 }">1</div>
          <div class="step-line" :class="{ active: forgotStep > 1 }"></div>
          <div class="step" :class="{ active: forgotStep >= 2, done: forgotStep > 2 }">2</div>
          <div class="step-line" :class="{ active: forgotStep > 2 }"></div>
          <div class="step" :class="{ active: forgotStep >= 3 }">3</div>
        </div>

        <!-- 步骤1: 输入用户名 -->
        <div v-if="forgotStep === 1" class="forgot-step">
          <p class="step-desc">请输入你的用户名</p>
          <div class="form-group">
            <div class="form-input-wrap">
              <input type="text" v-model="forgotUsername" placeholder="用户名" />
            </div>
          </div>
          <button class="submit-btn" @click="sendVerificationCode" :disabled="!forgotUsername || forgotCooldown > 0">
            {{ forgotCooldown > 0 ? `${forgotCooldown}s 后可重新发送` : '发送验证码' }}
          </button>
          <p class="demo-hint">演示模式：验证码为 <code>123456</code></p>
        </div>

        <!-- 步骤2: 输入验证码 -->
        <div v-if="forgotStep === 2" class="forgot-step">
          <p class="step-desc">请输入验证码</p>
          <div class="form-group">
            <div class="form-input-wrap">
              <input type="text" v-model="forgotCode" placeholder="请输入6位验证码" maxlength="6" />
            </div>
          </div>
          <button class="submit-btn" @click="verifyCode" :disabled="forgotCode.length !== 6">验证</button>
          <div v-if="forgotError" class="error-msg">{{ forgotError }}</div>
        </div>

        <!-- 步骤3: 设置新密码 -->
        <div v-if="forgotStep === 3" class="forgot-step">
          <p class="step-desc">请设置新密码</p>
          <div class="form-group">
            <label class="form-label">新密码</label>
            <div class="form-input-wrap password-wrap">
              <input :type="showForgotPassword ? 'text' : 'password'" v-model="forgotNewPassword" placeholder="至少6位，包含数字和字母" />
              <button type="button" class="password-toggle" @click="showForgotPassword = !showForgotPassword">
                <svg v-if="!showForgotPassword" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
              </button>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">确认密码</label>
            <div class="form-input-wrap">
              <input type="password" v-model="forgotConfirmPassword" placeholder="再次输入新密码" />
            </div>
          </div>
          <button class="submit-btn" @click="resetPassword" :disabled="!isForgotPasswordValid">重置密码</button>
          <div v-if="forgotError" class="error-msg">{{ forgotError }}</div>
        </div>

        <!-- 步骤4: 完成 -->
        <div v-if="forgotStep === 4" class="forgot-step success-step">
          <div class="success-icon">✓</div>
          <p class="success-text">密码重置成功！</p>
          <button class="submit-btn" @click="closeForgotModal">返回登录</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { validateUsername, validatePassword, validateEmail, checkPasswordStrength } from '../api/authApi'
import type { UserRole } from '../../../shared/types'

const router = useRouter()
const authStore = useAuthStore()

const mode = ref<'login' | 'register'>('login')
const loading = ref(false)
const errorMsg = ref('')
const errorMsgShake = ref(false)
const rememberMe = ref(false)
const showLoginPassword = ref(false)
const showRegPassword = ref(false)
const submitSuccess = ref(false)

// 粒子系统
const canvasRef = ref<HTMLCanvasElement | null>(null)
let animFrameId = 0

// 登录表单
const loginForm = reactive({ username: '', password: '' })
const loginErrors = reactive({ username: '', password: '' })

// 注册表单
const registerForm = reactive<{
  username: string
  password: string
  confirmPassword: string
  email: string
  role: UserRole
  inviteCode: string
}>({
  username: '',
  password: '',
  confirmPassword: '',
  email: '',
  role: 'student',
  inviteCode: '',
})
const registerErrors = reactive({ username: '', password: '', confirmPassword: '', email: '', inviteCode: '' })

// 忘记密码
const showForgotModal = ref(false)
const forgotStep = ref(1)
const forgotUsername = ref('')
const forgotCode = ref('')
const forgotNewPassword = ref('')
const forgotConfirmPassword = ref('')
const forgotError = ref('')
const forgotCooldown = ref(0)
const showForgotPassword = ref(false)

// 密码强度
const passwordStrength = computed(() => checkPasswordStrength(registerForm.password))
const passwordStrengthClass = computed(() => passwordStrength.value)
const passwordStrengthWidth = computed(() => {
  if (passwordStrength.value === 'strong') return '100%'
  if (passwordStrength.value === 'medium') return '66%'
  return '33%'
})
const passwordStrengthText = computed(() => {
  if (passwordStrength.value === 'strong') return '强'
  if (passwordStrength.value === 'medium') return '中'
  return '弱'
})

// 提交按钮状态
const submitClass = computed(() => ({
  'btn-success-state': submitSuccess.value,
  'btn-error-state': errorMsgShake.value,
}))

// 注册表单是否有效
const isRegisterValid = computed(() => {
  const baseValid =
    registerForm.username.length >= 3 &&
    registerForm.password.length >= 6 &&
    /[0-9]/.test(registerForm.password) &&
    /[a-zA-Z]/.test(registerForm.password) &&
    registerForm.password === registerForm.confirmPassword &&
    !registerErrors.username &&
    !registerErrors.password &&
    !registerErrors.confirmPassword

  // 管理员注册需要邀请码
  if (registerForm.role === 'admin') {
    return baseValid && registerForm.inviteCode.trim().length > 0 && !registerErrors.inviteCode
  }
  return baseValid
})

// 忘记密码表单是否有效
const isForgotPasswordValid = computed(() => {
  return (
    forgotNewPassword.value.length >= 6 &&
    /[0-9]/.test(forgotNewPassword.value) &&
    /[a-zA-Z]/.test(forgotNewPassword.value) &&
    forgotNewPassword.value === forgotConfirmPassword.value
  )
})

// 粒子系统初始化
function initParticles() {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  let W: number, H: number
  const resize = () => {
    W = canvas.width = window.innerWidth
    H = canvas.height = window.innerHeight
  }
  resize()
  window.addEventListener('resize', resize)

  const PARTICLE_COUNT = 120
  const CONNECTION_DISTANCE = 100

  // 适应暗色调的粒子颜色 - 加深饱和度
  const COLORS = [
    'rgba(66, 153, 225, 0.6)',
    'rgba(56, 161, 105, 0.55)',
    'rgba(128, 90, 213, 0.55)',
    'rgba(221, 107, 32, 0.5)',
    'rgba(214, 51, 132, 0.5)',
  ]

  class Particle {
    x: number
    y: number
    vx: number
    vy: number
    r: number
    color: string
    phase: number
    phaseSpeed: number

    constructor() {
      this.x = Math.random() * W
      this.y = Math.random() * H
      this.vx = (Math.random() - 0.5) * 0.5
      this.vy = (Math.random() - 0.5) * 0.5
      this.r = 2 + Math.random() * 3
      this.color = COLORS[Math.floor(Math.random() * COLORS.length)]
      this.phase = Math.random() * Math.PI * 2
      this.phaseSpeed = 0.01 + Math.random() * 0.02
    }

    update() {
      this.phase += this.phaseSpeed
      const oscX = Math.sin(this.phase) * 0.3
      const oscY = Math.cos(this.phase * 0.7) * 0.3

      this.x += this.vx + oscX
      this.y += this.vy + oscY

      if (this.x < -20) this.x = W + 20
      if (this.x > W + 20) this.x = -20
      if (this.y < -20) this.y = H + 20
      if (this.y > H + 20) this.y = -20
    }

    draw(ctx: CanvasRenderingContext2D) {
      ctx.beginPath()
      ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2)
      ctx.fillStyle = this.color
      ctx.fill()
    }
  }

  const particles = Array.from({ length: PARTICLE_COUNT }, () => new Particle())

  const drawConnections = () => {
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const a = particles[i]
        const b = particles[j]
        const dx = a.x - b.x
        const dy = a.y - b.y
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < CONNECTION_DISTANCE) {
          const alpha = (1 - dist / CONNECTION_DISTANCE) * 0.25
          ctx.beginPath()
          ctx.moveTo(a.x, a.y)
          ctx.lineTo(b.x, b.y)
          ctx.strokeStyle = `rgba(66, 153, 225, ${alpha})`
          ctx.lineWidth = 0.5
          ctx.stroke()
        }
      }
    }
  }

  const animate = () => {
    ctx.clearRect(0, 0, W, H)
    drawConnections()
    particles.forEach(p => {
      p.update()
      p.draw(ctx)
    })
    animFrameId = requestAnimationFrame(animate)
  }

  animate()
}

// 验证函数
function validateLoginUsername() {
  if (!loginForm.username) {
    loginErrors.username = '请输入用户名'
  } else {
    loginErrors.username = ''
  }
}

function validateLoginPassword() {
  if (!loginForm.password) {
    loginErrors.password = '请输入密码'
  } else {
    loginErrors.password = ''
  }
}

function validateRegisterUsername() {
  const result = validateUsername(registerForm.username)
  registerErrors.username = result.valid ? '' : result.message
}

function validateRegisterPassword() {
  const result = validatePassword(registerForm.password)
  registerErrors.password = result.valid ? '' : result.message
  if (registerForm.confirmPassword) {
    validateConfirmPassword()
  }
}

function validateConfirmPassword() {
  if (registerForm.password !== registerForm.confirmPassword) {
    registerErrors.confirmPassword = '两次输入的密码不一致'
  } else {
    registerErrors.confirmPassword = ''
  }
}

function validateRegisterEmail() {
  const result = validateEmail(registerForm.email)
  registerErrors.email = result.valid ? '' : result.message
}

function validateInviteCode() {
  if (registerForm.role === 'admin') {
    if (!registerForm.inviteCode || registerForm.inviteCode.trim().length === 0) {
      registerErrors.inviteCode = '注册管理员需要邀请码'
    } else {
      registerErrors.inviteCode = ''
    }
  } else {
    registerErrors.inviteCode = ''
  }
}

function onRoleChange() {
  if (registerForm.role === 'admin') {
    validateInviteCode()
  } else {
    registerErrors.inviteCode = ''
    registerForm.inviteCode = ''
  }
}

function showError(msg: string) {
  errorMsg.value = msg
  errorMsgShake.value = true
  setTimeout(() => {
    errorMsgShake.value = false
  }, 500)
}

async function handleLogin() {
  if (!loginForm.username || !loginForm.password) {
    showError('请输入用户名和密码')
    return
  }

  const { locked, remainingSeconds } = authStore.checkAccountLocked(loginForm.username)
  if (locked) {
    const mins = Math.floor(remainingSeconds / 60)
    const secs = remainingSeconds % 60
    showError(`账户已锁定，请等待 ${mins} 分 ${secs} 秒后重试`)
    return
  }

  loading.value = true
  errorMsg.value = ''
  try {
    await authStore.login(loginForm.username, loginForm.password)
    if (rememberMe.value) {
      localStorage.setItem('remembered_username', loginForm.username)
    } else {
      localStorage.removeItem('remembered_username')
    }
    submitSuccess.value = true
    setTimeout(() => {
      router.push(authStore.isAdmin ? '/admin/dashboard' : '/')
    }, 1500)
  } catch (err: any) {
    showError(err?.message || '登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  if (!isRegisterValid.value) {
    showError('请正确填写所有必填项')
    return
  }

  // 管理员注册时验证邀请码
  if (registerForm.role === 'admin' && !registerForm.inviteCode.trim()) {
    showError('注册管理员需要邀请码')
    return
  }

  loading.value = true
  errorMsg.value = ''
  try {
    await authStore.register({
      username: registerForm.username,
      password: registerForm.password,
      email: registerForm.email || undefined,
      role: registerForm.role,
      inviteCode: registerForm.role === 'admin' ? registerForm.inviteCode.trim() : undefined,
    })
    submitSuccess.value = true
    setTimeout(() => {
      router.push(authStore.isAdmin ? '/admin/dashboard' : '/')
    }, 1500)
  } catch (err: any) {
    showError(err?.message || '注册失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function sendVerificationCode() {
  if (!forgotUsername.value) return
  forgotStep.value = 2
  forgotCooldown.value = 60
  const timer = setInterval(() => {
    forgotCooldown.value--
    if (forgotCooldown.value <= 0) {
      clearInterval(timer)
    }
  }, 1000)
}

function verifyCode() {
  if (forgotCode.value === '123456') {
    forgotStep.value = 3
    forgotError.value = ''
  } else {
    forgotError.value = '验证码错误，请输入 123456'
  }
}

async function resetPassword() {
  if (!isForgotPasswordValid.value) {
    forgotError.value = '密码格式不正确或两次输入不一致'
    return
  }

  try {
    const success = await authStore.resetPassword(forgotNewPassword.value)
    if (success) {
      forgotStep.value = 4
    }
  } catch (err: any) {
    forgotError.value = err.message || '重置密码失败'
  }
}

function closeForgotModal() {
  showForgotModal.value = false
  forgotStep.value = 1
  forgotUsername.value = ''
  forgotCode.value = ''
  forgotNewPassword.value = ''
  forgotConfirmPassword.value = ''
  forgotError.value = ''
  forgotCooldown.value = 0
}

onMounted(() => {
  initParticles()
  const remembered = localStorage.getItem('remembered_username')
  if (remembered) {
    loginForm.username = remembered
    rememberMe.value = true
  }
  authStore.checkTokenExpiry()
})

onUnmounted(() => {
  if (animFrameId) cancelAnimationFrame(animFrameId)
})
</script>

<style lang="less" scoped>
@import '../../landing/styles/landing.less';

/* 粒子画布 */
.particle-canvas {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
}

/* 验证错误样式 */
.field-error {
  color: #ef4444;
  font-size: 0.75rem;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.input-error {
  border-color: rgba(239, 68, 68, 0.5) !important;
}

/* 密码强度指示器 */
.password-strength {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.strength-bar {
  flex: 1;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.strength-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease, background 0.3s ease;

  &.weak { background: #ef4444; }
  &.medium { background: #f59e0b; }
  &.strong { background: #22c55e; }
}

.strength-text {
  font-size: 0.75rem;
  font-weight: 500;
  min-width: 24px;

  &.weak { color: #ef4444; }
  &.medium { color: #f59e0b; }
  &.strong { color: #22c55e; }
}

/* 忘记密码链接 */
.forgot-link {
  margin-left: auto;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.5);
  transition: color 0.2s ease;
  background: none;
  border: none;
  cursor: pointer;

  &:hover {
    color: rgba(255, 255, 255, 0.8);
  }
}

/* 动画 */
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-4px); }
  20%, 40%, 60%, 80% { transform: translateX(4px); }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.shake {
  animation: shake 0.5s ease;
}

.btn-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.spinner {
  width: 18px;
  height: 18px;
  animation: spin 1s linear infinite;
}

.btn-success {
  color: #22c55e;
}

.submit-btn.btn-success-state {
  background: #22c55e !important;
  color: #fff !important;
}

/* 模态框 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 24px;
}

.modal-content {
  position: relative;
  width: 100%;
  max-width: 400px;
  border-radius: 24px;
  padding: 32px;
}

.modal-close {
  position: absolute;
  top: 16px;
  right: 16px;
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.5);
  font-size: 1.25rem;
  cursor: pointer;
  transition: color 0.2s ease;

  &:hover {
    color: #fff;
  }
}

.modal-title {
  font-size: 1.5rem;
  font-weight: 600;
  text-align: center;
  margin-bottom: 24px;
}

/* 步骤指示器 */
.step-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  margin-bottom: 32px;
}

.step {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.875rem;
  font-weight: 600;
  transition: all 0.3s ease;

  &.active {
    background: rgba(255, 255, 255, 0.2);
    color: #fff;
  }

  &.done {
    background: #22c55e;
    color: #fff;
  }
}

.step-line {
  width: 40px;
  height: 2px;
  background: rgba(255, 255, 255, 0.1);
  transition: background 0.3s ease;

  &.active {
    background: #22c55e;
  }
}

.forgot-step {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.step-desc {
  text-align: center;
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.9rem;
}

.demo-hint {
  text-align: center;
  color: rgba(255, 255, 255, 0.4);
  font-size: 0.75rem;

  code {
    background: rgba(255, 255, 255, 0.1);
    padding: 2px 8px;
    border-radius: 4px;
    color: #f59e0b;
  }
}

.success-step {
  text-align: center;
}

.success-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: #22c55e;
  color: #fff;
  font-size: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.success-text {
  color: #fff;
  font-size: 1.125rem;
  font-weight: 500;
  margin-bottom: 24px;
}
</style>
