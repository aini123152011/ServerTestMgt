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
- `-I lanplus` — IPMI v2.0 over LAN with encryption (most common for remote)
- `-I lan` — IPMI v1.5 over LAN (legacy, no encryption)
- `-I open` — local in-band via `/dev/ipmi0` kernel driver

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
reading = conn.get_sensor_reading(sensor_number=0x01)

# Get device SDR list
for sdr in conn.device_sdr_entries():
    print(sdr)

# Get FRU inventory
fru = conn.get_fru_inventory()
```

### 1.4 Comparison: pyghmi vs python-ipmi vs ipmitool subprocess

| Feature | pyghmi | python-ipmi | ipmitool (subprocess) |
|---------|--------|-------------|----------------------|
| Pure Python | Yes | Yes (but can use ipmitool backend) | No (CLI wrapper) |
| IPMI v2.0 | Yes | Yes | Yes |
| SOL support | Yes | Limited | Yes |
| OEM extensions | Lenovo, Dell, Huawei | Limited | Vendor-dependent |
| Async support | eventlet | No | No (blocking subprocess) |
| OpenStack integration | Ironic uses it | No | Ironic fallback |
| Maturity | High | Medium | Very High |
| Error handling | Python exceptions | Python exceptions | Exit codes + stderr parsing |

**Recommendation for test automation**: pyghmi for native Python integration; ipmitool subprocess as fallback for edge cases and raw commands.

---

## 2. Redfish Tools and Python Libraries

### 2.1 python-redfish-library (DMTF Official)

**Repository**: https://github.com/DMTF/python-redfish-library
**PyPI**: `pip install redfish`
**License**: BSD 3-Clause

The official DMTF Redfish client library.

**Usage examples:**
```python
import redfish

# Connect
client = redfish.redfish_client(
    base_url="https://192.168.1.100",
    username="admin",
    password="password",
    default_prefix="/redfish/v1"
)
client.login(auth="session")  # or auth="basic"

try:
    # Get system info
    response = client.get("/redfish/v1/Systems/1")
    system = response.dict
    print(f"Model: {system['Model']}")
    print(f"Power: {system['PowerState']}")

    # Power control
    body = {"ResetType": "ForceOff"}
    client.post("/redfish/v1/Systems/1/Actions/ComputerSystem.Reset", body=body)

    # ResetType options: On, ForceOff, GracefulShutdown, GracefulRestart,
    #                    ForceRestart, Nmi, ForceOn, PushPowerButton

    # Set boot override to PXE
    body = {
        "Boot": {
            "BootSourceOverrideTarget": "Pxe",
            "BootSourceOverrideEnabled": "Once"
        }
    }
    client.patch("/redfish/v1/Systems/1", body=body)

    # Read sensors / thermal
    thermal = client.get("/redfish/v1/Chassis/1/Thermal").dict
    for temp in thermal.get("Temperatures", []):
        print(f"{temp['Name']}: {temp['ReadingCelsius']}C")

    # Read power consumption
    power = client.get("/redfish/v1/Chassis/1/Power").dict
    for ctrl in power.get("PowerControl", []):
        print(f"Consumed: {ctrl['PowerConsumedWatts']}W")

    # Firmware inventory
    fw = client.get("/redfish/v1/UpdateService/FirmwareInventory").dict
    for member in fw["Members"]:
        fw_detail = client.get(member["@odata.id"]).dict
        print(f"{fw_detail['Name']}: {fw_detail['Version']}")

    # Firmware update (SimpleUpdate)
    body = {
        "ImageURI": "http://fileserver/firmware.bin",
        "TransferProtocol": "HTTP",
        "Targets": ["/redfish/v1/UpdateService/FirmwareInventory/BMC"]
    }
    client.post("/redfish/v1/UpdateService/Actions/UpdateService.SimpleUpdate", body=body)

    # Get event log / LogServices
    logs = client.get("/redfish/v1/Systems/1/LogServices/Log1/Entries").dict
    for entry in logs.get("Members", []):
        print(f"{entry['Created']}: {entry['Message']}")

