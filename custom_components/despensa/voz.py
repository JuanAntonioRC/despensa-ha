"""Assist: «¿qué caduca esta semana?», «he gastado la leche», «se han acabado los huevos», «¿quedan yogures?».

HA solo lee frases propias de <config>/custom_sentences/<idioma>/, así que la integración deja allí
despensa.yaml (y lo quita al borrarla). Las acciones pasan por los mismos servicios que el panel.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, intent

_LOGGER = logging.getLogger(__name__)

FRASES = """# Lo escribe la integración Despensa: los cambios a mano se pierden al arrancar.
language: es
intents:
  DespensaCaduca:
    data:
      - sentences:
          - "(qué|que) (caduca|va a caducar|hay que gastar|tengo que gastar|tenemos que gastar) [pronto|esta semana|en la despensa|en casa]"
          - "(qué|que) se va a poner malo"
  DespensaUsar:
    data:
      - sentences:
          - "(he|hemos) (gastado|usado|cogido|abierto|consumido|tomado) {producto}"
          - "(gasta|apunta que he gastado|apunta que hemos gastado) {producto}"
  DespensaAcabar:
    data:
      - sentences:
          - "se (ha|han) (acabado|terminado) {producto}"
          - "(ya no queda|ya no quedan|no queda|no quedan) {producto}"
  DespensaQueda:
    data:
      - sentences:
          - "(queda|quedan|tenemos) {producto} [en casa|en la despensa|en la nevera]"
          - "(cuánto|cuánta|cuántos|cuántas|cuanto|cuanta|cuantos|cuantas) {producto} (queda|quedan|hay|tenemos)"
lists:
  producto:
    wildcard: true
"""


def _fichero(hass: HomeAssistant) -> Path:
    return Path(hass.config.path("custom_sentences", "es", "despensa.yaml"))


async def async_poner_frases(hass: HomeAssistant) -> None:
    f = _fichero(hass)

    def escribir() -> bool:
        if f.exists() and f.read_text() == FRASES:
            return False
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(FRASES)
        return True

    if await hass.async_add_executor_job(escribir) and hass.services.has_service("conversation", "reload"):
        await hass.services.async_call("conversation", "reload", {}, blocking=True)


async def async_quitar_frases(hass: HomeAssistant) -> None:
    await hass.async_add_executor_job(lambda: _fichero(hass).unlink(missing_ok=True))
    if hass.services.has_service("conversation", "reload"):
        await hass.services.async_call("conversation", "reload", {}, blocking=True)


def _cuando(dias: int | None) -> str:
    if dias is None:
        return "no caduca"
    if dias < 0:
        return "ya caducado"
    return {0: "hoy", 1: "mañana"}.get(dias, f"en {dias} días")


def _cantidad(n: float, unidad: str) -> str:
    if unidad in ("ud", "uds", ""):
        unidad = "unidad" if n == 1 else "unidades"
    return f"{n:g} {unidad}".strip()


def _quedan(n: float) -> str:
    return "Queda" if n == 1 else "Quedan"


def _sin_articulo(texto: str) -> str:
    return re.sub(r"^(el|la|los|las|un|una|unos|unas)\s+", "", texto.strip(), flags=re.I)


class _Base(intent.IntentHandler):
    slot_schema = {vol.Required("producto"): cv.string}

    def __init__(self, obtener) -> None:
        self._obtener = obtener  # devuelve la Despensa cargada (o lanza si no lo está)

    def _buscar(self, intent_obj: intent.Intent, con_stock: bool = True):
        texto = self.async_validate_slots(intent_obj.slots)["producto"]["value"]
        d = self._obtener(intent_obj.hass)
        return d, _sin_articulo(texto), d.inv.buscar(texto, con_stock)

    @staticmethod
    def _decir(intent_obj: intent.Intent, texto: str) -> intent.IntentResponse:
        r = intent_obj.create_response()
        r.async_set_speech(texto)
        return r

    async def _servicio(self, intent_obj: intent.Intent, servicio: str, pid: str) -> None:
        await intent_obj.hass.services.async_call(
            "despensa", servicio, {"producto": pid}, blocking=True, context=intent_obj.context)


class Caduca(intent.IntentHandler):
    intent_type = "DespensaCaduca"
    description = "Lo que caduca pronto en la despensa"

    def __init__(self, obtener) -> None:
        self._obtener = obtener

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        d = self._obtener(intent_obj.hass)
        r = d.resumen()
        partes = []
        if r["pronto"]:
            partes.append("Hay que gastar " + ", ".join(f"{f['nombre']} ({_cuando(f['dias'])})" for f in r["pronto"][:6]) + ".")
        if r["caducado"]:
            partes.append("Ya ha caducado: " + ", ".join(f["nombre"] for f in r["caducado"][:6]) + ".")
        resp = intent_obj.create_response()
        resp.async_set_speech(" ".join(partes) or f"No caduca nada en los próximos {d.ventana} días.")
        return resp


class Usar(_Base):
    intent_type = "DespensaUsar"
    description = "Apunta que se ha gastado una unidad de un producto"

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        d, texto, hallados = self._buscar(intent_obj)
        if not hallados:
            return self._decir(intent_obj, f"No encuentro {texto} en la despensa.")
        p = hallados[0]
        await self._servicio(intent_obj, "usar", p["id"])
        queda = sum(l["cantidad"] for l in d.inv.lotes_de(p["id"]))
        if queda:
            return self._decir(intent_obj, f"Apuntado. {_quedan(queda)} {_cantidad(queda, p['unidad'])} de {p['nombre']}.")
        return self._decir(intent_obj, f"Apuntado. Era lo último de {p['nombre']}"
                           + (", lo añado a la lista de la compra." if d.lista else "."))


class Acabar(_Base):
    intent_type = "DespensaAcabar"
    description = "Apunta que un producto se ha acabado"

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        # Sin stock también vale: «se acabó» sirve igual para mandarlo a la lista de la compra.
        d, texto, hallados = self._buscar(intent_obj, con_stock=False)
        if not hallados:
            return self._decir(intent_obj, f"No tengo {texto} en la despensa.")
        p = hallados[0]
        await self._servicio(intent_obj, "acabar", p["id"])
        return self._decir(intent_obj, f"Apuntado, se acabó {p['nombre']}"
                           + (" y va a la lista de la compra." if d.lista else "."))


class Queda(_Base):
    intent_type = "DespensaQueda"
    description = "Cuánto queda de un producto y dónde"

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        d, texto, hallados = self._buscar(intent_obj, con_stock=False)
        if not hallados:
            return self._decir(intent_obj, f"No tengo {texto} en la despensa.")
        con_stock = [p for p in hallados if d.inv.lotes_de(p["id"])]
        if not con_stock:
            return self._decir(intent_obj, f"No queda {hallados[0]['nombre']}.")
        p = con_stock[0]
        lotes = d.inv.lotes_de(p["id"])
        total = sum(l["cantidad"] for l in lotes)
        dias = d.resumen_de(p["id"])
        caduca = "No caduca." if dias is None else f"Caduca {_cuando(dias)}." if dias >= 0 else "Está caducado."
        return self._decir(intent_obj, f"{_quedan(total)} {_cantidad(total, p['unidad'])} de {p['nombre']} "
                           f"({d.inv.sitio_nombre(lotes[0]['sitio'])}). {caduca}")


def async_registrar(hass: HomeAssistant, obtener) -> None:
    for h in (Caduca(obtener), Usar(obtener), Acabar(obtener), Queda(obtener)):
        intent.async_register(hass, h)
