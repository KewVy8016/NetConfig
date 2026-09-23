"""Parser สำหรับ output ที่ใช้แสดงในหน้า Show; parse ไม่ได้ต้องเก็บ raw output"""

from __future__ import annotations

import ipaddress
import re


def is_unsupported_ios_command(output: str) -> bool:
    """บอกว่า IOS ปฏิเสธ show command เพราะไม่รองรับ feature นั้นหรือไม่"""
    return bool(re.search(
        r"(?:%\s*(?:Invalid|Unrecognized|Incomplete|Ambiguous) input|\^\s*$)",
        output,
        re.IGNORECASE | re.MULTILINE,
    ))


def parse_switchport_state(output: str) -> str:
    """แปลงผล show interface switchport โดยไม่เดาสถานะเมื่อรูปแบบไม่ตรง"""
    if is_unsupported_ios_command(output):
        return "unsupported"
    match = re.search(r"^\s*Switchport:\s*(Enabled|Disabled)\s*$", output, re.IGNORECASE | re.MULTILINE)
    if match:
        return match.group(1).lower()
    return "unknown"


def parse_show_vlan_brief(output: str) -> list[dict[str, object]] | None:
    """แปลง `show vlan brief` เฉพาะบรรทัด VLAN ที่ IOS แสดงอย่างชัดเจน"""
    rows: list[dict[str, object]] = []
    pattern = re.compile(
        r"^(?P<vlan_id>\d{1,4})\s+(?P<name>.+?)\s{2,}(?P<status>\S+)\s*(?P<ports>.*)$"
    )
    for line in output.splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        values = match.groupdict()
        vlan_id = int(values["vlan_id"])
        if not 1 <= vlan_id <= 4094:
            continue
        ports = [port.strip() for port in values["ports"].split(",") if port.strip()]
        rows.append({
            "vlan_id": vlan_id,
            "name": values["name"].strip(),
            "status": values["status"].strip(),
            "ports": ports,
        })
    return rows or None


def parse_show_ip_interface_brief(output: str) -> list[dict[str, str]] | None:
    """แปลงตาราง show ip interface brief เป็นรายการ interface

    หากรูปแบบ output ไม่ใช่ Cisco IOS ที่คาดไว้ จะคืน None เพื่อให้ UI แสดง raw output
    แทนการแสดงข้อมูลที่อาจตีความผิด.
    """
    rows: list[dict[str, str]] = []
    pattern = re.compile(
        r"^(?P<interface>\S+)\s+(?P<ip>\S+)\s+(?P<ok>YES|NO)\s+"
        r"(?P<method>\S+)\s+(?P<status>.+)\s+(?P<protocol>up|down)\s*$",
        re.IGNORECASE,
    )
    for line in output.splitlines():
        match = pattern.match(line.strip())
        if match:
            rows.append({key: value.strip() for key, value in match.groupdict().items()})
    return rows or None


def parse_show_ip_route(output: str) -> list[dict[str, str]] | None:
    """แปลงบรรทัด route ที่มี prefix และ next-hop แบบพื้นฐาน

    คืน None เมื่อไม่พบ route ที่ parse ได้ เพื่อให้ผู้ใช้เห็น raw output ครบถ้วน.
    """
    rows: list[dict[str, str]] = []
    pattern = re.compile(
        r"^(?P<code>[A-Z*]+)\s+(?P<prefix>\d+(?:\.\d+){3}/\d+)\s+"
        r"(?:\[\S+\]\s+)?via\s+(?P<next_hop>\S+)"
    )
    for line in output.splitlines():
        match = pattern.search(line.strip())
        if match:
            rows.append(match.groupdict())
    return rows or None


def parse_static_routes(output: str) -> list[dict[str, str | None]]:
    """อ่าน `ip route` แบบ next-hop หรือ exit interface จาก running-config

    บรรทัดที่มี option ขั้นสูงเกิน contract ปัจจุบันจะถูกข้าม เพื่อไม่ให้ UI เสนอการลบ
    ด้วย inverse command ที่ไม่ครบถ้วน.
    """
    routes: list[dict[str, str | None]] = []
    pattern = re.compile(
        r"^ip route\s+(?P<destination>\d+(?:\.\d+){3})\s+"
        r"(?P<subnet_mask>\d+(?:\.\d+){3})\s+(?P<target>\S+)\s*$",
        re.IGNORECASE,
    )
    for line in output.splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        values = match.groupdict()
        target = values["target"]
        try:
            next_hop: str | None = str(ipaddress.IPv4Address(target))
            exit_interface: str | None = None
        except ValueError:
            next_hop = None
            exit_interface = target
        routes.append(
            {
                "destination": values["destination"],
                "subnet_mask": values["subnet_mask"],
                "next_hop": next_hop,
                "exit_interface": exit_interface,
                "route_type": "default" if values["destination"] == "0.0.0.0" and values["subnet_mask"] == "0.0.0.0" else "static",
            }
        )
    return routes


