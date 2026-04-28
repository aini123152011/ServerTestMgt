# Research: Existing Open-Source Server Test & Hardware Validation Platforms

- **Query**: Survey of open-source server test automation, bare-metal provisioning, and hardware lab management tools
- **Scope**: External (industry survey based on known open-source projects)
- **Date**: 2026-04-28

---

## 1. Server Test Automation Platforms

### 1.1 OpenBMC Test Framework (openbmc-test-automation)

- **Repository**: github.com/openbmc/openbmc-test-automation
- **Language**: Robot Framework + Python
- **License**: Apache 2.0

**What it does**: The official test automation suite for OpenBMC firmware. Tests BMC functionality via Redfish and IPMI interfaces.

**Architecture**:
- Built entirely on Robot Framework (`.robot` files + Python keyword libraries)
- Tests organized by functional area: `redfish/`, `ipmi/`, `gui/`, `security/`, `network/`
- Uses Robot Framework's built-in test scheduling, tagging, and reporting
- Connection to BMC via Redfish (primary) and IPMI (legacy)
- SSH for in-band OS operations
- Configuration via Robot variables files (`*.py` variable files per system)

**Key patterns**:
- Device inventory: Flat variable files per BMC host (IP, credentials, model-specific quirks)
- Test execution: Robot Framework's native runner (`robot` CLI), parallelism via `pabot`
- Result collection: Robot Framework XML output → HTML reports, with optional upload to ReportPortal
- Extension: Python keyword libraries; new test suites are just new `.robot` files

**Strengths**: Mature Redfish/IPMI coverage, large community, well-structured test taxonomy.
**Weaknesses**: Tightly coupled to OpenBMC; no built-in multi-DUT orchestration, no web UI for scheduling, no device lifecycle management.

**Relevance to our project**: HIGH — covers the BMC protocol interaction layer well. We could reuse patterns for Redfish/IPMI abstraction but need to build orchestration, scheduling, and UI on top.

---

### 1.2 Avocado Framework (avocado-framework)

- **Repository**: github.com/avocado-framework/avocado
- **Language**: Python
- **License**: GPLv2+

**What it does**: A general-purpose test framework originally developed by Red Hat for hardware and OS-level testing. Designed for long-running, complex test scenarios on physical and virtual machines.

**Architecture**:
- Core runner + plugin architecture (`avocado.core.plugin_interfaces`)
- Test types: `avocado-instrumented` (Python classes), `simple` (any executable), `tap` (TAP protocol)
- Varianter system for test parameterization (Cartesian product of parameters via YAML)
- Job/test/suite hierarchy: Job → Suite → Tests
- Result plugins: JSON, xUnit, HTML, custom
- `avocado-vt` plugin for virtualization testing (QEMU/KVM/libvirt)

**Key patterns**:
- Device inventory: Not built-in; relies on external provisioning or manual setup
- Test scheduling: Single-host runner; no native distributed scheduling
- Result collection: Pluggable result reporters (JSON, JUnit XML, HTML, custom)
- Extension: Rich plugin system — resolvers, runners, result writers, spawners, varianter

**Spawner abstraction** (notable):
- `process` — local subprocess
- `podman` — container-based isolation
- `lxc` — LXC container
- Custom spawners possible (e.g., remote SSH spawner)

**Strengths**: Excellent plugin architecture, varianter for combinatorial testing, good for long-running hardware tests, active Red Hat backing.
**Weaknesses**: No web UI, no native multi-host orchestration, no BMC-specific abstractions.

**Relevance to our project**: MEDIUM-HIGH — the plugin architecture and varianter patterns are worth studying. The spawner abstraction is a good model for how to run tests on remote targets.

---

### 1.3 Robot Framework (for hardware testing)

- **Repository**: github.com/robotframework/robotframework
- **Language**: Python (framework), Robot DSL (tests)
- **License**: Apache 2.0

**What it does**: Generic keyword-driven test automation framework. Widely used in hardware testing due to readable syntax and extensibility.

