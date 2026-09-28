<template>
  <div class="markdown-renderer" v-html="renderedHtml"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import hljs from 'highlight.js'
import 'highlight.js/styles/atom-one-dark.css'

const props = defineProps<{ content: string }>()

const md: MarkdownIt = new MarkdownIt({
  html: true,
  linkify: true,
  highlight(str: string, lang: string): string {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return `<pre class="hljs"><code>${hljs.highlight(str, { language: lang }).value}</code></pre>`
      } catch { /* fallback */ }
    }
    return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`
  },
})

// DOMPurify 配置：允许代码块所需的标签，但过滤危险标签
const purifyConfig = {
  ALLOWED_TAGS: [
    'p', 'br', 'strong', 'em', 'u', 's', 'code', 'pre', 'span',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'blockquote',
    'a', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'img', 'hr', 'div'
  ],
  ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class', 'id', 'target', 'rel'],
  ALLOW_DATA_ATTR: false,
}

const renderedHtml = computed(() => {
  const raw = md.render(props.content)
  return DOMPurify.sanitize(raw, purifyConfig) as string
})
</script>

<style lang="less" scoped>
.markdown-renderer {
  color: #1F1B2D;
  font-size: 14px;
  line-height: 1.8;
  word-break: break-word;

  :deep(h1), :deep(h2), :deep(h3), :deep(h4) {
    color: #1F1B2D;
    margin: 12px 0 8px;
    font-weight: 600;
  }
  :deep(h1) { font-size: 18px; }
  :deep(h2) { font-size: 16px; }
  :deep(h3) { font-size: 14px; }

  :deep(p) { 
    margin: 6px 0;
    color: #1F1B2D;
  }

  :deep(code) {
    background: #E8E7ED;
    color: #1F1B2D;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 13px;
    font-family: 'Cascadia Code', Consolas, monospace;
    border: 1px solid #D8D6DE;
  }

  :deep(pre) {
    background: #F0EFF5;
    border-radius: 8px;
    padding: 12px 14px;
    margin: 8px 0;
    overflow-x: auto;
    border: 1px solid #D8D6DE;

    code {
      background: none;
      padding: 0;
      color: #1F1B2D;
      border: none;
    }
  }

  :deep(table) {
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0;

    th, td {
      border: 1px solid #D8D6DE;
      padding: 8px 12px;
      text-align: left;
      color: #1F1B2D;
    }
    th {
      background: #F0EFF5;
      color: #1F1B2D;
      font-weight: 600;
    }
    td {
      color: #1F1B2D;
    }
    tr:hover td {
      background: #F8F7FA;
    }
  }

  :deep(ul), :deep(ol) {
    padding-left: 24px;
    margin: 8px 0;
  }
  :deep(li) {
    margin: 4px 0;
    color: #1F1B2D;
    font-size: 14px;
    line-height: 1.8;
  }

  :deep(blockquote) {
    border-left: 3px solid #00CFE8;
    padding: 8px 14px;
    margin: 8px 0;
    background: rgba(0, 207, 232, 0.06);
    border-radius: 0 8px 8px 0;
    color: #1F1B2D;
  }

  :deep(a) {
    color: #00CFE8;
    text-decoration: underline;
    font-weight: 500;
  }

  :deep(strong) {
    color: #1F1B2D;
    font-weight: 700;
    background: rgba(0, 207, 232, 0.12);
    padding: 1px 5px;
    border-radius: 3px;
  }

  :deep(em) {
    color: #1F1B2D;
    font-style: italic;
    font-weight: 500;
  }
}
</style>