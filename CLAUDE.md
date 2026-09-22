# despensa-ha

Integración HACS (repo custom) que sustituye a Grocy. Dominio `despensa`. Plan completo y registro de avance en la wiki: https://outline.jarclab.com/doc/despensa-en-home-assistant-plan-ur2hknNWXD — actualizar el registro en cada paso.

## Dónde está cada cosa

- `inventario.py`: toda la lógica, **sin HA**. `python3 inventario.py` ejecuta su comprobación. Cualquier regla nueva va aquí con su `assert`.
- `__init__.py`: guardado (`Store`), servicios, suscripción WebSocket `despensa/subscribe` (manda el estado entero en cada cambio), avisos y panel.
- `sensor.py`, `config_flow.py` (opciones: móviles, hora del resumen, ventana).
- `frontend/`: `despensa-panel.js`, `despensa-card.js` y lo que comparten en `comun.js`.
- `scripts/despensa.py`: el lector de tickets que corre en `chatty`. `--test` sin red, `--seco PDF` sin mandar nada.

## Frontend

Módulos JS sueltos en `custom_components/despensa/frontend/`, **sin compilación**. Se sirven en `/despensa_static` y el panel se registra con `panel_custom`. La URL lleva `?v=<version del manifest>`: sin subir la versión, la app de iOS sigue con la caché vieja.

El escáner usa el ponyfill `barcode-detector` (Safari no tiene `BarcodeDetector`). El `.wasm` va en `vendor/` y tiene que ser **exactamente** el de la versión de `zxing-wasm` que espera el ponyfill (comprueba su SHA-256), si no, no carga. Probado leyendo un EAN-13 en Chrome sin ventana.

## Publicar una versión

HACS instala **por tag**:

```bash
# subir "version" en custom_components/despensa/manifest.json
git commit -am "... (vX.Y.Z)" && git tag vX.Y.Z && git push && git push --tags
```

En HA: HACS → Despensa → Redescargar → reiniciar HA.

## Probar

Antes de publicar, en un HA local: `python3.14 -m venv havenv && havenv/bin/pip install homeassistant==<versión de casa>`, carpeta de config con `custom_components/despensa` enlazada y `hass -c .`. Tras el primer arranque escucha en el **8123** aunque la config diga otro puerto. Las capturas y los clics se prueban con Playwright usando el Chrome del Mac (`channel="chrome"`), metiendo `hassTokens` en `localStorage` con `add_init_script`.

Los errores de un servicio llegan como 500 por la API REST (es cosa de HA); por WebSocket llega el mensaje.

El HA real es `https://homeassistant.jarclab.com` (token: `security find-generic-password -s ha-token -w`). Desde aquí solo hay API REST/WebSocket, no sistema de ficheros: instalar por HACS lo hace Juan.
