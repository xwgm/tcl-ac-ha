"""TCL 冰箱实体：温度(Number) + 模式(Select) + 童锁(Lock) + 传感器(Sensor) + 电源(Switch)。"""
import logging
from homeassistant.components.lock import LockEntity
from homeassistant.components.number import NumberEntity
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    FRIDGE_MODES, FRIDGE_MODE_LABELS, FRIDGE_MODE_VALUES,
    FRIDGE_FRIDGE_TEMP_MIN, FRIDGE_FRIDGE_TEMP_MAX,
    FRIDGE_FREEZER_TEMP_MIN, FRIDGE_FREEZER_TEMP_MAX,
    SCAN_INTERVAL_SECONDS,
)
from .api import TclApi

_LOGGER = logging.getLogger(__name__)

DOMAIN = "tcl_ac"

# 兼容：HA <2024.x 没有 NumberMode
try:
    from homeassistant.components.number import NumberMode
    HAS_NUMBER_MODE = True
except ImportError:
    HAS_NUMBER_MODE = False


# ──────────────── 基类 ────────────────

class _TclFridgeEntity(Entity):
    """冰箱实体的基类（用 Entity 而非 RestoreEntity，避免 restore 复杂度）。"""

    _attr_should_poll = True

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

    _attr_icon = "mdi:temperature-celsius"
    _attr_native_min_value = FRIDGE_FRIDGE_TEMP_MIN
    _attr_native_max_value = FRIDGE_FRIDGE_TEMP_MAX
    _attr_native_step = 1

    def __init__(self, hass, api, device_id, device_name):
        super().__init__(hass, api, device_id, device_name)
        self._entity_name = f"{device_name} 冷藏室温度"
        self._attr_unique_id = f"tcl_fridge_{device_id}_fridge_temp"
        if HAS_NUMBER_MODE:
            self._attr_mode = NumberMode.SLIDER

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
    _attr_native_min_value = FRIDGE_FREEZER_TEMP_MIN
    _attr_native_max_value = FRIDGE_FREEZER_TEMP_MAX
    _attr_native_step = 1

    def __init__(self, hass, api, device_id, device_name):
        super().__init__(hass, api, device_id, device_name)
        self._entity_name = f"{device_name} 冷冻室温度"
        self._attr_unique_id = f"tcl_fridge_{device_id}_freezer_temp"
        if HAS_NUMBER_MODE:
            self._attr_mode = NumberMode.SLIDER

    @property
    def name(self):
        return self._entity_name

    @property
    def native_value(self):
        return float(self._get("freezeSetTemp", -18))

    async def async_set_native_value(self, value: float):
        await self.hass.async_add_executor_job(
            self._api.send_control, self._device_id,
            {"freezeSetTemp": int(value)},
        )


# ──────────────── 冰箱模式 (Select) ────────────────

class TclFridgeMode(_TclFridgeEntity, SelectEntity):
    """冰箱运行模式选择（AI智能 / 速冷 / 速冻）。"""

    _attr_icon = "mdi:tune"
    _attr_options = [FRIDGE_MODE_LABELS.get(m, m) for m in FRIDGE_MODES]

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
                return FRIDGE_MODE_LABELS.get(k, k)
        return None

    async def async_select_option(self, option: str) -> None:
        # 反查：从标签找到 key，再取 API 值
        reverse_labels = {v: k for k, v in FRIDGE_MODE_LABELS.items()}
        key = reverse_labels.get(option, option)
        mode_val = FRIDGE_MODE_VALUES.get(key, 0)
        await self.hass.async_add_executor_job(
            self._api.send_control, self._device_id,
            {"workMode": mode_val},
        )


# ──────────────── 童锁 (Lock) ────────────────

class TclFridgeChildLock(_TclFridgeEntity, LockEntity):
    """冰箱童锁开关。"""

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
        if unit == "\u00b0C":
            self._attr_native_unit_of_measurement = "\u00b0C"
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
