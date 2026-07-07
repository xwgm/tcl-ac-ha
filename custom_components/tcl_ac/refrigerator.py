"""TCL 冰箱实体：目标温度(Number) + 当前温度(只读 Sensor)。

注：冰箱不建电源开关/童锁/模式实体（用户只需看当前温度与调整温度）。
"""
import logging
from homeassistant.components.number import NumberEntity
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
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

    _attr_has_entity_name = True
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
        self._entity_name = "冷藏室温度"
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
        self._entity_name = "冷冻室温度"
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
        self._sensor_name = sensor_name
        self._status_key = status_key
        self._unit = unit
        self._attr_unique_id = f"tcl_fridge_{device_id}_{status_key}"
        if unit == "\u00b0C":
            self._attr_native_unit_of_measurement = "\u00b0C"
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
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
