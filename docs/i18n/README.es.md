# mtf-recomp (Español)

**Recompilación estática de *Mario Tennis Fever* (Nintendo Switch 2) a un programa nativo de PC.**
[English](../../README.md) · [Hoja de ruta](../roadmap.md) · [Notas de investigación](../research.md) ·
[Cómo contribuir](../../CONTRIBUTING.md)

> [!IMPORTANT]
> **No se incluye ningún archivo del juego, ni se incluirá nunca.** Necesitas tu propia copia de *Mario Tennis Fever*,
> volcada de tu propia consola. Todo lo que se genera a partir del juego se crea en tu máquina, desde tu volcado, en
> carpetas ignoradas por git.

## Qué es

Seguimos el enfoque de [mkw-recomp](https://github.com/adriadam10/mkw-recomp) y
[DKB Recomp](https://github.com/Lucas-blip-png/dkb-pc-recomp): el código AArch64 del juego se traduce a C **antes de
ejecutarlo** y se compila para tu CPU, sin emulador, intérprete ni JIT. El sistema de la consola y la API gráfica NVN2
se reimplementan sobre el host (Vulkan), y los shaders se traducen a SPIR-V offline.

*Mario Tennis Fever* usa el motor de Camelot, no el de Nintendo EPD, así que lo que hay que hacer aquí es sobre todo la
parte propia del juego; lo común a Switch 2 ya lo resolvieron esos proyectos.

## Estado

**Investigación temprana: ya se traduce el juego entero.** Todavía no arranca nada.

- `main` es solo un cargador (`nxboot`). Al arrancar, seis hilos descifran y descomprimen seis trozos de su `.data`
  en un NRO: el motor del juego (`basic.nrs`, 24 MB, unas 61.000 funciones), que pasa a `nn::ro::LoadModule`.
- `tools/unpack_engine.py` hace lo mismo offline, en tu máquina y desde tu volcado, en un segundo y medio. El
  SHA-256 del resultado es el que registra el propio `.nrr` del juego, en las dos versiones.
- `main`, `basic` y `sdk` se traducen a C **sin ninguna instrucción no soportada**, y 1.541 de las 1.542 formas de
  instrucción del juego dan lo mismo que Unicorn.
- Detalles: [docs/research.md](../research.md). El RomFS entero es un solo archivo de 7,8 GB, `42`, con la firma
  `CRA.`.

## Cómo ayudar

- **Ingeniería inversa:** el formato del archivo `CRA.` y dónde guarda el motor sus shaders.
- **Port:** traer el `runtime/` de mkw-recomp y arrancar hasta la primera SVC.
- **Sin programar:** ejecuta `uv run tools/inspect_dump.py <volcado>/exefs` y pega la salida en el issue de informes
  de volcado (solo imprime build ids, tamaños y entropía, nunca bytes del juego).

Lee [CONTRIBUTING.md](../../CONTRIBUTING.md) antes de abrir un pull request. Las issues y PRs pueden escribirse en
español o inglés; el código, los comentarios y los commits van en inglés.

## Licencia

[MIT](../../LICENSE). Proyecto de fans, independiente y sin ánimo de lucro, sin relación con Nintendo ni Camelot.