finally:
    client.logout()
```

### 2.2 sushy (OpenStack Redfish Library)

**Repository**: https://opendev.org/openstack/sushy
**PyPI**: `pip install sushy`
**License**: Apache 2.0

Higher-level, object-oriented Redfish library used by OpenStack Ironic.

**Usage examples:**
```python
import sushy

# Connect
root = sushy.Sushy("https://192.168.1.100", username="admin", password="password", verify=False)

# Iterate systems
for system in root.get_system_collection().get_members():
    print(f"System: {system.identity}")
    print(f"Power state: {system.power_state}")
    print(f"Model: {system.model}")
    print(f"Serial: {system.serial_number}")

    # Power control
    system.reset_system(sushy.RESET_FORCE_OFF)
    system.reset_system(sushy.RESET_ON)
    system.reset_system(sushy.RESET_GRACEFUL_RESTART)

    # Boot override
    system.set_system_boot_options(
        target=sushy.BOOT_SOURCE_TARGET_PXE,
        enabled=sushy.BOOT_SOURCE_ENABLED_ONCE
    )

    # BIOS attributes
    bios = system.bios
    print(f"BIOS attributes: {bios.attributes}")

# Managers (BMC)
for manager in root.get_manager_collection().get_members():
    print(f"BMC FW version: {manager.firmware_version}")
    manager.reset_manager(sushy.RESET_GRACEFUL_RESTART)
```

**sushy vs python-redfish-library:**

| Feature | sushy | python-redfish-library |
|---------|-------|----------------------|
| Abstraction level | High (OOP, resource objects) | Low (REST client) |
| Schema awareness | Yes (typed resources) | No (raw dicts) |
| OpenStack integration | Native (Ironic driver) | No |
| Vendor OEM support | Via sushy-oem-* plugins | Manual |
| Session management | Automatic | Manual login/logout |
| Learning curve | Moderate | Low |

### 2.3 Redfish Common URI Patterns

```
/redfish/v1/                              # Service root
/redfish/v1/Systems/                      # Computer systems collection
/redfish/v1/Systems/{id}                  # Specific system
/redfish/v1/Systems/{id}/Bios            # BIOS configuration
/redfish/v1/Systems/{id}/Processors      # CPU inventory
/redfish/v1/Systems/{id}/Memory          # DIMM inventory
/redfish/v1/Systems/{id}/Storage         # Storage controllers & drives
/redfish/v1/Systems/{id}/EthernetInterfaces  # NICs
/redfish/v1/Chassis/                      # Chassis collection
/redfish/v1/Chassis/{id}/Thermal         # Temperature sensors & fans
/redfish/v1/Chassis/{id}/Power           # Power supplies & consumption
/redfish/v1/Managers/                     # BMC collection
/redfish/v1/Managers/{id}                # BMC info
/redfish/v1/Managers/{id}/NetworkProtocol # BMC network config
/redfish/v1/Managers/{id}/LogServices    # BMC logs
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
dhcp-option=option:router,192.168.1.1
dhcp-option=option:dns-server,192.168.1.1

# PXE boot
dhcp-boot=pxelinux.0
enable-tftp
tftp-root=/var/lib/tftpboot

# UEFI PXE support (tag-based)
dhcp-match=set:efi-x86_64,option:client-arch,7
dhcp-match=set:efi-x86_64,option:client-arch,9
dhcp-boot=tag:efi-x86_64,grubx64.efi

# Per-host configuration (MAC-based)
dhcp-host=aa:bb:cc:dd:ee:ff,192.168.1.101,set:host1
dhcp-boot=tag:host1,pxelinux.0
```

**ISC DHCP (enterprise-grade, more complex):**
```
# /etc/dhcp/dhcpd.conf
subnet 192.168.1.0 netmask 255.255.255.0 {
    range 192.168.1.100 192.168.1.200;
    option routers 192.168.1.1;
    next-server 192.168.1.1;  # TFTP server

    class "pxeclients" {
        match if substring (option vendor-class-identifier, 0, 9) = "PXEClient";
        if option client-architecture = 00:07 {
            filename "grubx64.efi";
        } else {
            filename "pxelinux.0";
        }
    }
}

