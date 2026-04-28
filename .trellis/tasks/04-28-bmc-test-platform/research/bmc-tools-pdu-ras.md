## 4. PDU (Power Distribution Unit) Control

### 4.1 Common PDU Brands and Protocols

| Brand | REST API | SNMP | SSH/CLI | Python SDK |
|-------|----------|------|---------|------------|
| Raritan | Yes (JSON-RPC, REST) | Yes (v1/v2c/v3) | Yes | raritan-sdk (official) |
| APC (Schneider) | Yes (newer models) | Yes (v1/v2c/v3) | Yes | No official SDK |
| ServerTech (Legrand) | Yes (newer models) | Yes (v1/v2c/v3) | Yes | No official SDK |
| CyberPower | Limited | Yes | Yes | No official SDK |
| Eaton | Yes (newer ePDU) | Yes | Yes | No official SDK |
| Vertiv (Geist) | Yes | Yes | Yes | No official SDK |

### 4.2 SNMP-Based PDU Control

SNMP is the most universal PDU control method. Nearly all enterprise PDUs support it.

**Common MIBs:**

APC PDU (rPDU2):
```
# Outlet state OID pattern (APC rPDU2)
# .1.3.6.1.4.1.318.1.1.26.9.2.3.1.5.<outlet_index>
# Values: 1=off, 2=on

# Outlet control OID (APC rPDU2)
# .1.3.6.1.4.1.318.1.1.26.9.2.4.1.5.<outlet_index>
# Values: 1=immediateOn, 2=immediateOff, 3=immediateReboot,
#         4=delayedOn, 5=delayedOff, 6=delayedReboot, 7=cancel
```

ServerTech PDU:
```
# Outlet state OID (ServerTech Sentry4)
# .1.3.6.1.4.1.1718.4.1.8.3.1.1.<outlet_id>
# Values: 0=off, 1=on, 2=offWait, 3=onWait, ...

# Outlet control OID
# .1.3.6.1.4.1.1718.4.1.8.5.1.2.<outlet_id>
# Values: 0=noAction, 1=on, 2=off, 3=reboot
```

**Python SNMP control using pysnmp:**
```python
from pysnmp.hlapi import *

class SnmpPduController:
    def __init__(self, host, community="private", port=161):
        self.host = host
        self.community = community
        self.port = port

    def _snmp_set(self, oid, value, value_type=Integer):
        errorIndication, errorStatus, errorIndex, varBinds = next(
            setCmd(
                SnmpEngine(),
                CommunityData(self.community),
                UdpTransportTarget((self.host, self.port), timeout=10, retries=3),
                ContextData(),
                ObjectType(ObjectIdentity(oid), value_type(value))
            )
        )
        if errorIndication:
            raise RuntimeError(f"SNMP error: {errorIndication}")
        if errorStatus:
            raise RuntimeError(f"SNMP error: {errorStatus.prettyPrint()}")
        return varBinds

    def _snmp_get(self, oid):
        errorIndication, errorStatus, errorIndex, varBinds = next(
            getCmd(
                SnmpEngine(),
                CommunityData(self.community),
                UdpTransportTarget((self.host, self.port), timeout=10, retries=3),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )
        )
        if errorIndication:
            raise RuntimeError(f"SNMP error: {errorIndication}")
        return varBinds[0][1]

    # APC rPDU2 specific
    def apc_outlet_on(self, outlet_index):
        oid = f"1.3.6.1.4.1.318.1.1.26.9.2.4.1.5.{outlet_index}"
        self._snmp_set(oid, 1)

    def apc_outlet_off(self, outlet_index):
        oid = f"1.3.6.1.4.1.318.1.1.26.9.2.4.1.5.{outlet_index}"
        self._snmp_set(oid, 2)

    def apc_outlet_reboot(self, outlet_index):
        oid = f"1.3.6.1.4.1.318.1.1.26.9.2.4.1.5.{outlet_index}"
        self._snmp_set(oid, 3)

    def apc_get_outlet_state(self, outlet_index):
        oid = f"1.3.6.1.4.1.318.1.1.26.9.2.3.1.5.{outlet_index}"
        val = self._snmp_get(oid)
        return "on" if int(val) == 2 else "off"
```

### 4.3 REST-Based PDU Control

**Raritan JSON-RPC example:**
```python
import requests

class RaritanPduController:
    def __init__(self, host, user, password):
        self.base_url = f"https://{host}"
        self.session = requests.Session()
        self.session.auth = (user, password)
        self.session.verify = False

    def _jsonrpc(self, path, method, params=None):
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": 1
        }
        resp = self.session.post(f"{self.base_url}{path}", json=payload)
        resp.raise_for_status()
        return resp.json()

    def get_outlet_state(self, outlet_id):
        result = self._jsonrpc(
            f"/model/outlet/{outlet_id}", "getState"
        )
        return result["result"]["_ret_"]["powerState"]

    def set_outlet(self, outlet_id, state):
        # state: 0=off, 1=on
        self._jsonrpc(
            f"/model/outlet/{outlet_id}",
            "setPowerState",
            {"pstate": {"powerState": state}}
        )

    def cycle_outlet(self, outlet_id):
        self._jsonrpc(f"/model/outlet/{outlet_id}", "cyclePowerState")
```

**APC REST API (newer NMC3 cards):**
```python
import requests

class ApcRestPduController:
    def __init__(self, host, user, password):
        self.base_url = f"https://{host}/api"
        self.session = requests.Session()
        self.session.auth = (user, password)
        self.session.verify = False
        self.session.headers["Content-Type"] = "application/json"

    def get_outlets(self):
        return self.session.get(f"{self.base_url}/outlets").json()

    def outlet_control(self, outlet_id, action):
        # action: "on", "off", "reboot"
        return self.session.put(
            f"{self.base_url}/outlets/{outlet_id}/state",
            json={"state": action}
        ).json()
```

### 4.4 Python Libraries for PDU Management

| Library | PyPI | Protocol | Notes |
|---------|------|----------|-------|
| pysnmp-lextudio | `pip install pysnmp-lextudio` | SNMP v1/v2c/v3 | Universal; works with any SNMP PDU |
| easysnmp | `pip install easysnmp` | SNMP v1/v2c/v3 | C-based (net-snmp), faster but needs system libs |
| raritan-sdk | Raritan developer portal | JSON-RPC | Official Raritan SDK |
| requests | `pip install requests` | REST/HTTP | For REST-based PDU APIs |
| paramiko | `pip install paramiko` | SSH | For CLI-based PDU control over SSH |

**Abstraction pattern for multi-vendor PDU support:**
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

class ApcSnmpPdu(PduController): ...
class RaritanRestPdu(PduController): ...
class ServerTechSnmpPdu(PduController): ...
```
