<template>
  <div>
    <el-row :gutter="16" style="margin-bottom: 16px" justify="space-between">
      <el-col :span="8"><h3 style="margin: 0">PXE 装机</h3></el-col>
      <el-col :span="4" style="text-align: right">
        <el-button type="primary" @click="showAdd = true">新建装机</el-button>
      </el-col>
    </el-row>
    <el-table :data="jobs" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="device_name" label="设备" width="140" />
      <el-table-column prop="os_profile" label="OS 配置" width="140" />
      <el-table-column prop="username" label="操作人" width="100" />
      <el-table-column prop="status" label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'" size="small">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="showAdd" title="新建装机任务" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="设备 ID" required><el-input-number v-model="form.device_id" :min="1" /></el-form-item>
        <el-form-item label="OS 配置" required>
          <el-select v-model="form.os_profile">
            <el-option v-for="p in profiles" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" @click="handleAdd">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'
const jobs = ref<any[]>([])
const profiles = ref<any[]>([])
const loading = ref(false)
const showAdd = ref(false)
const form = reactive({ device_id: 1, os_profile: 'rhel9' })
async function fetchJobs() {
  loading.value = true
  try { const { data } = await api.get('/provision/'); jobs.value = data.items } finally { loading.value = false }
}
async function fetchProfiles() {
  try { const { data } = await api.get('/provision/profiles'); profiles.value = data } catch {}
}
async function handleAdd() {
  try { await api.post('/provision/', form); ElMessage.success('装机任务已创建'); showAdd.value = false; await fetchJobs() }
  catch (e: any) { ElMessage.error(e.response?.data?.detail || '创建失败') }
}
onMounted(() => { fetchJobs(); fetchProfiles() })
</script>
