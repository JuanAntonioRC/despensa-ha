// Panel "Despensa": el diseño "Inventario Cocina" conectado a la integración.
// Sin compilación: se pinta con plantillas y un solo manejador de clics (data-acc).
// Lo de arriba (buscador) se pinta una vez; #contenido se repinta con cada cambio; #capa son los diálogos.
import {
  TOKENS, cargarFuentes, esc, num, etiqueta, vista, suscribir, llamar, foto, fechaCorta, hoyISO, diasHasta,
} from "./comun.js";

const CSS = `
  ${TOKENS}
  :host { display:block; min-height:100vh; background:var(--fondo); color:var(--texto); font-family:var(--sans); -webkit-font-smoothing:antialiased }
  * { box-sizing:border-box }
  button, input, select { font-family:inherit; color:inherit }
  button { cursor:pointer }
  .mono { font-family:var(--mono) }
  .pagina { max-width:1180px; margin:0 auto; padding:18px 16px 80px; display:flex; flex-direction:column; gap:24px }
  .menu { height:0 } .menu:not(:empty) { height:auto; margin:-8px 0 -12px -8px }
  header { display:flex; flex-wrap:wrap; gap:16px; align-items:flex-end; justify-content:space-between }
  .ceja { font-family:var(--mono); font-size:11px; letter-spacing:.14em; text-transform:uppercase; color:var(--tenue) }
  h1 { font-size:34px; font-weight:600; letter-spacing:-.02em; margin:6px 0 0 }
  h2 { font-size:19px; font-weight:600; margin:0 }
  .acciones { display:flex; gap:8px; align-items:center; flex-wrap:wrap }
  input[type=search], .campo { border:1px solid var(--borde-2); background:var(--tarjeta); border-radius:10px; padding:10px 14px; font-size:16px; outline:none; min-width:0 }
  input[type=search] { width:210px }
  input:focus, select:focus { border-color:var(--acento) }
  .pri { border:none; border-radius:10px; padding:11px 16px; font-size:14px; font-weight:600; color:var(--acento-texto); background:var(--acento) }
  .pri:hover { filter:brightness(1.08) }
  .sec { border:1px solid var(--borde-2); background:var(--tarjeta); border-radius:10px; padding:10px 14px; font-size:14px; font-weight:600; color:var(--texto-2) }
  .sec:hover { background:var(--hueco) }
  .enlace { background:none; border:none; padding:0; color:var(--acento); font-size:13px; font-weight:600 }

  .cifras { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px }
  .cifra { background:var(--tarjeta); border:1px solid var(--borde); border-radius:14px; padding:14px 15px; display:flex; flex-direction:column; gap:7px }
  .cifra .et { font-family:var(--mono); font-size:10.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--tenue) }
  .cifra .v { font-size:27px; font-weight:600; letter-spacing:-.02em }
  .cifra .n { font-size:12.5px; color:var(--tenue) }

  .bloque { display:flex; flex-direction:column; gap:12px }
  .titulo { display:flex; flex-wrap:wrap; align-items:baseline; gap:10px; justify-content:space-between }
  .titulo .nota { font-family:var(--mono); font-size:11.5px; color:var(--tenue) }
  .rejilla { display:grid; grid-template-columns:repeat(auto-fill,minmax(152px,1fr)); gap:12px }
  .rejilla.grande { grid-template-columns:repeat(auto-fill,minmax(190px,1fr)) }

  .prod { position:relative; background:var(--tarjeta); border:1px solid var(--borde); border-radius:15px; overflow:hidden; display:flex; flex-direction:column }
  .prod .foto { position:relative; background:var(--hueco); cursor:pointer }
  .chip { position:absolute; top:7px; font-family:var(--mono); font-size:10px; font-weight:500; padding:3px 6px; border-radius:5px }
  .chip.izq { left:7px } .chip.der { right:7px; background:var(--sel-bg); color:var(--sel-texto) }
  .prod .cuerpo { padding:10px 11px 11px; display:flex; flex-direction:column; gap:8px; flex:1 }
  .prod .nombre { font-size:13.5px; font-weight:600; line-height:1.25; cursor:pointer; text-wrap:pretty; overflow-wrap:anywhere }
  .grande .prod .nombre { font-size:14px }
  .meta { font-family:var(--mono); font-size:10.5px; color:var(--tenue) }
  .barra { height:3px; border-radius:2px; background:var(--linea); overflow:hidden }
  .barra div { height:3px; border-radius:2px }
  .botones { margin-top:auto; display:flex; flex-direction:column; gap:6px }
  .fila { display:flex; gap:6px }
  .botones .pri { border-radius:8px; padding:9px 8px; font-size:12.5px; white-space:nowrap }
  .botones .sec { flex:1; border-radius:8px; padding:7px 6px; font-size:12px; white-space:nowrap }
  .grande .botones { flex-direction:row } .grande .botones .pri { flex:1; font-size:13px }
  .destinos { position:absolute; inset:0; background:color-mix(in srgb, var(--fondo) 96%, transparent); padding:11px; display:flex; flex-direction:column; gap:5px; overflow:auto }
  .destinos button { text-align:left; border:1px solid var(--borde-2); background:var(--tarjeta); border-radius:8px; padding:7px 9px; font-size:12px }
  .destinos button:hover { background:var(--hueco) }

  .revisar { background:var(--ambar-bg); border-radius:16px; padding:14px; display:flex; flex-direction:column; gap:10px }
  .rev { background:var(--tarjeta); border:1px solid var(--borde); border-radius:12px; padding:10px; display:flex; gap:12px; align-items:center; flex-wrap:wrap }
  .rev .mini { width:56px; height:56px; border-radius:9px; overflow:hidden; background:var(--hueco); flex:none }
  .rev .txt { flex:1 1 180px; min-width:0; display:flex; flex-direction:column; gap:3px }
  .rev .fila .sec, .rev .fila .pri { flex:none; padding:8px 12px; font-size:12.5px; border-radius:8px }

  .columnas { display:flex; flex-wrap:wrap; gap:22px; align-items:flex-start }
  aside { flex:0 0 212px; min-width:184px; display:flex; flex-direction:column; gap:4px }
  aside .et { font-family:var(--mono); font-size:10.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--tenue); padding:0 4px 8px; display:flex; justify-content:space-between; align-items:baseline }
  .sitio { display:flex; align-items:center; justify-content:space-between; gap:8px; text-align:left; border:1px solid var(--borde); background:var(--tarjeta); border-radius:11px; padding:10px 12px; font-size:13.5px; font-weight:500; width:100% }
  .sitio:hover { border-color:var(--borde-2) }
  .sitio.act { background:var(--sel-bg); color:var(--sel-texto); border-color:var(--sel-bg); font-weight:600 }
  .sitio .c { font-family:var(--mono); font-size:11px; opacity:.7 }
  .actividad { margin-top:14px; background:var(--tarjeta); border:1px solid var(--borde); border-radius:13px; padding:13px; display:flex; flex-direction:column; gap:8px }
  .actividad .item { display:flex; flex-direction:column; gap:2px; padding:6px 0; border-top:1px solid var(--linea) }
  .actividad .item div:first-child { font-size:12.5px; line-height:1.35 }
  .actividad .item div:last-child { font-family:var(--mono); font-size:10.5px; color:var(--tenue-2) }
  .principal { flex:1 1 440px; min-width:0; display:flex; flex-direction:column; gap:14px }
  .vacio { color:var(--tenue); font-size:14px; padding:28px 0; text-align:center }

  @media (max-width: 720px) {
    h1 { font-size:28px }
    header .acciones { width:100% } input[type=search] { flex:1 1 100%; width:auto }
    header .acciones button { flex:1 }
    aside { flex:1 1 100%; min-width:0 }
    .sitios { display:flex; gap:6px; overflow-x:auto; padding-bottom:4px; scrollbar-width:none }
    .sitios .sitio { width:auto; flex:none; padding:8px 12px }
    .actividad { display:none }
    .rejilla, .rejilla.grande { grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px }
    .grande .botones { flex-direction:column } .grande .botones .sec { flex:1 !important }
    .cifras { gap:8px } .cifra { padding:11px 12px; gap:4px } .cifra .v { font-size:22px }
  }

  /* diálogos */
  #capa { position:fixed; inset:0; z-index:10; background:rgba(20,18,14,.45); display:flex; align-items:center; justify-content:center; padding:16px }
  #capa[hidden] { display:none }
  .dialogo { background:var(--fondo); color:var(--texto); border-radius:18px; width:min(560px,100%); max-height:calc(100vh - 32px); overflow:auto; padding:18px; display:flex; flex-direction:column; gap:14px; box-shadow:0 20px 60px rgba(0,0,0,.25) }
  @media (max-width: 720px) {
    #capa { align-items:flex-end; padding:0 }
    .dialogo { border-radius:18px 18px 0 0; max-height:92vh; padding-bottom:calc(18px + env(safe-area-inset-bottom)) }
  }
  .dialogo .cab { display:flex; justify-content:space-between; align-items:center; gap:10px }
  .form { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px }
  label.l { display:flex; flex-direction:column; gap:5px; font-size:12px; color:var(--tenue); font-weight:500 }
  label.l .campo { font-size:16px; padding:9px 11px; color:var(--texto) }
  textarea.campo { resize:vertical; min-height:62px; font-family:var(--mono); font-size:13px }
  .check { display:flex; gap:8px; align-items:center; font-size:14px }
  .lote { display:grid; grid-template-columns:80px 1fr 1fr auto; gap:8px; align-items:center; background:var(--tarjeta); border:1px solid var(--borde); border-radius:10px; padding:8px }
  .lote .campo { padding:7px 8px; font-size:15px }
  .peligro { color:var(--rojo) !important; border-color:var(--rojo-bg) !important }
  video { width:100%; border-radius:12px; background:#000; aspect-ratio:4/3; object-fit:cover }
  .fila-sitio { display:flex; gap:6px; align-items:center }
  .fila-sitio .campo { flex:1 }
  .fila-sitio .sec { padding:8px 10px }

  #toast { position:fixed; left:50%; transform:translateX(-50%); bottom:calc(20px + env(safe-area-inset-bottom)); z-index:20; background:var(--sel-bg); color:var(--sel-texto); border-radius:12px; padding:11px 14px; display:flex; gap:14px; align-items:center; font-size:14px; box-shadow:0 8px 30px rgba(0,0,0,.25); max-width:calc(100vw - 32px) }
  #toast[hidden] { display:none }
  #toast.error { background:var(--rojo); color:#fff }
  #toast button { background:none; border:none; color:inherit; font-weight:700; text-decoration:underline; padding:0 }
`;