**Architecture**:
- Keyword-driven: tests written in human-readable `.robot` files
- Libraries: Python or Java keyword libraries
- Built-in: SSH, HTTP, XML, String, Collections, OperatingSystem
- External: RESTinstance (Redfish), SSHLibrary, SNMPLibrary
- Listener interface for custom reporting/integration

**Hardware testing patterns**:
- Serial console interaction via custom libraries (pyserial wrappers)
- IPMI via subprocess calls to `ipmitool` wrapped in keywords
- Redfish via RESTinstance or custom HTTP libraries
- Power control via PDU libraries (SNMP-based)
- Parallel execution via `pabot` (parallel robot)

**Strengths**: Readable test syntax, huge ecosystem, good for non-developer test engineers.
**Weaknesses**: Performance overhead for large suites, limited native parallelism, no built-in scheduling or device management.

**Relevance to our project**: MEDIUM — good as a test authoring layer but insufficient as a platform. OpenBMC-test-automation already demonstrates the Robot Framework approach for BMC testing.

---

### 1.4 Autotest

- **Repository**: github.com/autotest/autotest
- **Language**: Python
- **License**: GPLv2

**What it does**: Originally Google's internal server test framework, later open-sourced. Designed for distributed hardware testing at scale.

**Architecture**:
- Client-server model: central scheduler + agents on test machines
- Server: Django-based web frontend + MySQL backend
- Scheduler: assigns jobs to hosts based on labels/ACLs
- Client: runs on DUT, executes test code, reports results back
- AFE (Autotest Frontend): web UI for job management
- TKO (Test Kernel Output): result storage and analysis

**Key patterns**:
- Device inventory: Host objects with labels, ACLs, lock status, platform tags
- Test scheduling: Priority queue, host matching by labels, dependency resolution
- Result collection: Structured result dirs (job → test → iteration), parsed into DB
- Extension: Tests are Python packages dropped into `client/tests/` or `server/tests/`

**Host lifecycle states**: `Ready`, `Running`, `Repairing`, `Cleaning`, `Pending`

**Strengths**: Battle-tested at Google/ChromeOS scale, proper multi-host scheduling, web UI.
**Weaknesses**: Largely unmaintained (last significant activity ~2019), complex setup, dated Django frontend, Python 2 legacy.

**Relevance to our project**: MEDIUM — the scheduling model and host lifecycle state machine are excellent reference architecture, even though the codebase itself is dated. ChromeOS's fork (Autotest in ChromiumOS) is more actively maintained.

---

### 1.5 LAVA (Linaro Automated Validation Architecture)

- **Repository**: git.lavasoftware.org/lava/lava
- **Language**: Python (Django)
- **License**: GPLv2

**What it does**: Automated testing platform for deploying OS images on physical/virtual hardware and running tests. Primarily used in ARM/embedded ecosystem but applicable to server testing.

**Architecture**:
- `lava-server`: Django web app + PostgreSQL + REST API + scheduler
- `lava-dispatcher`: runs on worker nodes, executes jobs on DUTs
- Job definitions: YAML-based pipeline definitions
- Device types: templated Jinja2 device configurations
- Multi-node: supports synchronized multi-device test scenarios

**Pipeline stages** (per job):
1. `deploy` — flash image / PXE boot / NFS root
2. `boot` — power cycle, monitor boot via serial console
3. `test` — run test definitions (shell commands, test suites)
4. `finalize` — collect results, cleanup

**Key patterns**:
- Device inventory: Device Type (template) → Device (instance) with health checks, tags
- Scheduling: Priority-based queue, device tag matching, multi-node reservation
- Result collection: TestCase → TestSuite → TestJob hierarchy, stored in PostgreSQL, queryable via REST API and LAVA Queries
- Extension: Custom deploy/boot/test actions; Jinja2 device type templates

**Device health management**:
- Periodic health checks (automated test jobs to verify device is functional)
- States: `Idle`, `Reserved`, `Running`, `Offline`, `Retired`
- Automatic quarantine on repeated failures

