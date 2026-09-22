"""Lógica de la despensa sin nada de HA, para poder probarla sola.

`python3 inventario.py` ejecuta la comprobación del final.

Datos (un dict que se guarda tal cual en .storage/despensa):
  sitios     [{id, nombre}]                       el orden de la lista es el orden en pantalla
  productos  {id: {id, nombre, foto, ean[], alias[], sitio, dias, unidad,
                   revisar, no_inventariar, mercadona_id}}
  lotes      {id: {id, producto, cantidad, sitio, comprado, caduca, abierto}}
  actividad  [{ts, texto, tipo}]                  la más reciente primero, máximo 200
  facturas   [numero]                             tickets ya metidos
Fechas en ISO (AAAA-MM-DD). `dias` = -1 significa que no caduca.
"""
from __future__ import annotations

import copy
import re
import uuid
from datetime import date, datetime, timedelta

SITIOS_INICIALES = [
    "Nevera", "Congelador nevera", "Congelador sótano", "Despensa",
    "Armario alto", "Cajón verduras", "Hogar",
]
CAMPOS_EDITABLES = {"nombre", "foto", "ean", "alias", "sitio", "dias", "unidad", "revisar", "no_inventariar"}
MAX_ACTIVIDAD = 200


class ErrorDespensa(Exception):
    """Error que se le enseña tal cual a quien pulsó el botón."""


def nid() -> str:
    return uuid.uuid4().hex[:10]


def vacio() -> dict:
    return {
        "sitios": [{"id": nid(), "nombre": n} for n in SITIOS_INICIALES],
        "productos": {}, "lotes": {}, "actividad": [], "facturas": [],
    }


def alias_normal(texto: str) -> str:
    """El texto del ticket tal cual, en mayúsculas y sin espacios de sobra."""
    return re.sub(r"\s+", " ", texto).strip().upper()


def _num(x: float) -> str:
    return f"{x:g}"


