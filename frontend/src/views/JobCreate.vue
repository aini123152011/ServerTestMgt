<template>
  <div>
    <el-page-header @back="$router.push('/jobs')" content="创建测试任务" style="margin-bottom: 24px" />

    <el-form :model="form" label-width="120px" style="max-width: 650px">
      <el-form-item label="任务名称" required>
        <el-input v-model="form.name" placeholder="例如: CPU压力测试-Server01" />
      </el-form-item>

      <el-form-item label="目标设备" required>
        <el-select v-model="form.device_id" filterable placeholder="选择设备" style="width: 100%">
          <el-option v-for="d in devices" :key="d.id" :label="`${d.name} (${d.bmc_ip})`" :value="d.id" />
        </el-select>
      </el-form-item>

      <el-form-item label="测试类型" required>
        <el-radio-group v-model="form.job_type" @change="onTypeChange">
          <el-radio-button value="stress">压力测试</el-radio-button>
          <el-radio-button value="stability">稳定性测试</el-radio-button>
          <el-radio-button value="performance">性能测试</el-radio-button>
        </el-radio-group>
      </el-form-item>

      <!-- Stress config -->
      <template v-if="form.job_type === 'stress'">
        <el-divider content-position="left">压力测试配置</el-divider>
        <el-form-item label="测试工具">
          <el-select v-model="stressConfig.tool">
            <el-option label="stressapptest" value="stressapptest" />
            <el-option label="memtester" value="memtester" />
            <el-option label="fio" value="fio" />
          </el-select>
        </el-form-item>
        <el-form-item label="持续时间(秒)">
          <el-input-number v-model="stressConfig.duration_seconds" :min="60" :step="300" />
        </el-form-item>
        <el-form-item label="CPU 线程数">
          <el-input-number v-model="stressConfig.cpu_workers" :min="0" />
        </el-form-item>
        <el-form-item label="内存(MB)">
          <el-input-number v-model="stressConfig.memory_mb" :min="0" :step="256" />
        </el-form-item>
        <el-form-item v-if="stressConfig.tool === 'fio'" label="IO 目标">
          <el-input v-model="stressConfig.io_target" placeholder="/tmp/fio_test" />
        </el-form-item>
      </template>

      <!-- Stability config -->
      <template v-if="form.job_type === 'stability'">
        <el-divider content-position="left">稳定性测试配置</el-divider>
        <el-form-item label="循环类型">
          <el-select v-model="stabilityConfig.cycle_type">
            <el-option label="AC 上下电" value="ac_cycle" />
            <el-option label="DC 上下电" value="dc_cycle" />
            <el-option label="Reboot" value="reboot" />
          </el-select>
        </el-form-item>
        <el-form-item label="循环次数">
          <el-input-number v-model="stabilityConfig.cycle_count" :min="1" :max="10000" />
        </el-form-item>
        <el-form-item label="间隔(秒)">
          <el-input-number v-model="stabilityConfig.interval_seconds" :min="5" :step="10" />
        </el-form-item>
        <el-form-item label="等待启动(秒)">
          <el-input-number v-model="stabilityConfig.wait_boot_seconds" :min="30" :step="30" />
        </el-form-item>
        <el-form-item label="检查 SEL">
          <el-switch v-model="stabilityConfig.check_sel" />
        </el-form-item>
      </template>

      <!-- Performance config -->
      <template v-if="form.job_type === 'performance'">
        <el-divider content-position="left">性能测试配置</el-divider>
        <el-form-item label="Benchmark">
          <el-select v-model="perfConfig.benchmark">
            <el-option label="UnixBench" value="unixbench" />
            <el-option label="SPEC CPU 2017" value="specpu2017" />
            <el-option label="SPECjvm" value="specjvm" />
            <el-option label="SPECjbb" value="specjbb" />
          </el-select>
        </el-form-item>
        <el-form-item label="迭代次数">
          <el-input-number v-model="perfConfig.iterations" :min="1" :max="10" />
        </el-form-item>
        <el-form-item label="额外参数">
          <el-input v-model="perfConfig.extra_args" placeholder="可选" />
        </el-form-item>
      </template>

      <el-form-item>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">提交任务</el-button>
        <el-button @click="$router.push('/jobs')">取消</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api'
import { useJobsStore } from '@/stores/jobs'

const router = useRouter()
const store = useJobsStore()
const submitting = ref(false)
const devices = ref<any[]>([])

const form = reactive({ name: '', device_id: null as number | null, job_type: 'stress' })

const stressConfig = reactive({
  tool: 'stressapptest', duration_seconds: 3600, cpu_workers: 0, memory_mb: 0, io_target: '',
})
const stabilityConfig = reactive({
  cycle_type: 'reboot', cycle_count: 10, interval_seconds: 60, wait_boot_seconds: 300, check_sel: true,
})
const perfConfig = reactive({
  benchmark: 'unixbench', iterations: 1, extra_args: '',
})

function onTypeChange() {
  // reset is optional; configs are independent
}

function buildConfig() {
  if (form.job_type === 'stress') return { ...stressConfig }
  if (form.job_type === 'stability') return { ...stabilityConfig }
  if (form.job_type === 'performance') return { ...perfConfig }
  return {}
}

async function fetchDevices() {
  try {
    const { data } = await api.get('/devices/', { params: { size: 1000, state: 'ready' } })
    // Also include reserved and testing devices
    const { data: data2 } = await api.get('/devices/', { params: { size: 1000, state: 'reserved' } })
    const { data: data3 } = await api.get('/devices/', { params: { size: 1000, state: 'testing' } })
    devices.value = [...data.items, ...data2.items, ...data3.items]
  } catch {
    devices.value = []
  }
}

async function handleSubmit() {
  if (!form.name || !form.device_id) {
    ElMessage.warning('请填写任务名称并选择设备')
    return
  }
  submitting.value = true
  try {
    const job = await store.createJob({
      name: form.name,
      device_id: form.device_id,
      job_type: form.job_type,
      config: buildConfig(),
    })
    ElMessage.success('任务创建成功')
    router.push(`/jobs/${job.id}`)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    submitting.value = false
  }
}

onMounted(fetchDevices)
</script>
