# Research: BMC Management Tools and Libraries for Server Test Automation

- **Query**: BMC management tools, IPMI/Redfish libraries, PXE automation, PDU control, RAS error injection
- **Scope**: external
- **Date**: 2026-04-28

---

## 1. IPMI Tools and Python Libraries

### 1.1 ipmitool CLI

`ipmitool` is the de facto standard CLI for IPMI interaction. Available on all major Linux distros.

**Installation:**
```bash
# RHEL/CentOS
yum install ipmitool
# Ubuntu/Debian
apt-get install ipmitool
```

**Common usage patterns:**

```bash
# Power control
ipmitool -I lanplus -H <bmc_ip> -U <user> -P <pass> power status
ipmitool -I lanplus -H <bmc_ip> -U <user> -P <pass> power on
ipmitool -I lanplus -H <bmc_ip> -U <user> -P <pass> power off
ipmitool -I lanplus -H <bmc_ip> -U <user> -P <pass> power cycle
ipmitool -I lanplus -H <bmc_ip> -U <user> -P <pass> power reset

# Serial Over LAN (SOL)
ipmitool -I lanplus -H <bmc_ip> -U <user> -P <pass> sol activate
ipmitool -I lanplus -H <bmc_ip> -U <user> -P <pass> sol deactivate
ipmitool -I lanplus -H <bmc_ip> -U <user> -P <pass> sol info

# Sensor reading
ipmitool -I lanplus -H <bmc_ip> -U <user> -P <pass> sensor list
ipmitool -I lanplus -H <bmc_ip> -U <user> -P <pass> sensor get "CPU Temp"
ipmitool -I lanplus -H <bmc_ip> -U <user> -P <pass> sdr list

# FRU (Field Replaceable Unit) operations
ipmitool -I lanplus -H <bmc_ip> -U <user> -P <pass> fru list
ipmitool -I lanplus -H <bmc_ip> -U <user> -P <pass> fru print 0
ipmitool -I lanplus -H <bmc_ip> -U <user> -P <pass> fru edit 0 field b 0 "NewBoardMfg"

# SEL (System Event Log)
ipmitool -I lanplus -H <bmc_ip> -U <user> -P <pass> sel list
ipmitool -I lanplus -H <bmc_ip> -U <user> -P <pass> sel clear

# Boot device override
ipmitool -I lanplus -H <bmc_ip> -U <user> -P <pass> chassis bootdev pxe
ipmitool -I lanplus -H <bmc_ip> -U <user> -P <pass> chassis bootdev disk
ipmitool -I lanplus -H <bmc_ip> -U <user> -P <pass> chassis bootdev cdrom

# BMC management
ipmitool -I lanplus -H <bmc_ip> -U <user> -P <pass> mc reset cold
ipmitool -I lanplus -H <bmc_ip> -U <user> -P <pass> mc info

# Raw commands (for vendor-specific OEM operations)
ipmitool -I lanplus -H <bmc_ip> -U <user> -P <pass> raw 0x06 0x01
```

**Key interface types:**
- `-I lanplus` -- IPMI v2.0 over LAN with encryption (most common for remote)
- `-I lan` -- IPMI v1.5 over LAN (legacy, no encryption)
- `-I open` -- local in-band via `/dev/ipmi0` kernel driver

**Automation wrapper pattern (Python subprocess):**
```python
import subprocess
import shlex

def run_ipmitool(bmc_ip, user, password, command):
    cmd = f"ipmitool -I lanplus -H {bmc_ip} -U {user} -P {password} {command}"
    result = subprocess.run(
        shlex.split(cmd),
        capture_output=True, text=True, timeout=30
    )
    return result.stdout, result.stderr, result.returncode
```

### 1.2 pyghmi

**Repository**: https://opendev.org/x/pyghmi
**PyPI**: `pip install pyghmi`
**License**: Apache 2.0

Pure-Python IPMI implementation. No dependency on `ipmitool`. Used by OpenStack Ironic.

**Key features:**
- Native Python IPMI v2.0 implementation
- SOL console support
- Async-capable via eventlet
- OEM extensions for Lenovo, Dell, etc.

**Usage examples:**
```python
import pyghmi.ipmi.command as ipmi_cmd

# Create connection
conn = ipmi_cmd.Command(bmc="192.168.1.100", userid="admin", password="password")

# Power operations
power_state = conn.get_power()        # {'powerstate': 'on'}
conn.set_power('off')                 # graceful shutdown
conn.set_power('on')
conn.set_power('reset')               # hard reset
conn.set_power('off', wait=True)      # wait for completion

# Sensor reading
for sensor in conn.get_sensor_data():
    print(f"{sensor}: {conn.get_sensor_data()[sensor]}")

# Boot device
conn.set_bootdev('network')           # PXE boot
conn.set_bootdev('hd')                # hard disk
conn.set_bootdev('optical')           # CD/DVD

# FRU data
fru = conn.get_inventory_descriptions()

# SEL
sel_entries = conn.get_event_log()

# BMC info
bmc_info = conn.get_bmc_configuration()
```

