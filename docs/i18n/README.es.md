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

**Día 0: investigación.** Todavía no arranca nada.

- El lifter (traído de mkw-recomp) traduce `sdk` (47.907 funciones) y la parte visible de `main` **sin ninguna
  instrucción no soportada**.
- **Primer hallazgo:** `main` es un cargador (`nxboot`): 0,6 MiB de código y 12,9 MiB de `.data` con entropía de
  8,00 bits/byte (comprimido o cifrado). Pide un segundo módulo, `basic.nrs`, que es el motor real y se carga en tiempo
  de ejecución. Desempaquetarlo es el primer problema abierto: [docs/research.md](../research.md).
- El RomFS entero es un solo archivo de 7,8 GB, `42`, con la firma `CRA.`.

## Cómo ayudar

- **Ingeniería inversa:** cómo `nxboot` carga `basic.nrs`, y el formato del archivo `CRA.`.
- **Port:** traer el `runtime/` de mkw-recomp y arrancar hasta la primera SVC.
- **Sin programar:** ejecuta `uv run tools/inspect_dump.py <volcado>/exefs` y pega la salida en el issue de informes
  de volcado (solo imprime build ids, tamaños y entropía, nunca bytes del juego).

Lee [CONTRIBUTING.md](../../CONTRIBUTING.md) antes de abrir un pull request. Las issues y PRs pueden escribirse en
español o inglés; el código, los comentarios y los commits van en inglés.

## Licencia

[MIT](../../LICENSE). Proyecto de fans, independiente y sin ánimo de lucro, sin relación con Nintendo ni Camelot.
