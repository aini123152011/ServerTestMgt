import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export interface TestJob {
  id: number
  name: string
  device_id: number
  user_id: number
  job_type: string
  status: string
  config: Record<string, any> | null
  result: Record<string, any> | null
  started_at: string | null
  finished_at: string | null
  error_message: string | null
  celery_task_id: string | null
  device_name: string | null
  username: string | null
  created_at: string
  updated_at: string
}

export interface TestJobLog {
  id: number
  job_id: number
  level: string
  message: string
  timestamp: string
}

export const useJobsStore = defineStore('jobs', () => {
  const jobs = ref<TestJob[]>([])
  const total = ref(0)
  const loading = ref(false)

  async function fetchJobs(params: Record<string, any> = {}) {
    loading.value = true
    try {
      const { data } = await api.get('/jobs/', { params })
      jobs.value = data.items
      total.value = data.total
      return data
    } finally {
      loading.value = false
    }
  }

  async function fetchJob(id: number): Promise<TestJob> {
    const { data } = await api.get(`/jobs/${id}`)
    return data
  }

  async function createJob(payload: { name: string; device_id: number; job_type: string; config?: Record<string, any> }): Promise<TestJob> {
    const { data } = await api.post('/jobs/', payload)
    return data
  }

  async function cancelJob(id: number) {
    const { data } = await api.post(`/jobs/${id}/cancel`)
    return data
  }

  async function fetchJobLogs(id: number, params: Record<string, any> = {}) {
    const { data } = await api.get(`/jobs/${id}/logs`, { params })
    return data
  }

  return { jobs, total, loading, fetchJobs, fetchJob, createJob, cancelJob, fetchJobLogs }
})
