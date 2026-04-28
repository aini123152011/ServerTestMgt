<template>
  <div>
    <h3>CI/CD 集成设置</h3>
    <el-card style="margin-bottom: 20px">
      <template #header>API 密钥管理</template>
      <el-button type="primary" @click="createKey" :loading="creating" style="margin-bottom: 16px">创建 API 密钥</el-button>
      <el-alert v-if="newKey" type="success" :closable="false" style="margin-bottom: 16px">
        <p>新密钥（仅显示一次）：<code>{{ newKey }}</code></p>
      </el-alert>
      <el-table :data="keys" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="名称" width="200" />
        <el-table-column prop="key_prefix" label="前缀" width="120" />
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'danger'" size="small">{{ row.is_active ? '活跃' : '已撤销' }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button v-if="row.is_active" size="small" type="danger" @click="revokeKey(row.id)">撤销</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    <el-card>
      <template #header>使用示例</template>
      <pre style="background: #1e1e1e; color: #d4d4d4; padding: 16px; border-radius: 4px; font-size: 13px; overflow-x: auto">
# 触发测试
curl -X POST {{ baseUrl }}/api/v1/cicd/trigger \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"device_name": "server-01", "test_type": "stress", "config": {"duration": 3600}}'

# 查询状态
curl {{ baseUrl }}/api/v1/cicd/status/JOB_ID \
  -H "X-API-Key: YOUR_API_KEY"</pre>
    </el-card>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'
const keys = ref<any[]>([])
const newKey = ref('')
const creating = ref(false)
const baseUrl = window.location.origin
async function fetchKeys() {
  try { const { data } = await api.get('/api-keys/'); keys.value = data.items } catch {}
}
async function createKey() {
  creating.value = true
  try {
    const { data } = await api.post('/api-keys/', { name: `key-${Date.now()}` })
    newKey.value = data.raw_key
    ElMessage.success('API 密钥已创建')
    await fetchKeys()
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || '创建失败') }
  finally { creating.value = false }
}
async function revokeKey(id: number) {
  try { await api.delete(`/api-keys/${id}`); ElMessage.success('已撤销'); await fetchKeys() }
  catch (e: any) { ElMessage.error('撤销失败') }
}
onMounted(fetchKeys)
</script>
