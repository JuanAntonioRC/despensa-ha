#!/usr/bin/env python3
"""
Ticket digital de Mercadona (Gmail) -> Despensa de Home Assistant.

  despensa.py correo        lee Gmail por IMAP y procesa los tickets nuevos
  despensa.py TICKET.pdf    procesa un PDF suelto
  despensa.py --seco PDF    muestra lo que se mandaria a HA, sin mandarlo
  despensa.py --test        comprobacion del parser y del emparejado, sin red

Cada linea del ticket va a HA con su "candidato" del catalogo local de Mercadona
(mercadona.db, lo mantiene sync_catalogo.py): nombre, foto, EAN y caducidad de su
categoria (caducidades.tsv). HA decide: si el texto del ticket ya es alias de un
producto, suma stock; si no, crea el producto (a revisar si no era seguro) y guarda
el texto como alias. La segunda vez ya no se busca ni se pregunta nada.
Los avisos (ticket procesado, caducidades) los manda HA.

Config en .env junto al script: HA_URL, HA_TOKEN, GMAIL_USER, GMAIL_APP_PASSWORD.
Codigo: repo despensa-ha, scripts/despensa.py. Plan: wiki "Despensa en Home Assistant".
"""

import email
import imaplib
import json
import os
import re
import sqlite3
import subprocess
import sys
import unicodedata
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

DIR = Path(__file__).resolve().parent
PROCESADOS = DIR / "procesados.txt"     # numeros de factura ya mandados a HA (HA tambien los descarta)


def cargar_env():
    f = DIR / ".env"
    if f.exists():
        for l in f.read_text().splitlines():
            if "=" in l and not l.lstrip().startswith("#"):
                k, v = l.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


# --------------------------------------------------------------------------- #
#  Ticket                                                                      #
# --------------------------------------------------------------------------- #
LINEA = re.compile(r"^\s*(\d+)\s+(\S.*?)\s{2,}(?:(\d+,\d\d)\s+)?(\d+,\d\d)\s*$")
LINEA_PESO = re.compile(r"^\s*(\d+)\s+(\S.*?)\s*$")                        # "1 PLATANO"
PESO = re.compile(r"^\s*[\d,]+\s*kg\s+[\d,]+\s*€/kg\s+(\d+,\d\d)\s*$")     # "1,086 kg 2,15 €/kg 2,33"


def num(s):
    return float(s.replace(",", "."))


def parsear(texto):
    """-> (factura, fecha, [(cantidad, descripcion, precio_unidad)])"""
    factura = re.search(r"FACTURA SIMPLIFICADA:\s*(\S+)", texto)
    fecha = re.search(r"(\d\d/\d\d/\d{4})\s+\d\d:\d\d", texto)
    lineas, dentro, pendiente = [], False, None
    for l in texto.splitlines():
        if "Descripci" in l and "Importe" in l:               # con o sin "Cnt." segun el ticket
            dentro = True
            continue
        if not dentro:
            continue
        if "TOTAL" in l:
            break
        if pendiente and (m := PESO.match(l)):
            lineas.append((1, pendiente, num(m[1])))
            pendiente = None
        elif m := LINEA.match(l):
            cnt, desc, unit, importe = int(m[1]), m[2].strip(), m[3], num(m[4])
            if importe > 0:                                   # PARKING 0,00 y similares
                lineas.append((cnt, desc, num(unit) if unit else importe / cnt))
        elif m := LINEA_PESO.match(l):
            pendiente = m[2].strip()
    fecha = datetime.strptime(fecha[1], "%d/%m/%Y").date() if fecha else date.today()
    return (factura[1] if factura else None), fecha, lineas


def texto_pdf(datos: bytes) -> str:
    return subprocess.run(["pdftotext", "-layout", "-", "-"], input=datos,
                          capture_output=True, check=True).stdout.decode()