class Inventario:
    def __init__(self, data: dict | None = None) -> None:
        self.data = data if data is not None else vacio()
        self._anterior: dict | None = None  # ponytail: un solo nivel de deshacer

    # --- consultas -------------------------------------------------------

    def producto(self, pid: str) -> dict:
        try:
            return self.data["productos"][pid]
        except KeyError:
            raise ErrorDespensa("Ese producto ya no existe") from None

    def por_alias(self, texto: str) -> dict | None:
        a = alias_normal(texto)
        return next((p for p in self.data["productos"].values() if a in p["alias"]), None)

    def por_ean(self, ean: str) -> dict | None:
        ean = ean.strip()
        return next((p for p in self.data["productos"].values() if ean in p["ean"]), None)

    def por_nombre(self, nombre: str) -> dict | None:
        n = nombre.strip().casefold()
        return next((p for p in self.data["productos"].values() if p["nombre"].casefold() == n), None)

    def sitio_id(self, sitio: str | None) -> str | None:
        """Acepta id o nombre de sitio."""
        if not sitio:
            return None
        for s in self.data["sitios"]:
            if sitio in (s["id"], s["nombre"]) or s["nombre"].casefold() == sitio.casefold():
                return s["id"]
        raise ErrorDespensa(f"No existe el sitio «{sitio}»")

    def sitio_parecido(self, nombre: str | None) -> str | None:
        """Para lo que llega del ticket: «Congelador» vale por el primer sitio que empiece así."""
        n = (nombre or "").casefold()
        if not n:
            return None
        return next((s["id"] for s in self.data["sitios"] if s["nombre"].casefold() == n), None) or next(
            (s["id"] for s in self.data["sitios"] if s["nombre"].casefold().startswith(n)), None)

    def sitio_nombre(self, sid: str | None) -> str:
        return next((s["nombre"] for s in self.data["sitios"] if s["id"] == sid), "sin sitio")

    def lotes_de(self, pid: str) -> list[dict]:
        """Lotes del producto, primero el que caduca antes (los que no caducan, al final)."""
        return sorted(
            (l for l in self.data["lotes"].values() if l["producto"] == pid),
            key=lambda l: (l["caduca"] or "9999-12-31", l["comprado"] or ""),
        )

    def resumen(self, hoy: date, ventana: int) -> dict:
        """Lo que usan los sensores y los avisos: un producto por fila, con su lote más urgente."""
        filas = []
        for p in self.data["productos"].values():
            lotes = self.lotes_de(p["id"])
            if not lotes:
                continue
            caduca = lotes[0]["caduca"]
            filas.append({
                "id": p["id"], "nombre": p["nombre"],
                "cantidad": sum(l["cantidad"] for l in lotes),
                "unidad": p["unidad"],
                "sitio": self.sitio_nombre(lotes[0]["sitio"]),
                "caduca": caduca,
                "dias": (date.fromisoformat(caduca) - hoy).days if caduca else None,
            })
        con_fecha = sorted((f for f in filas if f["dias"] is not None), key=lambda f: f["dias"])
        return {
            "productos": filas,
            "caducado": [f for f in con_fecha if f["dias"] < 0],
            "pronto": [f for f in con_fecha if 0 <= f["dias"] <= ventana],
            "revisar": [p for p in self.data["productos"].values() if p["revisar"]],
        }

    # --- cambios ---------------------------------------------------------
    # Todos los cambios pasan por aquí: guarda la foto para deshacer y apunta la actividad.

    def _antes(self) -> None:
        self._anterior = copy.deepcopy(self.data)

    def _apunta(self, texto: str, tipo: str, quien: str | None = None, ts: str | None = None) -> None:
        if quien:
            texto = f"{texto} · {quien}"
        act = self.data["actividad"]
        act.insert(0, {"ts": ts or datetime.now().isoformat(timespec="seconds"), "texto": texto, "tipo": tipo})
        del act[MAX_ACTIVIDAD:]

    def deshacer(self) -> None:
        if self._anterior is None:
            raise ErrorDespensa("No hay nada que deshacer")
        self.data.clear()
        self.data.update(self._anterior)
        self._anterior = None

    def _nuevo_producto(self, nombre: str, **campos) -> dict:
        p = {
            "id": nid(), "nombre": nombre.strip(), "foto": "", "ean": [], "alias": [],
            "sitio": None, "dias": -1, "unidad": "ud", "revisar": False,
            "no_inventariar": False, "mercadona_id": None,
        }
        p.update({k: v for k, v in campos.items() if v is not None})
        self.data["productos"][p["id"]] = p
        return p

    def _nuevo_lote(self, p: dict, cantidad: float, comprado: str, caduca: str | None, sitio: str | None) -> None:
        l = {
            "id": nid(), "producto": p["id"], "cantidad": cantidad, "sitio": sitio or p["sitio"],
            "comprado": comprado, "caduca": caduca, "abierto": False,
        }
        self.data["lotes"][l["id"]] = l

    def registrar_ticket(self, factura: str, fecha: str, lineas: list[dict], tienda: str = "Mercadona") -> dict:
        """Mete un ticket. Cada línea: {texto, cantidad, precio?, seguro, candidato?}.

        candidato = {nombre, foto, ean, dias, sitio, mercadona_id, unidad} sacado del catálogo por despensa.py.
        La regla es la de siempre: el texto del ticket se guarda como alias del producto, así que
        cada producto se revisa como mucho una vez.
        """
        res = {"repetido": False, "nuevos": 0, "sumados": 0, "ignorados": 0, "revisar": []}
        if factura in self.data["facturas"]:
            res["repetido"] = True
            return res
        dia = date.fromisoformat(fecha)
        self._antes()
        try:
            self._lineas_ticket(dia, fecha, lineas, res)
        except Exception:
            self.data.clear()
            self.data.update(self._anterior)  # un ticket entra entero o no entra
            raise
        self.data["facturas"].append(factura)
        n = len(lineas)
        texto = f"Ticket {tienda} {dia:%d/%m}: {n} producto{'s' if n != 1 else ''}"
        if res["revisar"]:
            texto += f", {len(res['revisar'])} por revisar"
        self._apunta(texto, "ticket")
        return res

    def _lineas_ticket(self, dia: date, fecha: str, lineas: list[dict], res: dict) -> None:
        for ln in lineas:
            texto = alias_normal(ln["texto"])
            cand = ln.get("candidato") or {}
            p = self.por_alias(texto)
            if p is None and ln.get("seguro") and cand.get("nombre"):
                # Otro formato del mismo producto (brick suelto / pack): mismo nombre de catálogo.
                p = self.por_nombre(cand["nombre"])
                if p is not None:
                    p["alias"].append(texto)
            if p is None:
                p = self._nuevo_producto(
                    cand.get("nombre") or texto.capitalize(),
                    foto=cand.get("foto"), ean=[cand["ean"]] if cand.get("ean") else None,
                    alias=[texto], sitio=self.sitio_parecido(cand.get("sitio")),
                    dias=cand.get("dias"), unidad=cand.get("unidad"),
                    mercadona_id=cand.get("mercadona_id"), revisar=not ln.get("seguro"),
                )
                res["nuevos"] += 1
            if p["revisar"] and p["id"] not in res["revisar"]:
                res["revisar"].append(p["id"])
            if p["no_inventariar"]:
                res["ignorados"] += 1
                continue
            caduca = (dia + timedelta(days=p["dias"])).isoformat() if p["dias"] >= 0 else None
            self._nuevo_lote(p, float(ln.get("cantidad") or 1), fecha, caduca, None)
            res["sumados"] += 1

    def anadir(self, *, producto: str | None = None, nombre: str | None = None, cantidad: float = 1,
               caduca: str | None = None, sitio: str | None = None, ean: str | None = None,
               hoy: date | None = None, quien: str | None = None) -> dict:
        """Añadir a mano. Por id de producto, por EAN o por nombre (si no existe, lo crea)."""
        hoy = hoy or date.today()
        if cantidad <= 0:
            raise ErrorDespensa("La cantidad tiene que ser mayor que cero")
        sid = self.sitio_id(sitio)
        self._antes()
        p = (self.producto(producto) if producto
             else (self.por_ean(ean) if ean else None) or (self.por_nombre(nombre) if nombre else None))
        if p is None:
            if not nombre:
                raise ErrorDespensa("Falta el nombre del producto")
            p = self._nuevo_producto(nombre, sitio=sid, ean=[ean] if ean else None)
        elif ean and ean not in p["ean"]:
            p["ean"].append(ean)
        if not caduca and p["dias"] >= 0:
            caduca = (hoy + timedelta(days=p["dias"])).isoformat()
        self._nuevo_lote(p, float(cantidad), hoy.isoformat(), caduca or None, sid)
        self._apunta(f"Añadido: {p['nombre']} × {_num(cantidad)} → {self.sitio_nombre(sid or p['sitio'])}", "anadir", quien)
        return p

    def usar(self, pid: str, cantidad: float = 1, quien: str | None = None) -> None:
        """Gasta del lote que caduca antes. Lo que queda de ese lote se marca abierto."""
        p = self.producto(pid)
        lotes = self.lotes_de(pid)
        if not lotes:
            raise ErrorDespensa(f"No queda {p['nombre']}")
        self._antes()
        falta = cantidad
        for l in lotes:
            gasto = min(falta, l["cantidad"])
            l["cantidad"] = round(l["cantidad"] - gasto, 3)
            falta = round(falta - gasto, 3)
            if l["cantidad"] <= 0:
                del self.data["lotes"][l["id"]]
            else:
                l["abierto"] = True
            if falta <= 0:
                break
        queda = sum(l["cantidad"] for l in self.lotes_de(pid))
        cola = f"quedan {_num(queda)} {p['unidad']}" if queda else "se ha terminado"
        self._apunta(f"Usado: {p['nombre']} ({cola})", "usar", quien)

    def acabar(self, pid: str, quien: str | None = None) -> None:
        p = self.producto(pid)
        self._antes()
        for l in self.lotes_de(pid):
            del self.data["lotes"][l["id"]]
        self._apunta(f"Se acabó: {p['nombre']}", "acabar", quien)

    def mover(self, pid: str, sitio: str, quien: str | None = None) -> None:
        p = self.producto(pid)
        sid = self.sitio_id(sitio)
        self._antes()
        for l in self.lotes_de(pid):
            l["sitio"] = sid
        p["sitio"] = sid
        self._apunta(f"{p['nombre']} → {self.sitio_nombre(sid)}", "mover", quien)

    def editar_producto(self, pid: str, campos: dict, quien: str | None = None) -> None:
        p = self.producto(pid)
        malos = set(campos) - CAMPOS_EDITABLES
        if malos:
            raise ErrorDespensa(f"No se puede editar: {', '.join(sorted(malos))}")
        if "sitio" in campos:
            campos["sitio"] = self.sitio_id(campos["sitio"])
        if "alias" in campos:
            campos["alias"] = [alias_normal(a) for a in campos["alias"] if a.strip()]
            for a in campos["alias"]:
                otro = self.por_alias(a)
                if otro and otro["id"] != pid:
                    raise ErrorDespensa(f"«{a}» ya es alias de {otro['nombre']}")
        if "nombre" in campos and not campos["nombre"].strip():
            raise ErrorDespensa("El nombre no puede quedar vacío")
        self._antes()
        p.update(campos)
        self._apunta(f"Editado: {p['nombre']}", "editar", quien)

    def editar_lote(self, lid: str, campos: dict, quien: str | None = None) -> None:
        """Corregir un lote: la fecha del envase, la cantidad real, el sitio o si está abierto."""
        l = self.data["lotes"].get(lid)
        if l is None:
            raise ErrorDespensa("Ese lote ya no existe")
        malos = set(campos) - {"cantidad", "caduca", "sitio", "abierto"}
        if malos:
            raise ErrorDespensa(f"No se puede editar: {', '.join(sorted(malos))}")
        if "sitio" in campos:
            campos["sitio"] = self.sitio_id(campos["sitio"])
        if "caduca" in campos and campos["caduca"]:
            campos["caduca"] = date.fromisoformat(str(campos["caduca"])).isoformat()
        if "cantidad" in campos and float(campos["cantidad"]) < 0:
            raise ErrorDespensa("La cantidad no puede ser negativa")
        self._antes()
        l.update(campos)
        p = self.data["productos"][l["producto"]]
        if float(l["cantidad"]) == 0:
            del self.data["lotes"][lid]
        self._apunta(f"Corregido: {p['nombre']}", "editar", quien)

    def borrar_producto(self, pid: str, quien: str | None = None) -> None:
        """Para duplicados. Se pierden sus alias: el próximo ticket lo volvería a crear."""
        p = self.producto(pid)
        self._antes()
        for l in self.lotes_de(pid):
            del self.data["lotes"][l["id"]]
        del self.data["productos"][pid]
        self._apunta(f"Borrado: {p['nombre']}", "borrar", quien)

    def guardar_sitios(self, sitios: list[dict], quien: str | None = None) -> None:
        """Sustituye la lista entera: [{id?, nombre}] en el orden en que se quieren ver."""
        nombres = [s["nombre"].strip() for s in sitios]
        if not all(nombres):
            raise ErrorDespensa("Un sitio no puede quedar sin nombre")
        if len({n.casefold() for n in nombres}) != len(nombres):
            raise ErrorDespensa("Hay dos sitios con el mismo nombre")
        nuevos = [{"id": s.get("id") or nid(), "nombre": s["nombre"].strip()} for s in sitios]
        quedan = {s["id"] for s in nuevos}
        for s in self.data["sitios"]:
            if s["id"] not in quedan and any(l["sitio"] == s["id"] for l in self.data["lotes"].values()):
                raise ErrorDespensa(f"«{s['nombre']}» todavía tiene cosas: muévelas antes de borrarlo")
        self._antes()
        self.data["sitios"] = nuevos
        for p in self.data["productos"].values():
            if p["sitio"] not in quedan:
                p["sitio"] = None
        self._apunta("Sitios cambiados", "sitios", quien)

    def importar(self, data: dict) -> None:
        if self.data["productos"] or self.data["lotes"]:
            raise ErrorDespensa("La despensa no está vacía: importar solo vale para empezar")
        for k in ("sitios", "productos", "lotes"):
            if k not in data:
                raise ErrorDespensa(f"Falta «{k}» en lo que se importa")
        self._antes()
        self.data.update({k: data[k] for k in ("sitios", "productos", "lotes")})
        self.data["facturas"] = list(data.get("facturas", []))
        self._apunta(f"Importado: {len(data['productos'])} productos, {len(data['lotes'])} lotes", "importar")


