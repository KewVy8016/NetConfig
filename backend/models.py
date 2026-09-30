# Pydantic schemas สำหรับ NetConfig — Node, Transport, TestConnection
# response schema ห้ามคืน password หรือ secret ทุกกรณี

from __future__ import annotations

import re
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TransportType(str, Enum):
    """ประเภทการเชื่อมต่อที่รองรับ"""
    SSH = "ssh"
    TELNET = "telnet"
    SERIAL = "serial"


class DeviceKind(str, Enum):
    """ประเภทอุปกรณ์ที่แสดงใน UI"""
    ROUTER = "router"
    SWITCH = "switch"


class NodeStatus(str, Enum):
    """สถานะของ node — ต้องแสดงด้วย color + icon + text เสมอ"""
    CONNECTED = "connected"
    UNREACHABLE = "unreachable"
    CHECKING = "checking"
    UNKNOWN = "unknown"


class ConnectionStepStatus(str, Enum):
    """สถานะแต่ละขั้นของการทดสอบ connection"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# Transport configs
# ---------------------------------------------------------------------------

class SSHConfig(BaseModel):
    """การตั้งค่า SSH transport"""
    transport: Literal[TransportType.SSH] = TransportType.SSH
    host: str = Field(..., description="Management IP หรือ hostname")
    port: int = Field(default=22, ge=1, le=65535)
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)
    secret: str | None = Field(default=None, max_length=128, description="Enable secret")

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """ตรวจ IP address หรือ hostname รูปแบบที่ถูกต้อง"""
        import ipaddress
        v = v.strip()
        # ถ้ามีแต่ตัวเลขกับจุด น่าจะเป็น IP -> บังคับให้ต้องเป็น IP ที่ถูกต้อง
        if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", v):
            try:
                ipaddress.ip_address(v)
                return v
            except ValueError as exc:
                raise ValueError("รูปแบบ IPv4 ไม่ถูกต้อง") from exc

        # ถ้าไม่ใช่ IP ให้ตรวจว่าเป็น hostname/FQDN อย่างง่าย
        if re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9\-\.]{0,253}[a-zA-Z0-9])?$", v):
            return v
        raise ValueError("host ต้องเป็น IP address หรือ hostname ที่ถูกต้อง")


class TelnetConfig(BaseModel):
    """การตั้งค่า Telnet — รองรับทั้ง username/password และ password-only"""
    transport: Literal[TransportType.TELNET] = TransportType.TELNET
    host: str = Field(..., description="Management IP หรือ hostname")
    port: int = Field(default=23, ge=1, le=65535)
    username: str = Field(default="", max_length=64, description="เว้นว่างได้เมื่ออุปกรณ์ถามเฉพาะ password")
    password: str = Field(..., min_length=1, max_length=128)
    secret: str | None = Field(default=None, max_length=128)

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """ตรวจ IP address หรือ hostname"""
        import ipaddress
        v = v.strip()
        # ถ้ามีแต่ตัวเลขกับจุด น่าจะเป็น IP -> บังคับให้ต้องเป็น IP ที่ถูกต้อง
        if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", v):
            try:
                ipaddress.ip_address(v)
                return v
            except ValueError as exc:
                raise ValueError("รูปแบบ IPv4 ไม่ถูกต้อง") from exc

        # ถ้าไม่ใช่ IP ให้ตรวจว่าเป็น hostname/FQDN อย่างง่าย
        if re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9\-\.]{0,253}[a-zA-Z0-9])?$", v):
            return v
        raise ValueError("host ต้องเป็น IP address หรือ hostname ที่ถูกต้อง")


class SerialConfig(BaseModel):
    """การตั้งค่า Serial console — credential เป็นตัวเลือกตาม login ของอุปกรณ์"""
    transport: Literal[TransportType.SERIAL] = TransportType.SERIAL
    serial_port: str = Field(..., description="Serial port เช่น COM3 หรือ /dev/ttyUSB0")
    baudrate: int = Field(default=9600, description="Baud rate")
    username: str = Field(default="", max_length=64, description="เว้นว่างได้เมื่อ console ไม่ถาม username")
    password: str = Field(default="", max_length=128, description="เว้นว่างได้เมื่อ console ไม่ถาม password")
    secret: str | None = Field(default=None, max_length=128)

    @field_validator("serial_port")
    @classmethod
    def validate_serial_port(cls, v: str) -> str:
        """ตรวจรูปแบบ COM port หรือ Unix device path"""
        v = v.strip()
        if re.match(r"^(COM\d+|/dev/tty\w+)$", v, re.IGNORECASE):
            return v
        raise ValueError("serial_port ต้องเป็น COMx หรือ /dev/ttyXxx")


# ---------------------------------------------------------------------------
# Node schemas
# ---------------------------------------------------------------------------

class NodeCreate(BaseModel):
    """Request body สำหรับสร้าง node ใหม่"""
    hostname: str = Field(..., min_length=1, max_length=64, description="ชื่ออุปกรณ์")
    device_kind: DeviceKind = Field(default=DeviceKind.ROUTER)
    transport_config: SSHConfig | TelnetConfig | SerialConfig = Field(
        ..., discriminator="transport"
    )

    @field_validator("hostname")
    @classmethod
    def validate_hostname(cls, v: str) -> str:
        """ตรวจ hostname ไม่มีอักขระพิเศษที่อันตราย"""
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9_\-\.]{1,64}$", v):
            raise ValueError("hostname ต้องเป็น alphanumeric, _, -, . เท่านั้น")
        return v


class NodeResponse(BaseModel):
    """Response สำหรับ node — ห้ามมี password หรือ secret"""
    id: str
    hostname: str
    host: str | None = None          # None สำหรับ Serial
    transport: TransportType
    port: int | None = None          # None สำหรับ Serial
    serial_port: str | None = None   # เฉพาะ Serial
    device_kind: DeviceKind
    status: NodeStatus = NodeStatus.UNKNOWN
    created_at: str
    updated_at: str


class NodeListResponse(BaseModel):
    """Response สำหรับรายการ nodes"""
    total: int
    nodes: list[NodeResponse]


class SerialPortOption(BaseModel):
    """พอร์ต Serial ที่เครื่อง backend ตรวจพบสำหรับให้ผู้ใช้เลือก"""

    port: str
    description: str
    is_usb: bool


class SerialPortsResponse(BaseModel):
    """รายการพอร์ต Serial ปัจจุบันของเครื่อง backend"""

    ports: list[SerialPortOption] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Test connection schemas
# ---------------------------------------------------------------------------

class ConnectionStep(BaseModel):
    """ผลลัพธ์แต่ละขั้นของการทดสอบ connection"""
    step: str = Field(..., description="ชื่อขั้น: ping, port, login, hostname")
    status: ConnectionStepStatus
    message: str = Field(..., description="ข้อความภาษาไทยสำหรับผู้ใช้")
    detail: str | None = Field(
        default=None, description="ข้อมูลเพิ่มเติมที่ปลอดภัย (redact แล้ว)"
    )


class TestConnectionResponse(BaseModel):
    """ผลลัพธ์รวมของการทดสอบ connection แต่ละ node"""
    node_id: str
    overall_status: ConnectionStepStatus
    steps: list[ConnectionStep]
    hostname_detected: str | None = Field(
        default=None, description="Hostname ที่อ่านจาก device จริง"
    )


# ---------------------------------------------------------------------------
# Error response schema
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    """รูปแบบ error response มาตรฐาน — ห้ามมี traceback หรือ secret"""
    code: str = Field(..., description="Error code เช่น VALIDATION_ERROR")
    message_th: str = Field(..., description="ข้อความภาษาไทยสำหรับผู้ใช้")
    correlation_id: str = Field(..., description="ID สำหรับ trace log")
    details: dict | None = Field(
        default=None, description="ข้อมูลเพิ่มเติมที่ปลอดภัย เช่น field errors"
    )


# ---------------------------------------------------------------------------
# Interface configuration และ operation schemas
# ---------------------------------------------------------------------------

class InterfaceConfig(BaseModel):
    """ค่าตั้งค่า IPv4 interface ที่ผ่านการตรวจสอบก่อน render CLI"""

    interface_name: str = Field(..., min_length=1, max_length=64)
    ip_address: str = Field(..., description="IPv4 address ของ interface")
    subnet_mask: str = Field(..., description="Subnet mask แบบ dotted decimal")
    description: str | None = Field(default=None, max_length=240)
    admin_up: bool = True

    @field_validator("interface_name")
    @classmethod
    def validate_interface_name(cls, value: str) -> str:
        """ป้องกันอักขระที่ทำให้หลุดจากคำสั่ง interface context"""
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9/_.-]{0,63}", value):
            raise ValueError("ชื่อ interface ไม่ถูกต้อง")
        return value

    @field_validator("ip_address")
    @classmethod
    def validate_ipv4_address(cls, value: str) -> str:
        """ตรวจว่าเป็น IPv4 address ที่ใช้งานได้"""
        import ipaddress

        try:
            address = ipaddress.ip_address(value.strip())
        except ValueError as exc:
            raise ValueError("ip_address ต้องเป็น IPv4 address ที่ถูกต้อง") from exc
        if address.version != 4:
            raise ValueError("รองรับเฉพาะ IPv4 ใน phase นี้")
        return str(address)

    @field_validator("subnet_mask")
    @classmethod
    def validate_subnet_mask(cls, value: str) -> str:
        """ตรวจ subnet mask แบบ contiguous dotted decimal"""
        import ipaddress

        value = value.strip()
        try:
            network = ipaddress.IPv4Network(f"0.0.0.0/{value}")
        except ValueError as exc:
            raise ValueError("subnet_mask ต้องเป็น dotted decimal ที่ถูกต้อง") from exc
        return str(network.netmask)


class InterfaceAdminConfig(BaseModel):
    """ค่าควบคุมสถานะเปิด/ปิด interface โดยไม่ต้องเปลี่ยน IPv4 เดิม"""

    interface_name: str = Field(..., min_length=1, max_length=64)
    admin_up: bool

    @field_validator("interface_name")
    @classmethod
    def validate_interface_name(cls, value: str) -> str:
        """ตรวจชื่อ interface ก่อนสร้างคำสั่ง shutdown หรือ no shutdown"""
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9/_.-]{0,63}", value):
            raise ValueError("ชื่อ interface ไม่ถูกต้อง")
        return value


class InterfaceCurrentResponse(BaseModel):
    """ค่าปัจจุบันของ interface ที่อ่านจากอุปกรณ์เพื่อ prefill ฟอร์ม"""

    node_id: str
    interface_name: str
    ip_address: str | None = None
    subnet_mask: str | None = None
    description: str | None = None
    admin_up: bool
    status: str
    protocol: str
    collected_at: str


class LoopbackConfig(BaseModel):
    """ค่าตั้งค่า Loopback IPv4 ที่ผ่านการตรวจสอบก่อน render CLI"""

    loopback_id: int = Field(..., ge=0, le=2147483647)
    ip_address: str = Field(..., description="IPv4 address ของ Loopback")
    subnet_mask: str = Field(..., description="Subnet mask แบบ dotted decimal")
    description: str | None = Field(default=None, max_length=240)
    admin_up: bool = True

    @field_validator("ip_address")
    @classmethod
    def validate_ipv4_address(cls, value: str) -> str:
        """ตรวจว่าเป็น IPv4 address ที่ใช้งานได้"""
        import ipaddress

        try:
            address = ipaddress.ip_address(value.strip())
        except ValueError as exc:
            raise ValueError("ip_address ต้องเป็น IPv4 address ที่ถูกต้อง") from exc
        if address.version != 4:
            raise ValueError("รองรับเฉพาะ IPv4 ใน phase นี้")
        return str(address)

    @field_validator("subnet_mask")
    @classmethod
    def validate_subnet_mask(cls, value: str) -> str:
        """ตรวจ subnet mask แบบ contiguous dotted decimal"""
        import ipaddress

        value = value.strip()
        try:
            network = ipaddress.IPv4Network(f"0.0.0.0/{value}")
        except ValueError as exc:
            raise ValueError("subnet_mask ต้องเป็น dotted decimal ที่ถูกต้อง") from exc
        return str(network.netmask)


class LoopbackRemoveConfig(BaseModel):
    """ระบุ Loopback ที่จะลบโดยไม่รับ CLI จาก browser"""

    loopback_id: int = Field(..., ge=0, le=2147483647)


class DeviceCapabilitiesResponse(BaseModel):
    """ความสามารถที่อ่านจาก IOS ด้วย show command ฝั่ง server เท่านั้น"""

    node_id: str
    switchport_supported: bool
    vlan_supported: bool
    collected_at: str


class InterfaceCapabilitiesResponse(BaseModel):
    """สถานะ switchport ของ interface ที่อ่านจาก IOS แบบ read-only"""

    node_id: str
    interface_name: str
    switchport_state: Literal["enabled", "disabled", "unsupported", "unknown"]
    collected_at: str


class VlanEntry(BaseModel):
    """VLAN ที่ parser อ่านจาก show vlan brief ได้อย่างมั่นใจ"""

    vlan_id: int = Field(..., ge=1, le=4094)
    name: str
    status: str
    ports: list[str] = Field(default_factory=list)


class VlanListResponse(BaseModel):
    """รายการ VLAN actual state สำหรับ form L2/SVI"""

    node_id: str
    vlans: list[VlanEntry]
    collected_at: str


class AccessPortConfig(BaseModel):
    """ค่าตั้ง L2 access port ที่ browser ส่งเป็น typed intent เท่านั้น"""

    interface_name: str = Field(..., min_length=1, max_length=64)
    vlan_id: int = Field(..., ge=1, le=4094)
    description: str | None = Field(default=None, max_length=240)
    admin_up: bool = True

    @field_validator("interface_name")
    @classmethod
    def validate_interface_name(cls, value: str) -> str:
        """ป้องกันอักขระหลุดจาก interface context"""
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9/_.-]{0,63}", value):
            raise ValueError("ชื่อ interface ไม่ถูกต้อง")
        if re.match(r"(?:loopback|vlan)\d*$", value, re.IGNORECASE):
            raise ValueError("L2 access port ต้องเป็น physical interface")
        return value


class VlanConfig(BaseModel):
    """VLAN resource ที่สร้างผ่าน typed form"""

    vlan_id: int = Field(..., ge=2, le=4094)
    name: str | None = Field(default=None, max_length=32)

    @field_validator("name")
    @classmethod
    def validate_vlan_name(cls, value: str | None) -> str | None:
        """จำกัดชื่อ VLAN ให้เป็น token IOS เดียวและไม่มี command injection"""
        if value is None or not value.strip():
            return None
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,31}", value):
            raise ValueError("ชื่อ VLAN ใช้ได้เฉพาะตัวอักษร ตัวเลข จุด ขีด และขีดล่าง")
        return value


class VlanRemoveConfig(BaseModel):
    """VLAN resource ที่ผู้ใช้เลือกเพื่อลบอย่างชัดเจน"""

    vlan_id: int = Field(..., ge=2, le=4094)


class SviConfig(BaseModel):
    """ค่า IPv4 ของ SVI ซึ่งอ้าง VLAN ที่มีอยู่จริง"""

    vlan_id: int = Field(..., ge=1, le=4094)
    ip_address: str
    subnet_mask: str
    description: str | None = Field(default=None, max_length=240)
    admin_up: bool = True

    @field_validator("ip_address")
    @classmethod
    def validate_ipv4_address(cls, value: str) -> str:
        """ตรวจ IPv4 ก่อน render SVI command"""
        import ipaddress

        try:
            address = ipaddress.ip_address(value.strip())
        except ValueError as exc:
            raise ValueError("ip_address ต้องเป็น IPv4 address ที่ถูกต้อง") from exc
        if address.version != 4:
            raise ValueError("รองรับเฉพาะ IPv4 ใน phase นี้")
        return str(address)

    @field_validator("subnet_mask")
    @classmethod
    def validate_subnet_mask(cls, value: str) -> str:
        """ตรวจ subnet mask dotted decimal แบบ contiguous"""
        import ipaddress

        value = value.strip()
        try:
            network = ipaddress.IPv4Network(f"0.0.0.0/{value}")
        except ValueError as exc:
            raise ValueError("subnet_mask ต้องเป็น dotted decimal ที่ถูกต้อง") from exc
        return str(network.netmask)


class SviRemoveConfig(BaseModel):
    """ระบุ SVI ที่ลบโดยไม่ให้ browser ส่ง CLI"""

    vlan_id: int = Field(..., ge=1, le=4094)


class RoutedPortConfig(BaseModel):
    """ค่าตั้ง L3 routed port ที่ต้องเปลี่ยนจาก switchport อย่างชัดเจน"""

    interface_name: str = Field(..., min_length=1, max_length=64)
    ip_address: str
    subnet_mask: str
    description: str | None = Field(default=None, max_length=240)
    admin_up: bool = True

    @field_validator("interface_name")
    @classmethod
    def validate_interface_name(cls, value: str) -> str:
        """ป้องกันอักขระหลุดจาก interface context"""
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9/_.-]{0,63}", value):
            raise ValueError("ชื่อ interface ไม่ถูกต้อง")
        if re.match(r"(?:loopback|vlan)\d*$", value, re.IGNORECASE):
            raise ValueError("L3 routed port ต้องเป็น physical interface")
        return value

    @field_validator("ip_address")
    @classmethod
    def validate_ipv4_address(cls, value: str) -> str:
        """ตรวจ IPv4 ก่อน render routed-port command"""
        import ipaddress

        try:
            address = ipaddress.ip_address(value.strip())
        except ValueError as exc:
            raise ValueError("ip_address ต้องเป็น IPv4 address ที่ถูกต้อง") from exc
        if address.version != 4:
            raise ValueError("รองรับเฉพาะ IPv4 ใน phase นี้")
        return str(address)

    @field_validator("subnet_mask")
    @classmethod
    def validate_subnet_mask(cls, value: str) -> str:
        """ตรวจ subnet mask dotted decimal แบบ contiguous"""
        import ipaddress

        value = value.strip()
        try:
            network = ipaddress.IPv4Network(f"0.0.0.0/{value}")
        except ValueError as exc:
            raise ValueError("subnet_mask ต้องเป็น dotted decimal ที่ถูกต้อง") from exc
        return str(network.netmask)


class RoutedPortRestoreConfig(BaseModel):
    """ระบุ L3 routed port ที่คืนเป็น L2 switchport พื้นฐาน"""

    interface_name: str = Field(..., min_length=1, max_length=64)

    @field_validator("interface_name")
    @classmethod
    def validate_interface_name(cls, value: str) -> str:
        """ป้องกันอักขระหลุดจาก interface context"""
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9/_.-]{0,63}", value):
            raise ValueError("ชื่อ interface ไม่ถูกต้อง")
        return value


class StaticRouteConfig(BaseModel):
    """ค่าตั้ง Static/Default route ที่ระบุ next-hop หรือ exit interface เพียงอย่างเดียว"""

    destination: str = Field(..., description="Network address หรือ 0.0.0.0 สำหรับ default route")
    subnet_mask: str = Field(..., description="Subnet mask แบบ dotted decimal")
    next_hop: str | None = Field(default=None, description="IPv4 next-hop")
    exit_interface: str | None = Field(default=None, max_length=64)

    @field_validator("destination", "next_hop")
    @classmethod
    def validate_route_ipv4(cls, value: str | None, info: ValidationInfo) -> str | None:
        """ตรวจ IPv4 ของปลายทางและ next-hop โดยไม่ยอมรับ multicast/unspecified next-hop"""
        if value is None:
            return None
        import ipaddress

        try:
            address = ipaddress.IPv4Address(value.strip())
        except ValueError as exc:
            raise ValueError(f"{info.field_name} ต้องเป็น IPv4 address ที่ถูกต้อง") from exc
        if info.field_name == "next_hop" and (address.is_multicast or address.is_unspecified):
            raise ValueError("next_hop ต้องเป็น unicast IPv4 ที่ใช้งานได้")
        return str(address)

    @field_validator("subnet_mask")
    @classmethod
    def validate_route_mask(cls, value: str) -> str:
        """ตรวจ subnet mask ว่าเป็น dotted decimal และบิตต่อเนื่อง"""
        import ipaddress

        try:
            network = ipaddress.IPv4Network(f"0.0.0.0/{value.strip()}")
        except ValueError as exc:
            raise ValueError("subnet_mask ต้องเป็น dotted decimal ที่ถูกต้อง") from exc
        return str(network.netmask)

    @field_validator("exit_interface")
    @classmethod
    def validate_exit_interface(cls, value: str | None) -> str | None:
        """ตรวจชื่อ exit interface เพื่อป้องกัน command injection"""
        if value is None:
            return None
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9/_.-]{0,63}", value):
            raise ValueError("ชื่อ exit_interface ไม่ถูกต้อง")
        return value

    @model_validator(mode="after")
    def validate_route_contract(self) -> StaticRouteConfig:
        """บังคับ network boundary และ target เพียงชนิดเดียว"""
        import ipaddress

        if (self.next_hop is None) == (self.exit_interface is None):
            raise ValueError("ต้องระบุ next_hop หรือ exit_interface เพียงอย่างเดียว")
        network = ipaddress.IPv4Network(f"{self.destination}/{self.subnet_mask}", strict=False)
        if str(network.network_address) != self.destination:
            raise ValueError("destination ต้องเป็น network address ตาม subnet mask")
        if network.network_address.is_multicast:
            raise ValueError("destination ต้องไม่เป็น multicast network")
        return self


class StaticRouteUpdate(BaseModel):
    """คำขอแก้ route โดยลบค่าปัจจุบันแล้วเพิ่มค่าที่ต้องการใน preview เดียว"""

    current: StaticRouteConfig
    desired: StaticRouteConfig

    @model_validator(mode="after")
    def validate_changed(self) -> StaticRouteUpdate:
        """ปฏิเสธ update ที่ไม่มีข้อมูลเปลี่ยนแปลง"""
        if self.current == self.desired:
            raise ValueError("route ใหม่ต้องแตกต่างจากค่าปัจจุบัน")
        return self


class StaticRouteEntry(StaticRouteConfig):
    """Static route หนึ่งรายการที่อ่านจาก running-config"""

    route_type: Literal["default", "static"]


class StaticRouteListResponse(BaseModel):
    """รายการ Static/Default route ปัจจุบันของ node"""

    node_id: str
    routes: list[StaticRouteEntry]
    collected_at: str


class RipNetworkConfig(BaseModel):
    """ค่าตั้ง RIP network หนึ่งรายการพร้อม version ของ process"""

    version: Literal[1, 2] = 2
    network: str = Field(..., description="Classful IPv4 network สำหรับคำสั่ง router rip")

    @field_validator("network")
    @classmethod
    def validate_rip_network(cls, value: str) -> str:
        """บังคับ major network boundary ที่ IOS RIP `network` command ใช้งานจริง"""
        import ipaddress

        try:
            address = ipaddress.IPv4Address(value.strip())
        except ValueError as exc:
            raise ValueError("network ต้องเป็น IPv4 address ที่ถูกต้อง") from exc
        first_octet = int(str(address).split(".")[0])
        if address.is_multicast or address.is_unspecified or first_octet == 127 or first_octet >= 224:
            raise ValueError("network ต้องเป็น unicast IPv4 major network")
        prefix = 8 if first_octet <= 126 else 16 if first_octet <= 191 else 24
        major_network = ipaddress.IPv4Network(f"{address}/{prefix}", strict=False)
        if address != major_network.network_address:
            raise ValueError(f"network ต้องเป็น major network boundary เช่น {major_network.network_address}")
        return str(address)


class RipNetworkUpdate(BaseModel):
    """คำขอแก้ RIP network โดยอ้างค่าเดิมและค่าที่ต้องการ"""

    current: RipNetworkConfig
    desired: RipNetworkConfig

    @model_validator(mode="after")
    def validate_changed(self) -> RipNetworkUpdate:
        """ปฏิเสธ update ที่ไม่มีค่าเปลี่ยน"""
        if self.current == self.desired:
            raise ValueError("RIP network ใหม่ต้องแตกต่างจากค่าปัจจุบัน")
        return self


class RipProcessConfig(BaseModel):
    """snapshot ของ RIP process สำหรับยืนยันก่อน Remove Protocol"""

    version: Literal[1, 2]
    networks: list[str] = Field(default_factory=list)
    no_auto_summary: bool

    @field_validator("networks")
    @classmethod
    def validate_networks(cls, values: list[str]) -> list[str]:
        """ตรวจ network ทุกค่าและห้าม duplicate ใน process snapshot"""
        normalized = [RipNetworkConfig(version=2, network=value).network for value in values]
        if len(set(normalized)) != len(normalized):
            raise ValueError("RIP networks ห้ามซ้ำกัน")
        return normalized


class RipStateResponse(BaseModel):
    """สถานะ RIP ที่อ่านจาก running-config จริง"""

    node_id: str
    enabled: bool
    version: Literal[1, 2] | None = None
    networks: list[str] = Field(default_factory=list)
    no_auto_summary: bool = False
    collected_at: str


class OspfNetworkConfig(BaseModel):
    """ค่าตั้ง OSPF process, router ID และ network IPv4 หนึ่งรายการ"""

    process_id: int = Field(..., ge=1, le=65535)
    router_id: str
    network: str
    subnet_mask: str
    area: int = Field(..., ge=0, le=4_294_967_295)

    @field_validator("router_id", "network")
    @classmethod
    def validate_ospf_ipv4(cls, value: str, info: ValidationInfo) -> str:
        """ตรวจ IPv4 สำหรับ router ID และ network"""
        import ipaddress

        try:
            address = ipaddress.IPv4Address(value.strip())
        except ValueError as exc:
            raise ValueError(f"{info.field_name} ต้องเป็น IPv4 address ที่ถูกต้อง") from exc
        if address.is_multicast or address.is_unspecified:
            raise ValueError(f"{info.field_name} ต้องเป็น unicast IPv4 ที่ใช้งานได้")
        return str(address)

    @field_validator("subnet_mask")
    @classmethod
    def validate_ospf_mask(cls, value: str) -> str:
        """ตรวจ dotted decimal netmask แบบ contiguous"""
        import ipaddress

        try:
            return str(ipaddress.IPv4Network(f"0.0.0.0/{value.strip()}").netmask)
        except ValueError as exc:
            raise ValueError("subnet_mask ต้องเป็น dotted decimal ที่ถูกต้อง") from exc

    @model_validator(mode="after")
    def validate_ospf_network_boundary(self) -> OspfNetworkConfig:
        """บังคับให้ network ตรง boundary ของ netmask"""
        import ipaddress

        network = ipaddress.IPv4Network(f"{self.network}/{self.subnet_mask}", strict=False)
        if str(network.network_address) != self.network:
            raise ValueError("network ต้องเป็น network address ตาม subnet mask")
        return self


class OspfNetworkState(BaseModel):
    """OSPF network ที่อ่านจากอุปกรณ์; router ID อาจยังไม่ถูกกำหนด"""

    process_id: int = Field(..., ge=1, le=65535)
    router_id: str | None = None
    network: str
    subnet_mask: str
    area: int = Field(..., ge=0, le=4_294_967_295)

    @model_validator(mode="after")
    def validate_read_network(self) -> OspfNetworkState:
        """ใช้กฎ IPv4 เดียวกับ input โดยไม่สร้าง router ID ปลอม"""
        OspfNetworkConfig.model_validate({**self.model_dump(), "router_id": self.router_id or "1.1.1.1"})
        return self


class OspfNetworkUpdate(BaseModel):
    """คำขอแก้ OSPF network โดยระบุค่าเดิมและค่าที่ต้องการ"""

    current: OspfNetworkConfig | OspfNetworkState
    desired: OspfNetworkConfig

    @model_validator(mode="after")
    def validate_changed(self) -> OspfNetworkUpdate:
        """ปฏิเสธ update ที่ไม่มีค่าเปลี่ยน"""
        if self.current == self.desired:
            raise ValueError("OSPF network ใหม่ต้องแตกต่างจากค่าปัจจุบัน")
        return self


class OspfProcessConfig(BaseModel):
    """snapshot OSPF process สำหรับยืนยันก่อน Remove Protocol"""

    process_id: int = Field(..., ge=1, le=65535)
    router_id: str | None = None
    networks: list[OspfNetworkState] = Field(default_factory=list)


class OspfStateResponse(BaseModel):
    """สถานะ OSPF ที่อ่านจาก running-config จริง"""

    node_id: str
    enabled: bool
    process_id: int | None = None
    router_id: str | None = None
    networks: list[OspfNetworkState] = Field(default_factory=list)
    collected_at: str


class EigrpNetworkConfig(BaseModel):
    """ค่าตั้ง EIGRP AS, router ID และ network IPv4 หนึ่งรายการ"""

    as_number: int = Field(..., ge=1, le=65535)
    router_id: str
    network: str
    subnet_mask: str

    @field_validator("router_id", "network")
    @classmethod
    def validate_eigrp_ipv4(cls, value: str, info: ValidationInfo) -> str:
        """ตรวจ IPv4 สำหรับ router ID และ network"""
        import ipaddress

        try:
            address = ipaddress.IPv4Address(value.strip())
        except ValueError as exc:
            raise ValueError(f"{info.field_name} ต้องเป็น IPv4 address ที่ถูกต้อง") from exc
        if address.is_multicast or address.is_unspecified:
            raise ValueError(f"{info.field_name} ต้องเป็น unicast IPv4 ที่ใช้งานได้")
        return str(address)

    @field_validator("subnet_mask")
    @classmethod
    def validate_eigrp_mask(cls, value: str) -> str:
        """ตรวจ dotted decimal netmask แบบ contiguous"""
        import ipaddress

        try:
            return str(ipaddress.IPv4Network(f"0.0.0.0/{value.strip()}").netmask)
        except ValueError as exc:
            raise ValueError("subnet_mask ต้องเป็น dotted decimal ที่ถูกต้อง") from exc

    @model_validator(mode="after")
    def validate_eigrp_network_boundary(self) -> EigrpNetworkConfig:
        """บังคับ network boundary ตาม netmask"""
        import ipaddress

        network = ipaddress.IPv4Network(f"{self.network}/{self.subnet_mask}", strict=False)
        if str(network.network_address) != self.network:
            raise ValueError("network ต้องเป็น network address ตาม subnet mask")
        return self


class EigrpNetworkState(BaseModel):
    """EIGRP network ที่อ่านจากอุปกรณ์โดย router ID อาจว่าง"""

    as_number: int = Field(..., ge=1, le=65535)
    router_id: str | None = None
    network: str
    subnet_mask: str

    @model_validator(mode="after")
    def validate_read_network(self) -> EigrpNetworkState:
        """ตรวจ network และ mask ตามสัญญา input โดยไม่เติม router ID ในผลอ่าน"""
        EigrpNetworkConfig.model_validate({**self.model_dump(), "router_id": self.router_id or "1.1.1.1"})
        return self


class EigrpNetworkUpdate(BaseModel):
    """คำขอแก้ EIGRP network โดยลบค่าเดิมก่อนเพิ่มใหม่"""

    current: EigrpNetworkConfig | EigrpNetworkState
    desired: EigrpNetworkConfig

    @model_validator(mode="after")
    def validate_eigrp_update_changes_value(self) -> EigrpNetworkUpdate:
        """ปฏิเสธ update ที่ไม่มีค่าเปลี่ยนเพื่อลดคำสั่งโดยไม่จำเป็น"""
        if self.current == self.desired:
            raise ValueError("EIGRP network ใหม่ต้องแตกต่างจากค่าปัจจุบัน")
        return self


class EigrpProcessConfig(BaseModel):
    """snapshot EIGRP process สำหรับยืนยันก่อน Remove Protocol"""

    as_number: int = Field(..., ge=1, le=65535)
    router_id: str | None = None
    networks: list[EigrpNetworkState] = Field(default_factory=list)
    no_auto_summary: bool


class EigrpStateResponse(BaseModel):
    """สถานะ EIGRP ที่อ่านจาก running-config จริง"""

    node_id: str
    enabled: bool
    as_number: int | None = None
    router_id: str | None = None
    networks: list[EigrpNetworkState] = Field(default_factory=list)
    no_auto_summary: bool = False
    collected_at: str


class BgpNeighborConfig(BaseModel):
    """ค่าตั้ง BGP process และ neighbor หนึ่งรายการ"""

    local_as: int = Field(..., ge=1, le=4294967295)
    router_id: str
    neighbor_ip: str
    remote_as: int = Field(..., ge=1, le=4294967295)
    description: str | None = Field(default=None, max_length=240)

    @field_validator("router_id", "neighbor_ip")
    @classmethod
    def validate_bgp_ipv4(cls, value: str, info: ValidationInfo) -> str:
        """ตรวจ IPv4 router ID และ neighbor address"""
        import ipaddress

        try:
            address = ipaddress.IPv4Address(value.strip())
        except ValueError as exc:
            raise ValueError(f"{info.field_name} ต้องเป็น IPv4 address ที่ถูกต้อง") from exc
        if address.is_multicast or address.is_unspecified:
            raise ValueError(f"{info.field_name} ต้องเป็น unicast IPv4 ที่ใช้งานได้")
        return str(address)

    @field_validator("description")
    @classmethod
    def validate_bgp_description(cls, value: str | None) -> str | None:
        """ห้าม description มี newline เพื่อคง CLI template ปลอดภัย"""
        if value is not None and any(char in value for char in "\r\n"):
            raise ValueError("description ห้ามมีบรรทัดใหม่")
        return value or None


class BgpNeighborState(BaseModel):
    """BGP neighbor ที่อ่านได้แม้ IOS ยังไม่กำหนด router ID"""

    local_as: int = Field(..., ge=1, le=4294967295)
    router_id: str | None = None
    neighbor_ip: str
    remote_as: int = Field(..., ge=1, le=4294967295)
    description: str | None = Field(default=None, max_length=240)

    @model_validator(mode="after")
    def validate_read_neighbor(self) -> BgpNeighborState:
        """ตรวจ neighbor ด้วยกฎเดิมโดยไม่เปลี่ยนค่า router ID ที่อ่านได้"""
        BgpNeighborConfig.model_validate({**self.model_dump(), "router_id": self.router_id or "1.1.1.1"})
        return self


class BgpNetworkConfig(BaseModel):
    """network ที่ BGP จะ advertise ภายใต้ local AS ที่ระบุ"""

    local_as: int = Field(..., ge=1, le=4294967295)
    network: str
    subnet_mask: str

    @field_validator("network")
    @classmethod
    def validate_bgp_network(cls, value: str) -> str:
        """ตรวจ IPv4 network"""
        import ipaddress

        try:
            return str(ipaddress.IPv4Address(value.strip()))
        except ValueError as exc:
            raise ValueError("network ต้องเป็น IPv4 address ที่ถูกต้อง") from exc

    @field_validator("subnet_mask")
    @classmethod
    def validate_bgp_mask(cls, value: str) -> str:
        """ตรวจ dotted decimal netmask แบบ contiguous"""
        import ipaddress

        try:
            return str(ipaddress.IPv4Network(f"0.0.0.0/{value.strip()}").netmask)
        except ValueError as exc:
            raise ValueError("subnet_mask ต้องเป็น dotted decimal ที่ถูกต้อง") from exc

    @model_validator(mode="after")
    def validate_bgp_network_boundary(self) -> BgpNetworkConfig:
        """บังคับ network boundary ตาม netmask"""
        import ipaddress

        if str(ipaddress.IPv4Network(f"{self.network}/{self.subnet_mask}", strict=False).network_address) != self.network:
            raise ValueError("network ต้องเป็น network address ตาม subnet mask")
        return self


class BgpNeighborUpdate(BaseModel):
    """คำขอแก้ BGP neighbor โดยลบค่าเดิมก่อนเพิ่มใหม่"""

    current: BgpNeighborConfig | BgpNeighborState
    desired: BgpNeighborConfig

    @model_validator(mode="after")
    def validate_neighbor_change(self) -> BgpNeighborUpdate:
        """ปฏิเสธ update ที่ไม่มีค่าเปลี่ยน"""
        if self.current == self.desired:
            raise ValueError("BGP neighbor ใหม่ต้องแตกต่างจากค่าปัจจุบัน")
        return self


class BgpNetworkUpdate(BaseModel):
    """คำขอแก้ BGP advertised network โดยลบค่าเดิมก่อนเพิ่มใหม่"""

    current: BgpNetworkConfig
    desired: BgpNetworkConfig

    @model_validator(mode="after")
    def validate_network_change(self) -> BgpNetworkUpdate:
        """ปฏิเสธ update ที่ไม่มีค่าเปลี่ยน"""
        if self.current == self.desired:
            raise ValueError("BGP network ใหม่ต้องแตกต่างจากค่าปัจจุบัน")
        return self


class BgpProcessConfig(BaseModel):
    """snapshot BGP process สำหรับยืนยันก่อน Remove Protocol"""

    local_as: int = Field(..., ge=1, le=4294967295)
    router_id: str | None = None
    neighbors: list[BgpNeighborState] = Field(default_factory=list)
    networks: list[BgpNetworkConfig] = Field(default_factory=list)


class BgpStateResponse(BaseModel):
    """สถานะ BGP ที่อ่านจาก running-config จริง"""

    node_id: str
    enabled: bool
    local_as: int | None = None
    router_id: str | None = None
    neighbors: list[BgpNeighborState] = Field(default_factory=list)
    networks: list[BgpNetworkConfig] = Field(default_factory=list)
    collected_at: str


class SaveConfigRequest(BaseModel):
    """คำขอสร้าง preview สำหรับบันทึก running-config ลง NVRAM"""

    confirm: Literal[True]


class ScanSubnetRequest(BaseModel):
    """คำขอ scan management subnet แบบจำกัดขนาดและเฉพาะ SSH/Telnet"""

    subnet: str

    @field_validator("subnet")
    @classmethod
    def validate_scan_subnet(cls, value: str) -> str:
        """รับเฉพาะ IPv4 subnet ที่มี host สูงสุด 16 รายการ"""
        import ipaddress

        try:
            network = ipaddress.IPv4Network(value.strip(), strict=True)
        except ValueError as exc:
            raise ValueError("subnet ต้องเป็น IPv4 network boundary เช่น 192.168.8.128/28") from exc
        if network.num_addresses > 16:
            raise ValueError("เพื่อความปลอดภัย scanner รองรับ subnet ไม่เกิน /28 (16 addresses)")
        return str(network)


class ScanResult(BaseModel):
    """ผล probe TCP ที่ปลอดภัยสำหรับหนึ่ง management IP"""

    host: str
    open_ports: list[int] = Field(default_factory=list)


class ScanSubnetResponse(BaseModel):
    """ผล subnet scanner โดยไม่พยายาม login หรือเก็บ credential"""

    subnet: str
    results: list[ScanResult] = Field(default_factory=list)


class PreviewResponse(BaseModel):
    """ผลการ render คำสั่งที่ยังไม่ถูกส่งไปยังอุปกรณ์"""

    operation_id: str
    node_id: str
    operation_type: str
    payload_hash: str
    commands: list[str]
    expires_at: str
    warnings: list[str] = Field(default_factory=list)


class ApplyRequest(BaseModel):
    """คำขอ apply ที่อ้างอิง preview เดิมและ hash เดิม"""

    operation_id: str = Field(..., min_length=1)
    payload_hash: str = Field(..., min_length=64, max_length=64)


class CommandResult(BaseModel):
    """ผลลัพธ์ของคำสั่งแต่ละบรรทัดแบบ redact แล้ว"""

    command: str
    status: Literal["success", "failed"]
    output: str = ""
    error_code: str | None = None


class ApplyResponse(BaseModel):
    """ผลรวมของการ apply พร้อมสถานะ partial failure"""

    operation_id: str
    node_id: str
    correlation_id: str
    overall_status: Literal["success", "failed", "partial_failed"]
    results: list[CommandResult]


class ShowResponse(BaseModel):
    """ผลคำสั่ง show ที่อยู่ใน allowlist"""

    node_id: str
    command: str
    output: str
    parsed: list[dict] | None = None
    collected_at: str


class HistoryEntry(BaseModel):
    """รายการ command history ที่ redact แล้ว"""

    id: str
    node_id: str
    node_hostname: str | None = None
    correlation_id: str
    operation_id: str | None
    command_type: str
    commands: list[str]
    results: list[CommandResult]
    overall_status: str
    created_at: str


class HistoryNodeOption(BaseModel):
    """Node ที่มี audit history รวมถึง Node ที่ถูกลบไปแล้ว"""

    id: str
    hostname: str | None = None