const FORMATOS = ["ean_13", "ean_8", "upc_a", "upc_e"];

function cuando(ts) {
  const d = new Date(ts);
  const min = Math.round((Date.now() - d) / 60000);
  const hora = d.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
  if (min < 1) return "ahora";
  if (min < 60) return `hace ${min} min`;
  const dias = -diasHasta(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`);
  if (dias === 0) return `hoy ${hora}`;
  if (dias === 1) return `ayer ${hora}`;
  return d.toLocaleDateString("es-ES", { day: "numeric", month: "short" });
}

class DespensaPanel extends HTMLElement {
  constructor() {
    super();
    this._sel = "todo";
    this._busca = "";
    this._moviendo = null;
    this._capa = null; // {tipo, ...}
  }

  set hass(hass) {
    const primera = !this._hass;
    this._hass = hass;
    this.toggleAttribute("oscuro", !!hass.themes?.darkMode);
    if (this._menu) this._menu.hass = hass;
    if (primera) this._montar();
  }

  set narrow(v) {
    this._narrow = v;
    this._ponerMenu();
  }

  connectedCallback() {
    if (this._hass && !this._baja) this._suscribir();
  }

  disconnectedCallback() {
    this._pararCamara();
    this._baja?.then((f) => f());
    this._baja = null;
  }

  // --- montaje ----------------------------------------------------------

  _montar() {
    cargarFuentes();
    const root = this.attachShadow({ mode: "open" });
    root.innerHTML = `
      <style>${CSS}</style>
      <div class="pagina">
        <div class="menu" id="menu"></div>
        <header>
          <div>
            <div class="ceja">Home Assistant · despensa</div>
            <h1>Inventario de casa</h1>
          </div>
          <div class="acciones">
            <input id="busca" type="search" placeholder="Buscar producto…" aria-label="Buscar producto" autocomplete="off">
            <button class="sec" data-acc="escanear">Escanear</button>
            <button class="pri" data-acc="nuevo">Añadir a mano</button>
          </div>
        </header>
        <main id="contenido"><div class="vacio">Cargando…</div></main>
      </div>
      <div id="capa" hidden></div>
      <div id="toast" hidden></div>`;
    this._c = root.getElementById("contenido");
    this._capaEl = root.getElementById("capa");
    root.getElementById("busca").addEventListener("input", (e) => {
      this._busca = e.target.value.trim();
      this._pintar();
    });
    root.addEventListener("click", (e) => this._clic(e));
    this._capaEl.addEventListener("click", (e) => { if (e.target === this._capaEl) this._cerrar(); });
    root.addEventListener("change", (e) => this._cambio(e));
    root.addEventListener("keydown", (e) => { if (e.key === "Escape" && this._capa) this._cerrar(); });
    this._ponerMenu();
    this._suscribir();
  }

  _ponerMenu() {
    const cont = this.shadowRoot?.getElementById("menu");
    if (!cont) return;
    if (this._narrow && !this._menu) {
      this._menu = document.createElement("ha-menu-button");
      this._menu.hass = this._hass;
      this._menu.narrow = true;
      cont.appendChild(this._menu);
    } else if (!this._narrow && this._menu) {
      this._menu.remove();
      this._menu = null;
    }
  }

  _suscribir() {
    this._baja = suscribir(this._hass, (ev) => {
      const primera = !this._datos;
      this._datos = ev.datos;
      this._ventana = ev.ventana;
      this._puedeDeshacer = ev.puede_deshacer;
      this._pintar();
      if (this._capa?.tipo === "ficha" && !this.shadowRoot.activeElement?.closest?.("#capa")) this._pintarCapa();
      if (primera && new URLSearchParams(location.search).get("ver") === "revisar") {
        this._verRevisar = true;
        this._pintar();
        this.shadowRoot.getElementById("revisar")?.scrollIntoView({ behavior: "smooth" });
      }
    });
    this._baja.catch((e) => {
      this._c.innerHTML = `<div class="vacio">No se pudo conectar con la integración: ${esc(e?.message || e)}</div>`;
    });
  }

  // --- pintado ----------------------------------------------------------

  _pintar() {
    if (!this._datos) return;
    const v = vista(this._datos, this._ventana);
    this._v = v;
    const conStock = v.productos.filter((p) => p.lotes.length && !p.no_inventariar);
    const b = this._busca.toLocaleLowerCase("es");

    if (b) {
      const hallados = v.productos.filter((p) =>
        p.nombre.toLocaleLowerCase("es").includes(b) || p.alias.some((a) => a.toLowerCase().includes(b)) || p.ean.includes(this._busca));
      this._c.innerHTML = `
        <section class="bloque">
          <div class="titulo"><h2>Buscando «${esc(this._busca)}»</h2><div class="nota">${hallados.length} productos</div></div>
          ${hallados.length ? `<div class="rejilla">${hallados.map((p) => this._tarjeta(p)).join("")}</div>`
            : `<div class="vacio">Nada con ese nombre. <button class="enlace" data-acc="nuevo" data-nombre="${esc(this._busca)}">Añadirlo</button></div>`}
        </section>`;
      return;
    }

    const pronto = conStock.filter((p) => p.quedan !== null && p.quedan >= 0 && p.quedan <= this._ventana);
    const caducados = conStock.filter((p) => p.quedan !== null && p.quedan < 0);
    const urgentes = conStock.filter((p) => p.quedan !== null && p.quedan <= this._ventana);
    const congeladores = v.sitios.filter((s) => /^congelador/i.test(s.nombre));
    const congelado = conStock.filter((p) => p.lotes.some((l) => congeladores.some((s) => s.id === l.sitio)));
    const sitiosConCosas = new Set(conStock.flatMap((p) => p.lotes.map((l) => l.sitio)));
    const enSitio = (sid) => conStock.filter((p) => p.lotes.some((l) => l.sitio === sid));
    if (this._sel !== "todo" && !v.sitios.some((s) => s.id === this._sel)) this._sel = "todo";
    const visibles = this._sel === "todo" ? conStock : enSitio(this._sel);
    const revisar = v.productos.filter((p) => p.revisar);

    const cifra = (et, val, nota, color) =>
      `<div class="cifra"><div class="et">${et}</div><div class="v" style="color:${color}">${val}</div><div class="n">${esc(nota)}</div></div>`;

    this._c.innerHTML = `
      <div style="display:flex;flex-direction:column;gap:24px">
        <div class="cifras">
          ${cifra("Caduca pronto", pronto.length, `próximos ${this._ventana} días`, "var(--ambar)")}
          ${cifra("Caducado", caducados.length, "revisar y tirar", "var(--rojo)")}
          ${cifra("Productos", conStock.length, `en ${sitiosConCosas.size} sitios`, "var(--texto)")}
          ${cifra("Congelado", congelado.length, congeladores.map((s) => s.nombre.replace(/^congelador\s*/i, "") || "congelador").join(" + ") || "sin congelador", "var(--texto)")}
        </div>

        ${urgentes.length ? `
        <section class="bloque">
          <div class="titulo"><h2>Hay que gastarlo</h2>
            <div class="nota">${caducados.length ? `${caducados.length} caducado(s) y ${pronto.length} en ${this._ventana} días` : `${pronto.length} productos en ${this._ventana} días`}</div></div>
          <div class="rejilla grande">${urgentes.slice(0, 4).map((p) => this._tarjeta(p, true)).join("")}</div>
        </section>` : ""}

        ${revisar.length ? `
        <section class="revisar" id="revisar">
          <div class="titulo"><h2>Por revisar</h2><div class="nota" style="color:var(--ambar)">del ticket, sin estar seguro · se revisa una sola vez</div></div>
          ${(this._verRevisar ? revisar : revisar.slice(0, 3)).map((p) => this._revisar(p)).join("")}
          ${revisar.length > 3 ? `<button class="enlace" style="align-self:flex-start" data-acc="ver-revisar">${this._verRevisar ? "Ver menos" : `Ver los ${revisar.length}`}</button>` : ""}
        </section>` : ""}

        <div class="columnas">
          <aside>
            <div class="et"><span>Sitios</span><button class="enlace" data-acc="sitios">Editar</button></div>
            <div class="sitios">
              ${[{ id: "todo", nombre: "Todo" }, ...v.sitios].map((s) => `
                <button class="sitio ${s.id === this._sel ? "act" : ""}" data-acc="sitio" data-id="${s.id}">
                  <span>${esc(s.nombre)}</span><span class="c">${s.id === "todo" ? conStock.length : enSitio(s.id).length}</span>
                </button>`).join("")}
            </div>
            <div class="actividad">
              <div class="et" style="padding:0">Actividad</div>
              ${this._datos.actividad.slice(0, 8).map((a) => `
                <div class="item"><div>${esc(a.texto)}</div><div>${cuando(a.ts)}</div></div>`).join("") || `<div class="meta">Todavía nada</div>`}
            </div>
          </aside>
          <section class="principal">
            <div class="titulo">
              <h2>${this._sel === "todo" ? "Todo el inventario" : esc(v.sitiosPorId[this._sel])}</h2>
              <div class="nota">${visibles.length} productos · ordenados por caducidad</div>
            </div>
            ${visibles.length ? `<div class="rejilla">${visibles.map((p) => this._tarjeta(p)).join("")}</div>`
              : `<div class="vacio">${conStock.length ? "Aquí no hay nada." : "La despensa está vacía. Llegará sola con el próximo ticket, o usa «Añadir a mano»."}</div>`}
          </section>
        </div>
      </div>`;
  }

  _tarjeta(p, grande = false) {
    const et = p.et;
    const alto = grande ? 124 : 110;
    const hay = p.lotes.length > 0;
    const moviendo = this._moviendo === p.id;
    const destinos = moviendo ? this._v.sitios.filter((s) => s.id !== p.sitioId) : [];
    return `
      <article class="prod">
        <div class="foto" data-acc="ficha" data-id="${p.id}">
          ${foto(p, alto)}
          ${hay ? `<span class="chip izq" style="background:${et.bg};color:${et.fg}">${et.texto}</span>` : `<span class="chip izq" style="background:var(--neutro-bg);color:var(--neutro)">Sin stock</span>`}
          ${p.abierto ? `<span class="chip der">abierto</span>` : ""}
        </div>
        <div class="cuerpo">
          <div class="nombre" data-acc="ficha" data-id="${p.id}">${esc(p.nombre)}</div>
          <div class="meta">${hay ? `${num(p.cantidad)} ${esc(p.unidad)} · ${esc(p.sitioNombre)}` : p.no_inventariar ? "no se inventaría" : "se acabó"}</div>
          ${hay ? `<div class="barra"><div style="width:${et.pct}%;background:${et.fg}"></div></div>` : ""}
          <div class="botones">
            ${hay ? `
              <button class="pri" data-acc="usar" data-id="${p.id}">He usado uno</button>
              ${grande ? `<button class="sec" style="flex:none;padding:9px 11px" data-acc="acabar" data-id="${p.id}">Se acabó</button>` : `
              <div class="fila">
                <button class="sec" data-acc="acabar" data-id="${p.id}">Se acabó</button>
                <button class="sec" style="font-weight:500" data-acc="mover" data-id="${p.id}">Mover</button>
              </div>`}`
            : `<button class="pri" data-acc="anadir-uno" data-id="${p.id}">Añadir uno</button>`}
          </div>
        </div>
        ${moviendo ? `
          <div class="destinos">
            <div class="meta" style="letter-spacing:.08em;text-transform:uppercase">Mover a</div>
            ${destinos.map((s) => `<button data-acc="mover-a" data-id="${p.id}" data-sitio="${s.id}">${esc(s.nombre)}</button>`).join("")}
            <button data-acc="mover" data-id="${p.id}" style="color:var(--tenue)">Cancelar</button>
          </div>` : ""}
      </article>`;
  }

  _revisar(p) {
    return `
      <div class="rev">
        <div class="mini" data-acc="ficha" data-id="${p.id}">${foto(p, 56)}</div>
        <div class="txt">
          <div style="font-weight:600;font-size:14px">${esc(p.nombre)}</div>
          <div class="meta">Ticket: ${esc(p.alias.join(" · ") || "—")}</div>
          <div class="meta">${esc(p.sitioNombre)} · ${this._diasTexto(p.dias)}</div>
        </div>
        <div class="fila">
          <button class="pri" data-acc="rev-ok" data-id="${p.id}">Está bien</button>
          <button class="sec" data-acc="ficha" data-id="${p.id}">Editar</button>
          <button class="sec" data-acc="rev-no" data-id="${p.id}">No inventariar</button>
        </div>
      </div>`;
  }

  _diasTexto(d) {
    return d < 0 ? "no caduca" : `caduca a los ${d} días`;
  }

  // --- diálogos ---------------------------------------------------------

  _abrir(capa) {
    this._capa = capa;
    this._capaEl.hidden = false;
    this._pintarCapa();
  }

  _cerrar() {
    this._pararCamara();
    this._capa = null;
    this._capaEl.hidden = true;
    this._capaEl.innerHTML = "";
  }

  _opcionesSitio(sel) {
    return this._datos.sitios.map((s) => `<option value="${s.id}" ${s.id === sel ? "selected" : ""}>${esc(s.nombre)}</option>`).join("");
  }

  _pintarCapa() {
    const c = this._capa;
    if (!c) return;
    const cab = (t) => `<div class="cab"><h2>${t}</h2><button class="sec" data-acc="cerrar">Cerrar</button></div>`;
    let html = "";
    if (c.tipo === "ficha") {
      const p = this._datos.productos[c.id];
      if (!p) return this._cerrar();
      const pv = this._v.productos.find((x) => x.id === c.id);
      html = `
        ${cab(esc(p.nombre))}
        <div style="display:flex;gap:14px;align-items:center">
          <div style="width:84px;height:84px;border-radius:12px;overflow:hidden;background:var(--hueco);flex:none">${foto(p, 84)}</div>
          <div class="meta" style="line-height:1.6">${pv.lotes.length ? `${num(pv.cantidad)} ${esc(p.unidad)} en total` : "Sin stock"}${p.mercadona_id ? `<br>Mercadona ${esc(p.mercadona_id)}` : ""}</div>
        </div>
        ${pv.lotes.length ? `
        <div class="bloque" style="gap:8px">
          <div class="meta" style="text-transform:uppercase;letter-spacing:.1em">Lotes · cambia la fecha por la del envase</div>
          ${pv.lotes.map((l) => `
            <div class="lote">
              <input class="campo" type="number" step="any" min="0" value="${l.cantidad}" data-lote="${l.id}" data-campo="cantidad" aria-label="Cantidad">
              <input class="campo" type="date" value="${l.caduca || ""}" data-lote="${l.id}" data-campo="caduca" aria-label="Caduca">
              <select class="campo" data-lote="${l.id}" data-campo="sitio" aria-label="Sitio">${this._opcionesSitio(l.sitio)}</select>
              <span class="meta" title="Comprado">${fechaCorta(l.comprado)}</span>
            </div>`).join("")}
        </div>` : ""}
        <form class="form" id="f-ficha" onsubmit="return false">
          <label class="l" style="grid-column:1/-1">Nombre<input class="campo" name="nombre" value="${esc(p.nombre)}" required></label>
          <label class="l">Sitio habitual<select class="campo" name="sitio"><option value="">—</option>${this._opcionesSitio(p.sitio)}</select></label>
          <label class="l">Unidad<input class="campo" name="unidad" value="${esc(p.unidad)}"></label>
          <label class="l">Caduca a los (días)<input class="campo" name="dias" type="number" min="0" value="${p.dias >= 0 ? p.dias : ""}" placeholder="no caduca"></label>
          <label class="l">Foto (URL)<input class="campo" name="foto" value="${esc(p.foto)}"></label>
          <label class="l" style="grid-column:1/-1">Códigos EAN (uno por línea)<textarea class="campo" name="ean">${esc(p.ean.join("\n"))}</textarea></label>
          <label class="l" style="grid-column:1/-1">Textos del ticket (uno por línea)<textarea class="campo" name="alias">${esc(p.alias.join("\n"))}</textarea></label>
          <label class="check"><input type="checkbox" name="revisar" ${p.revisar ? "checked" : ""}> Por revisar</label>
          <label class="check"><input type="checkbox" name="no_inventariar" ${p.no_inventariar ? "checked" : ""}> No inventariar</label>
        </form>
        <div class="fila" style="justify-content:space-between">
          <button class="sec peligro" data-acc="borrar" data-id="${p.id}">${c.borrar ? "¿Seguro? Pulsa otra vez" : "Borrar producto"}</button>
          <button class="pri" data-acc="guardar-ficha" data-id="${p.id}">Guardar</button>
        </div>`;
    } else if (c.tipo === "nuevo") {
      html = `
        ${cab("Añadir a mano")}
        <form class="form" id="f-nuevo" onsubmit="return false">
          <label class="l" style="grid-column:1/-1">Nombre<input class="campo" name="nombre" list="nombres" value="${esc(c.nombre || "")}" required autocomplete="off"></label>
          <datalist id="nombres">${Object.values(this._datos.productos).map((p) => `<option value="${esc(p.nombre)}">`).join("")}</datalist>
          <label class="l">Cantidad<input class="campo" name="cantidad" type="number" step="any" min="0" value="1"></label>
          <label class="l">Caduca<input class="campo" name="caduca" type="date" min="${hoyISO()}"></label>
          <label class="l">Sitio<select class="campo" name="sitio"><option value="">el de siempre</option>${this._opcionesSitio(this._sel !== "todo" ? this._sel : "")}</select></label>
          ${c.ean ? `<label class="l">EAN<input class="campo" name="ean" value="${esc(c.ean)}" readonly></label>` : ""}
        </form>
        <div class="meta">Si el producto ya existe, se suma a lo que hay. Sin fecha, se calcula con sus días de siempre.</div>
        <div class="fila" style="justify-content:flex-end"><button class="pri" data-acc="guardar-nuevo">Guardar</button></div>`;
    } else if (c.tipo === "sitios") {
      html = `
        ${cab("Sitios")}
        <div class="bloque" style="gap:8px" id="lista-sitios">
          ${c.lista.map((s, i) => `
            <div class="fila-sitio">
              <input class="campo" value="${esc(s.nombre)}" data-i="${i}" aria-label="Nombre del sitio">
              <button class="sec" data-acc="sitio-subir" data-i="${i}" aria-label="Subir" ${i ? "" : "disabled"}>↑</button>
              <button class="sec peligro" data-acc="sitio-quitar" data-i="${i}" aria-label="Quitar">✕</button>
            </div>`).join("")}
        </div>
        <div class="fila" style="justify-content:space-between">
          <button class="sec" data-acc="sitio-nuevo">Añadir sitio</button>
          <button class="pri" data-acc="guardar-sitios">Guardar</button>
        </div>
        <div class="meta">Un sitio con cosas dentro no se puede quitar: muévelas antes.</div>`;
    } else if (c.tipo === "escaner") {
      const p = c.producto;
      html = `
        ${cab("Escanear")}
        ${c.leido ? (p ? `
          <div style="display:flex;gap:14px;align-items:center">
            <div style="width:84px;height:84px;border-radius:12px;overflow:hidden;background:var(--hueco);flex:none">${foto(p, 84)}</div>
            <div><div style="font-weight:600;font-size:16px">${esc(p.nombre)}</div>
              <div class="meta">${p.lotes.length ? `${num(p.cantidad)} ${esc(p.unidad)} · ${esc(p.sitioNombre)} · ${p.et.texto}` : "sin stock"}</div></div>
          </div>
          <div class="fila">
            ${p.lotes.length ? `<button class="pri" style="flex:1" data-acc="usar" data-id="${p.id}" data-cerrar>He usado uno</button>` : ""}
            <button class="sec" style="flex:1" data-acc="anadir-uno" data-id="${p.id}" data-cerrar>Añadir uno</button>
          </div>
          <div class="fila"><button class="sec" style="flex:1" data-acc="ficha" data-id="${p.id}">Ver ficha</button>
            <button class="sec" style="flex:1" data-acc="escanear">Escanear otro</button></div>`
          : `<div>El código <span class="mono">${esc(c.leido)}</span> no es de ningún producto.</div>
             <div class="fila"><button class="pri" style="flex:1" data-acc="nuevo" data-ean="${esc(c.leido)}">Añadir producto nuevo</button>
             <button class="sec" style="flex:1" data-acc="escanear">Escanear otro</button></div>
             <div class="meta">Para asociarlo a un producto que ya existe, pon el código en su ficha.</div>`) : `
          <video id="video" playsinline muted></video>
          <div class="meta" id="estado-cam">Abriendo la cámara…</div>
          <label class="sec" style="text-align:center">Hacer foto en su lugar
            <input id="foto-cam" type="file" accept="image/*" capture="environment" hidden></label>`}`;
    }
    this._capaEl.innerHTML = `<div class="dialogo" role="dialog" aria-modal="true">${html}</div>`;
    if (c.tipo === "escaner" && !c.leido) this._abrirCamara();
    if (c.tipo === "nuevo") this._capaEl.querySelector("[name=nombre]")?.focus();
  }

  // --- cámara -----------------------------------------------------------

  async _detector() {
    if (!this._det) {
      const { BarcodeDetector, setZXingModuleOverrides } = await import("./vendor/ponyfill.js");
      setZXingModuleOverrides({
        locateFile: (path, prefix) => (path.endsWith(".wasm") ? new URL("./vendor/zxing_reader.wasm", import.meta.url).href : prefix + path),
      });
      this._det = new BarcodeDetector({ formats: FORMATOS });
    }
    return this._det;
  }

  _leido(codigo) {
    this._pararCamara();
    navigator.vibrate?.(60);
    const p = this._v.productos.find((x) => x.ean.includes(codigo));
    this._capa = { tipo: "escaner", leido: codigo, producto: p };
    this._pintarCapa();
  }

  async _abrirCamara() {
    const estado = (t) => { const e = this._capaEl.querySelector("#estado-cam"); if (e) e.textContent = t; };
    this._capaEl.querySelector("#foto-cam").onchange = async (ev) => {
      const f = ev.target.files[0];
      if (!f) return;
      estado("Leyendo la foto…");
      try {
        const r = await (await this._detector()).detect(await createImageBitmap(f));
        r.length ? this._leido(r[0].rawValue) : estado("No se ve ningún código en la foto. Prueba más cerca y con luz.");
      } catch (e) { estado("No se pudo leer la foto: " + e.message); }
    };
    if (!navigator.mediaDevices?.getUserMedia) {
      estado(isSecureContext ? "Este navegador no deja usar la cámara. Usa «Hacer foto»."
        : "La cámara solo funciona con https. Entra por https://homeassistant.jarclab.com o usa «Hacer foto».");
      return;
    }
    try {
      const det = await this._detector();
      this._stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false });
      const v = this._capaEl.querySelector("#video");
      if (!v) return this._pararCamara();
      v.srcObject = this._stream;
      await v.play();
      estado("Enfoca el código de barras");
      const bucle = async () => {
        if (!this._stream) return;
        try {
          if (v.readyState >= 2) {
            const r = await det.detect(v);
            if (r.length) return this._leido(r[0].rawValue);
          }
        } catch { /* un fotograma malo no para el bucle */ }
        setTimeout(bucle, 200);
      };
      bucle();
    } catch (e) {
      estado(`No se pudo abrir la cámara (${e.name}). Usa «Hacer foto».`);
    }
  }

  _pararCamara() {
    this._stream?.getTracks().forEach((t) => t.stop());
    this._stream = null;
  }

  // --- acciones ---------------------------------------------------------

  _toast(texto, { error = false, deshacer = false } = {}) {
    const t = this.shadowRoot.getElementById("toast");
    t.className = error ? "error" : "";
    t.innerHTML = `<span>${esc(texto)}</span>${deshacer ? `<button data-acc="deshacer">Deshacer</button>` : ""}`;
    t.hidden = false;
    clearTimeout(this._toastT);
    this._toastT = setTimeout(() => (t.hidden = true), error ? 7000 : 5000);
  }

  async _hacer(servicio, datos, hecho, { respuesta = false } = {}) {
    const r = await llamar(this._hass, servicio, datos, respuesta);
    if (!r.ok) this._toast(r.error, { error: true });
    else if (hecho) this._toast(hecho, { deshacer: true });
    return r;
  }

  _nombre(id) {
    return this._datos.productos[id]?.nombre ?? "";
  }

  async _clic(e) {
    const el = e.target.closest("[data-acc]");
    if (!el || el.disabled) return;
    const { acc, id } = el.dataset;
    const c = this._capa;
    switch (acc) {
      case "sitio": this._sel = id; this._moviendo = null; this._pintar(); break;
      case "usar": await this._hacer("usar", { producto: id }, `Usado: ${this._nombre(id)}`); if (el.dataset.cerrar !== undefined) this._cerrar(); break;
      case "acabar": this._moviendo = null; await this._hacer("acabar", { producto: id }, `Se acabó: ${this._nombre(id)}`); break;
      case "mover": this._moviendo = this._moviendo === id ? null : id; this._pintar(); break;
      case "mover-a": this._moviendo = null; await this._hacer("mover", { producto: id, sitio: el.dataset.sitio }, `${this._nombre(id)} → ${this._datos.sitios.find((s) => s.id === el.dataset.sitio)?.nombre}`); break;
      case "anadir-uno": await this._hacer("anadir", { producto: id, cantidad: 1 }, `Añadido: ${this._nombre(id)}`); if (el.dataset.cerrar !== undefined) this._cerrar(); break;
      case "rev-ok": await this._hacer("editar_producto", { producto: id, campos: { revisar: false } }, `Revisado: ${this._nombre(id)}`); break;
      case "rev-no": await this._hacer("editar_producto", { producto: id, campos: { revisar: false, no_inventariar: true } }, `No se inventaría: ${this._nombre(id)}`); break;
      case "deshacer": this.shadowRoot.getElementById("toast").hidden = true; await this._hacer("deshacer", {}, null); break;
      case "ficha": this._pararCamara(); this._abrir({ tipo: "ficha", id }); break;
      case "nuevo": this._abrir({ tipo: "nuevo", nombre: el.dataset.nombre, ean: el.dataset.ean }); break;
      case "escanear": this._abrir({ tipo: "escaner" }); break;
      case "sitios": this._abrir({ tipo: "sitios", lista: this._datos.sitios.map((s) => ({ ...s })) }); break;
      case "cerrar": this._cerrar(); break;
      case "ver-revisar": this._verRevisar = !this._verRevisar; this._pintar(); break;

      case "guardar-ficha": {
        const f = this._capaEl.querySelector("#f-ficha");
        const v = (n) => f.elements[n].value.trim();
        const lineas = (n) => v(n).split("\n").map((x) => x.trim()).filter(Boolean);
        const campos = {
          nombre: v("nombre"), sitio: v("sitio") || null, unidad: v("unidad") || "ud",
          dias: v("dias") === "" ? -1 : parseInt(v("dias"), 10), foto: v("foto"),
          ean: lineas("ean"), alias: lineas("alias"),
          revisar: f.elements.revisar.checked, no_inventariar: f.elements.no_inventariar.checked,
        };
        if (campos.sitio === null) delete campos.sitio;
        const r = await this._hacer("editar_producto", { producto: id, campos }, `Guardado: ${campos.nombre}`);
        if (r.ok) this._cerrar();
        break;
      }
      case "borrar":
        if (!c.borrar) { c.borrar = true; this._pintarCapa(); break; }
        { const n = this._nombre(id); const r = await this._hacer("borrar_producto", { producto: id }, `Borrado: ${n}`); if (r.ok) this._cerrar(); }
        break;
      case "guardar-nuevo": {
        const f = this._capaEl.querySelector("#f-nuevo");
        const v = (n) => f.elements[n]?.value.trim() || "";
        if (!v("nombre")) { f.elements.nombre.focus(); break; }
        const datos = { nombre: v("nombre"), cantidad: parseFloat(v("cantidad")) || 1 };
        if (v("caduca")) datos.caduca = v("caduca");
        if (v("sitio")) datos.sitio = v("sitio");
        if (v("ean")) datos.ean = v("ean");
        const r = await this._hacer("anadir", datos, `Añadido: ${datos.nombre}`);
        if (r.ok) this._cerrar();
        break;
      }
      case "sitio-subir": { this._leerSitios(); const i = +el.dataset.i; [c.lista[i - 1], c.lista[i]] = [c.lista[i], c.lista[i - 1]]; this._pintarCapa(); break; }
      case "sitio-quitar": this._leerSitios(); c.lista.splice(+el.dataset.i, 1); this._pintarCapa(); break;
      case "sitio-nuevo": this._leerSitios(); c.lista.push({ nombre: "" }); this._pintarCapa(); this._capaEl.querySelector(`[data-i="${c.lista.length - 1}"]`)?.focus(); break;
      case "guardar-sitios": {
        this._leerSitios();
        const r = await this._hacer("guardar_sitios", { sitios: c.lista.filter((s) => s.nombre.trim()) }, "Sitios guardados");
        if (r.ok) this._cerrar();
        break;
      }
    }
  }

  _leerSitios() {
    this._capaEl.querySelectorAll("#lista-sitios input[data-i]").forEach((inp) => (this._capa.lista[+inp.dataset.i].nombre = inp.value));
  }

  // Los lotes se guardan al cambiar cada campo, sin botón.
  async _cambio(e) {
    const el = e.target;
    if (!el.dataset?.lote) return;
    let valor = el.value || null; // fecha vacía = no caduca
    if (el.dataset.campo === "cantidad") {
      valor = parseFloat(el.value);
      if (!(valor >= 0)) return;
    }
    await this._hacer("editar_lote", { lote: el.dataset.lote, campos: { [el.dataset.campo]: valor } }, valor === 0 ? "Lote quitado" : "Lote corregido");
    this._pintarCapa();
  }
}

customElements.define("despensa-panel", DespensaPanel);
