<template>
  <div class="markdown-renderer" v-html="renderedContent"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

interface Props {
  content: string
}

const props = defineProps<Props>()

const renderedContent = computed(() => {
  try {
    return marked.parse(props.content)
  } catch (error) {
    console.error('Markdown 渲染失败:', error)
    return props.content
  }
})
</script>

<style scoped>
.markdown-renderer {
  font-size: 14px;
  line-height: 1.5;
}

.markdown-renderer :deep(h1),
.markdown-renderer :deep(h2),
.markdown-renderer :deep(h3) {
  margin-top: 12px;
  margin-bottom: 6px;
  font-weight: 600;
  color: var(--n-text-color);
}

.markdown-renderer :deep(h1) {
  font-size: 1.4em;
}

.markdown-renderer :deep(h2) {
  font-size: 1.2em;
}

.markdown-renderer :deep(h3) {
  font-size: 1em;
}

.markdown-renderer :deep(ul),
.markdown-renderer :deep(ol) {
  padding-left: 20px;
  margin: 4px 0;
}

.markdown-renderer :deep(li) {
  margin: 2px 0;
  line-height: 1.5;
}

.markdown-renderer :deep(code) {
  background: var(--n-color-modal);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', Consolas, monospace;
  font-size: 0.9em;
  color: var(--n-text-color);
}

.markdown-renderer :deep(pre) {
  background: var(--n-color-modal);
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 6px 0;
  line-height: 1.4;
}

.markdown-renderer :deep(pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
}

.markdown-renderer :deep(p) {
  margin: 4px 0;
  line-height: 1.5;
}

.markdown-renderer :deep(strong) {
  font-weight: 600;
  color: var(--n-text-color);
}

.markdown-renderer :deep(em) {
  font-style: italic;
}

.markdown-renderer :deep(blockquote) {
  border-left: 4px solid var(--n-border-color);
  padding-left: 12px;
  margin: 6px 0;
  color: var(--n-text-color-placeholder);
}
</style>