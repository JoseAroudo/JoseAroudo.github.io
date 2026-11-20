# Portfolio

Sitio estático generado con Python. El contenido vive en un solo archivo TOML y
pasa por un pipeline pequeño antes de convertirse en HTML:

```
content/portfolio.toml ─► extract ─► contract ─► transform ─► load ─► dist/
```

| Paso        | Archivo                 | Qué hace                                                              |
|-------------|-------------------------|-----------------------------------------------------------------------|
| extract     | `pipeline/extract.py`   | Lee el TOML y calcula el hash de las entradas (el *run id*).           |
| contract    | `pipeline/contract.py`  | Valida tipos, fechas e integridad referencial; reporta todos los errores juntos. |
| transform   | `pipeline/transform.py` | Deriva el grafo de linaje (SVG), la línea de tiempo y las vistas.      |
| load        | `pipeline/load.py`      | Renderiza `templates/index.html.j2` con Jinja2 y escribe `dist/`.      |

## Uso

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

.\.venv\Scripts\python build.py          # genera dist/
.\.venv\Scripts\python build.py serve    # http://localhost:8000, reconstruye y recarga al guardar
```

Requiere Python 3.11 o superior (usa `tomllib`).

## Editar el contenido

Todo está en `content/portfolio.toml`. Dos cosas a saber:

- Las líneas del grafo del stack no se escriben: salen de qué herramientas
  comparte cada proyecto. Si un proyecto cita una herramienta que no está en
  ninguna etapa, el build falla y dice cuál.
- El sitio sale en tres idiomas: inglés en la raíz, español en `/es/` y
  portugués en `/pt/`. Un texto traducido se escribe con una clave por idioma
  (`titulo.en`, `titulo.es`, `titulo.pt`); si falta una, el build falla y dice
  cuál. Los textos fijos de la interfaz viven en `pipeline/i18n.py`.
- Con `borrador = true` el sitio muestra una franja de aviso. Ponlo en `false`
  cuando el contenido sea el tuyo.

## Publicar

`.github/workflows/pages.yml` construye y publica en GitHub Pages en cada push a
`main`. En el repositorio: *Settings → Pages → Source: GitHub Actions*.