# --------------------------------------------------------------------------- #
#  Emparejado con el catalogo                                                  #
# --------------------------------------------------------------------------- #
def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.findall(r"[a-z0-9]+", s)


def tokens_ticket(desc):
    # ponytail: letras sueltas ("C", "T", "B."), numeros sueltos ("P-6", "12 PAS") y "UDS" no distinguen nada; fuera
    return [("pack" if re.fullmatch(r"p\d+", t) else t) for t in norm(desc)
            if len(t) > 1 and not t.isdigit() and t != "uds"]


def puntuar(desc, nombre, slug):
    """Fraccion de palabras del ticket que son prefijo de alguna palabra del producto."""
    tt = tokens_ticket(desc)
    pp = set(norm(nombre)) | set(norm(slug))
    return sum(any(p.startswith(t) for p in pp) for t in tt) / len(tt) if tt else 0


def emparejar(conn, desc, precio):
    """-> (fila_producto | None, seguro: bool)"""
    filas = conn.execute("SELECT id, nombre, slug, categoria_id, categoria_nombre, precio_unidad,"
                         " foto_url, url FROM productos").fetchall()
    puntuados = sorted(((puntuar(desc, f[1], f[2]), abs(f[5] - precio) < 0.005, f) for f in filas),
                       key=lambda x: (x[0], x[1]), reverse=True)
    mejor_precio = [x for x in puntuados if x[1]]
    if mejor_precio and mejor_precio[0][0] == 1:              # todas las palabras + precio exacto
        f = mejor_precio[0][2]
        rivales = [x for x in mejor_precio[1:] if x[0] == 1 and x[2][1] != f[1]]
        return f, not rivales
    if mejor_precio and mejor_precio[0][0] > 0:              # intento: precio + alguna palabra
        return mejor_precio[0][2], False
    return None, False                                        # solo por nombre salian disparates ("DOBLE BURGER" -> salsa burger)


def caducidad(conn, categoria_id):
    """-> (dias, ubicacion) segun caducidades.tsv. None si la categoria no esta."""
    tabla = {}
    for l in (DIR / "caducidades.tsv").read_text().splitlines():
        if l.strip() and not l.startswith("#"):
            cat, dias, ubic = l.split("\t")
            tabla[cat] = (int(dias), ubic)
    fila = conn.execute("SELECT nombre, padre_nombre FROM categorias WHERE id = ?", (categoria_id,)).fetchone()
    if not fila:
        return None
    hoja, padre = fila
    return tabla.get(f"{padre}/{hoja}") or tabla.get(padre) or tabla.get(hoja)


