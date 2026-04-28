<template>
  <div v-loading="loading">
    <el-page-header @back="$router.push('/devices')" :content="device?.name || ''" style="margin-bottom: 20px" />
    <el-row :gutter="20" v-if="device">
      <el-col :span="12">
        <el-card>
          <template #header>基本信息</template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="名称">{{ device.name }}</el-descriptions-item>
            <el-descriptions-item label="BMC IP">{{ device.bmc_ip }}</el-descriptions-item>
            <el-descriptions-item label="协议">{{ device.bmc_protocol }}</el-descriptions-item>
            <el-descriptions-item label="OS IP">{{ device.os_ip || '-' }}</el-descriptions-item>
            <el-descriptions-item label="MAC">{{ device.mac_address || '-' }}</el-descriptions-item>
            <el-descriptions-item label="型号">{{ device.model || '-' }}</el-descriptions-item>
            <el-descriptions-item label="序列号">{{ device.serial_number || '-' }}</el-descriptions-item>
            <el-descriptions-item label="位置">{{ device.location || '-' }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag>{{ device.state }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>硬件信息</template>
          <pre v-if="device.hardware_info" style="font-size: 13px">{{ JSON.stringify(device.hardware_info, null, 2) }}</pre>
          <p v-else style="color: #909399">暂无硬件信息（执行 Commissioning 后自动采集）</p>
        </el-card>
        <el-card style="margin-top: 20px">
          <template #header>备注</template>
          <p>{{ device.notes || '无' }}</p>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api'

const route = useRoute()
const device = ref<any>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await api.get(`/devices/${route.params.id}`)
    device.value = data
  } finally {
    loading.value = false
  }
})
</script>
