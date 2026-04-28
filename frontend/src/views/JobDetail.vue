<template>
  <div v-loading="loading">
    <el-page-header @back="$router.push('/jobs')" style="margin-bottom: 24px">
      <template #content>
        <span>{{ job?.name || '任务详情' }}</span>
        <el-tag v-if="job" :type="statusTagType(job.status)" size="small" style="margin-left: 12px">
          {{ statusLabel(job.status) }}
        </el-tag>
      </template>
    </el-page-header>

    <template v-if="job">
      <el-row :gutter="24">
        <el-col :span="12">
          <el-descriptions title="基本信息" :column="1" border size="small">
            <el-descriptions-item label="任务 ID">{{ job.id }}</el-descriptions-item>
            <el-descriptions-item label="任务名称">{{ job.name }}</el-descriptions-item>
            <el-descriptions-item label="测试类型">
              <el-tag size="small">{{ typeLabel(job.job_type) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="设备">{{ job.device_name || job.device_id }}</el-descriptions-item>
            <el-descriptions-item label="创建人">{{ job.username || job.user_id }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatTime(job.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="开始时间">{{ job.started_at ? formatTime(job.started_at) : '-' }}</el-descriptions-item>
            <el-descriptions-item label="完成时间">{{ job.finished_at ? formatTime(job.finished_at) : '-' }}</el-descriptions-item>
            <el-descriptions-item v-if="job.error_message" label="错误信息">
              <span style="color: #f56c6c">{{ job.error_message }}</span>
            </el-descriptions-item>
          </el-descriptions>
        </el-col>
        <el-col :span="12">
          <el-descriptions title="测试配置" :column="1" border size="small">
            <el-descriptions-item v-for="(val, key) in (job.config || {})" :key="key" :label="String(key)">
              {{ val }}
            </el-descriptions-item>
          </el-descriptions>

          <el-descriptions v-if="job.result && Object.keys(job.result).length" title="测试结果" :column="1" border size="small" style="margin-top: 16px">
            <el-descriptions-item v-for="(val, key) in flatResult" :key="key" :label="String(key)">
              {{ typeof val === 'object' ? JSON.stringify(val) : val }}
            </el-descriptions-item>
          </el-descriptions>
        </el-col>
      </el-row>

      <div style="margin-top: 16px">
        <el-button v-if="canCancel" type="danger" @click="handleCancel">取消任务</el-button>
      </div>

      <!-- Logs -->
      <el-divider />
      <h3 style="margin-bottom: 12px">执行日志</h3>
      <div ref="logContainer" class="log-container">
        <div v-for="log in logs" :key="log.id" class="log-line" :class="`log-${log.level}`">
          <span class="log-time">{{ formatLogTime(log.timestamp) }}</span>
          <el-tag :type="logTagType(log.level)" size="small" style="margin: 0 8px">{{ log.level }}</el-tag>
          <span>{{ log.message }}</span>
        </div>
        <div v-if="logs.length === 0" style="color: #909399; padding: 12px">暂无日志</div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useJobsStore, type TestJob, type TestJobLog } from '@/stores/jobs'

const route = useRoute()
const router = useRouter()
const store = useJobsStore()

const loading = ref(true)
const job = ref<TestJob | null>(null)
const logs = ref<TestJobLog[]>([])
const logContainer = ref<HTMLElement | null>(null)
let ws: WebSocket | null = null
let pollTimer: number | null = null

const jobId = Number(route.params.id)

const canCancel = computed(() => {
  if (!job.value) return false
  return ['pending', 'queued', 'running', 'collecting'].includes(job.value.status)
})

const flatResult = computed(() => {
  if (!job.value?.result) return {}
  const r = { ...job.value.result }
  // Don't show large arrays inline
  if (Array.isArray(r.cycles) && r.cycles.length > 5) {
    r.cycles = `[${r.cycles.length} cycles]`
  }
  return r
})

function statusLabel(s: string) {
  const map: Record<string, string> = {
    pending: '等待中', queued: '排队中', running: '运行中', collecting: '收集中',
    completed: '已完成', failed: '失败', cancelled: '已取消',
  }
  return map[s] || s
}

function statusTagType(s: string) {
  const map: Record<string, string> = {
    pending: 'info', queued: 'info', running: 'warning', collecting: 'warning',
    completed: 'success', failed: 'danger', cancelled: 'info',
  }
  return map[s] || ''
}

function typeLabel(t: string) {
  const map: Record<string, string> = { stress: '压力测试', stability: '稳定性测试', performance: '性能测试' }
  return map[t] || t
}

function logTagType(level: string) {
  if (level === 'error') return 'danger'
  if (level === 'warning') return 'warning'
  return 'info'
}

function formatTime(t: string) {
  return new Date(t).toLocaleString()
}

function formatLogTime(t: string) {
  return new Date(t).toLocaleTimeString()
}

async function fetchJob() {
  try {
    job.value = await store.fetchJob(jobId)
  } catch {
    ElMessage.error('任务不存在')
    router.push('/jobs')
  }
}

async function fetchLogs() {
  try {
    const data = await store.fetchJobLogs(jobId, { size: 500 })
    logs.value = data.items
    await nextTick()
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  } catch {
    // ignore
  }
}

function connectWebSocket() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${location.host}/api/ws/jobs/${jobId}`
  ws = new WebSocket(wsUrl)

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'status' && job.value) {
        job.value.status = data.status
        if (data.started_at) job.value.started_at = data.started_at
        if (data.finished_at) job.value.finished_at = data.finished_at
        if (data.error_message) job.value.error_message = data.error_message
      }
      if (data.type === 'log') {
        logs.value.push({
          id: Date.now(),
          job_id: jobId,
          level: data.level,
          message: data.message,
          timestamp: data.timestamp,
        })
        nextTick(() => {
          if (logContainer.value) {
            logContainer.value.scrollTop = logContainer.value.scrollHeight
          }
        })
      }
    } catch {
      // ignore parse errors
    }
  }

  ws.onclose = () => {
    // Fallback to polling if WS disconnects and job is still active
    if (job.value && canCancel.value) {
      startPolling()
    }
  }
}

function startPolling() {
  if (pollTimer) return
  pollTimer = window.setInterval(async () => {
    await fetchJob()
    await fetchLogs()
    if (job.value && !canCancel.value) {
      stopPolling()
    }
  }, 5000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function handleCancel() {
  try {
    await store.cancelJob(jobId)
    ElMessage.success('任务已取消')
    await fetchJob()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '取消失败')
  }
}

onMounted(async () => {
  await fetchJob()
  await fetchLogs()
  loading.value = false
  if (job.value && canCancel.value) {
    connectWebSocket()
  }
})

onUnmounted(() => {
  if (ws) {
    ws.close()
    ws = null
  }
  stopPolling()
})
</script>

<style scoped>
.log-container {
  max-height: 400px;
  overflow-y: auto;
  background: #1e1e1e;
  border-radius: 4px;
  padding: 12px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  color: #d4d4d4;
}
.log-line {
  padding: 2px 0;
  line-height: 1.6;
}
.log-time {
  color: #6a9955;
  margin-right: 4px;
}
.log-error { color: #f48771; }
.log-warning { color: #cca700; }
</style>
