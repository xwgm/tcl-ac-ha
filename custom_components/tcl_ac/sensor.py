"""Sensor 平台：冰箱各间室当前温度（只读）。"""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CATEGORY_FRIDGE
from .__init__ import get_platform_devices
from .api import TclApi
from .refrigerator import TclFridgeSensor


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    api: TclApi = hass.data[DOMAIN]["api"]
    devices = get_platform_devices(hass, CATEGORY_FRIDGE)
    for dev in devices:
        device_id = dev["deviceId"]
        name = dev.get("nickName", f"TCL 冰箱 {device_id[-4:]}")
        async_add_entities([
            TclFridgeSensor(hass, api, device_id, name, "冷藏室温度", "fridgeTemp", "\u00b0C"),
            TclFridgeSensor(hass, api, device_id, name, "冷冻室温度", "freezerTemp", "\u00b0C"),
            TclFridgeSensor(hass, api, device_id, name, "安温室温度", "variableTemp", "\u00b0C"),
        ], update_before_add=True)
