"""TCL 冰箱实体：温度(Number) + 模式(Select) + 童锁(Lock) + 传感器(Sensor) + 电源(Switch)。"""
import logging
from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    FRIDGE_MODES, FRIDGE_MODE_LABELS, FRIDGE_MODE_VALUES,
    FRIDGE_FRIDGE_TEMP_MIN, FRIDGE_FRIDGE_TEMP_MAX,
    FRIDGE_FREEZER_TEMP_MIN, FRIDGE_FREEZER_TEMP_MAX,
    SCAN_INTERVAL_SECONDS,
)
from .api import TclApi

_LOGGER = logging.getLogger(__name__)

DOMAIN = "tcl_ac"


async def async_setup_entry(
    hass: HomeAssistant,
    entry_data: dict,
    device_info: dict,
    api: TclApi,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """为单台冰箱设备创建全部子实体。"""
    device_id = device_info["deviceId"]
    name = device_info.get("nickName", f"TCL 冰箱 {device_id[-4:]}")
    entities: list = [
        TclFridgeFridgeTemp(hass, api, device_id, name),
        TclFridgeFreezerTemp(hass, api, device_id, name),
        TclFridgeMode(hass, api, device_id, name),
        TclFridgeChildLock(hass, api, device_id, name),
        TclFridgePowerSwitch(hass, api, device_id, name),
        # 温度传感器（只读显示当前值）
        TclFridgeSensor(hass, api, device_id, name, "冷藏室温度", "fridgeTemp", "°C"),
        TclFridgeSensor(hass, api, device_id, name, "冷冻室温度", "freezerTemp", "°C"),
        TclFridgeSensor(hass, api, device_id, name, "安温室温度", "variableTemp", "°C"),
    ]
    async_add_entities(entities, update_before_add=True)


# ──────────────── 基类 ────────────────

class _TclFridgeEntity(RestoreEntity):
    """冰箱实体的基类。"""

    _attr_should_poll = True  # 轮询模式

    def __init__(self, hass: HomeAssistant, api: TclApi, device_id: str, device_name: str):
        self.hass = hass
        self._api = api
        self._device_id = device_id
        self._device_name = device_name
        self._status_cache: dict = {}

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._device_name,
            "manufacturer": "TCL",
            "model": "Refrigerator",
        }

    async def async_update(self):
        try:
            self._status_cache = await self.hass.async_add_executor_job(
                self._api.get_status, self._device_id
            )
        except Exception:
            _LOGGER.exception("TCL Fridge status fetch failed")

    def _get(self, key, default=0):
        return self._status_cache.get(key, default)


# ──────────────── 冷藏室温度 (Number) ────────────────

class TclFridgeFridgeTemp(_TclFridgeEntity, NumberEntity):
    """冷藏室目标温度设置（2~8°C）。"""

    _attr_name = None  # 由 unique_id 区分
    _attr_icon = "mdi:temperature-celsius"
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = FRIDGE_FRIDGE_TEMP_MIN
    _attr_native_max_value = FRIDGE_FRIDGE_TEMP_MAX
    _attr_native_step = 1

    def __init__(self, hass, api, device_id, device_name):
        super().__init__(hass, api, device_id, device_name)
        self._entity_name = f"{device_name} 冷藏室温度"
        self._attr_unique_id = f"tcl_fridge_{device_id}_fridge_temp"

    @property
    def name(self):
        return self._entity_name

    @property
    def native_value(self):
        return float(self._get("fridgeSetTemp", 6))

    async def async_set_native_value(self, value: float):
        await self.hass.async_add_executor_job(
            self._api.send_control, self._device_id,
            {"fridgeSetTemp": int(value)},
        )


# ──────────────── 冷冻室温度 (Number) ────────────────

class TclFridgeFreezerTemp(_TclFridgeEntity, NumberEntity):
    """冷冻室目标温度设置（-24~-15°C）。"""

    _attr_icon = "mdi:snowflake-thermometer"
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = FRIDGE_FREEZER_TEMP_MIN
    _attr_native_max_value = FRIDGE_FREEZER_TEMP_MAX
    _attr_native_step = 1

    def __init__(self, hass, api, device_id, device_name):
        super().__init__(hass, api, device_id, device_name)
        self._entity_name = f"{device_name} 冷冻室温度"
        self._attr_unique_id = f"tcl_fridge_{device_id}_freezer_temp"

    @property
    def name(self):
        return self._entity_name

    @property
    def native_value(self):
        return float(self._get("freezerSetTemp", -18))

    async def async_set_native_value(self, value: float):
        await self.hass.async_add_executor_job(
            self._api.send_control, self._device_id,
            {"freezerSetTemp": int(value)},
        )