host testserver1 {
    hardware ethernet aa:bb:cc:dd:ee:ff;
    fixed-address 192.168.1.101;
    filename "pxelinux.0";
}
```

**Python management pattern for dnsmasq:**
```python
import subprocess
import tempfile

class DnsmasqManager:
    def __init__(self, config_dir="/etc/dnsmasq.d"):
        self.config_dir = config_dir

    def add_host(self, mac, ip, hostname, boot_file="pxelinux.0"):
        config = f"dhcp-host={mac},{ip},{hostname}\n"
        path = f"{self.config_dir}/host-{hostname}.conf"
        with open(path, 'w') as f:
            f.write(config)
        self._reload()

    def remove_host(self, hostname):
        os.remove(f"{self.config_dir}/host-{hostname}.conf")
        self._reload()

    def _reload(self):
        subprocess.run(["systemctl", "reload", "dnsmasq"], check=True)
```

### 3.2 Kickstart / Preseed / AutoYaST Automation

**Kickstart (RHEL/CentOS/Fedora):**
```
# /var/www/html/ks/rhel9.ks
lang en_US.UTF-8
keyboard us
timezone UTC
rootpw --iscrypted $6$...
network --bootproto=dhcp --device=eth0 --activate
bootloader --location=mbr
clearpart --all --initlabel
autopart
text

%packages
@core
python3
openssh-server
%end

%post --log=/root/ks-post.log
# Register with test automation platform
curl -X POST http://automation-server/api/provision/complete \
  -d "hostname=$(hostname)&mac=$(cat /sys/class/net/eth0/address)"
%end

reboot
```

**Preseed (Debian/Ubuntu):**
```
# /var/www/html/preseed/ubuntu.cfg
d-i debian-installer/locale string en_US.UTF-8
d-i keyboard-configuration/xkb-keymap select us
d-i netcfg/choose_interface select auto
d-i netcfg/get_hostname string test-node
d-i partman-auto/method string regular
d-i partman-auto/choose_recipe select atomic
d-i passwd/root-password-crypted password $6$...
d-i pkgsel/include string python3 openssh-server
d-i finish-install/reboot_in_progress note

d-i preseed/late_command string \
  in-target curl -X POST http://automation-server/api/provision/complete
```

**AutoYaST (SUSE/SLES):**
```xml
<?xml version="1.0"?>
<profile xmlns="http://www.suse.com/1.0/yast2ns">
  <general>
    <mode><confirm config:type="boolean">false</confirm></mode>
  </general>
  <networking>
    <interfaces config:type="list">
      <interface>
        <bootproto>dhcp</bootproto>
        <device>eth0</device>
        <startmode>auto</startmode>
      </interface>
    </interfaces>
  </networking>
  <software>
    <packages config:type="list">
      <package>python3</package>
      <package>openssh</package>
    </packages>
  </software>
  <scripts>
    <post-scripts config:type="list">
      <script>
        <source><![CDATA[
curl -X POST http://automation-server/api/provision/complete
]]></source>
      </script>
    </post-scripts>
  </scripts>
</profile>
```

### 3.3 PXE Integration Pattern for Test Platforms

```
Test Orchestrator
    |
    ├── 1. Set boot device to PXE (via IPMI/Redfish)
    ├── 2. Generate kickstart/preseed with callback URL
    ├── 3. Update DHCP config (MAC -> IP + boot file)
    ├── 4. Power cycle server (via IPMI/Redfish)
    ├── 5. Monitor SOL for boot progress (optional)
    ├── 6. Wait for OS provision callback
    └── 7. Run tests via SSH
```

---
