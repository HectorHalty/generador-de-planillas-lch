# Generador de Planillas LCH

Programa de **La Chacra Fútbol** para armar las planillas de cancha de una jornada.

A partir del PDF masivo y el horario por cancha:

1. Completa **Día** (el sábado próximo), **Horario** y **Cancha N°**.
2. Conserva las hojas de los equipos que **sí juegan**.
3. Saca los que no están en el horario.
4. **No** agrega las dos hojas de cruces ni la franja de margen.

El horario de la jornada actual ya viene cargado, y el masivo también si está en `public/`.

## Cómo usarlo (doble clic)

### Windows

1. Instalá [Python 3.12+](https://www.python.org/downloads/). En el instalador **tildá “Add python.exe to PATH”**.
2. Hacé **doble clic** en `Generador de Planillas LCH.bat` (también sirve `iniciar.bat`).
3. La primera vez instala sola las librerías (un minuto). Después se abre el navegador.
4. Tocá **Armar planillas**. Se descarga `planillas-cancha.pdf`.
5. Dejá la ventana negra abierta mientras usás el programa. Cerrala para apagarlo.

Si más adelante publicás este repo en GitHub, en **Actions** se puede bajar `GeneradorPlanillasLCH.exe` (un ejecutable de Windows, sin abrir el `.bat`).

### macOS

1. Instalá Python 3 desde [python.org](https://www.python.org/downloads/).
2. Hacé doble clic en `Generador de Planillas LCH.command`. Si macOS lo bloquea: clic derecho → Abrir.

### Linux

```bash
chmod +x generador-de-planillas-lch.sh
./generador-de-planillas-lch.sh
```

## Cómo subir el PDF

El masivo de la jornada puede ir ya en `public/planillas-masivo.pdf`. Si querés cargar otro:

1. Entrá a la app.
2. En **1. Cómo subir el PDF**, tocá **Elegir archivo** o arrastrá el PDF.
3. Andá a **Descargas** y elegí `Planillas de Cancha - Masivo.pdf`.
4. Revisá el horario y tocá **Armar planillas**.

**Previsualizar** muestra qué equipos se tiran, sin generar el PDF todavía.

## Opciones

- **Día de la jornada**: por defecto el sábado próximo (Argentina).
- **Hojas de cruces al frente**: apagado.
- **Completar faltantes**: crea una planilla en blanco si el partido no estaba en el original.
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

## Desarrollo

Hace falta Python 3.12+. Node es opcional (solo si usás la interfaz Next.js).

```bash
python3 -m pip install -r requirements.txt
python3 lanzar.py
```

Pruebas:

```bash
python3 -m pytest tests -q
```

Motor en consola:

```bash
python3 -m processor.cli generate --pdf public/planillas-masivo.pdf --schedule public/horario-jornada.txt --out planillas-cancha.pdf --date 2026-09-19
```

Interfaz Next.js (opcional):

```bash
npm install
npm run dev
```