# ──────────────── 冰箱模式 (Select) ────────────────

class TclFridgeMode(_TclFridgeEntity, SelectEntity):
    """冰箱运行模式选择（AI智能 / 速冷 / 速冻）。"""

    _attr_icon = "mdi:tune"
    _attr_options = FRIDGE_MODES

    def __init__(self, hass, api, device_id, device_name):
        super().__init__(hass, api, device_id, device_name)
        self._entity_name = f"{device_name} 模式"
        self._attr_unique_id = f"tcl_fridge_{device_id}_mode"

    @property
    def name(self):
        return self._entity_name

    @property
    def current_option(self) -> str | None:
        mode_val = self._get("workMode", 0)
        for k, v in FRIDGE_MODE_VALUES.items():
            if v == mode_val:
                return k
        return None

    async def async_select_option(self, option: str) -> None:
        mode_val = FRIDGE_MODE_VALUES.get(option, 0)
        await self.hass.async_add_executor_job(
            self._api.send_control, self._device_id,
            {"workMode": mode_val},
        )

    @property
    def options(self) -> list:
        return [FRIDGE_MODE_LABELS.get(m, m) for m in FRIDGE_MODES]


# ──────────────── 童锁 (Lock) ────────────────

class TclFridgeChildLock(_TclFridgeEntity, LockEntity):
    """冰箱童锁开关。"""

    _attr_name = None
    _attr_icon = "mdi:lock-outline"

    def __init__(self, hass, api, device_id, device_name):
        super().__init__(hass, api, device_id, device_name)
        self._entity_name = f"{device_name} 童锁"
        self._attr_unique_id = f"tcl_fridge_{device_id}_child_lock"

    @property
    def name(self):
        return self._entity_name

    @property
    def is_locking(self) -> bool:
        return False

    @property
    def is_locked(self) -> bool:
        return bool(self._get("childLock", 0))

    async def async_lock(self, **kwargs):
        await self.hass.async_add_executor_job(
            self._api.send_control, self._device_id,
            {"childLock": 1},
        )

    async def async_unlock(self, **kwargs):
        await self.hass.async_add_executor_job(
            self._api.send_control, self._device_id,
            {"childLock": 0},
        )


# ──────────────── 电源开关 (Switch) ────────────────

class TclFridgePowerSwitch(_TclFridgeEntity, SwitchEntity):
    """冰箱主电源开关。"""

    _attr_name = None
    _attr_icon = "mdi:power-plug"

    def __init__(self, hass, api, device_id, device_name):
        super().__init__(hass, api, device_id, device_name)
        self._entity_name = f"{device_name} 开关"
        self._attr_unique_id = f"tcl_fridge_{device_id}_power"

    @property
    def name(self):
        return self._entity_name

    @property
    def is_on(self) -> bool:
        return bool(self._get("powerSwitch", 1))  # 冰箱默认常开

    async def async_turn_on(self, **kwargs):
        await self.hass.async_add_executor_job(
            self._api.send_control, self._device_id,
            {"powerSwitch": 1},
        )

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(
            self._api.send_control, self._device_id,
            {"powerSwitch": 0},
        )


# ──────────────── 温度传感器 (只读 Sensor) ────────────────

class TclFridgeSensor(_TclFridgeEntity, SensorEntity):
    """冰箱各间室当前温度传感器（只读显示）。"""

    _attr_should_poll = True

    def __init__(
        self,
        hass: HomeAssistant,
        api: TclApi,
        device_id: str,
        device_name: str,
        sensor_name: str,
        status_key: str,
        unit: str,
    ):
        super().__init__(hass, api, device_id, device_name)
        self._sensor_name = f"{device_name} {sensor_name}"
        self._status_key = status_key
        self._unit = unit
        self._attr_unique_id = f"tcl_fridge_{device_id}_{status_key}"
        if unit == "°C":
            self._attr_native_unit_of_measurement = "°C"
            self._attr_device_class = "temperature"
            self._attr_icon = "mdi:thermometer"

    @property
    def name(self):
        return self._sensor_name

    @property
    def native_value(self) -> float | None:
        val = self._get(self._status_key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                pass
        return None
