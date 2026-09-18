# Planillero

App para armar las **planillas de cancha** de una jornada a partir de un PDF masivo y la lista de partidos por cancha y horario.

Hace tres cosas:

1. Lee el horario (Hombres/Mujeres, cancha, hora, local vs visitante).
2. Conserva del PDF original las hojas cuyos equipos **sí están** en esa lista, y les completa cancha y hora.
3. **Elimina** equipos que no juegan, ordena el documento por cancha y horario, y genera planillas nuevas si un partido no estaba en el PDF.

El horario de la jornada actual ya viene cargado. Si tu PDF original no está a mano, podés probar con la planilla de ejemplo (incluye 3 partidos de más para ver el recorte).

## Cómo correrla

Necesitás Node 22+ y Python 3.12+ con:

```bash
python3 -m pip install -r processor/requirements.txt
npm install
npm run dev -- --port 43147
```

Abrí [http://127.0.0.1:43147](http://127.0.0.1:43147).

## Uso

1. Subí `Planillas de Cancha - Masivo.pdf` o usá el ejemplo.
2. Revisá o pegá el horario a la izquierda. También acepta un `.txt`.
3. **Previsualizar** muestra qué hojas se quedan y qué equipos se van.
4. **Armar planillas** descarga el PDF nuevo.

Opciones:

- **Hoja índice**: resumen al frente, agrupado por cancha.
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

## Motor en Python

```bash
python3 -m processor.cli parse --schedule public/horario-jornada.txt
python3 -m processor.cli analyze --pdf public/planillas-ejemplo.pdf --schedule public/horario-jornada.txt
python3 -m processor.cli generate --pdf public/planillas-ejemplo.pdf --schedule public/horario-jornada.txt --out /tmp/planillas.pdf
python3 -m pytest tests -q
```

Si el PDF es un escaneo sin texto, Planillero arma las planillas de cero con el horario.
