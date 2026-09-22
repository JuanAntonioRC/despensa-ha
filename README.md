# Despensa

Inventario de casa dentro de Home Assistant: qué hay, dónde está y qué caduca. Se rellena solo con el ticket de Mercadona y avisa en la app de HA.

- **Panel "Despensa"** en la barra lateral: lo que hay que gastar, lo que queda por revisar del ticket, todo por sitios, buscador, escáner de EAN con la cámara, ficha de cada producto con sus lotes y *Deshacer* en cada acción.
- **Tarjeta `custom:despensa-card`** para un dashboard (pensada para el kiosko de la cocina): solo *Hay que gastarlo*.
- **Sensores**: `sensor.despensa_caduca_pronto`, `sensor.despensa_caducado`, `sensor.despensa_por_revisar`, `sensor.despensa_productos`.
- **Avisos** (Configurar en la integración): resumen diario de lo que caduca y aviso de cada ticket, a los móviles elegidos.
- **Servicios** `despensa.*`: `registrar_ticket`, `anadir`, `usar`, `acabar`, `mover`, `editar_producto`, `editar_lote`, `borrar_producto`, `guardar_sitios`, `deshacer`, `conocidos`, `importar`.

Los datos viven en `.storage/despensa` y entran en las copias de seguridad de HA.

## Instalar

HACS → Repositorios personalizados → `https://github.com/JuanAntonioRC/despensa-ha` (tipo *Integración*) → Descargar → reiniciar HA → Ajustes → Dispositivos y servicios → Añadir → *Despensa*.

La cámara solo funciona si HA se abre por **https**.

## Tarjeta

```yaml
type: custom:despensa-card
max: 6
```

## Scripts

- `scripts/despensa.py`: lee el ticket digital de Mercadona (Gmail) y lo manda a `despensa.registrar_ticket`. Corre en otra máquina con `pdftotext`, `mercadona.db` y `caducidades.tsv`.
- `scripts/migrar_grocy.py`: pasa todo desde Grocy, una sola vez.

## Terceros

`frontend/vendor/`: [barcode-detector](https://github.com/Sec-ant/barcode-detector) 3.2.2 y el lector de [zxing-wasm](https://github.com/Sec-ant/zxing-wasm) 3.1.3 (MIT). `frontend/fonts/`: Instrument Sans e IBM Plex Mono (OFL). Todo incluido para no depender de un CDN.
