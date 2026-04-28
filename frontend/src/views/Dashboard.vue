<template>
  <div>
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="6" v-for="stat in stats" :key="stat.label">
        <el-card shadow="hover">
          <div style="text-align: center">
            <div style="font-size: 32px; font-weight: bold; color: #409eff">{{ stat.value }}</div>
            <div style="color: #909399; margin-top: 8px">{{ stat.label }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    <el-card>
      <template #header>设备状态分布</template>
      <p style="color: #909399; text-align: center; padding: 40px 0">图表区域（Phase 4 实现 ECharts 集成）</p>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'

const stats = ref([
  { label: '设备总数', value: 0 },
  { label: '就绪', value: 0 },
  { label: '测试中', value: 0 },
  { label: '活跃预约', value: 0 },
])

onMounted(async () => {
  try {
    const { data } = await api.get('/devices/', { params: { size: 1 } })
    stats.value[0].value = data.total
  } catch { /* ignore */ }
  try {
    const { data } = await api.get('/devices/', { params: { state: 'ready', size: 1 } })
    stats.value[1].value = data.total
  } catch { /* ignore */ }
  try {
    const { data } = await api.get('/devices/', { params: { state: 'testing', size: 1 } })
    stats.value[2].value = data.total
  } catch { /* ignore */ }
  try {
    const { data } = await api.get('/reservations/', { params: { size: 1 } })
    stats.value[3].value = data.total
  } catch { /* ignore */ }
})
</script>
