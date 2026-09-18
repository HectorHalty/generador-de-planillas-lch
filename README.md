# Generador de Planillas LCH

Programa de **La Chacra Fútbol** para armar las planillas de cancha de una jornada.

Repositorio: [HectorHalty/generador-de-planillas-lch](https://github.com/HectorHalty/generador-de-planillas-lch)

A partir del PDF masivo y el horario por cancha:

1. Completa **Día** (el sábado próximo), **Horario** y **Cancha N°**.
2. Conserva las hojas de los equipos que **sí juegan**.
3. Saca los que no están en el horario.
4. Si pegás una lista de **suspendidos** (`Nombre Apellido (Equipo)`, uno por línea), marca **solo esa fila** en gris y escribe **Suspendido** en la firma. Se nota al imprimir en blanco y negro, sin tapar los datos.

El horario de la jornada actual ya viene cargado, y el masivo también si está en `public/planillas-masivo.pdf`.

## Cómo usarlo

### Windows — ejecutable (recomendado)

1. Bajá **[GeneradorPlanillasLCH.exe](https://github.com/HectorHalty/generador-de-planillas-lch/releases/latest/download/GeneradorPlanillasLCH.exe)** (también está en [Releases](https://github.com/HectorHalty/generador-de-planillas-lch/releases/latest)).
2. Doble clic. Si Windows avisa que es desconocido, tocá **Más info → Ejecutar de todas formas**.
3. Se abre el navegador en `http://127.0.0.1:43147`.
4. Tocá **Armar planillas**. Se descarga `planillas-cancha.pdf`.
5. Si no se baja solo, tocá **Descargar PDF**.
6. Dejá la ventana negra abierta mientras usás el programa. Cerrala para apagarlo.

No hace falta instalar Python.

### Windows — con Python

1. Instalá [Python 3.12+](https://www.python.org/downloads/). En el instalador **tildá “Add python.exe to PATH”**.
2. Hacé **doble clic** en `Generador de Planillas LCH.bat` (también sirve `iniciar.bat`).
3. La primera vez instala sola las librerías (un minuto). Después se abre el navegador.
4. Tocá **Armar planillas**.

### macOS

1. Instalá Python 3 desde [python.org](https://www.python.org/downloads/).
2. Hacé doble clic en `Generador de Planillas LCH.command`. Si macOS lo bloquea: clic derecho → Abrir.

### Linux

```bash
sudo apt install python3 python3-venv python3-pip   # Ubuntu/Debian
chmod +x generador-de-planillas-lch.sh
./generador-de-planillas-lch.sh
```

Variables opcionales: `LCH_PORT` (por defecto `43147`) y `LCH_HOST` (por defecto `0.0.0.0`).

Si el navegador no puede hablar con el generador, abrí directo `http://127.0.0.1:43147` y dejá abierta la ventana del programa.

## Cómo subir el PDF

El masivo de la jornada puede ir ya en `public/planillas-masivo.pdf`. Si querés cargar otro:

1. Entrá a la app.
2. En **1. Cómo subir el PDF**, tocá **Elegir archivo** o arrastrá el PDF.
3. Andá a **Descargas** y elegí `Planillas de Cancha - Masivo.pdf`.
4. Revisá el horario y tocá **Armar planillas**.

**Previsualizar** muestra qué equipos se tiran, sin generar el PDF todavía.

## Opciones

- **Día de la jornada**: por defecto el sábado próximo (Argentina).
- **Suspendidos**: pegá uno por línea, igual que el horario, por ejemplo `Ezequiel Guzman (Mimetizarte)`. Marca solo esa fila en gris y escribe **Suspendido** en la firma. Si no está en la hoja, la app avisa.
- **Hombres, después mujeres** o **solo cancha y hora**.

## Formato del horario

```text
Hombres:

Cancha 1
11:30: Mambo F.C. vs Echale Pesteke
13:00: As Broma vs Mimetizarte

Mujeres:

Cancha 1
12:00: Wonka´s vs Es Contagioso
```

También acepta markdown (`**Hombres:**`, `*Cancha 1*`).

## Formato de suspendidos

```text
Ezequiel Guzman (Mimetizarte)
Agustin Ferreyra (Mimetizarte)
Bruno Lemma (Mimetizarte)
```

También acepta viñetas (`*`, `-`) y un título `Suspendidos:`.

## Desarrollo

Hace falta Python 3.12+. Node es opcional (solo si usás la interfaz Next.js).

```bash
python3 -m venv .lch-venv
.lch-venv/bin/pip install -r requirements.txt
python3 lanzar.py
```

Pruebas:

```bash
.lch-venv/bin/python -m pytest tests -q
```

Motor en consola:

```bash
python3 -m processor.cli generate --pdf public/planillas-masivo.pdf --schedule public/horario-jornada.txt --out planillas-cancha.pdf --date 2026-09-19 --no-blanks --players jugadores.txt
```

Interfaz Next.js (opcional):

```bash
npm install
npm run dev
```

## Ejecutable de Windows

Cada push a `main` arma `GeneradorPlanillasLCH.exe` en GitHub Actions y lo publica en [Releases](https://github.com/HectorHalty/generador-de-planillas-lch/releases/latest).

Localmente (en una PC con Windows):

```bat
python -m pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean packaging/generador.spec
```

El archivo queda en `dist/GeneradorPlanillasLCH.exe`.

También se puede disparar a mano: GitHub → **Actions → Build Windows executable → Run workflow**.

## Licencia

MIT. Uso interno de mesa de control de La Chacra Fútbol.