if __name__ == "__main__":
    inv = Inventario()
    hoy = date(2026, 9, 22)
    leche = {"texto": "LECHE  semi P6", "cantidad": 2, "seguro": True,
             "candidato": {"nombre": "Leche semidesnatada Hacendado", "ean": "8480000103819", "dias": 90, "sitio": "Despensa"}}
    gato = {"texto": "C ESTERIL T URINARIO", "cantidad": 1, "seguro": False,
            "candidato": {"nombre": "Comida gato", "dias": -1, "sitio": "Hogar"}}
    r = inv.registrar_ticket("F1", "2026-09-16", [leche, gato])
    assert (r["nuevos"], r["sumados"], len(r["revisar"])) == (2, 2, 1), r
    assert inv.registrar_ticket("F1", "2026-09-16", [leche])["repetido"]
    p = inv.por_alias("leche semi p6")
    assert p and p["nombre"] == "Leche semidesnatada Hacendado" and not p["revisar"]

    # Segunda compra: mismo producto, lote nuevo; otro formato del mismo producto -> alias.
    r = inv.registrar_ticket("F2", "2026-09-20", [leche, {**leche, "texto": "LECHE SEMI BRIK", "cantidad": 1}])
    assert r["nuevos"] == 0 and r["sumados"] == 2 and "LECHE SEMI BRIK" in p["alias"]
    assert [l["caduca"] for l in inv.lotes_de(p["id"])] == ["2026-12-15", "2026-12-19", "2026-12-19"]

    # Gastar va primero al lote que caduca antes y deja abierto lo que queda.
    inv.usar(p["id"])
    primero = inv.lotes_de(p["id"])[0]
    assert primero["caduca"] == "2026-12-15" and primero["cantidad"] == 1 and primero["abierto"]
    inv.usar(p["id"], 2)
    assert [l["cantidad"] for l in inv.lotes_de(p["id"])] == [1, 1]
    inv.deshacer()
    assert sum(l["cantidad"] for l in inv.lotes_de(p["id"])) == 4
    try:
        inv.deshacer(); raise AssertionError("dos deshacer seguidos")
    except ErrorDespensa:
        pass

    # No inventariar: se reconoce pero no suma.
    inv.editar_producto(inv.por_alias("C ESTERIL T URINARIO")["id"], {"no_inventariar": True, "revisar": False})
    assert inv.registrar_ticket("F3", "2026-09-21", [gato])["ignorados"] == 1

    # Añadir a mano por nombre (crea), por EAN (encuentra) y mover.
    y = inv.anadir(nombre="Yogur natural", cantidad=6, caduca="2026-09-25", sitio="nevera", hoy=hoy, quien="Juan")
    assert inv.anadir(ean="8480000103819", hoy=hoy)["id"] == p["id"]
    assert inv.lotes_de(p["id"])[-1]["caduca"] == "2026-12-21"  # hoy + 90
    inv.mover(y["id"], "Congelador sótano")
    assert inv.sitio_nombre(inv.lotes_de(y["id"])[0]["sitio"]) == "Congelador sótano"
    assert inv.data["actividad"][2]["texto"].endswith("· Juan")

    # Resumen: yogur caduca en 3 días -> pronto; nada caducado.
    res = inv.resumen(hoy, 7)
    assert [f["nombre"] for f in res["pronto"]] == ["Yogur natural"] and not res["caducado"]
    assert [f["dias"] for f in inv.resumen(date(2026, 9, 26), 7)["caducado"]] == [-1]

    # Sitios: no se borra uno con cosas; renombrar conserva el id.
    try:
        inv.guardar_sitios([s for s in inv.data["sitios"] if s["nombre"] != "Congelador sótano"]); raise AssertionError
    except ErrorDespensa:
        pass
    inv.guardar_sitios([{**s, "nombre": "Congelador abajo"} if s["nombre"] == "Congelador sótano" else s for s in inv.data["sitios"]])
    assert inv.sitio_nombre(inv.lotes_de(y["id"])[0]["sitio"]) == "Congelador abajo"

    # Alias repetido entre productos: error.
    try:
        inv.editar_producto(y["id"], {"alias": ["leche semi p6"]}); raise AssertionError
    except ErrorDespensa:
        pass
    try:
        inv.importar(vacio()); raise AssertionError
    except ErrorDespensa:
        pass
    guis = {"texto": "GUISANTES", "cantidad": 1, "seguro": True, "candidato": {"nombre": "Guisantes", "dias": 365, "sitio": "Congelador"}}
    inv.registrar_ticket("F4", "2026-09-22", [guis])
    assert inv.sitio_nombre(inv.por_alias("GUISANTES")["sitio"]) == "Congelador nevera"
    antes = copy.deepcopy(inv.data)
    try:
        inv.registrar_ticket("F5", "2026-09-22", [{"texto": "PAN", "cantidad": 1}, {"cantidad": 1}]); raise AssertionError
    except KeyError:
        pass
    assert inv.data == antes and "F5" not in inv.data["facturas"]
    lote = inv.lotes_de(y["id"])[0]
    inv.editar_lote(lote["id"], {"caduca": "2026-10-01", "cantidad": 4})
    assert inv.lotes_de(y["id"])[0]["caduca"] == "2026-10-01" and inv.lotes_de(y["id"])[0]["cantidad"] == 4
    inv.editar_lote(lote["id"], {"cantidad": 0})
    assert not inv.lotes_de(y["id"])
    print("ok")
