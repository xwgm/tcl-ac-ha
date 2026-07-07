"""Number 平台：冰箱温度（冷藏室/冷冻室）。"""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CATEGORY_FRIDGE
from .__init__ import get_platform_devices
from .api import TclApi
from .refrigerator import (
    TclFridgeFridgeTemp,
    TclFridgeFreezerTemp,
)


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
            TclFridgeFridgeTemp(hass, api, device_id, name),
            TclFridgeFreezerTemp(hass, api, device_id, name),
        ], update_before_add=True)
