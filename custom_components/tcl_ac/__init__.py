"""TCL Air Conditioner integration (App-controlled bypass)."""
from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.typing import ConfigType

DOMAIN = "tcl_ac"

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up via YAML.

    device_id 可在 configuration.yaml 的 tcl_ac: 段配置，
    HACS 更新组件时不会覆盖你的配置：
        tcl_ac:
          device_id: "36376945"
    """
    domain_cfg = config.get(DOMAIN, {})
    device_id = domain_cfg.get("device_id") if isinstance(domain_cfg, dict) else None
    hass.async_create_task(
        async_load_platform(hass, "climate", DOMAIN, {"device_id": device_id}, config)
    )
    return True
