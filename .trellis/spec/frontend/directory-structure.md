# Directory Structure

> How frontend code is organized in this project.

---

## Overview

Vue 3 + TypeScript + Vite SPA with Element Plus component library, Pinia state management, and ECharts for data visualization.

---

## Directory Layout

```
frontend/src/
├── main.ts              # App entry: createApp, plugins (Pinia, Router, ElementPlus)
├── App.vue              # Root component (just <router-view />)
├── api/
│   └── index.ts         # Axios instance with auth interceptor + base URL
├── router/
│   └── index.ts         # Vue Router with auth guard (redirect to /login if no token)
├── stores/
│   ├── auth.ts          # Auth store: login, logout, fetchUser, token persistence
│   └── jobs.ts          # Jobs store: CRUD operations for test jobs
├── views/               # Page-level components (one per route)
│   ├── Login.vue
│   ├── Layout.vue       # Sidebar + header + <router-view /> shell
│   ├── Dashboard.vue    # Stats cards + ECharts (pie + bar)
│   ├── DeviceList.vue   # Device table with search/filter/add/power control
│   ├── DeviceDetail.vue # Device info + hardware info
│   ├── ReservationList.vue
│   ├── JobList.vue      # Test jobs with status filters
│   ├── JobCreate.vue    # Job creation with typed config panels
│   ├── JobDetail.vue    # Job detail + real-time WebSocket log console
│   ├── ProvisionList.vue
│   ├── FirmwareList.vue
│   ├── OperationsPanel.vue  # Tabs: FRU + RAS
│   ├── ReportView.vue   # Structured report + export buttons
│   └── CICDSettings.vue # API key management + usage examples
├── components/          # Reusable components (currently empty, views are self-contained)
├── composables/         # Vue composables (future: useWebSocket, useDeviceStatus)
└── assets/              # Static assets
```

---

## Module Organization

Each view is a self-contained SFC (Single File Component) with `<template>`, `<script setup lang="ts">`, and optional `<style scoped>`. Views fetch data directly via the `api/index.ts` Axios client.

For shared state that persists across routes, use Pinia stores (`stores/`).

---

## Naming Conventions

- Views: `PascalCase.vue` (e.g., `DeviceList.vue`, `JobCreate.vue`)
- Stores: `camelCase.ts` (e.g., `auth.ts`, `jobs.ts`)
- Routes: kebab-case paths (e.g., `/devices`, `/jobs/create`, `/settings/cicd`)
- API calls: use the shared `api` instance, paths match backend routes without `/api/v1` prefix (handled by baseURL)