**Strengths**: Production-grade multi-device scheduling, excellent device lifecycle management, PXE/serial console support built-in, active community.
**Weaknesses**: Steep learning curve, complex YAML job definitions, primarily ARM/embedded focused (server support requires custom device types), heavy infrastructure requirements.

**Relevance to our project**: HIGH — LAVA's device management model, health check system, and pipeline-based job execution are directly applicable. The deploy→boot→test→finalize pipeline maps well to server test workflows.

---

## 2. Server Provisioning / Bare-Metal Management

### 2.1 MAAS (Metal as a Service)

- **Repository**: github.com/canonical/maas
- **Language**: Python (Django) + Go (agent)
- **License**: AGPL 3.0

**What it does**: Canonical's bare-metal provisioning system. Treats physical servers like cloud instances — discover, commission, deploy, release.

**Architecture**:
- Region controller: Django REST API + PostgreSQL, manages state and API
- Rack controller: DHCP, TFTP, PXE, HTTP proxy — handles network services per rack
- Agent (Go): runs on commissioned machines for hardware discovery
- Web UI: React-based dashboard
- Machine lifecycle: `New` → `Commissioning` → `Ready` → `Allocated` → `Deploying` → `Deployed` → `Releasing`

**Key patterns**:
- Device inventory: Rich hardware inventory auto-discovered during commissioning (CPU, RAM, disks, NICs, GPU, NUMA topology). Stored in PostgreSQL with full REST API access.
- Network management: DHCP, DNS, VLAN, subnet, fabric, space — full network topology modeling
- PXE boot: Built-in DHCP+TFTP+PXE with support for UEFI and legacy BIOS
- OS deployment: Ubuntu (native), CentOS, RHEL, Windows (via curtin + custom images)
- BMC integration: Auto-detects BMC type (IPMI, Redfish, virsh, etc.), uses it for power control
- Tags and resource pools for grouping machines

**Power driver abstraction** (notable for our project):
```
PowerDriver interface:
  - power_on(system_id, context)
  - power_off(system_id, context)
  - power_query(system_id, context) → on/off/error
  
Implementations: IPMI, Redfish, AMT, virsh, Manual, WoL, fence_cdu (PDU), ...
```

**Strengths**: Best-in-class PXE provisioning, excellent hardware discovery, production-grade at scale, good REST API.
**Weaknesses**: Heavy infrastructure (needs dedicated network control), AGPL license, primarily a provisioning tool (not a test framework), Ubuntu-centric.

**Relevance to our project**: HIGH for PXE and power control patterns. The power driver abstraction and machine lifecycle state machine are directly reusable concepts. We likely don't want to embed MAAS but should study its patterns.

---

### 2.2 Ironic (OpenStack Bare Metal)

- **Repository**: github.com/openstack/ironic
- **Language**: Python
- **License**: Apache 2.0

**What it does**: OpenStack's bare-metal provisioning service. Provisions physical machines as if they were VMs.

**Architecture**:
- `ironic-api`: REST API service
- `ironic-conductor`: manages node lifecycle, communicates with BMC/drivers
- Driver model: `hardware types` with pluggable `interfaces` (power, management, deploy, boot, inspect, console, raid, bios, vendor)
- Node states: `enroll` → `verifying` → `manageable` → `available` → `active` → `deleting`

**Driver interface model** (excellent abstraction):
```
HardwareType:
  - PowerInterface: power_on, power_off, reboot, get_power_state
  - ManagementInterface: get_boot_device, set_boot_device, get_sensors_data
  - DeployInterface: deploy, tear_down, prepare, clean_up
  - BootInterface: prepare_ramdisk, prepare_instance, clean_up_ramdisk
  - InspectInterface: inspect_hardware (auto-discover specs)
  - ConsoleInterface: start_console, stop_console, get_console
  - RAIDInterface: create_configuration, delete_configuration
  - BIOSInterface: apply_configuration, factory_reset, cache_bios_settings
  - VendorInterface: vendor_passthru (custom vendor-specific operations)
```

