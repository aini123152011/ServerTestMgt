# BMC 服务器测试平台 (ServerTestLab)

## Goal

构建一个覆盖 BMC 服务器测试常见业务场景的综合测试平台，支持压力测试、稳定性测试、性能测试等核心测试类型，以及 PXE 装机、固件批量升级、FRU 刷录、RAS 注入等运维功能模块。目标是提供统一的测试调度、执行、结果收集与报告能力，提升服务器验证效率。

## Decisions

| 问题 | 决定 |
|------|------|
| 部署规模 | 1000 台级，大规模验证农场 |
| BMC 协议 | IPMI + Redfish 双协议，统一抽象层 |
| 带内控制 | SSH + Agent 混合模式 |
| 基础设施 | 全部从零搭建，平台内置完整方案 |
| 权限管理 | RBAC（管理员/测试员/只读） |
| MVP 范围 | 核心功能 + 设备预约锁定 + CI/CD 对接 |

## Requirements

### 核心测试能力
* 压力测试（CPU/内存/IO 长时间高负载，支持 stressapptest、memtester、fio 等）
* 稳定性测试（AC 上下电、DC 上下电、Reboot 循环，支持自定义循环次数和间隔）
* 性能测试（SPECPU2017、SPECjvm、SPECjbb、UnixBench 等标准 benchmark）

### 功能模块
* PXE 网络装机（DHCP + TFTP + Kickstart/Preseed/AutoYaST）
* 固件批量升级（BIOS/BMC/CPLD，通过 Redfish UpdateService 或厂商工具）
* FRU 信息批量刷录（通过 IPMI FRU Write）
* RAS 错误注入与验证（EINJ / BMC 接口）

### 平台能力
* 分布式任务调度与执行引擎（支持 1000 台并发）
* IPMI + Redfish 统一设备抽象层（借鉴 Ironic 驱动模型）
* SSH + Agent 混合带内控制
* 设备预约/锁定机制（多团队共享，避免冲突）
* CI/CD 对接（REST API + Webhook，支持 Jenkins/GitLab CI 触发）
* RBAC 多用户权限管理
* 测试结果收集、存储与报告生成（支持导出）
* Web 管理界面（实时状态监控）

## Acceptance Criteria

* [ ] 能通过 Web UI 创建并调度测试任务到指定服务器
* [ ] 支持对多台服务器并行执行压力测试，实时查看进度
* [ ] 支持 AC/DC/Reboot 稳定性循环测试，记录每轮结果和异常
* [ ] 能执行 SPECPU2017 等性能 benchmark 并收集分数
* [ ] 支持 PXE 批量装机，装机完成自动回调
* [ ] 支持固件批量升级并验证升级后版本
* [ ] 支持 FRU 信息批量写入并验证
* [ ] 支持 RAS 错误注入并验证系统响应（MCE、PCIe AER 等）
* [ ] 设备可被预约/锁定，锁定期间其他用户无法操作
* [ ] 提供 REST API 供 CI/CD 系统调用
* [ ] 测试报告可导出（PDF/Excel/JSON）
* [ ] RBAC 权限控制生效（管理员/测试员/只读）

## Technical Approach

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Web Frontend (Vue 3)                     │
│                   Element Plus + ECharts + VxeTable             │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP/WebSocket
┌──────────────────────────▼──────────────────────────────────────┐
│                     API Gateway (Nginx)                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                   Backend API (FastAPI)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │ 设备管理  │ │ 任务调度  │ │ 用户权限  │ │ WebSocket Server │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────────┘  │
└──────────┬───────────┬──────────────────────────────────────────┘
           │           │
     ┌─────▼─────┐ ┌───▼────────────┐
     │PostgreSQL │ │  Redis          │
     │(主数据库)  │ │(Broker+Cache   │
     │+TimescaleDB│ │ +Pub/Sub)      │
     └───────────┘ └───┬────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                  Celery Workers (分布式)                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐    │
│  │ BMC Worker   │ │ Test Worker  │ │ Provision Worker     │    │
│  │ (IPMI/Redfish│ │ (执行测试)    │ │ (PXE/固件/FRU)       │    │
│  │  电源/传感器) │ │              │ │                      │    │
│  └──────┬───────┘ └──────┬───────┘ └──────────┬───────────┘    │
└─────────┼────────────────┼────────────────────┼────────────────┘
          │                │                    │
