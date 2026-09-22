// Fase 0: panel de prueba. Comprueba que el panel carga en la app de HA,
// que la cámara abre y que se leen EAN. Se sustituye por el panel real en la fase 2.
import { BarcodeDetector, setZXingModuleOverrides } from "./vendor/ponyfill.js";

setZXingModuleOverrides({
  locateFile: (path, prefix) =>
    path.endsWith(".wasm") ? new URL("./vendor/zxing_reader.wasm", import.meta.url).href : prefix + path,
});

const FORMATOS = ["ean_13", "ean_8", "upc_a", "upc_e"];

class DespensaPanel extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (!this.shadowRoot) this._pintar();
  }

  _pintar() {
    const root = this.attachShadow({ mode: "open" });
    root.innerHTML = `
      <style>
        :host { display:block; min-height:100vh; background:#faf8f4; color:#211f1b;
                font-family:-apple-system,Helvetica,sans-serif; padding:26px 16px; box-sizing:border-box }
        @media (prefers-color-scheme: dark) { :host { background:#1b1a17; color:#eeeae2 } .caja { background:#26241f !important; border-color:#3a372f !important } }
        h1 { font-size:28px; margin:0 0 4px; letter-spacing:-.02em }
        .mono { font-family:ui-monospace,Menlo,monospace; font-size:12px; color:#8a8478 }
        .caja { background:#fff; border:1px solid #eae5da; border-radius:14px; padding:14px; margin-top:14px }
        button, label.btn { display:inline-block; border:none; border-radius:10px; padding:11px 16px; font-weight:600; font-size:14px; font-family:inherit;
                 color:#fff; background:#2f6b46; cursor:pointer; margin:4px 6px 4px 0 }
        video { width:100%; max-width:480px; border-radius:12px; background:#000; margin-top:10px; display:none }
        .ok { color:#2f6b46; font-weight:600 } .mal { color:#a32b1e; font-weight:600 }
        #lectura { font-size:22px; font-weight:600; margin-top:8px }
      </style>
      <div class="mono">Home Assistant · despensa · fase 0</div>
      <h1>Prueba de cámara</h1>
      <div class="caja mono" id="diag"></div>
      <div class="caja">
        <button id="abrir">Abrir cámara</button>
        <button id="parar" style="background:#5d584d">Parar</button>
        <label class="btn" style="background:#1f4f7a">Hacer foto
          <input id="foto" type="file" accept="image/*" capture="environment" hidden></label>
        <video id="video" playsinline muted></video>
        <div id="estado" class="mono"></div>
        <div id="lectura"></div>
      </div>`;
    const $ = (id) => root.getElementById(id);
    const md = navigator.mediaDevices;
    $("diag").innerHTML = [
      `usuario: ${this._hass?.user?.name ?? "?"}`,
      `origen: ${location.origin}`,
      `https (contexto seguro): <span class="${isSecureContext ? "ok" : "mal"}">${isSecureContext ? "sí" : "NO — la cámara no abrirá"}</span>`,
      `getUserMedia: ${md?.getUserMedia ? '<span class="ok">sí</span>' : '<span class="mal">no</span>'}`,
      `BarcodeDetector nativo: ${"BarcodeDetector" in window ? "sí" : "no (se usa zxing-wasm)"}`,
      `navegador: ${navigator.userAgent}`,
    ].join("<br>");

    const detector = new BarcodeDetector({ formats: FORMATOS });
    const estado = (t) => ($("estado").textContent = t);
    const leido = (codes) => {
      if (!codes.length) return false;
      $("lectura").textContent = `${codes[0].rawValue}  (${codes[0].format})`;
      navigator.vibrate?.(80);
      return true;
    };

    $("abrir").onclick = async () => {
      try {
        estado("pidiendo permiso…");
        this._stream = await md.getUserMedia({ video: { facingMode: "environment" }, audio: false });
        const v = $("video");
        v.srcObject = this._stream;
        v.style.display = "block";
        await v.play();
        estado("buscando código…");
        const bucle = async () => {
          if (!this._stream) return;
          try {
            if (v.readyState >= 2 && leido(await detector.detect(v))) estado("leído ✓ (sigue buscando)");
          } catch (e) { estado("error al leer: " + e.message); }
          setTimeout(bucle, 250);
        };
        bucle();
      } catch (e) {
        estado(`no abre la cámara: ${e.name} — ${e.message}`);
      }
    };
    $("parar").onclick = () => this._parar();
    $("foto").onchange = async (ev) => {
      const f = ev.target.files[0];
      if (!f) return;
      estado("leyendo foto…");
      try {
        const bmp = await createImageBitmap(f);
        estado(leido(await detector.detect(bmp)) ? "foto leída ✓" : "no se encontró código en la foto");
      } catch (e) { estado("error con la foto: " + e.message); }
      ev.target.value = "";
    };
  }

  _parar() {
    this._stream?.getTracks().forEach((t) => t.stop());
    this._stream = null;
    const v = this.shadowRoot?.getElementById("video");
    if (v) v.style.display = "none";
  }

  disconnectedCallback() { this._parar(); }
}

customElements.define("despensa-panel", DespensaPanel);
