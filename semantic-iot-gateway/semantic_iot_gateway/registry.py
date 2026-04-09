from __future__ import annotations

import json
from pathlib import Path

from .models import GatewayConfig


def validate_gateway_config_payload(payload: dict) -> GatewayConfig:
    return GatewayConfig.model_validate(payload)


def dump_gateway_config_json(config: GatewayConfig) -> str:
    return json.dumps(config.model_dump(mode="json"), ensure_ascii=False, indent=2)


def load_gateway_config(path: str | Path) -> GatewayConfig:
    config_path = Path(path)
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    return validate_gateway_config_payload(payload)


def dump_gateway_config(config: GatewayConfig, path: str | Path) -> None:
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(dump_gateway_config_json(config), encoding="utf-8")
