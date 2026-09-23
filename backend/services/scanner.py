"""บริการ probe TCP 22/23 แบบจำกัดขนาดสำหรับ Add Node scanner"""

from __future__ import annotations

import asyncio
import ipaddress

from backend.models import ScanResult

_ALLOWED_PORTS = (22, 23)
_CONCURRENCY = 8
_TIMEOUT_SECONDS = 0.8


async def _probe(host: str, port: int, semaphore: asyncio.Semaphore) -> bool:
    """ตรวจ TCP port หนึ่งรายการโดยมี timeout และ concurrency limit"""
    async with semaphore:
        try:
            _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=_TIMEOUT_SECONDS)
            writer.close()
            await writer.wait_closed()
            return True
        except (OSError, TimeoutError):
            return False


async def scan_subnet(subnet: str) -> list[ScanResult]:
    """probe เฉพาะ TCP 22/23 ของ IPv4 subnet ที่ schema จำกัดแล้ว"""
    network = ipaddress.IPv4Network(subnet)
    semaphore = asyncio.Semaphore(_CONCURRENCY)
    hosts = [str(host) for host in network.hosts()]
    checks = await asyncio.gather(*[_probe(host, port, semaphore) for host in hosts for port in _ALLOWED_PORTS])
    results: list[ScanResult] = []
    for index, host in enumerate(hosts):
        open_ports = [port for offset, port in enumerate(_ALLOWED_PORTS) if checks[index * len(_ALLOWED_PORTS) + offset]]
        if open_ports:
            results.append(ScanResult(host=host, open_ports=open_ports))
    return results
