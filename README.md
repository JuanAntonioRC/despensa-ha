# Despensa

Inventario de casa dentro de Home Assistant: qué hay, dónde está y qué caduca. Se rellena solo con el ticket de Mercadona (script aparte) y avisa en la app de HA.

**Estado: fase 0** — el panel solo trae una prueba de cámara y lectura de EAN.

## Instalar

HACS → Repositorios personalizados → `https://github.com/JuanAntonioRC/despensa-ha` (tipo *Integración*) → Descargar → reiniciar HA → Ajustes → Dispositivos y servicios → Añadir → *Despensa*.

Sale **Despensa** en la barra lateral.

## Terceros

`frontend/vendor/`: [barcode-detector](https://github.com/Sec-ant/barcode-detector) 3.2.2 y el lector de [zxing-wasm](https://github.com/Sec-ant/zxing-wasm) 3.1.3 (MIT), incluidos para no depender de un CDN.
