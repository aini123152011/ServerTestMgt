<template>
  <div>
    <el-row style="margin-bottom: 16px" justify="end">
      <el-button type="primary" @click="showAdd = true">新建预约</el-button>
    </el-row>

    <el-table :data="reservations" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="device_name" label="设备" width="150" />
      <el-table-column prop="username" label="预约人" width="120" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="expires_at" label="过期时间" width="180">
        <template #default="{ row }">{{ new Date(row.expires_at).toLocaleString() }}</template>
      </el-table-column>
      <el-table-column prop="reason" label="原因" min-width="200" />
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status === 'active'" size="small" type="danger" @click="handleRelease(row.id)">释放</el-button>
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
      @current-change="fetchReservations"
    />

    <el-dialog v-model="showAdd" title="新建预约" width="450px">
      <el-form :model="addForm" label-width="80px">
        <el-form-item label="设备 ID" required><el-input-number v-model="addForm.device_id" :min="1" /></el-form-item>
        <el-form-item label="过期时间" required>
          <el-date-picker v-model="addForm.expires_at" type="datetime" placeholder="选择过期时间" />
        </el-form-item>
        <el-form-item label="原因"><el-input v-model="addForm.reason" type="textarea" /></el-form-item>
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

const reservations = ref<any[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 20
const showAdd = ref(false)

const addForm = reactive({ device_id: 1, expires_at: '', reason: '' })

async function fetchReservations() {
  loading.value = true
  try {
    const { data } = await api.get('/reservations/', { params: { page: page.value, size: pageSize } })
    reservations.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function handleAdd() {
  try {
    await api.post('/reservations/', addForm)
    ElMessage.success('预约成功')
    showAdd.value = false
    await fetchReservations()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '预约失败')
  }
}

async function handleRelease(id: number) {
  try {
    await api.post(`/reservations/${id}/release`)
    ElMessage.success('已释放')
    await fetchReservations()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '释放失败')
  }
}

onMounted(fetchReservations)
</script>
