"""Una sola entrada, sin campos: la despensa es de la casa."""
from __future__ import annotations

from homeassistant.config_entries import ConfigFlow

from . import DOMAIN


class DespensaConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    single_instance_allowed = True

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is None:
            return self.async_show_form(step_id="user")
        return self.async_create_entry(title="Despensa", data={})