┌─────────▼────────────────▼────────────────────▼────────────────┐
│                    被测服务器 (1000 台)                          │
│  ┌─────────┐  ┌─────────────┐  ┌────────────────────────────┐  │
│  │   BMC   │  │  OS (带内)   │  │  Test Agent (轻量常驻)     │  │
│  │IPMI/    │  │  SSH 访问    │  │  - 接收任务                │  │
│  │Redfish  │  │  应急控制    │  │  - 执行 benchmark          │  │
│  └─────────┘  └─────────────┘  │  - 上报状态/日志/结果      │  │
│                                │  - 心跳检测                 │  │
│                                └────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

### Tech Stack

| 层 | 技术 | 理由 |
|---|---|---|
| Backend | FastAPI + Uvicorn | 异步原生，WebSocket 内置，Pydantic 验证 |
| ORM | SQLAlchemy 2.0 (async) + Alembic | 异步支持，复杂查询能力强 |
| Task Queue | Celery 5.x + Redis Broker | 成熟的长任务支持，Canvas 工作流，Flower 监控 |
| Scheduler | Celery Beat | 定时/周期性测试任务 |
| Frontend | Vue 3 + TypeScript + Vite | 学习曲线低，响应式好，中文组件库丰富 |
| UI Library | Element Plus | 企业级组件，表格/表单能力强 |
| Charts | ECharts | 测试指标可视化 |
| Data Grid | VxeTable | 大数据量表格，虚拟滚动 |
| Database | PostgreSQL 16 + TimescaleDB | JSONB 灵活配置，时序数据，分区表 |
| Cache/Broker | Redis 7.x | 消息队列 + 缓存 + Pub/Sub 三合一 |
| IPMI | pyghmi (主) + ipmitool (备) | 纯 Python IPMI，Ironic 验证过 |
| Redfish | sushy (主) + python-redfish-library (备) | OOP 抽象，OpenStack 验证过 |
| PXE | dnsmasq (DHCP+TFTP) | 轻量，配置简单，支持 UEFI |
| PDU | pdudaemon 集成 | 多厂商支持，请求排队防浪涌 |
| Agent | 自研轻量 Agent (Python) | gRPC/MQTT 通信，任务执行+状态上报 |
| 部署 | Docker + Docker Compose | 开发和生产统一 |
| 反向代理 | Nginx | SSL、路由、静态文件 |

### 核心设计模式（借鉴业界最佳实践）

**1. 硬件驱动抽象层（借鉴 Ironic）**
```
HardwareDriver:
  ├── PowerInterface      → power_on / power_off / reboot / get_state
  ├── ManagementInterface → get_boot_device / set_boot_device / get_sensors
  ├── ConsoleInterface    → start_sol / stop_sol / get_console_output
  ├── FirmwareInterface   → get_versions / update_firmware / verify
  ├── FRUInterface        → read_fru / write_fru / verify_fru
  └── InspectInterface    → discover_hardware / get_inventory

Implementations:
  ├── IPMIDriver (pyghmi + ipmitool fallback)
  └── RedfishDriver (sushy + python-redfish-library fallback)
```

**2. 测试流水线（借鉴 LAVA）**
```
TestPipeline:
  deploy  → 装机/环境准备（PXE/Agent 部署）
  boot    → 启动验证（SOL 监控启动过程）
  test    → 执行测试（Agent 执行 benchmark/压力测试）
  collect → 收集结果（日志/分数/传感器数据）
  cleanup → 清理环境（可选）
```

**3. 设备生命周期状态机（借鉴 MAAS + LAVA）**
```
New → Commissioning → Ready → Reserved → Deploying → Testing → Ready
                        ↑                                  │
                        └──────── Releasing ←──────────────┘
                        
异常路径: * → Maintenance → Ready (修复后)
         * → Offline (失联)
```

**4. 设备预约/锁定**
```
Reservation:
  - user/team + device_list + time_range
  - 排他锁：锁定期间其他用户无法操作
  - 自动释放：超时未使用自动解锁
  - 队列等待：设备忙时可排队
```

### 目录结构（初步）