def parse_rip_config(output: str) -> dict[str, bool | int | list[str] | None]:
    """อ่าน RIP process แบบพื้นฐานจาก running-config

    คืนเฉพาะ version, network และ no auto-summary ตาม typed contract ปัจจุบัน;
    คำสั่ง RIP ขั้นสูงอื่นยังคงอยู่บนอุปกรณ์แต่ไม่ถูกแก้โดย workflow นี้.
    """
    lines = output.splitlines()
    start = next((index for index, line in enumerate(lines) if line.strip().lower() == "router rip"), None)
    if start is None:
        return {"enabled": False, "version": None, "networks": [], "no_auto_summary": False}

    version = 1
    networks: list[str] = []
    no_auto_summary = False
    for line in lines[start + 1:]:
        if not line.startswith((" ", "\t")):
            break
        command = line.strip().lower()
        version_match = re.fullmatch(r"version\s+([12])", command)
        network_match = re.fullmatch(r"network\s+(\d+(?:\.\d+){3})", command)
        if version_match:
            version = int(version_match.group(1))
        elif network_match:
            networks.append(str(ipaddress.IPv4Address(network_match.group(1))))
        elif command == "no auto-summary":
            no_auto_summary = True
    return {
        "enabled": True,
        "version": version,
        "networks": networks,
        "no_auto_summary": no_auto_summary,
    }


def parse_ospf_config(output: str) -> dict[str, bool | int | str | list[dict] | None]:
    """อ่าน OSPF process/router-id/network แบบ typed contract จาก running-config"""
    lines = output.splitlines()
    start = next(
        (index for index, line in enumerate(lines) if re.fullmatch(r"router ospf\s+\d+", line.strip(), re.IGNORECASE)),
        None,
    )
    if start is None:
        return {"enabled": False, "process_id": None, "router_id": None, "networks": []}

    process_match = re.fullmatch(r"router ospf\s+(\d+)", lines[start].strip(), re.IGNORECASE)
    if process_match is None:
        return {"enabled": False, "process_id": None, "router_id": None, "networks": []}
    process_id = int(process_match.group(1))
    router_id: str | None = None
    networks: list[dict[str, str | int]] = []
    for line in lines[start + 1:]:
        if not line.startswith((" ", "\t")):
            break
        command = line.strip().lower()
        router_match = re.fullmatch(r"router-id\s+(\d+(?:\.\d+){3})", command)
        network_match = re.fullmatch(
            r"network\s+(\d+(?:\.\d+){3})\s+(\d+(?:\.\d+){3})\s+area\s+(\d+)",
            command,
        )
        if router_match:
            router_id = str(ipaddress.IPv4Address(router_match.group(1)))
        elif network_match:
            wildcard = ipaddress.IPv4Address(network_match.group(2))
            mask = ipaddress.IPv4Address(int(ipaddress.IPv4Address("255.255.255.255")) - int(wildcard))
            networks.append({"network": network_match.group(1), "subnet_mask": str(mask), "area": int(network_match.group(3))})
    return {"enabled": True, "process_id": process_id, "router_id": router_id, "networks": networks}


def parse_eigrp_config(output: str) -> dict[str, bool | int | str | list[dict] | None]:
    """อ่าน EIGRP AS/router-id/network/no auto-summary จาก running-config"""
    lines = output.splitlines()
    start = next((index for index, line in enumerate(lines) if re.fullmatch(r"router eigrp\s+\d+", line.strip(), re.IGNORECASE)), None)
    if start is None:
        return {"enabled": False, "as_number": None, "router_id": None, "networks": [], "no_auto_summary": False}
    match = re.fullmatch(r"router eigrp\s+(\d+)", lines[start].strip(), re.IGNORECASE)
    if match is None:
        return {"enabled": False, "as_number": None, "router_id": None, "networks": [], "no_auto_summary": False}
    as_number = int(match.group(1))
    router_id: str | None = None
    networks: list[dict[str, str]] = []
    no_auto_summary = False
    for line in lines[start + 1:]:
        if not line.startswith((" ", "\t")):
            break
        command = line.strip().lower()
        router_match = re.fullmatch(r"eigrp router-id\s+(\d+(?:\.\d+){3})", command)
        network_match = re.fullmatch(r"network\s+(\d+(?:\.\d+){3})\s+(\d+(?:\.\d+){3})", command)
        if router_match:
            router_id = str(ipaddress.IPv4Address(router_match.group(1)))
        elif network_match:
            wildcard = ipaddress.IPv4Address(network_match.group(2))
            mask = ipaddress.IPv4Address(int(ipaddress.IPv4Address("255.255.255.255")) - int(wildcard))
            networks.append({"network": network_match.group(1), "subnet_mask": str(mask)})
        elif command == "no auto-summary":
            no_auto_summary = True
    return {"enabled": True, "as_number": as_number, "router_id": router_id, "networks": networks, "no_auto_summary": no_auto_summary}


