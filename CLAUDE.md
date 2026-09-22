# despensa-ha

Integración HACS (repo custom) que sustituye a Grocy. Dominio `despensa`. Plan completo y registro de avance en la wiki: https://outline.jarclab.com/doc/despensa-en-home-assistant-plan-ur2hknNWXD — actualizar el registro en cada paso.

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

El HA real es `https://homeassistant.jarclab.com` (token: `security find-generic-password -s ha-token -w`). Desde aquí solo hay API REST/WebSocket, no sistema de ficheros: instalar por HACS lo hace Juan.
