<template>
  <div v-loading="loading">
    <el-page-header @back="$router.back()" content="测试报告" style="margin-bottom: 20px" />
    <template v-if="report">
      <el-row :gutter="20" style="margin-bottom: 16px">
        <el-col :span="24" style="text-align: right">
          <el-button @click="exportReport('json')">导出 JSON</el-button>
          <el-button @click="exportReport('csv')">导出 CSV</el-button>
          <el-button @click="exportReport('html')">导出 HTML</el-button>
        </el-col>
      </el-row>
      <el-row :gutter="20">
        <el-col :span="12">
          <el-card><template #header>任务信息</template>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="任务 ID">{{ report.job_info?.id }}</el-descriptions-item>
              <el-descriptions-item label="名称">{{ report.job_info?.name }}</el-descriptions-item>
              <el-descriptions-item label="类型">{{ report.job_info?.job_type }}</el-descriptions-item>
              <el-descriptions-item label="状态"><el-tag>{{ report.job_info?.status }}</el-tag></el-descriptions-item>
              <el-descriptions-item label="开始">{{ report.job_info?.started_at }}</el-descriptions-item>
              <el-descriptions-item label="结束">{{ report.job_info?.finished_at }}</el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card><template #header>设备信息</template>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="设备">{{ report.device_info?.name }}</el-descriptions-item>
              <el-descriptions-item label="BMC IP">{{ report.device_info?.bmc_ip }}</el-descriptions-item>
              <el-descriptions-item label="型号">{{ report.device_info?.model }}</el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>
      </el-row>
      <el-card style="margin-top: 20px"><template #header>测试结果</template>
        <pre style="font-size: 13px">{{ JSON.stringify(report.results, null, 2) }}</pre>
      </el-card>
    </template>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api'
const route = useRoute()
const report = ref<any>(null)
const loading = ref(true)
onMounted(async () => {
  try { const { data } = await api.get(`/reports/${route.params.id}`); report.value = data }
  finally { loading.value = false }
})
function exportReport(format: string) {
  window.open(`/api/v1/reports/${route.params.id}/export?format=${format}`, '_blank')
}
</script>