**Key patterns**:
- Device inventory: Node objects with driver_info (BMC credentials), properties (hardware specs), extra (custom metadata)
- Cleaning: automated steps between deployments (disk erase, BIOS reset, firmware update)
- Inspection: auto-discovery of hardware specs via in-band (IPA agent) or out-of-band (Redfish)
- Conductor affinity: nodes assigned to specific conductors for HA

**Strengths**: Best driver abstraction model in the industry, production-grade, handles BIOS/RAID/firmware configuration, excellent separation of concerns.
**Weaknesses**: Requires OpenStack ecosystem (or standalone mode which is limited), complex deployment, heavy dependencies.

**Relevance to our project**: HIGH — Ironic's hardware type / interface model is the gold standard for abstracting BMC operations. The separation into Power/Management/Deploy/Boot/Inspect/Console/RAID/BIOS interfaces maps almost perfectly to our needs. We should adopt a similar driver model.

---

### 2.3 Foreman

- **Repository**: github.com/theforeman/foreman
- **Language**: Ruby on Rails
- **License**: GPLv3

**What it does**: Lifecycle management for physical and virtual servers. Provisioning, configuration management, and monitoring.

**Architecture**:
- Rails web app + PostgreSQL
- Smart Proxies: distributed agents handling DHCP, DNS, TFTP, Puppet/Ansible, BMC
- Compute Resources: abstraction for bare-metal and cloud providers
- Host Groups: hierarchical grouping with inherited parameters

**Key patterns**:
- Device inventory: Host model with facts (auto-collected), parameters (user-defined), host groups
- BMC integration: Smart Proxy BMC module (IPMI power control, boot device)
- Provisioning: PXE templates (ERB), partition tables, OS associations
- Configuration: Puppet/Ansible/Salt integration post-provisioning

**Strengths**: Mature lifecycle management, good plugin ecosystem, Ansible integration.
**Weaknesses**: Ruby ecosystem (less common in hardware testing), primarily a sysadmin tool, BMC support is basic (IPMI only, limited Redfish).

**Relevance to our project**: LOW-MEDIUM — useful reference for host group hierarchy and provisioning template patterns, but not a strong fit for test automation.

---

### 2.4 Cobbler

- **Repository**: github.com/cobbler/cobbler
- **Language**: Python
- **License**: GPLv2

**What it does**: Linux provisioning server that manages DHCP, DNS, TFTP, and PXE boot configurations. Simplifies network-based OS installation.

**Architecture**:
- Central daemon (`cobblerd`) managing all provisioning services
- Objects: `distro` → `profile` → `system` hierarchy
- Manages: DHCP (ISC/dnsmasq), TFTP, DNS, PXE menus
- Kickstart/Preseed/AutoYaST template rendering
- Power management: `fence-agents` integration for IPMI/SNMP/etc.

**Key patterns**:
- Distro: OS distribution (kernel + initrd + metadata)
- Profile: distro + kickstart template + repos + settings
- System: profile + network config + power management config (specific machine)
- Snippets: reusable kickstart template fragments

**Strengths**: Simple and focused on PXE provisioning, lightweight, good template system.
**Weaknesses**: Limited scope (provisioning only), aging codebase, no web UI (CLI + basic web), no test execution.

**Relevance to our project**: MEDIUM — the distro→profile→system hierarchy is a clean model for PXE configuration management. Worth adopting for our PXE module.

---

## 3. Hardware Lab Management Tools

### 3.1 labgrid

- **Repository**: github.com/labgrid-project/labgrid
- **Language**: Python
- **License**: LGPL 2.1

**What it does**: Embedded/hardware test infrastructure and device management framework. Manages access to shared lab resources (boards, serial consoles, power switches, USB devices).

**Architecture**:
- `labgrid-coordinator`: crossbar.io (WAMP) based central coordinator for resource sharing
- `labgrid-exporter`: runs on machines physically connected to DUTs, exports resources (serial ports, power ports, network interfaces)
- `labgrid-client`: CLI for reserving and interacting with devices
- pytest integration: `@pytest.fixture` based test authoring
- Environment files (YAML): describe DUT setup (resources + drivers)

