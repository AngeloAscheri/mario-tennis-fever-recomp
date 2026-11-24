# Primeros pasos

Para quien quiera ayudar sin ser experto en recompilación, con o sin un asistente de IA.
[English](../first-steps.md).

## Cómo es el trabajo

El código del juego ya se traduce a C (la parte difícil, resuelta). Lo que queda es sobre todo **que el runtime
responda a todo lo que el juego le pide a la consola**: archivos, mandos, sonido, gráficos, servicios del sistema. El
juego corre hasta que pide algo que el runtime todavía no responde, y se para ahí. Cada parada que se arregla lo lleva
más lejos. La mayoría son un cambio pequeño y acotado, por eso el proyecto va bien para quien empieza y para trabajar
con IA.

## Preparar el entorno (una vez)

Necesitas Linux, `git`, [uv](https://docs.astral.sh/uv/) y **tu propio** volcado descifrado de Mario Tennis Fever
(carpetas `exefs/` y `romfs/`). La compilación necesita clang y unas bibliotecas; en Bazzite, Silverblue o SteamOS
van en un distrobox. Los comandos exactos están en la skill `getting-started`
([.claude/skills/getting-started/SKILL.md](../../.claude/skills/getting-started/SKILL.md)); con Claude Code basta con
decir "ayúdame a empezar" y la sigue.

```
git clone <tu fork de este repositorio> && cd mario-tennis-fever-recomp
git config core.hooksPath tools/git
uv sync
uv run tools/setup.py "<carpeta de tu volcado>"
uv run tools/run/boot.py [--box <tu distrobox>]
```

El último comando compila el port, ejecuta el juego hasta su parada actual y te dice en palabras simples dónde y por
qué se paró.

## Elegir algo

- **La parada actual.** `tools/run/boot.py` la nombra. Si dice "the game called nn::... talks to a console service",
  es una tarea `fix-sdk-call`: una función de reemplazo y volver a ejecutar. Los pasos están en la skill.
- **Issues con la etiqueta `good first issue`.** Cada una dice qué hacer, cómo comprobarlo y trae un texto listo para
  pegarle a tu IA.
- **Investigación** (etiqueta `research`): formatos de archivo, qué hace una función. La skill `reverse-engineer`.
- **Sin programar**: ejecuta `tools/inspect_dump.py` sobre un volcado de otra región o actualización y publícalo
  (issue #4); prueba en tu GPU y cuenta hasta dónde llega.

Avisa en la issue que la tomas, para que nadie empiece lo mismo.

## Trabajar con un asistente de IA

El repositorio está preparado:

- [AGENTS.md](../../AGENTS.md) es la guía que lee cualquier agente de código (Claude Code la lee a través de
  `CLAUDE.md`).
- `.claude/skills/` tiene guías paso a paso que Claude Code carga solo: `getting-started`, `fix-sdk-call`,
  `reverse-engineer`, `open-pr`. Con otros asistentes, indícales el `SKILL.md` que corresponda.
- Las herramientas imprimen explicaciones en lugar de logs crudos, así tú y tu asistente podéis actuar sobre ellas.

Lo que sigue siendo tu trabajo: leer lo que cambió antes de enviarlo, pasar las comprobaciones y decir en el pull
request que fue asistido por IA. Los mantenedores revisan el código, no quién lo escribió.

Textos que funcionan bien:

- "Ejecuta tools/run/boot.py y arregla la siguiente parada siguiendo la skill fix-sdk-call."
- "Toma la issue #N. Léela y dime tu plan antes de cambiar nada."
- "Explícame en palabras simples qué hace este cambio antes de hacer el commit."

## Cuando falla

`boot.py` distingue tres tipos de parada:

1. **Una llamada a un servicio de la consola** ("talks to a console service"): falta un reemplazo. `fix-sdk-call`.
2. **Un fallo dentro de una función del SDK** (`nn::...` en la pila): normalmente un reemplazo anterior dejó sin
   preparar algo que el servicio habría creado (un objeto, un evento). Mira la llamada al SDK más interna que hizo el
   juego; `fix-sdk-call` también lo cubre.
3. **Un fallo dentro del código del propio juego** (solo `basic+0x...`): hay que leer el código. Publica la salida de
   `boot.py` en una issue (no contiene bytes del juego); la skill `reverse-engineer` es la entrada.

Nunca pegues archivos del juego, volcados hexadecimales ni listados de desensamblado en las issues: las direcciones y
las descripciones bastan.

## Las reglas, en corto

Nada del juego va al repositorio, a las issues ni a los pull requests. Código de otros proyectos solo si es compatible
con MIT y citado. Por defecto, el comportamiento de la consola. La lista completa: [CONTRIBUTING.md](../../CONTRIBUTING.md).
