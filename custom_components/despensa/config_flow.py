"""Una sola entrada, sin campos: la despensa es de la casa. Lo demás son opciones."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from . import (CONF_AVISAR_ACABADO, CONF_HORA, CONF_LISTA, CONF_NOTIFICAR, CONF_VENTANA, DEF_HORA,
               DEF_VENTANA, DOMAIN)


class DespensaConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    single_instance_allowed = True

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is None:
            return self.async_show_form(step_id="user")
        return self.async_create_entry(title="Despensa", data={})

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return OpcionesDespensa()


class OpcionesDespensa(OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)  # sin lista elegida, la clave no llega: se apaga
        o = self.config_entry.options
        moviles = sorted(s for s in self.hass.services.async_services_for_domain("notify") if s.startswith("mobile_app_"))
        return self.async_show_form(step_id="init", data_schema=vol.Schema({
            vol.Optional(CONF_NOTIFICAR, default=o.get(CONF_NOTIFICAR, [])): selector.SelectSelector(
                selector.SelectSelectorConfig(options=moviles, multiple=True)),
            vol.Optional(CONF_HORA, default=o.get(CONF_HORA, DEF_HORA)): selector.TimeSelector(),
            vol.Optional(CONF_VENTANA, default=o.get(CONF_VENTANA, DEF_VENTANA)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=2, max=30, step=1, mode=selector.NumberSelectorMode.BOX,
                                              unit_of_measurement="días")),
            vol.Optional(CONF_LISTA, description={"suggested_value": o.get(CONF_LISTA)}): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="todo")),
            vol.Optional(CONF_AVISAR_ACABADO, default=o.get(CONF_AVISAR_ACABADO, False)): selector.BooleanSelector(),
        }))
