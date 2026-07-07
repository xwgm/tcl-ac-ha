"""Switch 平台：通用设备电源开关 + 冰箱主电源。"""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CATEGORY_AC, CATEGORY_FRIDGE
from . import __init__
from .api import TclApi
from .climate import TclAcClimate  # noqa: F401 - 仅用于类型引用
from .refrigerator import TclFridgePowerSwitch


class TclGenericSwitch:
    """TCL 通用设备电源开关（非空调/非冰箱）。"""

    _attr_should_poll = True

    def __init__(
        self,
        hass: HomeAssistant,
        api: TclApi,
        device_id: str,
        name: str,
        category: str,
    ):
        self.hass = hass
        self._api = api
        self._device_id = device_id
        self._attr_name = name
        self._attr_unique_id = f"tcl_switch_{device_id}"
        self._category = category
        self._status_cache: dict = {}

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._attr_name,
            "manufacturer": "TCL",
            "model": f"Device ({self._category})",
        }

    @property
    def extra_state_attributes(self):
        return {"category": self._category}

    async def async_update(self):
        try:
            self._status_cache = await self.hass.async_add_executor_job(
                self._api.get_status, self._device_id
            )
        except Exception:
            pass

    @property
    def is_on(self) -> bool:
        return bool(self._status_cache.get("powerSwitch", 0))

    async def async_turn_on(self, **kwargs):
        await self.hass.async_add_executor_job(
            self._api.send_control, self._device_id, {"powerSwitch": 1}
        )

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(
            self._api.send_control, self._device_id, {"powerSwitch": 0}
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """为通用设备和冰箱创建 Switch 实体。"""
    api: TclApi = hass.data[DOMAIN]["api"]
    all_devices = __init__.get_platform_devices(hass)
    entities = []

    for dev in all_devices:
        device_id = dev["deviceId"]
        name = dev.get("nickName", f"TCL 设备 {device_id[-4:]}")
        category = dev.get("category", "unknown")

        # 冰箱 → 电源开关实体
        if category == CATEGORY_FRIDGE:
            entities.append(TclFridgePowerSwitch(hass, api, device_id, name))
        # 非空调/非冰箱的 app 可控设备 → 通用开关
        elif category != CATEGORY_AC:
            entities.append(TclGenericSwitch(hass, api, device_id, name, category))

    if entities:
        async_add_entities(entities, update_before_add=True)