# --------------------------------------------------------------------------- #
#  Home Assistant                                                              #
# --------------------------------------------------------------------------- #
def ha(servicio, datos):
    """Llama a un servicio de la integracion Despensa y devuelve su respuesta."""
    url = os.environ["HA_URL"].rstrip("/") + f"/api/services/despensa/{servicio}?return_response"
    req = urllib.request.Request(url, data=json.dumps(datos).encode(), method="POST", headers={
        "Authorization": "Bearer " + os.environ["HA_TOKEN"], "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())["service_response"]
    except urllib.error.HTTPError as e:
        # los errores de la integracion salen como 500: el motivo esta en el log de HA
        raise RuntimeError(f"HA {servicio}: HTTP {e.code} {e.read()[:300]!r} (mira el log de HA)") from None


def ean(mercadona_id, wh):
    try:
        req = urllib.request.Request(f"https://tienda.mercadona.es/api/products/{mercadona_id}/?lang=es&wh={wh}",
                                     headers={"User-Agent": "despensa-personal/1.0 (uso privado)"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()).get("ean")
    except Exception:
        return None


def candidato(conn, desc, precio, wh=None):
    """-> {texto, precio, seguro, candidato} para una linea del ticket. Con wh, busca el EAN en la tienda."""
    fila, seguro = emparejar(conn, desc, precio)
    if not fila:
        return {"texto": desc, "precio": round(precio, 2), "seguro": False, "candidato": None}
    dias, ubic = caducidad(conn, fila[3]) or (0, "Despensa")
    if "ultracongelad" in (fila[1] + fila[2]).lower():    # congelados y frescos comparten nombre de categoria ("Verdura")
        dias, ubic = 365, "Congelador"                     # HA lo lleva al primer sitio que empiece por "Congelador"
    return {"texto": desc, "precio": round(precio, 2), "seguro": seguro, "candidato": {
        "nombre": fila[1], "foto": (fila[6] or "").replace("h=300&w=300", "h=600&w=600"),
        "dias": dias if dias > 0 else -1,                  # en la tabla, 0 y -1 son "sin fecha"
        "sitio": ubic, "mercadona_id": fila[0], "unidad": "ud",
        "ean": ean(fila[0], wh) if (seguro and wh) else None,
    }}


def procesar(texto, conn, seco=False):
    factura, fecha, lineas = parsear(texto)
    hechos = set(PROCESADOS.read_text().split()) if PROCESADOS.exists() else set()
    if factura in hechos:
        print(f"Factura {factura} ya procesada, se salta.")
        return
    if not lineas:
        print(f"Ticket {factura} sin lineas: no se entiende el formato, se salta.")
        return
    wh = conn.execute("SELECT valor FROM sync_meta WHERE clave='warehouse'").fetchone()[0]
    # El EAN se pide a la tienda solo para lo que HA todavia no conoce.
    conocidos = set() if seco else set(ha("conocidos", {"textos": [d for _, d, _ in lineas]})["conocidos"])
    datos = {"factura": factura or f"sin-numero-{fecha.isoformat()}", "fecha": fecha.isoformat(), "tienda": "Mercadona",
             "lineas": [{**candidato(conn, d, p, None if (seco or d.upper() in conocidos) else wh), "cantidad": c}
                        for c, d, p in lineas]}
    if seco:
        print(json.dumps(datos, ensure_ascii=False, indent=1))
        return
    r = ha("registrar_ticket", datos)
    if factura:
        with PROCESADOS.open("a") as f:
            f.write(factura + "\n")
    print(f"Ticket {factura} {fecha:%d/%m}: {r['sumados']} al stock, {r['nuevos']} nuevos, "
          f"{len(r['revisar'])} a revisar, {r['ignorados']} sin inventariar" + (" (HA ya lo tenia)" if r["repetido"] else ""))


def correo(conn):
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"])
    # "Todos" / "All Mail" segun el idioma de la cuenta: se busca por su marca \\All
    todos = next(l.decode().rsplit(' "/" ', 1)[1] for l in imap.list()[1] if b"\\All" in l)
    imap.select(todos, readonly=True)
    _, ids = imap.search(None, "X-GM-RAW", '"from:mercadona has:attachment newer_than:30d"')
    for i in ids[0].split():
        _, d = imap.fetch(i, "(RFC822)")
        for parte in email.message_from_bytes(d[0][1]).walk():
            if parte.get_content_type() == "application/pdf" or (parte.get_filename() or "").lower().endswith(".pdf"):
                procesar(texto_pdf(parte.get_payload(decode=True)), conn)
    imap.logout()


# --------------------------------------------------------------------------- #
def test():
    sin_cnt = "  16/09/2026 16:58\n    Descripción      P. Unit   Importe\n  1 BAGEL                    1,42\n  TOTAL (€)  1,42"
    assert parsear(sin_cnt)[2] == [(1, "BAGEL", 1.42)]   # cabecera sin "Cnt." (tickets de agosto)
    t = """      FACTURA SIMPLIFICADA: 3469-020-973212
          16/09/2026 16:58    OP: 1087614
Cnt. Descripción                    P. Unit       Importe
  1 C ESTERIL T URINARIO                             5,80
  2 40 B.CIERRA FÁCIL                   1,80         3,60
  2 LECHE SEMI P6                       5,04        10,08
  1 PLATANO
      1,086 kg      2,15 €/kg      2,33
  1 PARKING                                          0,00
                                TOTAL (€)           25,48"""
    f, d, l = parsear(t)
    assert (f, d) == ("3469-020-973212", date(2026, 9, 16)), (f, d)
    assert l == [(1, "C ESTERIL T URINARIO", 5.8), (2, "40 B.CIERRA FÁCIL", 1.8),
                 (2, "LECHE SEMI P6", 5.04), (1, "PLATANO", 2.33)], l
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE productos (id, nombre, slug, categoria_id, categoria_nombre, precio_unidad, foto_url, url)")
    c.executemany("INSERT INTO productos VALUES (?,?,?,?,?,?,?,?)", [
        ("10381", "Leche semidesnatada Hacendado", "leche-semidesnatada-hacendado-pack-6", 1, "", 5.04, "", ""),
        ("10382", "Leche semidesnatada Hacendado", "leche-semidesnatada-hacendado-brick", 1, "", 0.84, "", ""),
        ("15560", "Comida gato adulto esterilizado Supreme Compy", "comida-gato-esterilizado", 2, "", 5.8, "", ""),
        ("13714", "Comida gato adulto Supreme Compy", "comida-gato-adulto", 2, "", 5.8, "", ""),
        ("49750", "Bolsas de basura 30L Bosque Verde", "bolsa-basura-30l", 3, "", 1.8, "", ""),
    ])
    f, seguro = emparejar(c, "LECHE SEMI P6", 5.04)
    assert f[0] == "10381" and seguro
    f, seguro = emparejar(c, "C ESTERIL T URINARIO", 5.8)
    assert f[0] == "15560" and not seguro          # buen intento, pero a revisar
    f, seguro = emparejar(c, "40 B.CIERRA FÁCIL", 1.8)
    assert f is None and not seguro                # solo coincide el precio: no se adivina
    c.execute("INSERT INTO productos VALUES ('17347','Salsa Burger Hacendado','salsa-burger',4,'',1.4,'','')")
    assert emparejar(c, "DOBLE BURGER", 6.0) == (None, False)
    c.execute("INSERT INTO productos VALUES ('1','Yogur griego natural Hacendado','yogur-griego',5,'',1.45,'','')")
    assert emparejar(c, "GRIEGO NATURAL P-6", 1.45)[1]           # el "P-6" no estorba   # sin precio no se adivina por nombre
    c.execute("CREATE TABLE categorias (id, nombre, padre_nombre)")
    c.execute("INSERT INTO productos VALUES ('2','Guisantes ultracongelados Hacendado','guisantes',6,'',1.2,'x?fit=crop&h=300&w=300','')")
    l = candidato(c, "GUISANTES ULTRACONG", 1.2)
    assert l["seguro"] and l["candidato"]["sitio"] == "Congelador" and l["candidato"]["dias"] == 365, l
    assert l["candidato"]["foto"].endswith("h=600&w=600") and l["candidato"]["ean"] is None   # sin wh no hay red
    assert candidato(c, "LECHE SEMI P6", 5.04)["candidato"]["dias"] == -1    # categoria sin tabla -> sin fecha
    assert candidato(c, "DOBLE BURGER", 6.0) == {"texto": "DOBLE BURGER", "precio": 6.0, "seguro": False, "candidato": None}
    print("ok")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--test":
        sys.exit(test())
    cargar_env()
    conn = sqlite3.connect(DIR / "mercadona.db")
    if arg == "correo":
        correo(conn)
    elif arg == "--seco" and len(sys.argv) > 2:
        procesar(texto_pdf(Path(sys.argv[2]).read_bytes()), conn, seco=True)
    elif arg.endswith(".pdf"):
        procesar(texto_pdf(Path(arg).read_bytes()), conn)
    else:
        sys.exit(__doc__)
