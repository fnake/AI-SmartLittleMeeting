<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import {
  ChatLineRound,
  EditPen,
  Plus,
  Position,
  User,
  VideoPause,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { ApiRequestError, chatStream, clearToken, deleteTopic, fetchTopicHistory, listTopics } from '@/api'
import type { Topic } from '@/api'
import { useAuth } from '@/composables/useAuth'
import LoginDialog from '@/components/LoginDialog.vue'

interface ChatMessage {
  role: 'user' | 'ai'
  content: string
}

const { userInfo, refreshMe, signOut } = useAuth()

const topics = ref<Topic[]>([])
const activeTopicId = ref<number | null>(null)
const messages = ref<ChatMessage[]>([])
const draft = ref('')
const sending = ref(false)
const historyLoading = ref(false)
const loginDialogVisible = ref(false)
const scrollRef = ref<InstanceType<typeof import('element-plus')['ElScrollbar']>>()
let abortController: AbortController | null = null

const recommends = [
  '用一句话介绍你自己',
  '帮我制定一份 Python 学习计划',
  '解释一下什么是装饰器',
  '写一首关于秋天的短诗',
]

const activeTopic = computed<Topic | null>(() => {
  const id = activeTopicId.value
  if (id === null) return null
  return topics.value.find((t) => t.id === id) ?? null
})

const userLabel = computed(() => {
  const info = userInfo.value
  if (info === null) return ''
  return info.is_guest === 1 ? `游客 ${info.user_id}` : (info.phone ?? `用户 ${info.user_id}`)
})

async function scrollBottom(): Promise<void> {
  await nextTick()
  scrollRef.value?.setScrollTop(99999999)
}

function handleApiError(error: unknown): void {
  if (error instanceof ApiRequestError) {
    if (error.status === 401) {
      clearToken()
      userInfo.value = null
      loginDialogVisible.value = true
      return
    }
    ElMessage.error(error.message === '' ? '请求失败' : error.message)
    return
  }
  ElMessage.error('发生未知错误')
}

async function loadTopics(): Promise<void> {
  try {
    const res = await listTopics()
    topics.value = res.topics
  } catch (error) {
    handleApiError(error)
  }
}

function startNewChat(): void {
  activeTopicId.value = null
  messages.value = []
}

async function openTopic(topic: Topic): Promise<void> {
  activeTopicId.value = topic.id
  messages.value = []
  historyLoading.value = true
  try {
    const history = await fetchTopicHistory(topic.id)
    if (activeTopicId.value !== topic.id) return
    messages.value = history
  } catch (error) {
    if (activeTopicId.value === topic.id) handleApiError(error)
  } finally {
    if (activeTopicId.value === topic.id) historyLoading.value = false
    scrollBottom()
  }
}

async function removeTopic(topic: Topic): Promise<void> {
  try {
    await deleteTopic(topic.id)
    topics.value = topics.value.filter((t) => t.id !== topic.id)
    if (activeTopicId.value === topic.id) startNewChat()
    ElMessage.success('话题已删除')
  } catch (error) {
    handleApiError(error)
  }
}

function applyRecommend(text: string): void {
  draft.value = text
}

async function sendMessage(): Promise<void> {
  const text = draft.value.trim()
  if (text === '' || sending.value) return
  draft.value = ''
  messages.value.push({ role: 'user', content: text })
  messages.value.push({ role: 'ai', content: '' })
  // 关键：从 reactive 数组取代理引用，直接改原始对象不会触发视图更新
  const aiMsg = messages.value[messages.value.length - 1]
  if (aiMsg === undefined) return
  sending.value = true
  abortController = new AbortController()
  scrollBottom()
  try {
    const result = await chatStream(text, activeTopicId.value ?? undefined, {
      signal: abortController.signal,
      onDelta: (chunk) => {
        aiMsg.content += chunk
        scrollBottom()
      },
    })
    if (result.topicId !== null && activeTopicId.value === null) {
      activeTopicId.value = result.topicId
    }
    await loadTopics()
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      if (aiMsg.content === '') aiMsg.content = '（已停止生成）'
    } else {
      handleApiError(error)
      if (aiMsg.content === '') aiMsg.content = '（回复失败，请重试）'
    }
  } finally {
    sending.value = false
    abortController = null
    scrollBottom()
  }
}

