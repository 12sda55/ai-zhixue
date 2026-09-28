<template>
  <div class="landing-page">
    <!-- ════════ SECTION 1 — HERO ════════ -->
    <section class="hero">
      <video
        ref="heroVideo"
        class="hero-video"
        muted
        playsinline
        preload="auto"
        src="https://plugin-assets.open-design.ai/plugins/innovation/hf_20260405_074625_a81f018a-956b-43fb-9aee-4d1508e30e6a-6993b9.mp4"
      ></video>

      <nav class="nav">
        <div class="nav-pill liquid-glass">
          <div class="nav-left">
            <div class="brand">
              <div class="brand-icon">AI</div>
              <span>智学</span>
            </div>
            <div class="nav-links">
              <a href="#about" @click.prevent="scrollTo('about')">关于</a>
              <a href="#philo" @click.prevent="scrollTo('philo')">理念</a>
              <a href="#services" @click.prevent="scrollTo('services')">功能</a>
            </div>
          </div>
          <div class="nav-right">
            <router-link to="/login" class="nav-signup">注册</router-link>
            <router-link to="/login" class="nav-login liquid-glass">登录</router-link>
          </div>
        </div>
      </nav>

      <div class="hero-body">
        <h1 class="hero-h1 serif">学而后 <em class="serif-i">知</em></h1>
        <div class="email-row">
          <div class="email-pill liquid-glass">
            <input type="email" placeholder="输入邮箱，抢先体验" />
            <button class="email-submit" aria-label="提交">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
            </button>
          </div>
        </div>
        <p class="hero-sub">AI 多智能体协同驱动，为每位学习者构建独一无二的成长路径。八维画像精准建模，因材施教触手可及。</p>
        <router-link to="/login" class="manifesto liquid-glass">开始体验</router-link>
      </div>

      <div class="socials">
        <button class="social-btn liquid-glass" aria-label="GitHub">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.36 6.44-6.43 0-1.39-.49-2.65-1.34-3.62.14-.42.58-2.1-.14-4.36 0 0-1.11-.35-3.62 1.39a12.5 12.5 0 0 0-6.68 0C6.14 2.21 5.03 2.56 5.03 2.56c-.72 2.27-.28 3.94-.14 4.36A5.15 5.15 0 0 0 3.55 10c0 5.07 3.29 6.08 6.44 6.43a3.37 3.37 0 0 0-.94 2.61V19"/></svg>
        </button>
        <button class="social-btn liquid-glass" aria-label="邮件">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
        </button>
        <button class="social-btn liquid-glass" aria-label="网站">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
        </button>
      </div>
    </section>

    <!-- ════════ SECTION 2 — ABOUT ════════ -->
    <section class="about" id="about">
      <div class="about-grad"></div>
      <div class="about-inner">
        <p class="eyebrow reveal-sm">关于项目</p>
        <h2 class="about-h2 reveal">
          为 <span class="serif-i" style="color:rgba(255,255,255,0.6)">每一个</span> 学习者
          <br class="hide-mobile" />
          <span class="serif-i" style="color:rgba(255,255,255,0.6)">量身定制成长之路</span>
        </h2>
        <p class="about-body reveal">
          本系统源自中国软件杯大赛课题，支持多领域个性化学习。我们构建了七个 AI 智能体——画像、文档、思维导图、习题、代码、视频与路径——它们协同工作，从对话中理解学习者，生成个性化资源，规划自适应学习路径，并将评估结果反馈回画像模型，形成真正因材施教的闭环。
        </p>
      </div>
    </section>

    <!-- ════════ SECTION 3 — FEATURED VIDEO ════════ -->
    <section class="featured">
      <div class="featured-inner">
        <div class="video-frame reveal-up">
          <video muted autoplay loop playsinline preload="auto"
            src="https://plugin-assets.open-design.ai/plugins/innovation/hf_20260402_054547_9875cfc5-155a-4229-8ec8-b7ba7125cbf8-eee511.mp4"></video>
          <div class="video-grad-t"></div>
          <div class="featured-overlay">
            <div class="approach-card liquid-glass">
              <p class="approach-label">核心方法</p>
              <p class="approach-body">我们相信学习不是流水线——每位学生都有独特的认知节奏、薄弱环节与兴趣偏好。系统以八维画像为起点，让 AI 智能体群协同推理，从「教什么」走向「教谁」与「怎么教」。</p>
            </div>
            <router-link to="/login" class="explore-btn liquid-glass">开始使用</router-link>
          </div>
        </div>
      </div>
    </section>

    <!-- ════════ SECTION 4 — PHILOSOPHY ════════ -->
    <section class="philo" id="philo">
      <div class="philo-inner">
        <h2 class="philo-h2 serif reveal">多智能体 <span class="serif-i" style="color:rgba(255,255,255,0.4)">×</span> 个性化</h2>
        <div class="philo-grid">
          <div class="philo-video reveal-l">
            <video muted autoplay loop playsinline preload="auto"
              src="https://plugin-assets.open-design.ai/plugins/liquid-glass-agency/hf_20260307_083826_e938b29f-a43a-41ec-a153-3d4730578ab8-b7258e.mp4"></video>
          </div>
          <div class="philo-blocks reveal-r">
            <div>
              <p class="philo-label">八维画像建模</p>
              <p class="philo-text">从专业、年级、基础水平、薄弱知识点、学习目标、认知风格、学习节奏到兴趣偏好——八个维度精准刻画学习者画像，为后续资源生成与路径规划提供数据驱动的决策依据。</p>
            </div>
            <div class="divider"></div>
            <div>
              <p class="philo-label">闭环反馈机制</p>
              <p class="philo-text">评估结果实时回写画像，路径自动调优。学习不再是开环推送，而是一个不断进化的自适应系统——每一次练习都在让下一轮推荐更懂你。</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ════════ SECTION 5 — SERVICES ════════ -->
    <section class="services" id="services">
      <div class="services-grad"></div>
      <div class="services-inner">
        <div class="services-head reveal">
          <h2 class="services-h2">核心功能</h2>
          <span class="services-label">智能体服务</span>
        </div>
        <div class="services-grid">
          <div class="scard liquid-glass reveal-up" data-delay="0">
            <div class="scard-media">
              <video muted autoplay loop playsinline preload="auto"
                src="https://plugin-assets.open-design.ai/plugins/innovation/hf_20260314_131748_f2ca2a28-fed7-44c8-b9a9-bd9acdd5ec31-b2a357.mp4"></video>
              <div class="scard-grad"></div>
            </div>
            <div class="scard-body">
              <div class="scard-top">
                <span class="scard-tag">画像</span>
                <span class="scard-arrow liquid-glass">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="7" y1="17" x2="17" y2="7"/><polyline points="7 7 17 7 17 17"/></svg>
                </span>
              </div>
              <h3 class="scard-title serif">智能画像 &amp; 对话</h3>
              <p class="scard-desc">AI 对话驱动画像构建，八维度逐步丰满。实时雷达图可视化，让学习者的能力全景一目了然。</p>
            </div>
          </div>
          <div class="scard liquid-glass reveal-up" data-delay="150">
            <div class="scard-media">
              <video muted autoplay loop playsinline preload="auto"
                src="https://plugin-assets.open-design.ai/plugins/innovation/hf_20260324_151826_c7218672-6e92-402c-9e45-f1e0f454bdc4-c2f128.mp4"></video>
              <div class="scard-grad"></div>
            </div>
            <div class="scard-body">
              <div class="scard-top">
                <span class="scard-tag">路径</span>
                <span class="scard-arrow liquid-glass">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="7" y1="17" x2="17" y2="7"/><polyline points="7 7 17 7 17 17"/></svg>
                </span>
              </div>
              <h3 class="scard-title serif">自适应学习路径</h3>
              <p class="scard-desc">多智能体协同规划，生成个性化学习阶段与资源序列。评估驱动路径调优，始终匹配当前能力水平。</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const heroVideo = ref<HTMLVideoElement | null>(null)
