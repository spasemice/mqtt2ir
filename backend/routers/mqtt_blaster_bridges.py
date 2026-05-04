from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..dependencies import LoggerDep, MQTTManagerDep, SettingsDep
from ..models import MqttBlasterBridgeConfig
from ..utils import update_options_file
from ..websockets import broadcast_ws

router = APIRouter(prefix="/api/bridges/mqtt-blaster", tags=["mqtt-blaster-bridges"])


class CreateMqttBlasterBridgeRequest(BaseModel):
    bridge_id: str
    name: str
    tx_topic: str
    rx_topic: str
    learn_topic: str | None = None
    learn_command_topic: str | None = None
    learn_command_payload: dict[str, Any] | None = None
    send_payload_key: str = "ir_code_to_send"
    learned_code_key: str = "learned_ir_code"
    online: bool = True


class UpdateMqttBlasterBridgeRequest(BaseModel):
    name: str
    tx_topic: str
    rx_topic: str
    learn_topic: str | None = None
    learn_command_topic: str | None = None
    learn_command_payload: dict[str, Any] | None = None
    send_payload_key: str = "ir_code_to_send"
    learned_code_key: str = "learned_ir_code"
    online: bool = True


@router.get("/{bridge_id:path}", response_model=dict[str, Any])
async def get_mqtt_blaster_bridge(
    bridge_id: str,
    settings: SettingsDep,
):
    cfg = settings.mqtt_blaster_bridges.get(bridge_id)
    if not cfg:
        raise HTTPException(404, "MQTT blaster bridge not found")
    return {"bridge_id": bridge_id, **cfg.model_dump()}


@router.post("", response_model=dict[str, Any])
async def create_mqtt_blaster_bridge(
    payload: CreateMqttBlasterBridgeRequest,
    mqtt: MQTTManagerDep,
    settings: SettingsDep,
    logger: LoggerDep,
):
    bridge_id = payload.bridge_id.strip()
    if not bridge_id:
        raise HTTPException(400, "bridge_id is required")
    if bridge_id in settings.mqtt_blaster_bridges or bridge_id in mqtt.bridges:
        raise HTTPException(409, f"Bridge '{bridge_id}' already exists")

    settings.mqtt_blaster_bridges[bridge_id] = MqttBlasterBridgeConfig(
        name=payload.name.strip() or bridge_id,
        tx_topic=payload.tx_topic.strip(),
        rx_topic=payload.rx_topic.strip(),
        learn_topic=(payload.learn_topic.strip() if payload.learn_topic else None),
        learn_command_topic=(payload.learn_command_topic.strip() if payload.learn_command_topic else None),
        learn_command_payload=payload.learn_command_payload or {"learn_ir_code": "ON"},
        send_payload_key=payload.send_payload_key,
        learned_code_key=payload.learned_code_key,
        online=payload.online,
    )

    update_options_file(
        settings.options_file,
        {"mqtt_blaster_bridges": {k: v.model_dump() for k, v in settings.mqtt_blaster_bridges.items()}},
    )
    mqtt._load_configured_mqtt_blaster_bridges()
    if mqtt.client and mqtt.connected:
        mqtt.subscribe(payload.rx_topic.strip())

    logger.info("Created MQTT blaster bridge '%s' (tx=%s, rx=%s)", bridge_id, payload.tx_topic, payload.rx_topic)
    await broadcast_ws({"type": "bridges_updated", "bridges": mqtt._get_bridges_list_for_broadcast()})
    return {"status": "ok", "bridge_id": bridge_id}


@router.put("/{bridge_id:path}", response_model=dict[str, Any])
async def update_mqtt_blaster_bridge(
    bridge_id: str,
    payload: UpdateMqttBlasterBridgeRequest,
    mqtt: MQTTManagerDep,
    settings: SettingsDep,
    logger: LoggerDep,
):
    if bridge_id not in settings.mqtt_blaster_bridges:
        raise HTTPException(404, "MQTT blaster bridge not found")

    old_cfg = settings.mqtt_blaster_bridges[bridge_id]
    settings.mqtt_blaster_bridges[bridge_id] = MqttBlasterBridgeConfig(
        name=payload.name.strip() or bridge_id,
        tx_topic=payload.tx_topic.strip(),
        rx_topic=payload.rx_topic.strip(),
        learn_topic=(payload.learn_topic.strip() if payload.learn_topic else None),
        learn_command_topic=(payload.learn_command_topic.strip() if payload.learn_command_topic else None),
        learn_command_payload=payload.learn_command_payload or {"learn_ir_code": "ON"},
        send_payload_key=payload.send_payload_key,
        learned_code_key=payload.learned_code_key,
        online=payload.online,
    )

    update_options_file(
        settings.options_file,
        {"mqtt_blaster_bridges": {k: v.model_dump() for k, v in settings.mqtt_blaster_bridges.items()}},
    )

    if mqtt.client and mqtt.connected:
        if old_cfg.rx_topic:
            mqtt.unsubscribe(old_cfg.rx_topic)
        if old_cfg.learn_topic and old_cfg.learn_topic != old_cfg.rx_topic:
            mqtt.unsubscribe(old_cfg.learn_topic)

    mqtt._load_configured_mqtt_blaster_bridges()
    if mqtt.client and mqtt.connected:
        new_cfg = settings.mqtt_blaster_bridges[bridge_id]
        if new_cfg.rx_topic:
            mqtt.subscribe(new_cfg.rx_topic)
        if new_cfg.learn_topic and new_cfg.learn_topic != new_cfg.rx_topic:
            mqtt.subscribe(new_cfg.learn_topic)

    logger.info("Updated MQTT blaster bridge '%s'", bridge_id)
    await broadcast_ws({"type": "bridges_updated", "bridges": mqtt._get_bridges_list_for_broadcast()})
    return {"status": "ok", "bridge_id": bridge_id}


@router.delete("/{bridge_id:path}", response_model=dict[str, Any])
async def delete_mqtt_blaster_bridge(
    bridge_id: str,
    mqtt: MQTTManagerDep,
    settings: SettingsDep,
    logger: LoggerDep,
):
    if bridge_id not in settings.mqtt_blaster_bridges:
        raise HTTPException(404, "MQTT blaster bridge not found")

    cfg = settings.mqtt_blaster_bridges.pop(bridge_id)
    if mqtt.client and mqtt.connected and cfg.rx_topic:
        mqtt.unsubscribe(cfg.rx_topic)

    mqtt.bridges.pop(bridge_id, None)

    update_options_file(
        settings.options_file,
        {"mqtt_blaster_bridges": {k: v.model_dump() for k, v in settings.mqtt_blaster_bridges.items()}},
    )
    logger.info("Deleted MQTT blaster bridge '%s'", bridge_id)
    await broadcast_ws({"type": "bridges_updated", "bridges": mqtt._get_bridges_list_for_broadcast()})
    return {"status": "ok"}