### 1.3 python-ipmi

**Repository**: https://github.com/kontron/python-ipmi
**PyPI**: `pip install python-ipmi`
**License**: LGPL

Lower-level IPMI library with good protocol coverage.

**Usage examples:**
```python
import pyipmi
import pyipmi.interfaces

# Create interface (RMCP+ / lanplus equivalent)
interface = pyipmi.interfaces.create_interface('ipmitool', interface_type='lanplus')
conn = pyipmi.create_connection(interface)
conn.target = pyipmi.Target(0x20)
conn.session.set_session_type_rmcp(host='192.168.1.100', port=623)
conn.session.set_auth_type_user(username='admin', password='password')
conn.session.establish()

# Chassis control
conn.chassis_control_power_down()
conn.chassis_control_power_up()
conn.chassis_control_power_cycle()

# Get sensor reading by number
reading = conn.get_sensor_reading(sensor_number=0x01)	 device SDRst
for sdr in conn.device_sdr_entries():
    print(sdr)

# Get FRU inventory
fru = conn.get_fru_inventory()
```

### 1.4 Comparison: pyghmi vs python-ipmi vs ipmitool subprocess

| Feature | pyghmi | python-ipmi | ipmitool (subprocess) |
|---------|--------|-------------|----------------------|
| Pure Python | Yes | Yes (can use ipmitool backend) | No (CLI wrapper) |
| IPMI v2.0 | Yes | Yes | Yes |
| SOL support | Yes | Limited | Yes |
| OEM extensions | Lenovo, Dell, Huawei | Limited | Vendor-dependent |
| Async support | eventlet | No | No (blocking subprocess) |
| OpenStack integration | Ironic uses it | No | Ironic fallback |
| Maturity | High | Medium | Very High |
| Error handling | Python exceptions | Python exceptions | Exit codes + stderr parsing |

**Recommendation**: pyghmi for native Python integration; ipmitool subprocess as fallback for edge cases and raw commands.

---

## 2. Redfish Tools and Python Libraries

### 2.1 python-redfish-library (DMTF Official)

**Repository**: https://github.com/DMTF/python-redfish-library
**PyPI**: `pip install redfish`
**License**: BSD 3-Clause

**Usage examples:**
```python
import redfish

client = redfish.redsh_client(
    base_url="https://192.168.1.100",
    username="admin", password="password",
    default_prefix="/redfish/v1"
)
client.login(auth="session")

try:
    # System info
    system = client.get("/redfish/v1/Systems/1").dict

    # Power control
    client.post("/redfish/v1/Systems/1/Actions/ComputerSystem.Reset",
                body={"ResetType": "ForceOff"})
    # ResetType: On, ForceOff, GracefulShutdown, GracefulRestart,
    #            ForceRestart, Nmi, ForceOn, PushPowerButton

    # Boot override to PXE
    client.patch("/redfish/v1/Systems/1", body={
        "Boot": {"BootSourceOverrideTarget": "Pxe",
                 "BootSourceOverrideEnabled": "Once"}
    })

    # Thermal sensors
    thermal = client.get("/redfish/v1/Chassis/1/Thermal").dict
    for temp in thermal.get("Temperatures", []):
        print(f"{temp['Name']}: {temp['ReadingCelsius']}C")

    # Firmware update (SimpleUpdate)
    client.post("/redfish/v1/UpdateService/Actions/UpdateService.SimpleUpdate",
                body={"ImageURI": "http://fileserver/firmware.bin",
                      "TransferProtocol": "HTTP"}lly:
    client.logout()
```

### 2.2 sushy (OpenStack Redfish Library)

**Repository**: https://opendev.org/openstack/sushy
**PyPI**: `pip install sushy`
**License**: Apache 2.0

Higher-level, object-oriented Redfish library used by OpenStack Ironic.

```python
import sushy

root = sushy.Sushy("https://192.168.1.100", username="admin",
                   password="password", verify=False)

for system in root.get_system_collection().get_members():
    print(f"Power: {system.power_state}, Model: {system.model}")
    system.reset_system(sushy.RESET_FORCE_OFF)
    system.set_system_boot_options(
        target=sushy.BOOT_SOURCE_TARGET_PXE,
        enabled=sushy.BOOT_SOURCE_ENABLED_ONCE
    )
```

