// Tarjeta "custom:despensa-card" para el kiosko de la cocina: solo «Hay que gastarlo».
//   type: custom:despensa-card
//   max: 6          # cuántos productos como mucho
import { TOKENS, cargarFuentes, esc, num, vista, suscribir, llamar, foto } from "./comun.js";

const CSS = `
  ${TOKENS}
  :host { display:block }
  ha-card { background:var(--fondo); color:var(--texto); font-family:var(--sans); padding:16px; border-radius:16px; overflow:hidden }
  .cab { display:flex; justify-content:space-between; align-items:baseline; gap:10px; margin-bottom:12px }
  h2 { font-size:19px; font-weight:600; margin:0 }
  .nota, .meta { font-family:var(--mono); font-size:11px; color:var(--tenue) }
  .lista { display:flex; flex-direction:column; gap:8px }
  .fila { display:flex; align-items:center; gap:12px; background:var(--tarjeta); border:1px solid var(--borde); border-radius:13px; padding:8px 10px 8px 8px }
  .mini { width:52px; height:52px; border-radius:9px; overflow:hidden; background:var(--hueco); flex:none }
  .txt { flex:1; min-width:0; display:flex; flex-direction:column; gap:3px }
  .nombre { font-size:14.5px; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis }
  .chip { font-family:var(--mono); font-size:10.5px; font-weight:500; padding:3px 7px; border-radius:6px; align-self:flex-start }
  button { font-family:inherit; border-radius:9px; padding:10px 12px; font-size:13px; font-weight:600; cursor:pointer; white-space:nowrap }
  .pri { border:none; color:var(--acento-texto); background:var(--acento) }
  .sec { border:1px solid var(--borde-2); background:var(--tarjeta); color:var(--texto-2) }
  .vacio { color:var(--tenue); font-size:14px; padding:10px 2px }
  .error { color:var(--rojo); font-size:13px; margin-top:8px }
`;

class DespensaCard extends HTMLElement {
  setConfig(config) {
    this._max = config.max ?? 6;
  }

  set hass(hass) {
    const primera = !this._hass;
    this._hass = hass;
    this.toggleAttribute("oscuro", !!hass.themes?.darkMode);
    if (primera) {
      cargarFuentes();
      this.attachShadow({ mode: "open" }).innerHTML = `<style>${CSS}</style><ha-card><div class="vacio">Cargando…</div></ha-card>`;
      this.shadowRoot.addEventListener("click", (e) => this._clic(e));
      this._suscribir();
    }
  }

  connectedCallback() {
    if (this._hass && !this._baja) this._suscribir();
  }

  disconnectedCallback() {
    this._baja?.then((f) => f());
    this._baja = null;
  }

  _suscribir() {
    this._baja = suscribir(this._hass, (ev) => { this._ev = ev; this._pintar(); });
    this._baja.catch((e) => this._error(`No se pudo conectar: ${e?.message || e}`));
  }

  _pintar() {
    const { datos, ventana } = this._ev;
    const urgentes = vista(datos, ventana).productos
      .filter((p) => p.lotes.length && !p.no_inventariar && p.quedan !== null && p.quedan <= ventana);
    const mostrar = urgentes.slice(0, this._max);
    this.shadowRoot.querySelector("ha-card").innerHTML = `
      <div class="cab"><h2>Hay que gastarlo</h2><div class="nota">${urgentes.length ? `${urgentes.length} en ${ventana} días` : ""}</div></div>
      <div class="lista">
        ${mostrar.map((p) => `
          <div class="fila">
            <div class="mini">${foto(p, 52)}</div>
            <div class="txt">
              <div class="nombre">${esc(p.nombre)}</div>
              <div style="display:flex;gap:8px;align-items:center">
                <span class="chip" style="background:${p.et.bg};color:${p.et.fg}">${p.et.texto}</span>
                <span class="meta">${num(p.cantidad)} ${esc(p.unidad)} · ${esc(p.sitioNombre)}</span>
              </div>
            </div>
            <button class="pri" data-acc="usar" data-id="${p.id}">He usado uno</button>
            <button class="sec" data-acc="acabar" data-id="${p.id}">Se acabó</button>
          </div>`).join("") || `<div class="vacio">Nada caduca en los próximos ${ventana} días.</div>`}
        ${urgentes.length > mostrar.length ? `<div class="meta">y ${urgentes.length - mostrar.length} más en el panel Despensa</div>` : ""}
      </div>
      <div class="error" hidden></div>`;
  }

  _error(t) {
    const e = this.shadowRoot.querySelector(".error");
    if (!e) return;
    e.textContent = t;
    e.hidden = false;
    clearTimeout(this._t);
    this._t = setTimeout(() => (e.hidden = true), 6000);
  }

  async _clic(e) {
    const b = e.target.closest("[data-acc]");
    if (!b) return;
    b.disabled = true;
    const r = await llamar(this._hass, b.dataset.acc, { producto: b.dataset.id });
    if (!r.ok) { b.disabled = false; this._error(r.error); }
  }

  getCardSize() {
    return 1 + Math.min(this._max ?? 6, 6);
  }
}

if (!customElements.get("despensa-card")) {
  customElements.define("despensa-card", DespensaCard);
  (window.customCards ||= []).push({
    type: "despensa-card",
    name: "Despensa: hay que gastarlo",
    description: "Lo que caduca pronto, con «He usado uno» y «Se acabó». Pensada para el kiosko de la cocina.",
  });
}
