from __future__ import annotations

import argparse
import asyncio
import json
import logging

from .gui import launch_gui
from .probe import probe_bacnet, probe_modbus_hosts, probe_modbus_subnet
from .registry import load_gateway_config
from .runtime import EdgeGatewayRuntime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="semantic-iot-gateway")
    parser.add_argument("--log-level", default="INFO")

    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate a gateway config file.")
    validate.add_argument("--config", required=True)

    run = subparsers.add_parser("run", help="Run the edge gateway.")
    run.add_argument("--config", required=True)
    run.add_argument("--duration", type=float, default=None, help="Optional run duration in seconds.")

    probe_modbus = subparsers.add_parser("probe-modbus", help="Probe Modbus TCP hosts or a subnet once.")
    probe_modbus.add_argument("--hosts", help="Comma-separated host list.")
    probe_modbus.add_argument("--cidr", help="CIDR block, for example 192.168.1.0/24.")
    probe_modbus.add_argument("--port", type=int, default=502)
    probe_modbus.add_argument("--timeout", type=float, default=1.0)
    probe_modbus.add_argument("--limit", type=int, default=None)

    probe_bacnet_parser = subparsers.add_parser("probe-bacnet", help="Run a one-shot BACnet Who-Is.")
    probe_bacnet_parser.add_argument("--local-address", default=None)
    probe_bacnet_parser.add_argument("--timeout", type=float, default=3.0)
    probe_bacnet_parser.add_argument("--target-address", default=None)
    probe_bacnet_parser.add_argument("--vendor-identifier", type=int, default=999)
    probe_bacnet_parser.add_argument("--local-device-instance", type=int, default=599001)
    probe_bacnet_parser.add_argument("--local-device-name", default="SemanticEdgeGateway")
    probe_bacnet_parser.add_argument("--network", type=int, default=0)
    probe_bacnet_parser.add_argument("--foreign", default=None)
    probe_bacnet_parser.add_argument("--ttl", type=int, default=300)

    gui = subparsers.add_parser("gui", help="Launch the local desktop GUI.")
    gui.add_argument("--config", default=None, help="Optional config file to load at startup.")

    return parser


async def async_main(args: argparse.Namespace) -> int:
    if args.command == "validate":
        config = load_gateway_config(args.config)
        print(json.dumps(config.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0

    if args.command == "run":
        config = load_gateway_config(args.config)
        runtime = EdgeGatewayRuntime(config)
        await runtime.run(duration_s=args.duration)
        return 0

    if args.command == "probe-modbus":
        if args.hosts:
            hosts = [host.strip() for host in args.hosts.split(",") if host.strip()]
            results = await probe_modbus_hosts(hosts, port=args.port, timeout_s=args.timeout)
        elif args.cidr:
            results = await probe_modbus_subnet(args.cidr, port=args.port, timeout_s=args.timeout, limit=args.limit)
        else:
            raise SystemExit("probe-modbus requires --hosts or --cidr")
        print(json.dumps([result.model_dump(mode="json") for result in results], ensure_ascii=False, indent=2))
        return 0

    if args.command == "probe-bacnet":
        results = await probe_bacnet(
            local_address=args.local_address,
            timeout_s=args.timeout,
            target_address=args.target_address,
            vendor_identifier=args.vendor_identifier,
            local_device_instance=args.local_device_instance,
            local_device_name=args.local_device_name,
            network=args.network,
            foreign=args.foreign,
            ttl=args.ttl,
        )
        print(json.dumps([result.model_dump(mode="json") for result in results], ensure_ascii=False, indent=2))
        return 0

    return 1


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.command == "gui":
        return launch_gui(initial_config_path=args.config)

    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