| Feature | sushy | python-redfish-library |
|---------|-------|----------------------|
| Abstraction | High (OOP, typed resources) | Low (REST client, raw dicts) |
| OpenStack integration | Native (Ironic driver) | No |
| Vendor OEM | Via sushy-oem-* plugins | Manual |
| Session management | Automatic | Manual login/logout |

### 2.3 Redfish Common URI Patterns

```
/redfish/v1/Systems/{id}                  # System info, power,n/redfish/v1/Systems/{id}/Bios            # BIOS configuration
/redfish/v1/Systems/{id}/Processors      # CPU inventory
/redfish/v1/Systems/{id}/Memory          # DIMM inventory
/redfish/v1/Systems/{id}/Storage         # Storage controllers & drives
/redfish/v1/Chassis/{id}/Thermal         # Temperature sensors & fans
/redfish/v1/Chassis/{id}/Power           # Power supplies & consumption
/redfish/v1/Managers/{id}                # BMC info
/redfish/v1/UpdateService                # Firmware update service
/redfish/v1/TaskService/Tasks            # Async task tracking
/redfish/v1/EventService                 # Event subscriptions (SSE/webhook)
```

---

## 3. PXE Boot Automation

### 3.1 DHCP/TFTP Server Management

**dnsmasq (lightweight, combined DHCP+TFTP+DNS):**
```ini
# /etc/dnsmasq.d/pxe.conf
interface=eth0
dhcp-range=192.168.1.100,192.168.1.200,12h
dhcp-boot=pxelinux.0
enable-tftp
tftp-root=/var/lib/tftpboot

# UEFI PXE support
dhcp-match=set:efi-x86_64,option:client-arch,7
dhcp-boot=tag:efi-x86_64,grubx64.efi

# Per-host configuration
dhcp-host=aa:bb:cc:dd:ee:ff,192.168.1.101,set:host1
```

**Python management pattern:**
```python
class DnsmasqManager:
 it__(self, config_dir="/etc/dnsmasq.d"):
        self.config_dir = config_dir

    def add_host(self, mac, ip, hostname, boot_file="pxelinux.0"):
        config = f"dhcp-host={mac},{ip},{hostname}\n"
        with open(f"{self.config_dir}/host-{hostname}.conf", 'w') as f:
            f.write(config)
        subprocess.run(["systemctl", "reload", "dnsmasq"], check=True)
```

### 3.2 Kickstart / Preseed / AutoYaST

All three support a `%post` / `late_command` / `<post-scripts>` hook to call back to the automation platform after OS installation completes. Use Jinja2 templates to generate per-host configs dynamically.

### 3.3 PXE Integration Pattern

```
Test Orchestrator
  1. Set boot device to PXE (via IPMI/Redfish)
  2. Generate kickstart/preseed with callback URL
  3. Update DHCP config (MAC -> IP + boot file)
  4. Power cycle server (via IPMI/Redfish)
  5. Monitor SOL for boot progress (optional)
  6. Wait for OS provision callback
  7. Run tests via SSH
```

---

## 4. PDU (Power Distribution Unit) Control

### 4.1 Common PDU Brands and Protocols

| Brand | REST API | SNMP | Python SDK |
|-------|----------|------|------------|
| Raritan | Yes (JSON-RPC) | Yes (v1/v2c/v3) | raritan-sdk (official) |
| APC (Schneider) | Yes (newer NMC3) | Yes (v1/v2c/v3) | No official SDK |
| ServerTech (Legrand) | Yes (newer) | Yes (v1/v2c/v3) | No official SDK |
| Eaton | Yes (newer ePDU) | Yes | No official SDK |

### 4.2 SNMP-Based PDU Control

```python
from pysnmp.hlapi import *

class SnmpPduController:
    def __init__(self, host, community="private", port=161):
        self.host = host
        self.community = community
        self.port = port

    def _snmp_set(self, oid, value):
        errorIndication, errorStatus, _, varBinds = next(
            setCmd(SnmpEngine(), Comelf.community),
                   UdpTransportTarget((self.host, self.port), timeout=10),
                   ContextData(),
                   ObjectType(ObjectIdentity(oid), Integer(value))))
        if errorIndication or errorStatus:
            raise RuntimeError(f"SNMP error: {errorIndication or errorStatus}")

    # APC rPDU2: OID .1.3.6.1.4.1.318.1.1.26.9.2.4.1.5.<outlet>
    # Values: 1=immediateOn, 2=immediateOff, 3=immediateReboot
    def apc_outlet_on(self, outlet):
        self._snmp_set(f"1.3.6.1.4.1.318.1.1.26.9.2.4.1.5.{outlet}", 1)

    def apc_outlet_off(self, outlet):
        self._snmp_set(f"1.3.6.1.4.1.318.1.1.26.9.2.4.1.5.{outlet}", 2)
```

