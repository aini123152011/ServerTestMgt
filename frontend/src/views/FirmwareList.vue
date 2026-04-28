<template>
  <div>
    <el-row :gutter="16" style="margin-bottom: 16px" justify="space-between">
      <el-col :span="8"><h3 style="margin: 0">固件升级</h3></el-col>
      <el-col :span="4" style="text-align: right">
        <el-button type="primary" @click="showAdd = true">固件升级</el-button>
      </el-col>
    </el-row>
    <el-table :data="jobs" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="device_name" label="设备" width="140" />
      <el-table-column prop="component" label="组件" width="100" />
      <el-table-column prop="current_version" label="当前版本" width="120" />
      <el-table-column prop="target_version" label="目标版本" width="120" />
      <el-table-column prop="status" label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'" size="small">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="showAdd" title="固件升级" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="设备 ID" required><el-input-number v-model="form.device_id" :min="1" /></el-form-item>
        <el-form-item label="组件" required><el-input v-model="form.component" placeholder="BMC / BIOS / CPLD" /></el-form-item>
        <el-form-item label="固件 URL" required><el-input v-model="form.image_url" placeholder="http://fileserver/firmware.bin" /></el-form-item>
        <el-form-item label="目标版本"><el-input v-model="form.target_version" /></el-form-item>
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
const loading = ref(false)
const showAdd = ref(false)
const form = reactive({ device_id: 1, component: 'BMC', image_url: '', target_version: '' })
async function fetchJobs() {
  loading.value = true
  try { const { data } = await api.get('/firmware/jobs'); jobs.value = data.items } finally { loading.value = false }
}
async function handleAdd() {
  try { await api.post('/firmware/upgrade', form); ElMessage.success('固件升级任务已创建'); showAdd.value = false; await fetchJobs() }
  catch (e: any) { ElMessage.error(e.response?.data?.detail || '创建失败') }
}
onMounted(fetchJobs)
</script>
