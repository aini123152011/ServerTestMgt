## 5. RAS (Reliability, Availability, Serviceability) Error Injection

### 5.1 Linux EINJ (ACPI Error Injection Table)

The EINJ mechanism uses the ACPI 5.0+ Error Injection Table to inject hardware errors for testing OS/firmware error handling.

**Prerequisites:**
- BIOS/firmware must expose EINJ ACPI table (enable in BIOS setup)
- Linux kernel module: `einj` (part of `acpi` subsystem)
- Kernel config: `CONFIG_ACPI_APEI_EINJ=m`

**Setup:**
```bash
# Load the EINJ module
modprobe einj

# Verify EINJ is available
ls /sys/kernel/debug/apei/einj/
# Expected files: available_error_type, error_inject, error_type,
#                 flags, notrigger, param1, param2, param3, param4
```

**Available error types (bitmask):**
```
0x00000001 - Processor Correctable
0x00000002 - Processor Uncorrectable non-fatal
0x00000004 - Processor Uncorrectable fatal
0x00000008 - Memory Correctable
0x00000010 - Memory Uncorrectable non-fatal
0x00000020 - Memory Uncorrectable fatal
0x00000040 - PCI Express Correctable
0x00000080 - PCI Express Uncorrectable non-fatal
0x00000100 - PCI Express Uncorrectable fatal
0x00000200 - Platform Correctable
0x00000400 - Platform Uncorrectable non-fatal
0x00000800 - Platform Uncorrectable fatal
```

**Injection examples:**
```bash
# Check available error types
cat /sys/kernel/debug/apei/einj/available_error_type

# Inject correctable memory error
echo 0x8 > /sys/kernel/debug/apei/einj/error_type
echo 0x100000000 > /sys/kernel/debug/apei/einj/param1      # physical address
echo 0xfffffffffffff000 > /sys/kernel/debug/apei/einj/param2  # address mask
echo 1 > /sys/kernel/debug/apei/einj/error_inject

# Inject uncorrectable non-fatal memory error
echo 0x10 > /sys/kernel/debug/apei/einj/error_type
echo 1 > /sys/kernel/debug/apei/einj/error_inject

# Inject PCIe correctable error
echo 0x40 > /sys/kernel/debug/apei/einj/error_type
echo 1 > /sys/kernel/debug/apei/einj/error_inject
```

**Python wrapper for EINJ:**
```python
import os

class EinjController:
    EINJ_PATH = "/sys/kernel/debug/apei/einj"

    ERROR_TYPES = {
        "cpu_correctable":     0x00000001,
        "cpu_uncorrectable":   0x00000002,
        "cpu_fatal":           0x00000004,
        "mem_correctable":     0x00000008,
        "mem_uncorrectable":   0x00000010,
        "mem_fatal":           0x00000020,
        "pcie_correctable":    0x00000040,
        "pcie_uncorrectable":  0x00000080,
        "pcie_fatal":          0x00000100,
    }

    def __init__(self):
        if not os.path.exists(self.EINJ_PATH):
            os.system("modprobe einj")
        if not os.path.exists(self.EINJ_PATH):
            raise RuntimeError("EINJ not available. Check BIOS EINJ support.")

    def _write(self, filename, value):
        path = os.path.join(self.EINJ_PATH, filename)
        with open(path, 'w') as f:
            f.write(str(value))

    def _read(self, filename):
        path = os.path.join(self.EINJ_PATH, filename)
        with open(path, 'r') as f:
            return f.read().strip()

    def available_types(self):
        raw = self._read("available_error_type")
        avail = int(raw, 0)
        return {name: val for name, val in self.ERROR_TYPES.items() if avail & val}

    def inject(self, error_type, phys_addr=None, addr_mask=None):
        if isinstance(error_type, str):
            error_type = self.ERROR_TYPES[error_type]
        self._write("error_type", hex(error_type))
        if phys_addr is not None:
            self._write("param1", hex(phys_addr))
        if addr_mask is not None:
            self._write("param2", hex(addr_mask))
        self._write("error_inject", "1")
```

### 5.2 BMC-Based Error Injection

Some BMC firmware supports error injection via OEM IPMI commands or Redfish OEM extensions.

**Intel BMC (OpenBMC / AMI) -- IPMI raw commands:**
```bash
# Example: Intel platform memory CE injection via OEM IPMI
# (Exact commands are platform-specific, consult vendor docs)
ipmitool -I lanplus -H <bmc_ip> -U <user> -P <pass> raw 0x30 0xXX 0xYY ...
```

**Redfish OEM error injection (vendor-specific):**
```python
# Example pattern for vendor OEM Redfish error injection
# (Actual URIs and payloads vary by vendor)
body = {
    "Oem": {
        "VendorName": {
            "ErrorType": "MemoryCorrectable",
            "Target": "DIMM_A1"
        }
    }
}
client.post(
    "/redfish/v1/Systems/1/Oem/VendorName/Actions/ErrorInjection",
    body=body
)
```

