<template>
  <div>
    <el-row :gutter="16" style="margin-bottom: 16px" justify="space-between">
      <el-col :span="6">
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable @change="fetchJobs">
          <el-option v-for="s in statuses" :key="s" :label="statusLabel(s)" :value="s" />
        </el-select>
      </el-col>
      <el-col :span="6">
        <el-select v-model="typeFilter" placeholder="类型筛选" clearable @change="fetchJobs">
          <el-option label="压力测试" value="stress" />
          <el-option label="稳定性测试" value="stability" />
          <el-option label="性能测试" value="performance" />
        </el-select>
      </el-col>
      <el-col :span="4" style="text-align: right">
        <el-button type="primary" @click="$router.push('/jobs/create')">创建任务</el-button>
      </el-col>
    </el-row>

    <el-table :data="jobs" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="任务名称" min-width="160">
        <template #default="{ row }">
          <router-link :to="`/jobs/${row.id}`" style="color: #409eff; text-decoration: none">{{ row.name }}</router-link>
        </template>
      </el-table-column>
      <el-table-column prop="device_name" label="设备" width="130" />
      <el-table-column prop="job_type" label="类型" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="typeTagType(row.job_type)">{{ typeLabel(row.job_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="110">
        <template #default="{ row }">
          <el-tag size="small" :type="statusTagType(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="username" label="创建人" width="100" />
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column prop="finished_at" label="完成时间" width="170">
        <template #default="{ row }">{{ row.finished_at ? formatTime(row.finished_at) : '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button v-if="canCancel(row.status)" size="small" type="danger" @click="handleCancel(row.id)">取消</el-button>
          <el-button size="small" @click="$router.push(`/jobs/${row.id}`)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="total > pageSize"
      style="margin-top: 16px; justify-content: center"
      layout="total, prev, pager, next"
      :total="total"
      :page-size="pageSize"
      v-model:current-page="page"
      @current-change="fetchJobs"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useJobsStore } from '@/stores/jobs'

const store = useJobsStore()
const jobs = ref<any[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 20
const statusFilter = ref('')
const typeFilter = ref('')

const statuses = ['pending', 'queued', 'running', 'collecting', 'completed', 'failed', 'cancelled']

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

function typeTagType(t: string) {
  const map: Record<string, string> = { stress: 'danger', stability: 'warning', performance: '' }
  return map[t] || ''
}

function canCancel(status: string) {
  return ['pending', 'queued', 'running', 'collecting'].includes(status)
}

function formatTime(t: string) {
  return new Date(t).toLocaleString()
}

async function fetchJobs() {
  loading.value = true
  try {
    const params: any = { page: page.value, size: pageSize }
    if (statusFilter.value) params.status_filter = statusFilter.value
    if (typeFilter.value) params.job_type = typeFilter.value
    const data = await store.fetchJobs(params)
    jobs.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function handleCancel(id: number) {
  try {
    await store.cancelJob(id)
    ElMessage.success('任务已取消')
    await fetchJobs()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '取消失败')
  }
}

onMounted(fetchJobs)
</script>
