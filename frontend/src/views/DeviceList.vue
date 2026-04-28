<template>
  <div>
    <el-row :gutter="16" style="margin-bottom: 16px" justify="space-between">
      <el-col :span="12">
        <el-input v-model="search" placeholder="搜索设备名称/IP/型号" clearable @clear="fetchDevices" @keyup.enter="fetchDevices" />
      </el-col>
      <el-col :span="4">
        <el-select v-model="stateFilter" placeholder="状态筛选" clearable @change="fetchDevices">
          <el-option v-for="s in states" :key="s" :label="s" :value="s" />
        </el-select>
      </el-col>
      <el-col :span="4" style="text-align: right">
        <el-button type="primary" @click="showAdd = true">添加设备</el-button>
      </el-col>
    </el-row>

    <el-table :data="devices" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="名称" min-width="120">
        <template #default="{ row }">
          <router-link :to="`/devices/${row.id}`" style="color: #409eff; text-decoration: none">{{ row.name }}</router-link>
        </template>
      </el-table-column>
      <el-table-column prop="bmc_ip" label="BMC IP" width="140" />
      <el-table-column prop="bmc_protocol" label="协议" width="90" />
      <el-table-column prop="model" label="型号" width="140" />
      <el-table-column prop="state" label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="stateTagType(row.state)" size="small">{{ row.state }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="location" label="位置" width="120" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="handlePower(row, 'status')">电源状态</el-button>
          <el-dropdown trigger="click" @command="(cmd: string) => handlePower(row, cmd)">
            <el-button size="small">电源控制</el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="on">开机</el-dropdown-item>
                <el-dropdown-item command="off">关机</el-dropdown-item>
                <el-dropdown-item command="cycle">重启</el-dropdown-item>
                <el-dropdown-item command="reset">复位</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
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
      @current-change="fetchDevices"
    />

    <el-dialog v-model="showAdd" title="添加设备" width="500px">
      <el-form :model="addForm" label-width="100px">
        <el-form-item label="名称" required><el-input v-model="addForm.name" /></el-form-item>
        <el-form-item label="BMC IP" required><el-input v-model="addForm.bmc_ip" /></el-form-item>
        <el-form-item label="BMC 用户名" required><el-input v-model="addForm.bmc_username" /></el-form-item>
        <el-form-item label="BMC 密码" required><el-input v-model="addForm.bmc_password" type="password" show-password /></el-form-item>
        <el-form-item label="协议">
          <el-select v-model="addForm.bmc_protocol">
            <el-option label="IPMI" value="ipmi" />
            <el-option label="Redfish" value="redfish" />
          </el-select>
        </el-form-item>
        <el-form-item label="型号"><el-input v-model="addForm.model" /></el-form-item>
        <el-form-item label="位置"><el-input v-model="addForm.location" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" @click="handleAdd" :loading="adding">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const states = ['new', 'commissioning', 'ready', 'reserved', 'deploying', 'testing', 'maintenance', 'offline']
const devices = ref<any[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 20
const search = ref('')
const stateFilter = ref('')
const showAdd = ref(false)
const adding = ref(false)

const addForm = reactive({
  name: '', bmc_ip: '', bmc_username: 'admin', bmc_password: '', bmc_protocol: 'ipmi', model: '', location: '',
})

function stateTagType(state: string) {
  const map: Record<string, string> = {
    ready: 'success', testing: 'warning', reserved: '', offline: 'danger', maintenance: 'info', new: 'info',
  }
  return map[state] || ''
}

async function fetchDevices() {
  loading.value = true
  try {
    const params: any = { page: page.value, size: pageSize }
    if (search.value) params.q = search.value
    if (stateFilter.value) params.state = stateFilter.value
    const { data } = await api.get('/devices/', { params })
    devices.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function handleAdd() {
  adding.value = true
  try {
    await api.post('/devices/', addForm)
    ElMessage.success('设备添加成功')
    showAdd.value = false
    Object.assign(addForm, { name: '', bmc_ip: '', bmc_password: '', model: '', location: '' })
    await fetchDevices()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '添加失败')
  } finally {
    adding.value = false
  }
}

async function handlePower(device: any, action: string) {
  try {
    const { data } = await api.post(`/devices/${device.id}/power`, { action })
    ElMessage.info(data.message)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

onMounted(fetchDevices)
</script>