function stopGenerating(): void {
  abortController?.abort()
}

function onEnter(event: KeyboardEvent): void {
  if (event.isComposing) return
  event.preventDefault()
  sendMessage()
}

async function onLoginSuccess(): Promise<void> {
  await refreshMe().catch(() => undefined)
  await loadTopics()
}

async function onLogout(): Promise<void> {
  await signOut()
  topics.value = []
  startNewChat()
}

onMounted(() => {
  void refreshMe().catch(() => undefined)
  void loadTopics()
})
</script>

<template>
  <el-container class="layout">
    <!-- ===== 左侧栏 ===== -->
    <el-aside width="264px" class="sidebar">
      <div class="brand">小会</div>

      <div class="menu-item" @click="startNewChat">
        <el-icon :size="18"><EditPen /></el-icon>
        <span>新对话</span>
      </div>

      <div class="section-label">最近</div>
      <el-scrollbar class="topic-scroll">
        <div v-if="topics.length === 0" class="topic-empty">暂无话题</div>
        <div
          v-for="t in topics"
          :key="t.id"
          class="topic-item"
          :class="{ active: t.id === activeTopicId }"
          @click="openTopic(t)"
        >
          <el-icon :size="16" class="topic-icon"><ChatLineRound /></el-icon>
          <span class="topic-name">{{ t.title }}</span>
          <el-popconfirm
            title="删除该话题及其全部记忆？"
            confirm-button-text="删除"
            cancel-button-text="取消"
            width="200"
            @confirm="removeTopic(t)"
          >
            <template #reference>
              <el-button class="topic-del" size="small" text circle>&times;</el-button>
            </template>
          </el-popconfirm>
        </div>
      </el-scrollbar>

      <!-- 左下角：登录按钮 / 用户信息 -->
      <div class="sidebar-foot">
        <button v-if="userInfo === null" class="login-btn" @click="loginDialogVisible = true">
          登录
        </button>
        <div v-else class="user-box">
          <el-icon :size="16"><User /></el-icon>
          <span class="user-name">{{ userLabel }}</span>
          <el-button link type="danger" size="small" @click="onLogout">退出</el-button>
        </div>
      </div>
    </el-aside>

    <!-- ===== 主区域 ===== -->
    <el-container class="chat">
      <el-header height="52px" class="topbar">
        <span class="topbar-title">{{ activeTopic?.title ?? '' }}</span>
      </el-header>

      <el-main v-loading="historyLoading" element-loading-text="加载历史记录…" class="chat-main">
        <!-- 欢迎态 -->
        <div v-if="messages.length === 0" class="welcome">
          <h1 class="welcome-title">有什么我能帮你的吗？</h1>
          <div class="recommends">
            <div class="recommends-label">为你推荐</div>
            <button
              v-for="q in recommends"
              :key="q"
              class="rec-chip"
              @click="applyRecommend(q)"
            >
              {{ q }}
            </button>
          </div>
        </div>

        <!-- 会话态：历史消息与实时回复使用完全相同的渲染 -->
        <el-scrollbar v-else ref="scrollRef" class="msg-scroll">
          <TransitionGroup name="msg" tag="div" class="msg-list">
            <div
              v-for="(m, i) in messages"
              :key="i"
              class="msg"
              :class="[m.role, { streaming: sending && m.role === 'ai' && i === messages.length - 1 }]"
            >
              <div v-if="m.role === 'user'" class="bubble">{{ m.content }}</div>
              <div v-else class="ai-text">{{ m.content }}</div>
            </div>
          </TransitionGroup>
        </el-scrollbar>
      </el-main>

      <!-- 底部输入卡 -->
      <div class="composer">
        <div class="input-card">
          <el-input
            v-model="draft"
            type="textarea"
            :autosize="{ minRows: 1, maxRows: 6 }"
            placeholder="发消息…"
            resize="none"
            class="composer-input"
            @keydown.enter="onEnter"
          />
          <div class="input-row">
            <el-tooltip content="新对话" placement="top">
              <el-button :icon="Plus" circle text @click="startNewChat" />
            </el-tooltip>
            <div class="flex-spacer" />
            <el-button
              v-if="!sending"
              type="primary"
              :icon="Position"
              circle
              class="send-btn"
              @click="sendMessage"
            />
            <el-button
              v-else
              type="warning"
              :icon="VideoPause"
              circle
              class="send-btn"
              @click="stopGenerating"
            />
          </div>
        </div>
      </div>
    </el-container>

    <!-- 登录弹窗（Element Plus 样式） -->
    <LoginDialog v-model="loginDialogVisible" @success="onLoginSuccess" />
  </el-container>
