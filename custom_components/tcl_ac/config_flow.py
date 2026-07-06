"""Config flow for TCL AC (App-controlled) integration."""
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN


class TclAcConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TCL AC."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step.

        用户在「设置 → 设备与服务 → 添加集成」搜索 TCL 后，
        填设备 ID（以及可选的账号密码用于 token 自动续期）。
        """
        errors = {}
        if user_input is not None:
            device_id = (user_input.get("device_id") or "").strip()
            if not device_id:
                errors["device_id"] = "invalid_device_id"
            else:
                # device_id 作为 unique_id，避免重复添加同一台空调
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured()
                return await self.async_create_entry(
                    title=f"TCL 空调 ({device_id})",
                    data={
                        "device_id": device_id,
                        "username": (user_input.get("username") or "").strip(),
                        "password": (user_input.get("password") or "").strip(),
                    },
                )

        data_schema = vol.Schema(
            {
                vol.Required("device_id"): str,
                vol.Optional("username"): str,
                vol.Optional("password"): str,
            }
        )
        return await self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={},
        )
