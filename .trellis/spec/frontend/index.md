# Frontend Development Guidelines

> Best practices for frontend development in this project.

---

## Overview

Vue 3 SPA for an internal BMC server test platform. Prioritizes functionality and data density over visual polish. Backend engineers are the primary developers.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Module organization and file layout | ✅ Filled |
| [Component Guidelines](./component-guidelines.md) | Component patterns, props, composition | To fill |
| [Hook Guidelines](./hook-guidelines.md) | Custom hooks, data fetching patterns | To fill |
| [State Management](./state-management.md) | Local state, global state, server state | ✅ Filled |
| [Quality Guidelines](./quality-guidelines.md) | Code standards, forbidden patterns | To fill |
| [Type Safety](./type-safety.md) | Type patterns, validation | To fill |

---

## Key Architecture Decisions

### Element Plus as UI library
Enterprise-grade components with strong table/form support. Chinese-origin project with excellent docs for the team.

### Self-contained views over component decomposition
Each view is a complete page. Extract to `components/` only when reuse is proven (3+ usages).

### Axios with auth interceptor
Single API client instance in `api/index.ts`. Auto-attaches JWT, auto-redirects on 401.

### WebSocket for real-time
Job detail page connects directly to `ws://host/ws/jobs/{id}` for live log streaming. No library wrapper — native WebSocket API.

### ECharts for visualization
Dashboard uses `vue-echarts` with tree-shakeable imports. Pie chart for device states, bar chart for test results.

---

**Language**: All documentation should be written in **English**.
