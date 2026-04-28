<template>
  <el-container style="min-height: 100vh">
    <el-aside width="220px" style="background: #304156">
      <div style="padding: 20px; text-align: center; color: #fff; font-size: 18px; font-weight: bold">
        ServerTestLab
      </div>
      <el-menu :default-active="route.path" router background-color="#304156" text-color="#bfcbd9" active-text-color="#409eff">
        <el-menu-item index="/">
          <el-icon><Monitor /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/devices">
          <el-icon><Cpu /></el-icon>
          <span>设备管理</span>
        </el-menu-item>
        <el-menu-item index="/reservations">
          <el-icon><Calendar /></el-icon>
          <span>设备预约</span>
        </el-menu-item>
        <el-menu-item index="/jobs">
          <el-icon><List /></el-icon>
          <span>测试任务</span>
        </el-menu-item>
        <el-menu-item index="/provision">
          <el-icon><Upload /></el-icon>
          <span>PXE 装机</span>
        </el-menu-item>
        <el-menu-item index="/firmware">
          <el-icon><UploadFilled /></el-icon>
          <span>固件升级</span>
        </el-menu-item>
        <el-menu-item index="/operations">
          <el-icon><Tools /></el-icon>
          <span>运维工具</span>
        </el-menu-item>
        <el-sub-menu index="settings">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>设置</span>
          </template>
          <el-menu-item index="/settings/cicd">CI/CD 集成</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header style="display: flex; align-items: center; justify-content: flex-end; background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,0.08)">
        <span style="margin-right: 16px; color: #606266">{{ auth.user?.username }}</span>
        <el-tag size="small" :type="auth.isAdmin ? 'danger' : 'info'">{{ auth.user?.role }}</el-tag>
        <el-button text style="margin-left: 16px" @click="handleLogout">退出</el-button>
      </el-header>
      <el-main style="background: #f0f2f5">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Monitor, Cpu, Calendar, List, Upload, UploadFilled, Tools, Setting } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

onMounted(() => {
  if (auth.isLoggedIn && !auth.user) {
    auth.fetchUser()
  }
})

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>