### 5.3 Other RAS Testing Tools

**mcelog (Machine Check Exception logger):**
```bash
mcelog --client                              # read MCEs
mcelog --ascii < /dev/mcelog
mcelog --inject mce-test/corrected-memory.cfg  # software-simulated
```

**mce-inject (inject synthetic MCEs):**
```bash
git clone https://git.kernel.org/pub/scm/utils/cpu/mce-inject.git
cd mce-inject && make

cat > test.cfg << EOF
CPU 0 BANK 9
STATUS CORRECTED ENABLED 0x0000008000000000
ADDR 0x100000000
MISC 0x0000000000000000
EOF
mce-inject test.cfg
```

**rasdaemon (RAS event collector):**
```bash
apt-get install rasdaemon   # or yum install rasdaemon
systemctl start rasdaemon
ras-mc-ctl --errors          # query collected errors
ras-mc-ctl --summary
# SQLite database at /var/lib/rasdaemon/ras-mc_event.db
```

**edac-utils (Error Detection and Correction):**
```bash
edac-util --status
edac-util --report=full
cat /sys/devices/system/edac/mc/mc0/ce_count    # correctable errors
cat /sys/devices/system/edac/mc/mc0/ue_count    # uncorrectable errors
```

### 5.4 Common RAS Test Patterns

```
1. Memory CE Storm Test:
   - Inject N correctable memory errors via EINJ
   - Verify OS logs CE events (rasdaemon / mcelog)
   - Verify BMC SEL records the events
   - Verify page offlining if threshold exceeded

2. Memory UCE Recovery Test:
   - Inject uncorrectable non-fatal memory error
   - Verify OS handles via machine check handler
   - Verify affected process is killed (not kernel panic)
   - Verify BMC SEL records the event

3. PCIe AER Test:
   - Inject PCIe correctable/uncorrectable errors
   - Verify AER driver logs events
   - Verify device recovery (for non-fatal)
   - Verify link reset and re-enumeration

4. CPU Thermal Throttle Test:
   - Inject processor thermal event
   - Verify OS thermal management response
   - Verify BMC fan speed adjustment

5. Firmware-First Error Handling:
   - Inject error with firmware-first bit set
   - Verify BMC processes error first
   - Verify error is forwarded to OS via GHES/HEST
   - Verify both BMC SEL and OS logs are consistent
```

---

## 6. Architecture Recommendations for Test Platform Integration

### 6.1 Suggested Python Package Dependencies

```
# BMC / IPMI
pyghmi>=1.5.0           # Pure Python IPMI
python-ipmi>=0.5.0      # Alternative IPMI library

# Redfish
redfish>=3.2.0          # DMTF official Redfish client
sushy>=5.0.0            # OpenStack Redfish (higher-level)

# PDU / SNMP
pysnmp-lextudio>=6.0.0  # SNMP v1/v2c/v3 (maintained fork)
requests>=2.31.0        # REST API calls

# SSH / Remote execution
paramiko>=3.4.0         # SSH client
fabric>=3.2.0           # Higher-level SSH task runner

# PXE / Provisioning
jinja2>=3.1.0           # Template kickstart/preseed files

# Utilities
pyyaml>=6.0             # Config file parsing
pydantic>=2.5.0         # Data validation for BMC configs
```

### 6.2 Abstraction Layer Pattern

```
+------------------------------------------+
|           Test Orchestrator              |
+------------------------------------------+
|         BMC Abstraction Layer            |
|  +----------+  +----------+             |
|  |   IPMI   |  | Redfish  |             |
|  | Provider |  | Provider |             |
|  +----------+  +----------+             |
+------------------------------------------+
|  +----------+  +----------+  +--------+ |
|  |   PDU    |  |   PXE    |  |  RAS   | |
|  | Control  |  | Manager  |  | Inject | |
|  +----------+  +----------+  +--------+ |
+------------------------------------------+
|     Transport: IPMI / HTTPS / SNMP      |
+------------------------------------------+
```

---

## Caveats / Notes

- IPMI is being gradually superseded by Redfish, but many older servers (pre-2018) only support IPMI. A dual-stack approach (try Redfish first, fall back to IPMI) is recommended.
- PDU SNMP OIDs are vendor-specific and sometimes model-specific. Always verify OIDs against the actual MIB files shipped with the PDU.
- EINJ availability depends on BIOS configuration -- many server BIOSes ship with EINJ disabled by default. It must be enabled in BIOS setup before the ACPI table is exposed to the OS.
- BMC OEM error injection commands are highly vendor-specific and often undocumented publicly. Vendor NDA documentation or engineering contacts may be required.
- pysnmp has had maintenance issues; the `pysnmp-lextudio` fork (maintained by LeXtudio) is the recommended replacement as of 2024+.
- SOL via pyghmi can be fragile with some BMC firmware versions. ipmitool SOL is generally more battle-tested for production use.
- Redfish EventService (SSE/webhook) support varies significantly across BMC vendors. Test thoroughly before relying on it for event-driven automation.