### 4.3 REST-Based PDU Control (Raritan)

```python
class RaritanPduController:
    def __init__(self, host, user, password):
        self.base_url = f"https://{host}"
        self.session = requests.Session()
        self.session.auth = (user, password)
        self.session.verify = False

    def set_outlet(self, outlet_id, state):
        payload = {"jsonrpc": "2.0", "method": "setPowerState",
                   "params": {"pstate": {"powerState": state}}, "id": 1}
        self.session.post(f"{self.base_url}/model/outlet/{outlet_id}", json=payload)
```

### 4.4 Abstraction Pattern

```python
from abc import ABC, abstractmethod

class PduController(ABC):
    @abstractmethod
    def outlet_on(self, outlet_id: int) -> None: ...
    @abstractmethod
    def outlet_off(self, outlet_id: int) -> None: ...
    @abstractmethod
    def outlet_cycle(self, outlet_id: int) -> None: ...
    @abstractmethod
    def get_outlet_state(self, outlet_id: int) -> str: ...
```

**Key libraries:** pysnmp-lextudio (SNMP), requests (REST), paramiko (SSH CLI)

---

## 5. RAS Error Injection

### 5.1 Linux EINJ (ACPI Eon Table)

**Prerequisites:**OS must expose EINJ ACPI table; kernel module `einj` (`CONFIG_ACPI_APEI_EINJ=m`)

**Error types (bitmask):**
```
0x01 - Processor Correctable       0x08 - Memory Correctable
0x02 - Processor Uncorrectable NF   0x10 - Memory Uncorrectable NF
0x04 - Processor Fatal              0x20 - Memory Fatal
0x40 - PCIe Correctable            0x80 - PCIe Uncorrectable NF
0x100 - PCIe Fatal
```

**Injection:**
```bash
modprobe einj
echo 0x8 > /sys/kernel/debug/apei/einj/error_type       # mem CE
echo 0x100000000 > /sys/kernel/debug/apei/einj/param1   # phys addr
echo 1 > /sys/kernel/debug/apei/einj/error_inject       # trigger
```

**Python wrapper:**
```python
class EinjController:
    EINJ_PATH = "/sys/kernel/debug/apei/einj"
    ERROR_TYPES = {
        "mem_correctable": 0x08, "mem_uncorrectable": 0x10,
        "mem_fatal": 0x20, "pcie_correctable": 0x40,
        "pcie_uncorrectable": 0x80, "pcie_fatal": 0x100,
    }

    def inject(self, error_type, phys_addr=None, addr_mask=None):
        if isinstance(error_type, str):
            error_type = self.ERROR_TYPES[error_type]
        self._write("error_type", hex(error_type))
        if phys_addr: self._write("param1", hex(phys_addr))
        if addr_mask: self._write("param2", hex(addr_mask))
        self._write("error_inject", "1")
```

### 5.2 Other RAS Tools

| Tool | Purpose |
|------|---------|
| mcelog | Machine Check Exception logger and injector |
| mce-inject | Inject synthetic MCEs into kernel |
| rasdaemon | RAS event collector (SQLite DB at /var/lib/rasdaemon/) |
| edac-utils | EDAC status reporting (CE/UE counts) |

### 5.3 Common RAS Test Patterns

1. **Memory CE Storm** -- inject N CEs, verify OS logging + BMC SEL + page offlining
2. **Memory UCE Recovery** -- inject UCE NF, verify process kill (not panic) + SEL
3. **PCIe AER** -- inject PCIe errors, verify AER logging + device recovery
4. **Firmware-First** -- verify BMC processes error before OS via GHES/HEST

---

## 6. Suggested Dependencies

```
pyghmi>=1.5.0              # Pure Python IPMI
redfish>=3.2.0             # DMTF Redfish client
sushy>=5.0.0               # OpenStack Redfish (higher-level)
pysnmp-lextudio>=6.0.0     # SNMP (maintained fork)
paramiko>=3.4.0            # SSH
fabric>=3.2.0              # SSH task runner
jinja2>=3.1.0              # Template provisioning configs
requests>=2.31.0           # REST APIs
pydantic>=2.5.0            # Config validation
pyyaml>=6.0                # YAML config parsing
```

---

## Caveats

- IPMI is being superseded by Redfish; dual-stack (Redfish-first, IPMI-fallback) recommended
- PDU SNMP OIDs are vendor/model-specific; verify against actual MIB files
- EINJ requires explicit BIOS enablement (often disabled by default)
- BMC OEM error injection is vendor-specific and often under NDA
- pysnmp-lextudio is the maintained fork (original pysnmp unmaintained since 2022)
- SOL via pyghmi can be fragile; ipmitool SOL is more battle-tested
- Redfish EventService /webhook) support varies significantly across vendors
