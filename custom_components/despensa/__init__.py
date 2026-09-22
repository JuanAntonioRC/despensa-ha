"""Despensa: inventario de casa dentro de Home Assistant.

Plan y registro de avance: https://outline.jarclab.com/doc/despensa-en-home-assistant-plan-ur2hknNWXD
"""
from __future__ import annotations

import json
import logging
from datetime import date, time
from pathlib import Path

import voluptuous as vol

from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .inventario import ErrorDespensa, Inventario, vacio

_LOGGER = logging.getLogger(__name__)

DOMAIN = "despensa"
PLATFORMS = ["sensor"]
SIGNAL = "despensa_cambio"
STATIC_URL = "/despensa_static"
FRONTEND = Path(__file__).parent / "frontend"
VERSION = json.loads((Path(__file__).parent / "manifest.json").read_text())["version"]

CONF_VENTANA = "ventana"
CONF_NOTIFICAR = "notificar"
CONF_HORA = "hora_resumen"
DEF_VENTANA = 7
DEF_HORA = "09:00:00"

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


class Despensa:
    """Lo que vive mientras la integración está cargada."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, store: Store, data: dict) -> None:
        self.hass, self.entry, self.store = hass, entry, store
        self.inv = Inventario(data)

    @property
    def ventana(self) -> int:
        return int(self.entry.options.get(CONF_VENTANA, DEF_VENTANA))

    def resumen(self) -> dict:
        return self.inv.resumen(dt_util.now().date(), self.ventana)

    @callback
    def cambiado(self) -> None:
        self.store.async_delay_save(lambda: self.inv.data, 1)
        async_dispatcher_send(self.hass, SIGNAL)

    async def avisar(self, titulo: str, mensaje: str, url: str = "/despensa") -> None:
        for svc in self.entry.options.get(CONF_NOTIFICAR, []):
            try:
                await self.hass.services.async_call(
                    "notify", svc,
                    {"title": titulo, "message": mensaje, "data": {"url": url, "group": "despensa"}},
                    blocking=True,
                )
            except Exception as err:  # un móvil caído no debe impedir avisar a los demás
                _LOGGER.warning("No se pudo avisar por notify.%s: %s", svc, err)


def _despensa(hass: HomeAssistant) -> Despensa:
    d = hass.data.get(DOMAIN, {}).get("activa")
    if d is None:
        raise HomeAssistantError("La integración Despensa no está cargada")
    return d


# --- servicios -----------------------------------------------------------

_LINEA = vol.Schema({
    vol.Required("texto"): cv.string,
    vol.Optional("cantidad", default=1): vol.Coerce(float),
    vol.Optional("precio"): vol.Coerce(float),
    vol.Optional("seguro", default=False): cv.boolean,
    vol.Optional("candidato"): vol.Any(None, dict),
}, extra=vol.ALLOW_EXTRA)

_ESQUEMAS = {
    "registrar_ticket": vol.Schema({
        vol.Required("factura"): cv.string,
        vol.Required("fecha"): cv.date,
        vol.Optional("tienda", default="Mercadona"): cv.string,
        vol.Required("lineas"): [_LINEA],
    }),
    "anadir": vol.Schema({
        vol.Exclusive("producto", "que"): cv.string,
        vol.Exclusive("nombre", "que"): cv.string,
        vol.Optional("ean"): cv.string,
        vol.Optional("cantidad", default=1): vol.Coerce(float),
        vol.Optional("caduca"): vol.Any(None, "", cv.date),
        vol.Optional("sitio"): vol.Any(None, cv.string),
    }),
    "usar": vol.Schema({
        vol.Exclusive("producto", "que"): cv.string,
        vol.Exclusive("ean", "que"): cv.string,
        vol.Optional("cantidad", default=1): vol.All(vol.Coerce(float), vol.Range(min=0.001)),
    }),
    "acabar": vol.Schema({vol.Required("producto"): cv.string}),
    "mover": vol.Schema({vol.Required("producto"): cv.string, vol.Required("sitio"): cv.string}),
    "editar_producto": vol.Schema({vol.Required("producto"): cv.string, vol.Required("campos"): dict}),
    "borrar_producto": vol.Schema({vol.Required("producto"): cv.string}),
    "editar_lote": vol.Schema({vol.Required("lote"): cv.string, vol.Required("campos"): dict}),
    "guardar_sitios": vol.Schema({vol.Required("sitios"): [vol.Schema({
        vol.Optional("id"): vol.Any(None, cv.string), vol.Required("nombre"): cv.string})]}),
    "deshacer": vol.Schema({}),
    "conocidos": vol.Schema({vol.Required("textos"): [cv.string]}),
    "importar": vol.Schema({vol.Required("datos"): dict}),
}


async def _quien(hass: HomeAssistant, call: ServiceCall) -> str | None:
    if not call.context.user_id:
        return None
    user = await hass.auth.async_get_user(call.context.user_id)
    return user.name if user and not user.system_generated else None


async def _servicio(hass: HomeAssistant, call: ServiceCall) -> ServiceResponse:
    d = _despensa(hass)
    inv, q, s = d.inv, await _quien(hass, call), call.service
    if s == "conocidos":  # solo lectura: qué textos del ticket ya son de algún producto
        return {"conocidos": [t for t in call.data["textos"] if inv.por_alias(t)]}
    datos = dict(call.data)
    resp = None
    try:
        if s == "registrar_ticket":
            fecha = datos["fecha"].isoformat()
            resp = inv.registrar_ticket(datos["factura"], fecha, datos["lineas"], datos["tienda"])
            if not resp["repetido"]:
                hass.async_create_task(_avisar_ticket(d, datos, resp))
        elif s == "anadir":
            caduca = datos.get("caduca")
            p = inv.anadir(producto=datos.get("producto"), nombre=datos.get("nombre"), ean=datos.get("ean"),
                           cantidad=datos["cantidad"], caduca=caduca.isoformat() if caduca else None,
                           sitio=datos.get("sitio"), hoy=dt_util.now().date(), quien=q)
            resp = {"producto": p["id"]}
        elif s == "usar":
            pid = datos.get("producto")
            if not pid:
                p = inv.por_ean(datos.get("ean") or "")
                if p is None:
                    raise ErrorDespensa("Ese código no es de ningún producto")
                pid = p["id"]
            inv.usar(pid, datos["cantidad"], q)
        elif s == "acabar":
            inv.acabar(datos["producto"], q)
        elif s == "mover":
            inv.mover(datos["producto"], datos["sitio"], q)
        elif s == "editar_producto":
            inv.editar_producto(datos["producto"], dict(datos["campos"]), q)
        elif s == "editar_lote":
            inv.editar_lote(datos["lote"], dict(datos["campos"]), q)
        elif s == "borrar_producto":
            inv.borrar_producto(datos["producto"], q)
        elif s == "guardar_sitios":
            inv.guardar_sitios(datos["sitios"], q)
        elif s == "deshacer":
            inv.deshacer()
        elif s == "importar":
            inv.importar(datos["datos"])
    except ErrorDespensa as err:
        raise ServiceValidationError(str(err)) from err
    d.cambiado()
    return resp if call.return_response else None


async def _avisar_ticket(d: Despensa, datos: dict, res: dict) -> None:
    titulo = f"{datos['tienda']} {datos['fecha']:%d/%m}"
    msg = f"{len(datos['lineas'])} productos"
    url = "/despensa"
    if res["revisar"]:
        nombres = [d.inv.data["productos"][pid]["nombre"] for pid in res["revisar"]
                   if pid in d.inv.data["productos"]]
        msg += f", {len(nombres)} por revisar: " + ", ".join(nombres[:5]) + ("…" if len(nombres) > 5 else "")
        url = "/despensa?ver=revisar"
    await d.avisar(titulo, msg, url)


def resumen_diario(res: dict) -> str | None:
    """Texto del aviso de la mañana, o nada si no hay nada urgente."""
    def lista(fs):
        return ", ".join(f["nombre"] for f in fs)
    partes = []
    if res["caducado"]:
        partes.append("Caducado: " + lista(res["caducado"]))
    hoy = [f for f in res["pronto"] if f["dias"] == 0]
    manana = [f for f in res["pronto"] if f["dias"] == 1]
    if hoy:
        partes.append("Hoy: " + lista(hoy))
    if manana:
        partes.append("Mañana: " + lista(manana))
    return "\n".join(partes) or None


# --- WebSocket: el panel se suscribe y recibe el estado entero en cada cambio ---

@websocket_api.websocket_command({vol.Required("type"): "despensa/subscribe"})
@callback
def _ws_subscribe(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    try:
        d = _despensa(hass)
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "no_cargada", str(err))
        return

    @callback
    def enviar() -> None:
        connection.send_message(websocket_api.event_message(msg["id"], {
            "datos": d.inv.data,
            "puede_deshacer": d.inv._anterior is not None,
            "ventana": d.ventana,
        }))

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(hass, SIGNAL, enviar)
    connection.send_result(msg["id"])
    enviar()


# --- montaje ---------------------------------------------------------------

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(FRONTEND), cache_headers=False)]
    )
    websocket_api.async_register_command(hass, _ws_subscribe)

    async def manejar(call: ServiceCall) -> ServiceResponse:
        return await _servicio(hass, call)

    for nombre, esquema in _ESQUEMAS.items():
        hass.services.async_register(
            DOMAIN, nombre, manejar, schema=esquema,
            supports_response=(SupportsResponse.ONLY if nombre == "conocidos"
                               else SupportsResponse.OPTIONAL if nombre in ("registrar_ticket", "anadir")
                               else SupportsResponse.NONE),
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    store = Store(hass, 1, DOMAIN)
    data = await store.async_load()
    if data is None:
        data = vacio()
        await store.async_save(data)  # primera vez: que existan los sitios iniciales
    d = Despensa(hass, entry, store, data)
    hass.data[DOMAIN]["activa"] = d

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path="despensa",
        webcomponent_name="despensa-panel",
        module_url=f"{STATIC_URL}/despensa-panel.js?v={VERSION}",
        sidebar_title="Despensa",
        sidebar_icon="mdi:fridge-outline",
        require_admin=False,
    )
    frontend.add_extra_js_url(hass, f"{STATIC_URL}/despensa-card.js?v={VERSION}")

    hora = time.fromisoformat(entry.options.get(CONF_HORA, DEF_HORA))

    async def por_la_manana(_now) -> None:
        texto = resumen_diario(d.resumen())
        if texto:
            await d.avisar("Hay que gastarlo", texto)

    entry.async_on_unload(async_track_time_change(
        hass, por_la_manana, hour=hora.hour, minute=hora.minute, second=0))
    @callback
    def medianoche(_now) -> None:
        # Los días que faltan cambian aunque nadie toque nada.
        async_dispatcher_send(hass, SIGNAL)

    entry.async_on_unload(async_track_time_change(hass, medianoche, hour=0, minute=0, second=5))
    entry.async_on_unload(entry.add_update_listener(_opciones_cambiadas))
    return True


async def _opciones_cambiadas(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        d = hass.data[DOMAIN].pop("activa", None)
        if d:
            await d.store.async_save(d.inv.data)
        frontend.async_remove_panel(hass, "despensa")
        frontend.remove_extra_js_url(hass, f"{STATIC_URL}/despensa-card.js?v={VERSION}")
    return ok
