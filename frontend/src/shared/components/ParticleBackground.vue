<template>
  <canvas ref="canvasRef" class="particle-bg" />
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const canvasRef = ref<HTMLCanvasElement | null>(null)
let animFrameId = 0

onMounted(() => {
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

  const PARTICLE_COUNT = 200
  const GATHER_RADIUS = 180
  const GATHER_FORCE = 0.04
  const DISPERSE_FORCE = 0.06
  const FRICTION = 0.96
  const FLOAT_SPEED = 0.3

  const COLORS = [
    'rgba(37,99,235,0.35)',
    'rgba(59,130,246,0.3)',
    'rgba(6,182,212,0.3)',
    'rgba(14,165,233,0.25)',
    'rgba(99,102,241,0.25)',
  ]

  class Particle {
    x: number; y: number; baseVx: number; baseVy: number
    vx: number; vy: number; r: number; color: string
    phase: number; phaseSpeed: number; amplitude: number

    constructor() {
      this.x = Math.random() * W
      this.y = Math.random() * H
      this.baseVx = (Math.random() - 0.5) * FLOAT_SPEED
      this.baseVy = (Math.random() - 0.5) * FLOAT_SPEED
      this.vx = this.baseVx
      this.vy = this.baseVy
      this.r = 2 + Math.random() * 3
      this.color = COLORS[Math.floor(Math.random() * COLORS.length)]
      this.phase = Math.random() * Math.PI * 2
      this.phaseSpeed = 0.005 + Math.random() * 0.01
      this.amplitude = 0.3 + Math.random() * 0.5
    }

    update(mouse: any, isPressed: boolean) {
      this.phase += this.phaseSpeed
      const oscX = Math.sin(this.phase) * this.amplitude
      const oscY = Math.cos(this.phase * 0.7) * this.amplitude

      if (isPressed && mouse.x !== null) {
        const dx = mouse.x - this.x
        const dy = mouse.y - this.y
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < GATHER_RADIUS * 2.5) {
          const strength = GATHER_FORCE * (1 - dist / (GATHER_RADIUS * 2.5))
          this.vx += dx * strength
          this.vy += dy * strength
        }
      } else if (mouse.justReleased) {
        const dx = this.x - mouse.releaseX
        const dy = this.y - mouse.releaseY
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < GATHER_RADIUS * 2) {
          const strength = DISPERSE_FORCE * (1 - dist / (GATHER_RADIUS * 2))
          const angle = Math.atan2(dy, dx)
          this.vx += Math.cos(angle) * strength * 30
          this.vy += Math.sin(angle) * strength * 30
        }
      }

      this.vx *= FRICTION
      this.vy *= FRICTION
      this.vx += (this.baseVx - this.vx) * 0.01
      this.vy += (this.baseVy - this.vy) * 0.01
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
  const mouse: any = { x: null, y: null, justReleased: false, releaseX: null, releaseY: null }
  let isPressed = false

  const drawConnections = () => {
    const maxDist = 100
    const cellSize = maxDist
    const grid: Record<string, number[]> = {}
    for (let i = 0; i < particles.length; i++) {
      const cx = Math.floor(particles[i].x / cellSize)
      const cy = Math.floor(particles[i].y / cellSize)
      const key = cx + ',' + cy
      if (!grid[key]) grid[key] = []
      grid[key].push(i)
    }
    for (const key in grid) {
      const [cx, cy] = key.split(',').map(Number)
      const cell = grid[key]
      for (let dx = 0; dx <= 1; dx++) {
        for (let dy = -1; dy <= 1; dy++) {
          if (dx === 0 && dy < 0) continue
          const nKey = (cx + dx) + ',' + (cy + dy)
          const neighbor = grid[nKey]
          if (!neighbor) continue
          const sameCell = dx === 0 && dy === 0
          for (let i = 0; i < cell.length; i++) {
            const startJ = sameCell ? i + 1 : 0
            for (let j = startJ; j < neighbor.length; j++) {
              const a = particles[cell[i]]
              const b = particles[neighbor[j]]
              const ddx = a.x - b.x
              const ddy = a.y - b.y
              const dist = Math.sqrt(ddx * ddx + ddy * ddy)
              if (dist < maxDist) {
                const alpha = (1 - dist / maxDist) * 0.1
                ctx.beginPath()
                ctx.moveTo(a.x, a.y)
                ctx.lineTo(b.x, b.y)
                ctx.strokeStyle = `rgba(37,99,235,${alpha})`
                ctx.lineWidth = 0.5
                ctx.stroke()
              }
            }
          }
        }
      }
    }
  }

  const drawGatherEffect = () => {
    if (isPressed && mouse.x !== null) {
      const gradient = ctx.createRadialGradient(mouse.x, mouse.y, 0, mouse.x, mouse.y, GATHER_RADIUS)
      gradient.addColorStop(0, 'rgba(37,99,235,0.06)')
      gradient.addColorStop(0.5, 'rgba(6,182,212,0.03)')
      gradient.addColorStop(1, 'rgba(37,99,235,0)')
      ctx.beginPath()
      ctx.arc(mouse.x, mouse.y, GATHER_RADIUS, 0, Math.PI * 2)
      ctx.fillStyle = gradient
      ctx.fill()
    }
  }

  const animate = () => {
    ctx.clearRect(0, 0, W, H)
    drawGatherEffect()
    drawConnections()
    particles.forEach(p => { p.update(mouse, isPressed); p.draw(ctx) })
    if (mouse.justReleased) mouse.justReleased = false
    animFrameId = requestAnimationFrame(animate)
  }

  const onMouseDown = (e: MouseEvent) => { isPressed = true; mouse.x = e.clientX; mouse.y = e.clientY }
  const onMouseMove = (e: MouseEvent) => { if (isPressed) { mouse.x = e.clientX; mouse.y = e.clientY } }
  const onMouseUp = (e: MouseEvent) => { isPressed = false; mouse.justReleased = true; mouse.releaseX = e.clientX; mouse.releaseY = e.clientY }
  const onTouchStart = (e: TouchEvent) => { isPressed = true; mouse.x = e.touches[0].clientX; mouse.y = e.touches[0].clientY }
  const onTouchMove = (e: TouchEvent) => { if (isPressed) { mouse.x = e.touches[0].clientX; mouse.y = e.touches[0].clientY } }
  const onTouchEnd = () => { isPressed = false; mouse.justReleased = true; mouse.releaseX = mouse.x; mouse.releaseY = mouse.y }

  document.addEventListener('mousedown', onMouseDown)
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
  document.addEventListener('touchstart', onTouchStart, { passive: true })
  document.addEventListener('touchmove', onTouchMove, { passive: true })
  document.addEventListener('touchend', onTouchEnd)

  animate()
})

onUnmounted(() => {
  if (animFrameId) cancelAnimationFrame(animFrameId)
})
</script>

<style scoped>
.particle-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}
</style>