```
ServerTestLab/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── api/               # API 路由
│   │   │   ├── devices.py     # 设备管理
│   │   │   ├── jobs.py        # 测试任务
│   │   │   ├── provision.py   # PXE/固件/FRU
│   │   │   ├── reports.py     # 报告导出
│   │   │   ├── auth.py        # 认证授权
│   │   │   └── webhooks.py    # CI/CD 对接
│   │   ├── core/              # 核心模块
│   │   │   ├── config.py
│   │   │   ├── security.py    # RBAC
│   │   │   └── websocket.py   # 实时推送
│   │   ├── drivers/           # 硬件驱动抽象层
│   │   │   ├── base.py        # 接口定义
│   │   │   ├── ipmi.py        # IPMI 实现
│   │   │   ├── redfish.py     # Redfish 实现
│   │   │   └── pdu.py         # PDU 控制
│   │   ├── models/            # SQLAlchemy 模型
│   │   ├── schemas/           # Pydantic 模型
│   │   ├── services/          # 业务逻辑
│   │   └── workers/           # Celery 任务
│   │       ├── bmc_tasks.py   # BMC 操作任务
│   │       ├── test_tasks.py  # 测试执行任务
│   │       └── provision_tasks.py
│   ├── alembic/               # 数据库迁移
│   ├── tests/
│   └── pyproject.toml
├── frontend/                   # Vue 3 前端
│   ├── src/
│   │   ├── views/             # 页面
│   │   ├── components/        # 组件
│   │   ├── composables/       # 组合式函数
│   │   ├── stores/            # Pinia 状态
│   │   └── api/               # API 客户端
│   ├── package.json
│   └── vite.config.ts
├── agent/                      # 被测机 Agent
│   ├── agent.py               # Agent 主程序
│   ├── executors/             # 测试执行器
│   └── reporters/             # 结果上报
├── deploy/                     # 部署配置
│   ├── docker-compose.yml
│   ├── nginx.conf
│   └── pxe/                   # PXE 配置模板
│       ├── kickstart/
│       ├── preseed/
│       └── autoyast/
└── docs/
```

## Decision (ADR-lite)

**Context**: 需要选择一个能支撑 1000 台服务器并发测试的技术架构，同时覆盖 BMC 带外管理、OS 带内控制、PXE 装机、固件升级等多种场景。

**Decision**: 采用 FastAPI + Celery + Vue 3 + PostgreSQL + Redis 技术栈，借鉴 Ironic 的硬件驱动抽象模型和 LAVA 的测试流水线模式，自研统一平台。

**Consequences**:
* (+) FastAPI 异步架构天然适合高并发设备管理
* (+) Celery Canvas 工作流能很好地建模测试流水线
* (+) Ironic 驱动模型经过 OpenStack 大规模验证，可靠性高
* (+) Vue 3 + Element Plus 对后端为主的团队友好
* (-) Celery 长任务需要仔细调优 visibility_timeout
* (-) 自研 Agent 需要额外开发和维护成本
* (-) 全栈自研工作量大，需要分阶段交付

## Out of Scope (MVP)

* 非 BMC 设备支持（交换机、存储等）
* 测试用例版本管理系统
* 移动端适配
* 多数据中心/跨地域部署
* 自动化硬件故障诊断（AI/ML）

## Research References

* [`research/tech-stack.md`](research/tech-stack.md) — FastAPI+Celery+Vue3+PG 技术栈详细对比
* [`research/similar-platforms.md`](research/similar-platforms.md) — LAVA/Ironic/labgrid/Autotest 等同类平台调研
* [`research/bmc-tools.md`](research/bmc-tools.md) — IPMI/Redfish/PXE/PDU/RAS 工具链调研

## Implementation Plan (分阶段)

**Phase 1: 基础框架 + 设备管理**
* 项目脚手架（FastAPI + Vue 3 + Docker Compose）
* 数据库模型 + 迁移
* 硬件驱动抽象层（IPMI + Redfish）
* 设备 CRUD + 状态管理
* 基础 RBAC + JWT 认证
* 设备预约/锁定机制

**Phase 2: 测试执行引擎**
* Celery Worker 架构
* 测试流水线（deploy→boot→test→collect）
* Agent 开发（任务接收、执行、上报）
* 压力测试 / 稳定性测试 / 性能测试模板
* WebSocket 实时状态推送

**Phase 3: 运维功能模块**
* PXE 装机（dnsmasq 集成 + Kickstart/Preseed 模板）
* 固件批量升级（Redfish UpdateService）
* FRU 批量刷录（IPMI FRU Write）
* RAS 错误注入（EINJ 集成）

**Phase 4: 报告 + CI/CD + 完善**
* 测试报告生成与导出
* CI/CD REST API + Webhook
* 前端完善（Dashboard、设备拓扑、趋势图）
* 性能优化 + 文档
