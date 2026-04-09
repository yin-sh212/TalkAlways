from __future__ import annotations

import asyncio
import ipaddress
from typing import Iterable

from .collectors.bacnet_ip import BacnetApplicationManager
from .models import BacnetRuntimeConfig, ModbusProbeResult


async def probe_modbus_hosts(
    hosts: Iterable[str],
    *,
    port: int = 502,
    timeout_s: float = 1.0,
) -> list[ModbusProbeResult]:
    async def probe_one(host: str) -> ModbusProbeResult:
        try:
            _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout_s)
        except Exception as exc:
            return ModbusProbeResult(host=host, port=port, reachable=False, detail=str(exc))

        writer.close()
        await writer.wait_closed()
        return ModbusProbeResult(host=host, port=port, reachable=True, detail="TCP 502 reachable")

    return list(await asyncio.gather(*(probe_one(host) for host in hosts)))


async def probe_modbus_subnet(
    cidr: str,
    *,
    port: int = 502,
    timeout_s: float = 1.0,
    limit: int | None = None,
) -> list[ModbusProbeResult]:
    hosts = [str(host) for host in ipaddress.ip_network(cidr, strict=False).hosts()]
    if limit is not None:
        hosts = hosts[:limit]
    return await probe_modbus_hosts(hosts, port=port, timeout_s=timeout_s)


async def probe_bacnet(
    *,
    local_address: str | None,
    timeout_s: float = 3.0,
    target_address: str | None = None,
    vendor_identifier: int = 999,
    local_device_instance: int = 599001,
    local_device_name: str = "SemanticEdgeGateway",
    network: int = 0,
    foreign: str | None = None,
    ttl: int = 300,
):
    manager = BacnetApplicationManager(
        BacnetRuntimeConfig(
            enabled=True,
            local_address=local_address,
            local_device_instance=local_device_instance,
            local_device_name=local_device_name,
            vendor_identifier=vendor_identifier,
            network=network,
            foreign=foreign,
            ttl=ttl,
        )
    )
    try:
        return await manager.who_is(timeout=timeout_s, address=target_address)
    finally:
        await manager.close()

