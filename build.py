"""Construye el portfolio.

    python build.py          genera dist/ (inglés en la raíz, /es/ y /pt/)
    python build.py serve    genera, sirve en http://localhost:8000 y reconstruye al guardar
"""

from __future__ import annotations

import functools
import sys
import threading
import time
from datetime import date, datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from pipeline import contract, extract, i18n, load, transform

ROOT = Path(__file__).parent
CONTENT = ROOT / "content" / "portfolio.toml"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
DIST = ROOT / "dist"
INPUTS = (CONTENT, TEMPLATES, STATIC, ROOT / "pipeline")


def build(dev: bool = False) -> None:
    t0 = time.perf_counter()
    raw = extract.read(CONTENT)
    # Se valida cada idioma antes de escribir nada: si falta una traducción, no se publica ninguno.
    portfolios = {lang: contract.validate(raw, lang) for lang in i18n.LANGS}
    run = {"id": extract.fingerprint(*INPUTS), "at": datetime.now().strftime("%Y-%m-%d %H:%M")}

    pages, log = {}, []
    for lang, portfolio in portfolios.items():
        ui = i18n.UI[lang]
        folder = "" if lang == i18n.LANGS[0] else lang
        root = "../" if folder else ""  # prefijo hasta la raíz de dist/
        dag = transform.lineage(portfolio, ui)
        log = [
            ("extract", ui["log_extract"].format(file=CONTENT.relative_to(ROOT).as_posix(), p=len(portfolio.proyectos), h=len(portfolio.trayectoria))),
            ("contract", ui["log_contract"]),
            ("transform", ui["log_transform"].format(n=dag["nodes"], e=dag["edges"])),
            ("load", ui["log_load"].format(out=f"dist/{folder + '/' if folder else ''}index.html")),
        ]
        contacto = portfolio.contacto
        pages[folder] = {
            "dev": dev,
            "run": run,
            "log": log,
            "lang": lang,
            "ui": ui,
            "root": root,
            # Selector de idioma: enlaces relativos desde esta página hacia las demás.
            "langs": [
                {"code": code, "name": i18n.NAMES[code], "href": (root + ("" if code == i18n.LANGS[0] else code + "/")) or "./"}
                for code in i18n.LANGS
            ],
            "borrador": portfolio.borrador,
            "perfil": portfolio.perfil,
            "nombre_corto": " ".join(portfolio.perfil.nombre.split()[:2]),
            "contacto": contacto,
            "cv_url": contacto.cv if not contacto.cv or "://" in contacto.cv else root + contacto.cv,
            "cifras": portfolio.cifras,
            "describe": transform.describe(portfolio, ui),
            "dag": dag,
            "proyectos": transform.projects(portfolio),
            "tl": transform.timeline(portfolio, date.today(), lang, ui["now"]),
        }

    size = load.write(pages, run, TEMPLATES, STATIC, DIST)
    for step, message in pages[""]["log"]:
        print(f"  [{step:<9}] {message}")
    print(f"  {len(pages)} idiomas: {', '.join(i18n.LANGS)} · run {run['id']} · {size / 1024:.1f} kB · {(time.perf_counter() - t0) * 1000:.0f} ms")


def safe_build(dev: bool) -> bool:
    try:
        build(dev)
        return True
    except contract.ContractError as exc:
        print("  El contenido no cumple el contrato:")
        for error in exc.errors:
            print(f"    ✗ {error}")
    except Exception as exc:  # en modo serve, un error de plantilla no debe tumbar el servidor
        print(f"  ✗ {type(exc).__name__}: {exc}")
    return False


def serve(port: int = 8000) -> None:
    safe_build(dev=True)
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(DIST))
    handler.log_message = lambda *args: None
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"\n  http://localhost:{port}  (Ctrl+C para salir)\n")

    seen = extract.fingerprint(*INPUTS)
    try:
        while True:
            time.sleep(0.6)
            current = extract.fingerprint(*INPUTS)
            if current != seen:
                seen = current
                print(f"  cambio detectado · {datetime.now():%H:%M:%S}")
                safe_build(dev=True)
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1:2] == ["serve"]:
        serve(int(sys.argv[2]) if len(sys.argv) > 2 else 8000)
    else:
        sys.exit(0 if safe_build(dev=False) else 1)
