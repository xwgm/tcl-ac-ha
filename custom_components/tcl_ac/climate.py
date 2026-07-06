"""TCL Air Conditioner climate entity."""
import json
import logging
import random
import ssl
import time
import urllib.request
import urllib.error
from datetime import timedelta

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    CONFIG_FILE, DEVICE_ID,
    APP_ID, APP_TENANT_ID, APP_SECRET,
    CONTROL_SOURCE, PLATFORM_TYPE, USER_AGENT,
    MODE_MAP, MODE_REVERSE, FAN_MAP,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the TCL AC platform."""
    discovery = discovery_info or {}
    device_id = discovery.get("device_id") or DEVICE_ID
    if not device_id:
        _LOGGER.error("tcl_ac: device_id 未配置，请在 configuration.yaml 的 tcl_ac: 段填写 device_id")
        return
    async_add_entities([TclAcClimate(hass, device_id)], update_before_add=True)

class TclApi:
    """TCL IoT API (stdlib only, runs in executor)."""

    def __init__(self, device_id: str):
        self._device_id = device_id
        self._token = ""
        self._token_ts = 0.0

    def _load_config(self):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)

    def _save_config(self, cfg):
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

    def _http(self, url, headers, data=None, method="GET"):
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            return json.loads(resp.read().decode())

    def get_token(self):
        if self._token and (time.time() - self._token_ts) < 3000:
            return self._token
        cfg = self._load_config()
        url = (
            f"https://cn.account.tcl.com/auth/auth/refershToken"
            f"?appId={APP_ID}&accountId={cfg.get('account_id', '')}"
            f"&tenantId={APP_TENANT_ID}&appSecret={APP_SECRET}"
        )
        headers = {
            "Host": "cn.account.tcl.com",
            "Content-Type": "application/json;charset=UTF-8",
            "t-platform-type": "iOS",
            "Encrypt": "false",
            "EncryptVersion": "2.0",
            "t-app-version": "2.7.33",
            "t-store-uuid": "TCL+",
            "User-Agent": "TCLPlus/2.6.1",
            "refreshToken": cfg.get("refresh_token", ""),
        }
        result = self._http(url, headers)
        self._token = result["accessToken"]
        self._token_ts = time.time()
        cfg["access_token"] = self._token
        cfg["refresh_token"] = result["refreshToken"]
        cfg["access_token_ts"] = self._token_ts
        self._save_config(cfg)
        return self._token

    def _iot_headers(self):
        # 改造点：伪装成 App 请求（原版带 MicroMessenger/小程序标识）
        return {
            "Host": "io.zx.tcljd.com",
            "accessToken": self.get_token(),
            "t-app-version": "2.7.33",
            "t-store-uuid": "TCL+",
            "Content-Type": "application/json;charset=UTF-8",
            "t-platform-type": PLATFORM_TYPE,
            "User-Agent": USER_AGENT,
        }

    def get_status(self):
        return self._http(
            "https://io.zx.tcljd.com/v1/thing/status",
            self._iot_headers(),
            data={"deviceId": self._device_id},
            method="POST",
        ).get("data", {}).get("status", {})

    def send_control(self, attrs: dict) -> bool:
        url = f"https://io.zx.tcljd.com/v1/control/property/{self._device_id}"
        body = {
            "msgId": f"ha_{int(random.random()*1e5)}_{int(time.time()*1000)}",
            "source": CONTROL_SOURCE,  # 改造点：伪装成 app 请求
            "version": "3.0.0",
            "params": [{k: v} for k, v in attrs.items()],
        }
        result = self._http(url, self._iot_headers(), data=body, method="POST")
        return result.get("code") == "200"

class TclAcClimate(ClimateEntity):
    """TCL AC climate entity."""

    _attr_name = "TCL 空调"
    _attr_unique_id = "tcl_ac_climate"
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
    )

    def __init__(self, hass: HomeAssistant, device_id: str):
        self.hass = hass
        self._device_id = device_id
        self._api = TclApi(device_id)
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_current_temperature = None
        self._attr_target_temperature = 26
        self._attr_fan_mode = "auto"
        self._attr_swing_mode = "off"
        self._extra = {}

    @property
    def extra_state_attributes(self):
        return self._extra

    async def async_update(self):
        try:
            status = await self.hass.async_add_executor_job(self._api.get_status)
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

        self._extra = {
            "eco": status.get("ECO", 0),
            "screen": status.get("screen", 0),
            "beep": status.get("beepSwitch", 1),
            "sleep": status.get("sleep", 0),
            "self_clean": status.get("selfClean", 0),
            "fan_pct": fan_pct,
            "external_temp": status.get("externalUnitTemperature", 0),
        }

    async def _send(self, attrs):
        ok = await self.hass.async_add_executor_job(self._api.send_control, attrs)
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