**Resource/Driver model** (notable):
```
Resources (physical):         Drivers (logical):
  SerialPort                    SerialDriver
  NetworkPowerPort              PowerDriver (ManualPowerDriver, NetworkPowerDriver, ...)
  USBSerialPort                 ShellDriver (SSHDriver, SerialDriver)
  EthernetPort                  BootstrapDriver
  RemotePlace                   UBootDriver, BareboxDriver
  PDUDaemonPort                 RedfishDriver (newer addition)
```

**Key patterns**:
- Device inventory: "Places" — named collections of resources. Exporters publish resources; coordinator tracks availability.
- Resource locking: Reservation system prevents conflicts when multiple users/CI jobs share lab hardware
- Power control: Abstracted via PowerDriver — supports PDUDaemon, SNMP PDUs, uhubctl (USB), REST APIs, shell commands
- Serial console: First-class support via ser2net, RFC2217, direct serial
- Extension: Custom Resource and Driver classes via Python

**Strengths**: Excellent resource sharing model for shared labs, clean resource/driver separation, pytest integration, good for CI pipelines.
**Weaknesses**: No web UI, no built-in test scheduling (relies on external CI), limited reporting, primarily embedded-focused.

**Relevance to our project**: HIGH — the resource/driver abstraction and place-based device management are excellent patterns. The exporter model (agent on machines connected to DUTs) is directly applicable to our distributed lab setup.

---

### 3.2 pdudaemon

- **Repository**: github.com/pdudaemon/pdudaemon
- **Language**: Python
- **License**: GPLv2

**What it does**: Daemon for controlling network-attached PDUs (Power Distribution Units). Provides a unified API for power control across different PDU vendors.

**Architecture**:
- Single daemon with REST API + legacy TCP protocol
- PDU driver plugins for different vendors
- Request queuing to prevent power surge from simultaneous operations
- Configuration via YAML

**Supported PDU types** (partial list):
- APC (SNMP-based: AP7900, AP7920, AP7930, AP8941, etc.)
- Raritan (SNMP)
- CyberPower (SNMP)
- Eaton (SNMP)
- ServerTech (SNMP)
- Ubiquiti mFi / EdgePower
- IP9258 (HTTP)
- Devantech (HTTP)
- ACME (custom)
- localcmdline (shell command wrapper)

**API**:
```
POST /power/control/on    — {hostname, port}
POST /power/control/off   — {hostname, port}
POST /power/control/reboot — {hostname, port}
GET  /power/control/status — {hostname, port}
```

**Strengths**: Simple, focused, supports many PDU vendors, request queuing prevents power issues.
**Weaknesses**: Very narrow scope (PDU control only), basic API.

**Relevance to our project**: HIGH — we should either integrate pdudaemon directly or adopt its driver pattern for PDU control. The request queuing pattern is important for preventing power surge when cycling many servers.

---

### 3.3 ConServer / conman

**ConServer** (github.com/conserver/conserver):
- **Language**: C
- **License**: BSD
- Centralized serial console management daemon
- Supports multiple simultaneous read-only viewers + one read-write user
- Logging of all console output to files
- Access control per console

**conman** (github.com/dun/conman):
- **Language**: C
- **License**: GPLv3
- Serial console manager for HPC clusters
- Supports serial devices, IPMI SOL (Serial over LAN), external process consoles
- Logging, broadcast, shared/exclusive access modes

**ser2net** (github.com/cminyard/ser2net):
- **Language**: C
- **License**: GPLv2
- Exposes serial ports over network (telnet/RFC2217/raw TCP)
- YAML configuration
- Often used with labgrid and LAVA

**Key patterns across all three**:
- Console multiplexing: multiple readers, one writer
- Persistent logging: all console output captured to timestamped log files
- Network access: serial ports exposed over TCP for remote access
- IPMI SOL: Serial-over-LAN for BMC console access without physical serial cable

**Relevance to our project**: MEDIUM-HIGH — serial console management is essential for monitoring boot processes, capturing kernel panics, and debugging. We should integrate with ser2net or conman rather than building our own. IPMI SOL support is critical for BMC testing.

