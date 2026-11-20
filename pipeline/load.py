"""Load: renderiza la plantilla una vez por idioma y escribe el sitio estático en dist/."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup


def write(pages: dict[str, dict], run: dict, templates: Path, static: Path, dist: Path) -> int:
    """`pages` mapea la carpeta de salida ("" para la raíz, "es", "pt"…) a su contexto."""
    env = Environment(
        loader=FileSystemLoader(templates),
        autoescape=select_autoescape(["html", "j2"]),
        undefined=StrictUndefined,  # una variable mal escrita rompe el build, no la página
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("index.html.j2")

    dist.mkdir(exist_ok=True)
    shutil.copytree(static, dist / "static", dirs_exist_ok=True)
    size = 0
    for folder, context in pages.items():
        html = template.render(**{**context, "dag_svg": Markup(context["dag"]["svg"])})
        out = dist / folder if folder else dist
        out.mkdir(exist_ok=True)
        (out / "index.html").write_text(html, encoding="utf-8")
        size += len(html.encode("utf-8"))
    (dist / "build.json").write_text(json.dumps(run), encoding="utf-8")
    (dist / ".nojekyll").touch()
    return size
