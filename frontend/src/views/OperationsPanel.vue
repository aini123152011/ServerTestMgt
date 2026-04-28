<template>
  <div>
    <el-tabs v-model="activeTab">
      <el-tab-pane label="FRU 刷录" name="fru">
        <el-form :model="fruForm" label-width="100px" style="max-width: 600px">
          <el-form-item label="设备 ID"><el-input-number v-model="fruForm.device_id" :min="1" /></el-form-item>
          <el-form-item>
            <el-button @click="readFru" :loading="fruLoading">读取 FRU</el-button>
          </el-form-item>
          <template v-if="fruData">
            <el-form-item v-for="(val, key) in fruData" :key="key" :label="String(key)">
              <el-input v-model="fruData[key]" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="writeFru" :loading="fruWriting">写入 FRU</el-button>
            </el-form-item>
          </template>
        </el-form>
      </el-tab-pane>
      <el-tab-pane label="RAS 注入" name="ras">
        <el-form :model="rasForm" label-width="100px" style="max-width: 600px">
          <el-form-item label="设备 ID"><el-input-number v-model="rasForm.device_id" :min="1" /></el-form-item>
          <el-form-item label="错误类型">
            <el-select v-model="rasForm.error_type">
              <el-option v-for="t in errorTypes" :key="t.value" :label="t.description" :value="t.value" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="danger" @click="injectError" :loading="rasLoading">注入错误</el-button>
            <el-button @click="verifyResponse" :loading="rasVerifying">验证响应</el-button>
          </el-form-item>
        </el-form>
        <el-card v-if="rasResult" style="margin-top: 16px">
          <pre style="font-size: 13px">{{ JSON.stringify(rasResult, null, 2) }}</pre>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'
const activeTab = ref('fru')
const fruForm = reactive({ device_id: 1 })
const fruData = ref<Record<string, any> | null>(null)
const fruLoading = ref(false)
const fruWriting = ref(false)
const rasForm = reactive({ device_id: 1, error_type: 'correctable_memory' })
const errorTypes = ref<any[]>([])
const rasLoading = ref(false)
const rasVerifying = ref(false)
const rasResult = ref<any>(null)
async function readFru() {
  fruLoading.value = true
  try { const { data } = await api.post(`/fru/${fruForm.device_id}/read`); fruData.value = data }
  catch (e: any) { ElMessage.error(e.response?.data?.detail || '读取失败') }
  finally { fruLoading.value = false }
}
async function writeFru() {
  if (!fruData.value) return
  fruWriting.value = true
  try { await api.post(`/fru/${fruForm.device_id}/write`, { data: fruData.value }); ElMessage.success('FRU 写入成功') }
  catch (e: any) { ElMessage.error(e.response?.data?.detail || '写入失败') }
  finally { fruWriting.value = false }
}
async function injectError() {
  rasLoading.value = true
  try { const { data } = await api.post('/ras/inject', rasForm); rasResult.value = data; ElMessage.warning('错误已注入') }
  catch (e: any) { ElMessage.error(e.response?.data?.detail || '注入失败') }
  finally { rasLoading.value = false }
}
async function verifyResponse() {
  rasVerifying.value = true
  try { const { data } = await api.post('/ras/verify', rasForm); rasResult.value = data }
  catch (e: any) { ElMessage.error(e.response?.data?.detail || '验证失败') }
  finally { rasVerifying.value = false }
}
onMounted(async () => {
  try { const { data } = await api.get('/ras/error-types'); errorTypes.value = data } catch {}
})
</script>