let raf: number | null = null

function animateOpacity(v: HTMLVideoElement, from: number, to: number, dur: number) {
  if (raf) cancelAnimationFrame(raf)
  const start = performance.now()
  function step(now: number) {
    const t = Math.min((now - start) / dur, 1)
    v.style.opacity = (from + (to - from) * t).toFixed(3)
    if (t < 1) raf = requestAnimationFrame(step)
  }
  raf = requestAnimationFrame(step)
}

function initHeroVideo() {
  const v = heroVideo.value
  if (!v) return
  const FADE = 500

  v.addEventListener('canplay', () => {
    v.play().catch(() => {})
    animateOpacity(v, 0, 1, FADE)
  })

  v.addEventListener('timeupdate', () => {
    if (!isNaN(v.duration) && v.duration - v.currentTime <= 0.55) {
      animateOpacity(v, parseFloat(v.style.opacity) || 1, 0, FADE)
    }
  })

  v.addEventListener('ended', () => {
    v.style.opacity = '0'
    setTimeout(() => {
      v.currentTime = 0
      v.play().catch(() => {})
      animateOpacity(v, 0, 1, FADE)
    }, 100)
  })

  if (v.readyState >= 3) {
    v.play().catch(() => {})
    animateOpacity(v, 0, 1, FADE)
  }
}

function initScrollReveal() {
  const items = document.querySelectorAll('.reveal, .reveal-sm, .reveal-l, .reveal-r, .reveal-up')
  if (!('IntersectionObserver' in window)) {
    items.forEach((el) => el.classList.add('in'))
    return
  }
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          const d = parseInt(e.target.getAttribute('data-delay') || '0', 10)
          setTimeout(() => e.target.classList.add('in'), d)
          io.unobserve(e.target)
        }
      })
    },
    { rootMargin: '-100px 0px', threshold: 0.1 },
  )
  items.forEach((el) => io.observe(el))
}

function scrollTo(id: string) {
  const el = document.getElementById(id)
  if (el) el.scrollIntoView({ behavior: 'smooth' })
}

onMounted(() => {
  initHeroVideo()
  initScrollReveal()
})

onUnmounted(() => {
  if (raf) cancelAnimationFrame(raf)
})
</script>

<style lang="less" scoped>
@import '../styles/landing.less';
</style>
