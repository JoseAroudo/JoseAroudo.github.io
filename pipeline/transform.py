"""Transform: deriva lo que la plantilla necesita — grafo de linaje, línea de tiempo y vistas de proyecto."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from html import escape

from .contract import Portfolio, slug
from .i18n import MONTHS

# Geometría del grafo (unidades del viewBox).
COL_W, NODE_W, NODE_H, GAP, TOP, PAD = 186, 146, 32, 12, 54, 14


def _tool_index(p: Portfolio) -> dict[str, tuple[int, int, str]]:
    """slug → (columna, fila, nombre visible)."""
    return {
        slug(tool): (col, row, tool)
        for col, etapa in enumerate(p.etapas)
        for row, tool in enumerate(etapa.herramientas)
    }


def lineage(p: Portfolio, ui: dict[str, str]) -> dict:
    """Grafo del stack. Las aristas salen de los proyectos: dos herramientas se
    conectan si un mismo proyecto las usa en etapas consecutivas de su recorrido."""
    index = _tool_index(p)
    used_by: dict[str, list[str]] = defaultdict(list)
    edges: dict[tuple[str, str], list[str]] = defaultdict(list)

    for proyecto in p.proyectos:
        by_col: dict[int, list[str]] = defaultdict(list)
        for tool in proyecto.herramientas:
            tid = slug(tool)
            by_col[index[tid][0]].append(tid)
            used_by[tid].append(proyecto.slug)
        cols = sorted(by_col)
        for left, right in zip(cols, cols[1:]):
            for a in by_col[left]:
                for b in by_col[right]:
                    edges[(a, b)].append(proyecto.slug)

    tallest = max(len(e.herramientas) for e in p.etapas)
    inner_h = tallest * NODE_H + (tallest - 1) * GAP
    width = PAD * 2 + len(p.etapas) * COL_W - (COL_W - NODE_W)
    height = TOP + inner_h + PAD

    def xy(tid: str) -> tuple[float, float]:
        col, row, _ = index[tid]
        n = len(p.etapas[col].herramientas)
        y0 = TOP + (inner_h - (n * NODE_H + (n - 1) * GAP)) / 2
        return PAD + col * COL_W, y0 + row * (NODE_H + GAP)

    titles = {pr.slug: pr.titulo for pr in p.proyectos}
    out = [
        f'<svg class="dag" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{escape(ui["dag_label"].format(n=len(index), s=len(p.etapas)))}">'
    ]
    for col, etapa in enumerate(p.etapas):
        x = PAD + col * COL_W
        out.append(f'<text class="dag__stage" x="{x}" y="20"><tspan class="dag__n">{col + 1:02d}</tspan> {escape(etapa.nombre)}</text>')
        out.append(f'<line class="dag__rule" x1="{x}" y1="32" x2="{x + NODE_W}" y2="32"/>')

    for (a, b), projects in sorted(edges.items()):
        (ax, ay), (bx, by) = xy(a), xy(b)
        x1, y1, x2, y2 = ax + NODE_W, ay + NODE_H / 2, bx, by + NODE_H / 2
        mid = (x1 + x2) / 2
        out.append(
            f'<path class="dag__edge" data-a="{a}" data-b="{b}" data-p="{" ".join(projects)}" '
            f'd="M{x1} {y1:.1f}C{mid} {y1:.1f} {mid} {y2:.1f} {x2} {y2:.1f}"/>'
        )

    for tid, (_, _, name) in index.items():
        x, y = xy(tid)
        users = used_by.get(tid, [])
        hint = f"{ui['used_in']}: " + ", ".join(titles[s] for s in users) if users else ui["unused"]
        out.append(
            f'<g class="dag__node{"" if users else " is-idle"}" data-tool="{tid}" data-p="{" ".join(users)}" tabindex="0">'
            f"<title>{escape(name)} — {escape(hint)}</title>"
            f'<rect x="{x}" y="{y:.1f}" width="{NODE_W}" height="{NODE_H}"/>'
            f'<circle cx="{x}" cy="{y + NODE_H / 2:.1f}" r="2.5"/>'
            f'<circle cx="{x + NODE_W}" cy="{y + NODE_H / 2:.1f}" r="2.5"/>'
            f'<text x="{x + 14}" y="{y + NODE_H / 2 + 4.5:.1f}">{escape(name)}</text>'
            "</g>"
        )
    out.append("</svg>")
    return {"svg": "".join(out), "nodes": len(index), "edges": len(edges)}


def _months(stamp: str) -> int:
    year, month = map(int, stamp.split("-"))
    return year * 12 + month - 1


def _stamp(months: int) -> str:
    return f"{months // 12}-{months % 12 + 1:02d}"


def timeline(p: Portfolio, today: date, lang: str, now_label: str) -> dict:
    """Posiciones en porcentaje para dibujar la trayectoria como un Gantt en CSS.
    Un hito con pausas se parte en varios tramos sobre la misma fila."""
    if not p.trayectoria:
        return {"years": [], "items": []}

    def label(stamp: str) -> str:
        year, month = stamp.split("-")
        return f"{MONTHS[lang][int(month) - 1]} {year}"

    first_year = min(int(h.inicio[:4]) for h in p.trayectoria)
    start, end = first_year * 12, (today.year + 1) * 12
    now = today.year * 12 + today.month  # fin exclusivo del mes en curso
    items = []
    for h in sorted(p.trayectoria, key=lambda h: h.inicio, reverse=True):
        # Tramos [a, b) en meses, recortando las pausas.
        tramos, a = [], _months(h.inicio)
        for pausa in sorted(h.pausas, key=lambda x: x.inicio):
            tramos.append((a, _months(pausa.inicio)))
            a = _months(pausa.fin) + 1
        tramos.append((a, _months(h.fin) + 1 if h.fin else now))

        textos = []
        for i, (a, b) in enumerate(tramos):
            last = i == len(tramos) - 1
            fin = now_label if last and not h.fin else label(_stamp(b - 1))
            textos.append(label(_stamp(a)) if fin == label(_stamp(a)) else f"{label(_stamp(a))} — {fin}")
        items.append(
            {
                "hito": h,
                "periodo": " · ".join(textos),
                "bars": [
                    {
                        "s": round((a - start) / (end - start) * 100, 2),
                        "w": round(max(b - a, 1) / (end - start) * 100, 2),
                        "actual": i == len(tramos) - 1 and not h.fin,
                    }
                    for i, (a, b) in enumerate(tramos)
                ],
            }
        )
    return {"years": list(range(first_year, today.year + 1)), "items": items}


def projects(p: Portfolio) -> list[dict]:
    """Proyectos con sus herramientas ordenadas según el recorrido del dato."""
    index = _tool_index(p)
    view = []
    # El orden del TOML es el orden de relevancia: no se reordena por año.
    for n, proyecto in enumerate(p.proyectos, 1):
        tools = sorted((slug(t) for t in proyecto.herramientas), key=lambda tid: index[tid][:2])
        view.append({"n": n, "p": proyecto, "tools": [{"id": tid, "nombre": index[tid][2]} for tid in tools]})
    return view


def describe(p: Portfolio, ui: dict[str, str]) -> list[tuple[str, str, str]]:
    """El perfil, visto como lo vería un DESCRIBE sobre una tabla."""
    f = p.perfil
    return [
        (ui["row_name"], "STRING", f.nombre),
        (ui["row_role"], "STRING", f.rol),
        (ui["row_degree"], "STRING", f.titulo),
        (ui["row_base"], "GEOGRAPHY", f.ubicacion),
        (ui["row_langs"], "ARRAY<STRING>", ", ".join(map(str, f.idiomas))),
        (ui["row_available"], "BOOLEAN", "TRUE" if f.disponible else "FALSE"),
    ]