---

## 4. Architectural Patterns Comparison

### 4.1 Device Inventory Models

| Platform | Model | Hierarchy | Auto-Discovery | Metadata |
|----------|-------|-----------|----------------|----------|
| LAVA | DeviceType → Device | 2-level with tags | No (manual registration) | Jinja2 templates + tags |
| MAAS | Machine (auto-discovered) | Flat + resource pools + tags | Yes (PXE commission) | Rich hardware facts (CPU, RAM, disk, NIC, NUMA) |
| Ironic | Node + driver_info + properties | Flat + conductor affinity | Yes (inspect interface) | driver_info, properties, extra, traits |
| Autotest | Host + labels + ACLs | Flat + labels | No | Labels (key-value), platform, locked status |
| labgrid | Place → Resources + Drivers | Place contains resources | Via exporters | Resource attributes |
| Foreman | Host + HostGroup + Facts | Hierarchical groups | Yes (Puppet/Ansible facts) | Facts + parameters |

**Recommended pattern for our project**: 
- 2-level hierarchy: `ServerModel` (template) → `Server` (instance), similar to LAVA's DeviceType→Device
- Rich metadata: auto-discovered via Redfish (like MAAS commissioning) + user-defined tags
- Resource pools / groups for organizing by rack, project, or test purpose
- BMC connection info stored per server (IP, protocol, credentials)

---

### 4.2 Test Scheduling Models

| Platform | Scheduler Type | Matching | Priority | Multi-DUT |
|----------|---------------|----------|----------|-----------|
| LAVA | Queue + device matching | Tags + device type | Yes (7 levels) | Yes (multi-node) |
| Autotest | Queue + label matching | Labels + ACLs | Yes | Limited |
| Avocado | Local runner | N/A (single host) | No | No |
| Robot/pabot | Parallel local | N/A | No | No |

**Recommended pattern for our project**:
- Job queue with priority levels
- Server matching by tags/labels (e.g., "cpu=intel", "memory>=256GB", "bmc=redfish")
- Support for multi-server jobs (e.g., cluster stress tests)
- Job states: `Submitted` → `Queued` → `Scheduled` → `Running` → `Complete/Failed/Cancelled`
- Reservation system to prevent conflicts (like labgrid)

---

### 4.3 Test Execution Models

| Platform | Execution Model | Remote Control | Result Format |
|----------|----------------|----------------|---------------|
| LAVA | Pipeline (deploy→boot→test→finalize) | Serial + SSH | TestCase/TestSuite in DB |
| Autotest | Client agent on DUT | Agent + SSH | Structured result dirs → DB |
| Avocado | Spawner abstraction | Process/Container/Custom | JSON/xUnit/HTML plugins |
| OpenBMC-test | Robot runner | Redfish + IPMI + SSH | Robot XML → HTML |
| labgrid | pytest fixtures | Serial + SSH + Redfish | pytest/JUnit XML |

**Recommended pattern for our project**:
- Pipeline model inspired by LAVA: `provision` → `configure` → `execute` → `collect` → `cleanup`
- For BMC tests: direct Redfish/IPMI (no agent needed)
- For OS-level tests (benchmarks, stress): SSH-based execution
- For stability tests (AC/DC cycling): BMC power control + serial console monitoring
- Result collection: structured JSON → database, with raw logs preserved

---

### 4.4 Plugin/Extension Mechanisms

| Platform | Extension Model | Plugin Types |
|----------|----------------|--------------|
| Avocado | Python entry_points | Resolvers, runners, result writers, spawners, varianter |
| Ironic | Stevedore (entry_points) | Hardware types with interface plugins |
| LAVA | Python class inheritance | Deploy/boot/test actions, device types |
| labgrid | Python class registration | Resources, drivers, strategies |
| Robot Framework | Python/Java libraries | Keyword libraries, listeners |
| Foreman | Rails plugins + Smart Proxies | Compute resources, provisioning, BMC |

