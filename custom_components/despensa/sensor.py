"""Cuatro sensores para tarjetas y automatizaciones."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, SIGNAL

MAX_ATRIB = 30  # los atributos van a la base de datos de HA: que no crezcan sin límite


def _fila(f: dict) -> dict:
    return {k: f[k] for k in ("nombre", "cantidad", "unidad", "sitio", "caduca", "dias")}


SENSORES = {
    # clave: (nombre, icono, valor, atributos)
    "caduca_pronto": ("Despensa caduca pronto", "mdi:clock-alert-outline",
                      lambda r: len(r["pronto"]), lambda r: {"productos": [_fila(f) for f in r["pronto"][:MAX_ATRIB]]}),
    "caducado": ("Despensa caducado", "mdi:delete-clock-outline",
                 lambda r: len(r["caducado"]), lambda r: {"productos": [_fila(f) for f in r["caducado"][:MAX_ATRIB]]}),
    "por_revisar": ("Despensa por revisar", "mdi:help-circle-outline",
                    lambda r: len(r["revisar"]),
                    lambda r: {"productos": [{"nombre": p["nombre"], "ticket": p["alias"][:1]} for p in r["revisar"][:MAX_ATRIB]]}),
    "productos": ("Despensa productos", "mdi:fridge-outline", lambda r: len(r["productos"]), lambda r: {}),
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    add(SensorDespensa(entry, clave) for clave in SENSORES)


class SensorDespensa(SensorEntity):
    _attr_should_poll = False
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, entry: ConfigEntry, clave: str) -> None:
        nombre, icono, self._valor, self._atrib = SENSORES[clave]
        self._attr_name = nombre
        self._attr_icon = icono
        self._attr_unique_id = f"{entry.entry_id}_{clave}"
        self.entity_id = f"sensor.despensa_{clave}"

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL, self._refrescar))
        self._calcular()

    def _calcular(self) -> None:
        r = self.hass.data[DOMAIN]["activa"].resumen()
        self._attr_native_value = self._valor(r)
        self._attr_extra_state_attributes = self._atrib(r)

    @callback
    def _refrescar(self) -> None:
        self._calcular()
        self.async_write_ha_state()
