// Lo que comparten el panel y la tarjeta del kiosko.

const BASE = new URL(".", import.meta.url).href;

// @font-face no funciona dentro de un shadow DOM: se declara una vez en el documento.
export function cargarFuentes() {
  if (document.getElementById("despensa-fuentes")) return;
  const s = document.createElement("style");
  s.id = "despensa-fuentes";
  s.textContent = `
    @font-face { font-family:"Instrument Sans"; font-weight:400 700; font-display:swap; src:url(${BASE}fonts/instrument-sans.woff2) format("woff2"); }
    @font-face { font-family:"IBM Plex Mono"; font-weight:400; font-display:swap; src:url(${BASE}fonts/plex-mono-400.woff2) format("woff2"); }
    @font-face { font-family:"IBM Plex Mono"; font-weight:500; font-display:swap; src:url(${BASE}fonts/plex-mono-500.woff2) format("woff2"); }`;
  document.head.appendChild(s);
}

// Colores del diseño "Inventario Cocina". El modo oscuro sigue al de HA (atributo oscuro en el host).
export const TOKENS = `
  :host {
    --fondo:#faf8f4; --tarjeta:#fff; --borde:#eae5da; --borde-2:#e2ddd2; --hueco:#f2efe8; --linea:#f1ede4;
    --texto:#211f1b; --texto-2:#5d584d; --tenue:#8a8478; --tenue-2:#a09a8d;
    --acento:#2f6b46; --acento-texto:#fff;
    --rojo-bg:#f9e3e0; --rojo:#a32b1e; --ambar-bg:#fbeedb; --ambar:#8a5a12; --verde-bg:#e9f1ea; --verde:#2f6b46;
    --neutro-bg:#efece5; --neutro:#6f695d;
    --sel-bg:#211f1b; --sel-texto:#faf8f4;
    --sans:"Instrument Sans",-apple-system,Helvetica,sans-serif; --mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
    color-scheme: light;
  }
  :host([oscuro]) {
    --fondo:#171613; --tarjeta:#211f1b; --borde:#34312a; --borde-2:#3d3a32; --hueco:#2a2822; --linea:#2c2a24;
    --texto:#eeeae2; --texto-2:#c4beb1; --tenue:#9a9486; --tenue-2:#7d7769;
    --acento:#4f9a6c; --acento-texto:#0f1a13;
    --rojo-bg:#43201b; --rojo:#f0998c; --ambar-bg:#3f3019; --ambar:#e9bd72; --verde-bg:#1f3326; --verde:#8cc9a0;
    --neutro-bg:#2c2a24; --neutro:#b3ad9f;
    --sel-bg:#eeeae2; --sel-texto:#171613;
    color-scheme: dark;
  }`;

export const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

export const num = (x) => (Math.round(x * 1000) / 1000).toLocaleString("es-ES");

function hoy() {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

export function diasHasta(iso) {
  if (!iso) return null;
  const [y, m, d] = iso.split("-").map(Number);
  return Math.round((new Date(y, m - 1, d) - hoy()) / 86400000);
}

export const fechaCorta = (iso) => (iso ? `${iso.slice(8, 10)}/${iso.slice(5, 7)}` : "");
export const hoyISO = () => {
  const d = hoy();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

// Etiqueta de caducidad, con los mismos cortes que el diseño.
export function etiqueta(dias, ventana) {
  if (dias === null) return { texto: "No caduca", bg: "var(--neutro-bg)", fg: "var(--neutro)", pct: 100 };
  const pct = Math.max(4, Math.min(100, Math.round((Math.max(dias, 0) / 45) * 100)));
  if (dias < 0) return { texto: "Caducado", bg: "var(--rojo-bg)", fg: "var(--rojo)", pct };
  if (dias === 0) return { texto: "Hoy", bg: "var(--rojo-bg)", fg: "var(--rojo)", pct };
  if (dias === 1) return { texto: "Mañana", bg: "var(--ambar-bg)", fg: "var(--ambar)", pct };
  if (dias <= ventana) return { texto: `${dias} días`, bg: "var(--ambar-bg)", fg: "var(--ambar)", pct };
  if (dias <= 40) return { texto: `${dias} días`, bg: "var(--verde-bg)", fg: "var(--verde)", pct };
  return { texto: `${Math.round(dias / 30)} meses`, bg: "var(--verde-bg)", fg: "var(--verde)", pct };
}

// Un producto tal como se pinta: suma de sus lotes y el lote más urgente.
export function vista(datos, ventana) {
  const sitios = Object.fromEntries(datos.sitios.map((s) => [s.id, s.nombre]));
  const lotesPor = {};
  for (const l of Object.values(datos.lotes)) (lotesPor[l.producto] ||= []).push(l);
  const orden = (a, b) => (a.caduca || "9999") .localeCompare(b.caduca || "9999") || (a.comprado || "").localeCompare(b.comprado || "");
  const productos = Object.values(datos.productos).map((p) => {
    const lotes = (lotesPor[p.id] || []).sort(orden);
    const quedan = lotes.length ? diasHasta(lotes[0].caduca) : null;
    const sitioId = lotes[0]?.sitio ?? p.sitio;
    return {
      ...p, lotes, quedan, // p.dias son los días de caducidad por defecto; quedan, los que faltan
      cantidad: lotes.reduce((n, l) => n + l.cantidad, 0),
      abierto: lotes.some((l) => l.abierto),
      sitioId, sitioNombre: sitios[sitioId] || "Sin sitio",
      et: etiqueta(quedan, ventana),
    };
  });
  const porDias = (a, b) => (a.quedan ?? 1e9) - (b.quedan ?? 1e9) || a.nombre.localeCompare(b.nombre, "es");
  return { productos: productos.sort(porDias), sitios: datos.sitios, sitiosPorId: sitios };
}

export function suscribir(hass, alRecibir) {
  return hass.connection.subscribeMessage(alRecibir, { type: "despensa/subscribe" });
}

export async function llamar(hass, servicio, datos = {}, conRespuesta = false) {
  try {
    const r = await hass.callWS({
      type: "call_service", domain: "despensa", service: servicio, service_data: datos,
      ...(conRespuesta ? { return_response: true } : {}),
    });
    return { ok: true, respuesta: r?.response };
  } catch (e) {
    return { ok: false, error: String(e?.message || e).replace(/^Validation error:\s*/, "") };
  }
}

// Foto del producto o, si no hay, sus iniciales sobre el color de hueco.
export function foto(p, alto) {
  if (p.foto) return `<img src="${esc(p.foto)}" alt="" loading="lazy" style="width:100%;height:${alto}px;object-fit:contain;display:block;background:#fff">`;
  const ini = p.nombre.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
  return `<div style="height:${alto}px;display:flex;align-items:center;justify-content:center;font:600 ${Math.round(alto / 3.2)}px var(--sans);color:var(--tenue-2);letter-spacing:.02em">${esc(ini)}</div>`;
}