**Recommended pattern for our project**:
- Python entry_points or explicit registry pattern
- Plugin categories:
  - `bmc_driver`: Redfish, IPMI, vendor-specific (like Ironic's hardware type model)
  - `power_driver`: BMC power, PDU power (like pdudaemon's driver model)
  - `test_type`: stress, stability, performance, custom
  - `provisioner`: PXE, USB, manual
  - `reporter`: HTML, PDF, JSON, email, webhook
  - `console_driver`: IPMI SOL, SSH, serial (like labgrid's driver model)

---

### 4.5 Result Collection & Reporting

| Platform | Storage | Query | Export | Dashboards |
|----------|---------|-------|--------|------------|
| LAVA | PostgreSQL | REST API + LAVA Queries | CSV, YAML | Built-in charts |
| Autotest | MySQL (TKO) | Web UI + SQL | CSV | TKO dashboard |
| Avocado | File-based (JSON/XML) | CLI | JSON, xUnit, HTML | No (external) |
| Robot Framework | XML files | rebot tool | HTML, XML | No (external) |
| ReportPortal | PostgreSQL + Elasticsearch | REST API + UI | PDF, CSV | Rich dashboards |

**Recommended pattern for our project**:
- Primary storage: PostgreSQL (structured results) + object storage (raw logs, artifacts)
- Result hierarchy: `TestRun` → `TestSuite` → `TestCase` → `TestStep`
- Each level has: status, duration, logs, metrics, artifacts
- REST API for programmatic access
- Web dashboard with filtering, comparison, trend analysis
- Export: PDF reports, CSV data, JSON API

---

## 5. Gap Analysis: What Our Platform Should Fill

### 5.1 Gaps in Existing Tools

| Gap | Description | Which tools fall short |
|-----|-------------|----------------------|
| **Unified BMC test + provisioning platform** | No single tool combines BMC test automation with PXE provisioning, firmware management, and hardware validation in one UI | LAVA is closest but ARM-focused; MAAS provisions but doesn't test; OpenBMC-test tests but doesn't manage |
| **Server-specific test orchestration** | Existing tools are either embedded-focused (LAVA, labgrid) or generic (Avocado, Robot). None are purpose-built for x86 server validation workflows | All — server validation teams typically glue together 3-5 tools |
| **Stability test lifecycle** | AC/DC power cycling, reboot loops with automatic pass/fail detection, SEL (System Event Log) monitoring, and hang detection are not first-class in any platform | Partially in LAVA (boot monitoring), but no dedicated stability test engine |
| **Firmware management workflow** | Batch firmware upgrade with version verification, rollback capability, and upgrade matrix testing is not a built-in workflow anywhere | Ironic has cleaning steps for firmware, but not a test-oriented workflow |
| **FRU management** | FRU data programming and verification is a niche need not addressed by any general platform | None — typically custom scripts |
| **RAS injection framework** | ACPI EINJ, BMC error injection, and response validation as a structured test framework | None — typically manual or custom scripts |
| **Performance benchmark orchestration** | Running SPEC CPU/jvm/jbb with proper configuration, compilation, and result parsing is complex and not automated by any platform | None — benchmark teams use custom scripts |
| **Modern web UI for hardware labs** | Most tools have dated UIs (LAVA, Autotest) or no UI at all (labgrid, Avocado, Robot) | MAAS has a good UI but for provisioning only |
| **Chinese localization** | None of the existing platforms have Chinese UI/documentation, which matters for Chinese server ODM/OEM teams | All |

### 5.2 Our Platform's Unique Value Proposition

Based on the gaps above, our platform (ServerTestLab) should differentiate by:

1. **All-in-one server validation platform**: Combine device management, test scheduling, PXE provisioning, firmware management, and result reporting in a single system — eliminating the need to glue together MAAS + LAVA + custom scripts.

2. **Server-native test types**: First-class support for the specific test patterns server teams need:
   - Stress tests with configurable duration, load profiles, and health monitoring
   - Stability tests (AC/DC/reboot cycles) with automatic hang detection and SEL analysis
   - Performance benchmarks with proper setup, execution, and result parsing
   - Firmware upgrade workflows with version matrix testing
   - FRU programming and verification
   - RAS error injection with expected-response validation

3. **BMC-first architecture**: Unlike LAVA/labgrid (serial-console-first) or MAAS (PXE-first), our platform should be BMC-first — Redfish and IPMI are the primary control plane, with SSH and serial as secondary channels.

4. **Modern tech stack with good UX**: React/Vue frontend with real-time updates, intuitive dashboard, and Chinese language support.

### 5.3 What We Should Borrow vs. Build

| Component | Borrow From | Build Custom |
|-----------|-------------|--------------|
| BMC driver abstraction | Ironic's interface model | Adapt for test (not just provisioning) context |
| Power control | pdudaemon patterns + MAAS power drivers | Unified power API (BMC + PDU) |
| Device inventory | LAVA's DeviceType→Device + MAAS's auto-discovery | Server-specific metadata (BMC info, firmware versions, FRU data) |
| Test scheduling | LAVA's queue + tag matching | Server-aware scheduling (rack affinity, power budget) |
| Test execution pipeline | LAVA's deploy→boot→test→finalize | Server-specific stages (firmware check, BMC health, OS provision, test, collect) |
| Plugin architecture | Avocado's entry_points model | Domain-specific plugin types (bmc_driver, test_type, reporter) |
| Serial console | Integrate ser2net/conman | IPMI SOL wrapper |
| PXE provisioning | Cobbler's distro→profile→system model | Integration with our device inventory |
| Result storage | LAVA's TestCase hierarchy | Benchmark-specific result schemas, trend analysis |
| Stress test tools | Existing tools (stress-ng, fio, iperf3, memtester) | Orchestration, monitoring, and result collection |
| Benchmark execution | SPEC CPU/jvm/jbb binaries | Automated setup, compilation, execution, and result parsing |

### 5.4 Recommended Technology Choices (based on ecosystem analysis)

| Layer | Recommendation | Rationale |
|-------|---------------|-----------|
| Backend language | Python | All reference platforms use Python; rich BMC libraries (python-redfish, pyipmi); test ecosystem compatibility |
| Backend framework | FastAPI | Modern async, auto-generated OpenAPI docs, better than Django for API-first design |
| Task queue | Celery + Redis | Proven for long-running tasks; used by LAVA and MAAS patterns |
| Database | PostgreSQL | Used by LAVA, MAAS; excellent for structured test results + JSON metadata |
| Frontend | React or Vue 3 | Modern SPA; MAAS uses React successfully |
| BMC libraries | python-redfish (Redfish), pyghmi or ipmitool subprocess (IPMI) | Industry standard |
| Serial console | ser2net integration | Used by LAVA and labgrid; proven |
| PDU control | pdudaemon or custom driver layer | Covers most PDU vendors |
| PXE | dnsmasq (DHCP+TFTP) + iPXE | Lighter than ISC DHCP; iPXE is more flexible than legacy PXE |

---

## 6. Summary of Key Takeaways

1. **No existing platform covers our full scope** — server teams currently cobble together 3-5 tools. This is our opportunity.

2. **Ironic has the best driver abstraction** — its Power/Management/Deploy/Boot/Inspect/Console/RAID/BIOS interface model should be our primary reference for BMC driver architecture.

3. **LAVA has the best device lifecycle and scheduling** — its DeviceType→Device model, health checks, and pipeline-based execution are directly applicable.

4. **MAAS has the best PXE and hardware discovery** — its commissioning flow and power driver abstraction are worth studying.

5. **labgrid has the best resource sharing model** — its exporter/coordinator/place pattern solves the "shared lab" problem elegantly.

6. **Avocado has the best plugin architecture** — its entry_points-based extension model is clean and Pythonic.

7. **pdudaemon solves PDU control** — we should integrate it or adopt its patterns rather than building from scratch.

8. **Serial console management is a solved problem** — use ser2net/conman, don't reinvent.

9. **The unique value is in integration and server-specific workflows** — BMC-first control, stability test automation, firmware management, FRU handling, RAS injection, and benchmark orchestration are all gaps we can fill.
