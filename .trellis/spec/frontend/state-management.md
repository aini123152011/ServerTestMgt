# State Management

> How state is managed in this project.

---

## Overview

- **Library**: Pinia (Vue 3 official state management)
- **Pattern**: Composition API style (`defineStore` with `setup` function)
- **Persistence**: Auth token stored in `localStorage`, other state is ephemeral

---

## State Categories

| Category | Where | Example |
|----------|-------|---------|
| Auth state | `stores/auth.ts` | token, user profile, role |
| Domain CRUD | `stores/jobs.ts` | job list, create/cancel operations |
| Page-local | `ref()` in `<script setup>` | form data, loading flags, pagination |
| Server state | Fetched on mount via `api.get()` | device list, reservation list |
| Real-time | WebSocket in component | job logs streaming |

---

## When to Use Global State (Pinia Store)

Use a Pinia store when:
- State is needed across multiple routes (auth token, user info)
- Multiple components need to read/write the same data
- Complex async operations with shared loading/error state

Keep in page-local `ref()` when:
- Data is only used in one view
- Simple fetch-on-mount patterns
- Form state

---

## Store Pattern

```typescript
export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<User | null>(null)
  const isLoggedIn = computed(() => !!token.value)

  async function login(username: string, password: string) {
    const { data } = await api.post('/auth/login', { username, password })
    token.value = data.access_token
    localStorage.setItem('token', data.access_token)
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  return { token, user, isLoggedIn, login, logout }
})
```

---

## Common Mistakes

### Storing server data in Pinia that should be fetched fresh
Device lists and job lists change frequently. Fetch on mount rather than caching in a store, unless you need cross-component reactivity.

### Not handling 401 in the API interceptor
The Axios interceptor in `api/index.ts` auto-redirects to `/login` on 401. Don't duplicate this logic in stores.