</template>

<style scoped>
.layout {
  height: 100vh;
  background: #fff;
}

/* ---------- 侧栏 ---------- */
.sidebar {
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--el-border-color-lighter);
  background: #fff;
  padding: 0 12px;
}

.brand {
  padding: 20px 12px 18px;
  font-size: 20px;
  font-weight: 700;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 12px;
  border-radius: 10px;
  font-size: 15px;
  cursor: pointer;
  color: var(--el-text-color-primary);
}

.menu-item:hover {
  background: var(--el-fill-color-light);
}

.section-label {
  padding: 18px 12px 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.topic-scroll {
  flex: 1;
  min-height: 0;
}

.topic-empty {
  padding: 8px 12px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.topic-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.topic-item:hover {
  background: var(--el-fill-color-light);
}

.topic-item.active {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}

.topic-icon {
  flex-shrink: 0;
}

.topic-name {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.topic-del {
  visibility: hidden;
  color: var(--el-text-color-secondary);
}

.topic-item:hover .topic-del {
  visibility: visible;
}

.sidebar-foot {
  padding: 14px 4px 16px;
}

.login-btn {
  width: 100%;
  height: 44px;
  border: none;
  border-radius: 24px;
  background: #1a1a1a;
  color: #fff;
  font-size: 15px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.login-btn:hover {
  opacity: 0.82;
}

.user-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 12px;
  background: var(--el-fill-color-light);
  font-size: 14px;
}

.user-name {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ---------- 主区域 ---------- */
.chat {
  min-width: 0;
}

.topbar {
  -webkit-app-region: drag;
  display: flex;
  align-items: center;
  justify-content: center;
}

.topbar-title {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 60%;
}

.chat-main {
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 0;
}

/* 欢迎态 */
.welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding-bottom: 10vh;
}

.welcome-title {
  margin: 0 0 40px;
  font-size: 32px;
  font-weight: 700;
  color: #111;
}

.recommends {
  width: min(560px, 86%);
}

.recommends-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin: 0 0 12px 4px;
}

.rec-chip {
  display: block;
  width: 100%;
  text-align: left;
  padding: 14px 18px;
  margin-bottom: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 14px;
  background: #fff;
  font-size: 14px;
  color: var(--el-text-color-primary);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.rec-chip:hover {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-5);
}

/* ---------- 消息区：历史与实时回复共用 ---------- */
.msg-scroll {
  flex: 1;
  min-height: 0;
}

.msg-list {
  max-width: 820px;
  margin: 0 auto;
  padding: 12px 24px 24px;
}

/* 消息样式见通用样式：src/styles/chat.css */

/* ---------- 底部输入卡 ---------- */
.composer {
  padding: 8px 24px 22px;
}

.input-card {
  max-width: 820px;
  margin: 0 auto;
  border: 1px solid var(--el-border-color);
  border-radius: 22px;
  background: #fff;
  padding: 6px 10px 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
}

.input-card:focus-within {
  border-color: var(--el-color-primary-light-5);
}

.composer-input :deep(.el-textarea__inner) {
  border: none;
  box-shadow: none;
  background: transparent;
  padding: 10px 10px 2px;
  font-size: 15px;
}

.input-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 2px 4px 0;
}

.flex-spacer {
  flex: 1;
}

.send-btn {
  width: 40px;
  height: 40px;
}
</style>
