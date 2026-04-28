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
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="12">
        <el-card><template #header>设备状态分布</template>
          <v-chart :option="deviceChartOption" style="height: 300px" autoresize />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card><template #header>测试结果统计</template>
          <v-chart :option="jobChartOption" style="height: 300px" autoresize />
        </el-card>
      </el-col>
    </el-row>
    <el-card>
      <template #header>最近测试任务</template>
      <el-table :data="recentJobs" stripe size="small">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="job_type" label="类型" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { PieChart, BarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import api from '@/api'

use([PieChart, BarChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer])

const stats = ref([
  { label: '设备总数', value: 0 },
  { label: '就绪', value: 0 },
  { label: '测试中', value: 0 },
  { label: '活跃预约', value: 0 },
])

const deviceStates = ref<Record<string, number>>({})
const jobSummary = ref<any>({})
const recentJobs = ref<any[]>([])

const deviceChartOption = computed(() => ({
  tooltip: { trigger: 'item' },
  series: [{
    type: 'pie', radius: ['40%', '70%'],
    data: Object.entries(deviceStates.value).map(([name, value]) => ({ name, value })),
  }],
}))

const jobChartOption = computed(() => ({
  tooltip: {},
  xAxis: { type: 'category', data: Object.keys(jobSummary.value.by_type || {}) },
  yAxis: { type: 'value' },
  series: [{
    type: 'bar', data: Object.values(jobSummary.value.by_type || {}),
    itemStyle: { color: '#409eff' },
  }],
}))

onMounted(async () => {
  const fetches = [
    api.get('/devices/', { params: { size: 1 } }).then(r => { stats.value[0].value = r.data.total }).catch(() => {}),
    api.get('/devices/', { params: { state: 'ready', size: 1 } }).then(r => { stats.value[1].value = r.data.total }).catch(() => {}),
    api.get('/devices/', { params: { state: 'testing', size: 1 } }).then(r => { stats.value[2].value = r.data.total }).catch(() => {}),
    api.get('/reservations/', { params: { size: 1 } }).then(r => { stats.value[3].value = r.data.total }).catch(() => {}),
    api.get('/jobs/', { params: { size: 10 } }).then(r => { recentJobs.value = r.data.items }).catch(() => {}),
    api.get('/reports/summary').then(r => { jobSummary.value = r.data }).catch(() => {}),
  ]
  for (const state of ['new', 'ready', 'reserved', 'testing', 'deploying', 'maintenance', 'offline']) {
    fetches.push(
      api.get('/devices/', { params: { state, size: 1 } }).then(r => { deviceStates.value[state] = r.data.total }).catch(() => {})
    )
  }
  await Promise.all(fetches)
})
</script>
