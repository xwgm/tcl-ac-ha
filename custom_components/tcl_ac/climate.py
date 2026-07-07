"""Climate 平台：空调设备（增强版：ECO / 睡眠 / 健康 / 矢量送风）。"""
import logging
from datetime import timedelta

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN, CATEGORY_AC,
    MODE_MAP, MODE_REVERSE, FAN_MAP,
    PRESET_MODES, PRESET_MODE_LABELS,
    SCAN_INTERVAL_SECONDS,
)
from .api import TclApi
from .__init__ import get_platform_devices

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """为所有空调设备创建 Climate 实体。"""
    api: TclApi = hass.data[DOMAIN]["api"]
    devices = get_platform_devices(hass, CATEGORY_AC)

    if not devices:
        _LOGGER.warning("tcl_ac: 未发现空调设备")
        return

    entities = []
    for dev in devices:
        device_id = dev["deviceId"]
        name = dev.get("nickName", f"TCL 空调 {device_id[-4:]}")
        entities.append(TclAcClimate(hass, api, device_id, name))

    async_add_entities(entities, update_before_add=True)


class TclAcClimate(ClimateEntity):
    """TCL AC climate entity（per-device，支持 ECO/睡眠/健康预设模式）。"""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [
        HVACMode.OFF, HVACMode.AUTO, HVACMode.COOL,
        HVACMode.DRY, HVACMode.FAN_ONLY, HVACMode.HEAT,
    ]
    _attr_fan_modes = ["auto", "low", "medium", "high", "full"]
    _attr_swing_modes = ["off", "vertical", "horizontal", "both"]
    _attr_min_temp = 16
    _attr_max_temp = 31
    _attr_target_temperature_step = 0.5
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.PRESET_MODE
    )
    _attr_preset_modes = PRESET_MODES
    _attr_should_poll = True

    def __init__(self, hass: HomeAssistant, api: TclApi, device_id: str, name: str):
        self.hass = hass
        self._api = api
        self._device_id = device_id
        self._attr_name = name
        self._attr_unique_id = f"tcl_ac_{device_id}"
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_current_temperature = None
        self._attr_target_temperature = 26
        self._attr_fan_mode = "auto"
        self._attr_swing_mode = "off"
        self._attr_preset_mode = "none"
        self._extra: dict = {}

    @property
    def extra_state_attributes(self) -> dict:
        return self._extra

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._attr_name,
            "manufacturer": "TCL",
            "model": "Air Conditioner",
        }

    async def async_update(self):
        try:
            status = await self.hass.async_add_executor_job(
                self._api.get_status, self._device_id
            )
        except Exception:
            _LOGGER.exception("TCL AC status fetch failed")
            return

        power = status.get("powerSwitch", 0)
        mode_code = status.get("workMode", 0)

        if power == 0:
            self._attr_hvac_mode = HVACMode.OFF
        else:
            mode_str = MODE_REVERSE.get(mode_code, "auto")
            self._attr_hvac_mode = HVACMode(mode_str)

        self._attr_target_temperature = status.get("targetTemperature", 26)
        self._attr_current_temperature = status.get("currentTemperature")

        fan_pct = status.get("windSpeedPercentage", 0)
        fan_auto = status.get("windSpeedAutoSwitch", 0)
        if fan_auto == 1 or fan_pct == 0:
            self._attr_fan_mode = "auto"
        elif fan_pct <= 25:
            self._attr_fan_mode = "low"
        elif fan_pct <= 50:
            self._attr_fan_mode = "medium"
        elif fan_pct <= 75:
            self._attr_fan_mode = "high"
        else:
            self._attr_fan_mode = "full"

        v = status.get("verticalWind", 0)
        h = status.get("horizontalWind", 0)
        if v and h:
            self._attr_swing_mode = "both"
        elif v:
            self._attr_swing_mode = "vertical"
        elif h:
            self._attr_swing_mode = "horizontal"
        else:
            self._attr_swing_mode = "off"

        # 预设模式状态解析
        eco_val = status.get("ECO", 0)
        sleep_val = status.get("sleep", 0)
        health_val = status.get("health", 0)

        if eco_val == 1:
            self._attr_preset_mode = "eco"
        elif sleep_val == 1:
            self._attr_preset_mode = "sleep"
        elif health_val == 1:
            self._attr_preset_mode = "health"
        else:
            self._attr_preset_mode = "none"

        self._extra = {
            "eco": eco_val,
            "screen": status.get("screen", 0),
            "beep": status.get("beepSwitch", 1),
            "sleep": sleep_val,
            "health": health_val,
            "self_clean": status.get("selfClean", 0),
            "fan_pct": fan_pct,
            "external_temp": status.get("externalUnitTemperature", 0),
        }

    # ──────────────── 控制方法 ────────────────

    async def _send(self, attrs: dict):
        ok = await self.hass.async_add_executor_job(
            self._api.send_control, self._device_id, attrs
        )
        if not ok:
            _LOGGER.warning("TCL AC control failed: %s", attrs)
        await self.async_update()

    async def async_set_temperature(self, **kwargs):
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is not None:
            await self._send({"targetTemperature": float(temp)})

    async def async_turn_on(self):
        await self._send({"powerSwitch": 1})

    async def async_turn_off(self):
        await self._send({"powerSwitch": 0})

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        if hvac_mode == HVACMode.OFF:
            await self._send({"powerSwitch": 0})
        else:
            mode_key = hvac_mode.value
            if mode_key == "fan_only":
                mode_key = "fan"
            mode_val = MODE_MAP.get(mode_key, 0)
            await self._send({"powerSwitch": 1, "workMode": mode_val})

    async def async_set_fan_mode(self, fan_mode: str):
        pct = FAN_MAP.get(fan_mode, 0)
        if pct == 0:
            await self._send({"windSpeedPercentage": 0, "windSpeedAutoSwitch": 1})
        else:
            await self._send({"windSpeedPercentage": pct, "windSpeedAutoSwitch": 0})

    async def async_set_swing_mode(self, swing_mode: str):
        v = 1 if swing_mode in ("vertical", "both") else 0
        h = 1 if swing_mode in ("horizontal", "both") else 0
        await self._send({"verticalWind": v, "horizontalWind": h})

    # ──────────────── 预设模式（新增） ────────────────

    async def async_set_preset_mode(self, preset_mode: str):
        """设置预设模式：none(关闭)/eco(节能)/sleep(睡眠)/health(健康)。"""
        attrs = {"ECO": 0, "sleep": 0, "health": 0}
        if preset_mode == "eco":
            attrs["ECO"] = 1
        elif preset_mode == "sleep":
            attrs["sleep"] = 1
        elif preset_mode == "health":
            attrs["health"] = 1
        await self._send(attrs)
