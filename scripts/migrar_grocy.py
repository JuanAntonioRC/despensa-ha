#!/usr/bin/env python3
"""Pasa todo de Grocy a la integración Despensa, una sola vez. Grocy solo se lee.

  migrar_grocy.py --grocy https://grocy.jarclab.com --db ~/mercadona/mercadona.db \
                  --facturas procesados.txt --ha https://homeassistant.jarclab.com
  (sin --ha: escribe el JSON por la salida y no toca nada)

Claves: GROCY_KEY y HA_TOKEN en el entorno.
- Códigos de barras de 8 o 13 cifras -> EAN; el resto son textos del ticket -> alias.
- Foto e id de Mercadona: el enlace de la tienda que despensa.py dejó en la descripción.
- Días por defecto: en Grocy 0 = sin fecha, así que 0 y -1 pasan a -1 (no caduca).
- Stock con caducidad 2999-12-31 = no caduca.
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import urllib.request
import uuid
from pathlib import Path

SITIOS = ["Nevera", "Congelador nevera", "Congelador sótano", "Despensa", "Armario alto", "Cajón verduras", "Hogar"]
DE_GROCY = {"Nevera": "Nevera", "Despensa": "Despensa", "Congelador": "Congelador nevera", "Hogar": "Hogar"}


def pedir(url, token=None, cuerpo=None, grocy_key=None):
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    if grocy_key:
        h["GROCY-API-KEY"] = grocy_key
    req = urllib.request.Request(url, headers=h, data=json.dumps(cuerpo).encode() if cuerpo is not None else None,
                                 method="POST" if cuerpo is not None else "GET")
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def alias_normal(t):
    return re.sub(r"\s+", " ", t).strip().upper()


def nid():
    return uuid.uuid4().hex[:10]


def migrar(g, db):
    sitios = [{"id": nid(), "nombre": n} for n in SITIOS]
    sid = {s["nombre"]: s["id"] for s in sitios}
    loc = {l["id"]: sid.get(DE_GROCY.get(l["name"], l["name"])) for l in g("locations")}
    grupos = {x["id"]: x["name"] for x in g("product_groups")}
    codigos = {}
    for b in g("product_barcodes"):
        codigos.setdefault(b["product_id"], []).append(b["barcode"])

    productos, pid_nuevo = {}, {}
    for p in g("products"):
        m = re.search(r"tienda\.mercadona\.es/product/(\d+)", p.get("description") or "")
        mid = m.group(1) if m else None
        fila = db.execute("SELECT foto_url FROM productos WHERE id = ? LIMIT 1", (mid,)).fetchone() if mid and db else None
        cods = codigos.get(p["id"], [])
        dias = int(p.get("default_best_before_days") or 0)
        nuevo = {
            "id": nid(), "nombre": p["name"].strip(),
            "foto": fila[0].replace("h=300&w=300", "h=600&w=600") if fila and fila[0] else "",
            "ean": [c for c in cods if re.fullmatch(r"\d{8}|\d{13}", c)],
            "alias": [alias_normal(c) for c in cods if not re.fullmatch(r"\d{8}|\d{13}", c)],
            "sitio": loc.get(p.get("location_id")),
            "dias": dias if dias > 0 else -1,
            "unidad": "ud",
            "revisar": grupos.get(p.get("product_group_id")) == "Revisar",
            "no_inventariar": grupos.get(p.get("product_group_id")) == "No inventariar",
            "mercadona_id": mid,
        }
        productos[nuevo["id"]] = nuevo
        pid_nuevo[p["id"]] = nuevo["id"]

    lotes = {}
    for s in g("stock"):
        if s["product_id"] not in pid_nuevo:
            continue
        cad = s.get("best_before_date")
        l = {
            "id": nid(), "producto": pid_nuevo[s["product_id"]], "cantidad": float(s["amount"]),
            "sitio": loc.get(s.get("location_id")) or productos[pid_nuevo[s["product_id"]]]["sitio"],
            "comprado": s.get("purchased_date"), "caduca": None if not cad or cad.startswith("2999") else cad,
            "abierto": bool(int(s.get("open") or 0)),
        }
        lotes[l["id"]] = l
    return {"sitios": sitios, "productos": productos, "lotes": lotes}


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--grocy", required=True)
    a.add_argument("--db", help="mercadona.db, para las fotos")
    a.add_argument("--facturas", help="procesados.txt de despensa.py")
    a.add_argument("--ha", help="URL de HA; sin ella solo se escribe el JSON")
    o = a.parse_args()

    key = os.environ["GROCY_KEY"]
    g = lambda obj: pedir(f"{o.grocy.rstrip('/')}/api/objects/{obj}", grocy_key=key)
    db = sqlite3.connect(Path(o.db).expanduser()) if o.db else None
    datos = migrar(g, db)
    if o.facturas:
        datos["facturas"] = Path(o.facturas).expanduser().read_text().split()

    n = (len(datos["productos"]), sum(len(p["alias"]) for p in datos["productos"].values()),
         sum(len(p["ean"]) for p in datos["productos"].values()), len(datos["lotes"]))
    print(f"productos {n[0]}, alias {n[1]}, EAN {n[2]}, lotes {n[3]}, facturas {len(datos.get('facturas', []))}", file=sys.stderr)
    if not o.ha:
        print(json.dumps(datos, ensure_ascii=False, indent=1))
        return
    pedir(f"{o.ha.rstrip('/')}/api/services/despensa/importar", token=os.environ["HA_TOKEN"], cuerpo={"datos": datos})
    print("importado", file=sys.stderr)


if __name__ == "__main__":
    main()