def parse_bgp_config(output: str) -> dict[str, bool | int | str | list[dict] | None]:
    """อ่าน BGP process, router-id, neighbor และ advertised network จาก running-config"""
    lines = output.splitlines()
    start = next((index for index, line in enumerate(lines) if re.fullmatch(r"router bgp\s+\d+", line.strip(), re.IGNORECASE)), None)
    if start is None:
        return {"enabled": False, "local_as": None, "router_id": None, "neighbors": [], "networks": []}
    match = re.fullmatch(r"router bgp\s+(\d+)", lines[start].strip(), re.IGNORECASE)
    if match is None:
        return {"enabled": False, "local_as": None, "router_id": None, "neighbors": [], "networks": []}
    local_as = int(match.group(1))
    router_id: str | None = None
    neighbor_values: dict[str, dict[str, str | int | None]] = {}
    networks: list[dict[str, str]] = []
    for line in lines[start + 1:]:
        if not line.startswith((" ", "\t")):
            break
        command = line.strip()
        router_match = re.fullmatch(r"bgp router-id\s+(\d+(?:\.\d+){3})", command, re.IGNORECASE)
        neighbor_match = re.fullmatch(r"neighbor\s+(\d+(?:\.\d+){3})\s+remote-as\s+(\d+)", command, re.IGNORECASE)
        description_match = re.fullmatch(r"neighbor\s+(\d+(?:\.\d+){3})\s+description\s+(.+)", command, re.IGNORECASE)
        network_match = re.fullmatch(r"network\s+(\d+(?:\.\d+){3})\s+mask\s+(\d+(?:\.\d+){3})", command, re.IGNORECASE)
        if router_match:
            router_id = str(ipaddress.IPv4Address(router_match.group(1)))
        elif neighbor_match:
            neighbor_values[neighbor_match.group(1)] = {"neighbor_ip": neighbor_match.group(1), "remote_as": int(neighbor_match.group(2)), "description": neighbor_values.get(neighbor_match.group(1), {}).get("description")}
        elif description_match:
            neighbor_values.setdefault(description_match.group(1), {"neighbor_ip": description_match.group(1), "remote_as": None, "description": None})["description"] = description_match.group(2)
        elif network_match:
            networks.append({"network": network_match.group(1), "subnet_mask": network_match.group(2)})
    neighbors = [item for item in neighbor_values.values() if item["remote_as"] is not None]
    return {"enabled": True, "local_as": local_as, "router_id": router_id, "neighbors": neighbors, "networks": networks}


def parse_show_interface_detail(output: str, interface_name: str) -> dict[str, str | bool | None] | None:
    """อ่าน IP/mask/description/admin state จากผล `show interfaces` หนึ่ง interface

    Parameters:
        output: ข้อความดิบจาก Cisco IOS
        interface_name: ชื่อ interface ที่ backend ขออ่าน

    Returns:
        dict สำหรับ prefill หรือ None เมื่อยืนยันรูปแบบ output ไม่ได้
    """
    heading = re.search(
        rf"^{re.escape(interface_name)} is (?P<status>.+?), line protocol is (?P<protocol>\S+)",
        output,
        re.MULTILINE | re.IGNORECASE,
    )
    if not heading:
        return None

    ip_match = re.search(r"^\s*Internet address is (?P<ip>\d+(?:\.\d+){3})/(?P<prefix>\d{1,2})\s*$", output, re.MULTILINE)
    description_match = re.search(r"^\s*Description:\s*(?P<description>.+?)\s*$", output, re.MULTILINE)
    ip_address: str | None = None
    subnet_mask: str | None = None
    if ip_match:
        ip_address = str(ipaddress.IPv4Address(ip_match.group("ip")))
        subnet_mask = str(ipaddress.IPv4Network(f"0.0.0.0/{ip_match.group('prefix')}").netmask)

    status = heading.group("status").strip().lower()
    return {
        "interface_name": interface_name,
        "ip_address": ip_address,
        "subnet_mask": subnet_mask,
        "description": description_match.group("description").strip() if description_match else None,
        "admin_up": status != "administratively down",
        "status": status,
        "protocol": heading.group("protocol").strip().lower(),
    }
