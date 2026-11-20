"""Contract: convierte el diccionario crudo en registros tipados o falla con todos los errores juntos.

Cualquier texto puede escribirse como cadena (igual en todos los idiomas) o como
tabla por idioma, p. ej. `titulo.en = "…"`, `titulo.es = "…"`, `titulo.pt = "…"`.
`validate(raw, lang)` resuelve cada texto al idioma pedido y exige que estén todos."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from .i18n import LANGS

_MISSING = object()
_FECHA = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class ContractError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


def slug(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")


@dataclass(frozen=True)
class Metrica:
    valor: str
    etiqueta: str


@dataclass(frozen=True)
class Enlace:
    texto: str
    url: str


@dataclass(frozen=True)
class Perfil:
    nombre: str
    rol: str
    titulo: str
    ubicacion: str
    coordenadas: str
    disponible: bool
    idiomas: list[str]
    enfoque: str
    resumen: str


@dataclass(frozen=True)
class Contacto:
    email: str
    github: str
    linkedin: str
    cv: str


@dataclass(frozen=True)
class Etapa:
    nombre: str
    herramientas: list[str]


@dataclass(frozen=True)
class Proyecto:
    slug: str
    titulo: str
    anio: int
    estado: str
    tipo: str
    resumen: str
    problema: str
    solucion: str
    resultado: str
    herramientas: list[str]
    metricas: list[Metrica]
    enlaces: list[Enlace]


@dataclass(frozen=True)
class Pausa:
    inicio: str
    fin: str


@dataclass(frozen=True)
class Hito:
    tipo: str
    rol: str
    lugar: str
    inicio: str
    fin: str
    detalle: str
    pausas: list[Pausa] = field(default_factory=list)


@dataclass(frozen=True)
class Portfolio:
    borrador: bool
    perfil: Perfil
    contacto: Contacto
    cifras: list[Metrica]
    etapas: list[Etapa]
    proyectos: list[Proyecto]
    trayectoria: list[Hito] = field(default_factory=list)


class _Reader:
    """Lee claves con tipo esperado y acumula errores en vez de detenerse en el primero."""

    def __init__(self, data: dict, path: str, errors: list[str], lang: str):
        self.data, self.path, self.errors, self.lang = data, path, errors, lang

    def text(self, value, where: str):
        """Resuelve un texto traducible: cadena tal cual, o tabla {en, es, pt} → el idioma pedido."""
        if isinstance(value, dict):
            missing = [lang for lang in LANGS if not isinstance(value.get(lang), str)]
            if missing:
                self.errors.append(f"{where}: falta la traducción {', '.join(missing)}")
                return ""
            return value[self.lang]
        return value

    def texts(self, key: str, default=_MISSING) -> list:
        """Lista cuyos elementos pueden ser traducibles."""
        where = f"{self.path}.{key}" if self.path else key
        return [self.text(v, f"{where}[{i}]") for i, v in enumerate(self.get(key, list, default))]

    def get(self, key: str, typ: type, default=_MISSING):
        value = self.data.get(key, default)
        where = f"{self.path}.{key}" if self.path else key
        if typ is str:
            value = self.text(value, where)
        if value is _MISSING:
            self.errors.append(f"{where}: falta y es obligatorio")
            return typ()
        # bool es subclase de int: un `true` no debe pasar por año.
        if not isinstance(value, typ) or (typ is int and isinstance(value, bool)):
            self.errors.append(f"{where}: se esperaba {typ.__name__}, llegó {type(value).__name__}")
            return typ()
        return value

    def child(self, key: str) -> "_Reader":
        return _Reader(self.get(key, dict), f"{self.path}.{key}".lstrip("."), self.errors, self.lang)

    def children(self, key: str, default=_MISSING) -> list["_Reader"]:
        rows = self.get(key, list, default)
        out = []
        for i, row in enumerate(rows):
            where = f"{self.path}.{key}[{i}]".lstrip(".")
            if isinstance(row, dict):
                out.append(_Reader(row, where, self.errors, self.lang))
            else:
                self.errors.append(f"{where}: se esperaba una tabla")
        return out


def _metricas(readers: list[_Reader]) -> list[Metrica]:
    return [Metrica(r.get("valor", str), r.get("etiqueta", str)) for r in readers]


def validate(raw: dict, lang: str = LANGS[0]) -> Portfolio:
    errors: list[str] = []
    root = _Reader(raw, "", errors, lang)

    p = root.child("perfil")
    perfil = Perfil(
        nombre=p.get("nombre", str),
        rol=p.get("rol", str),
        titulo=p.get("titulo", str),
        ubicacion=p.get("ubicacion", str),
        coordenadas=p.get("coordenadas", str, ""),
        disponible=p.get("disponible", bool, False),
        idiomas=p.texts("idiomas", []),
        enfoque=p.get("enfoque", str),
        resumen=" ".join(p.get("resumen", str).split()),
    )

    c = root.child("contacto")
    contacto = Contacto(
        email=c.get("email", str),
        github=c.get("github", str, ""),
        linkedin=c.get("linkedin", str, ""),
        cv=c.get("cv", str, ""),
    )

    # Una herramienta puede tener nombre traducido; los proyectos la citan por
    # cualquiera de sus variantes y aquí se reemplaza por el nombre del idioma.
    etapas, alias = [], {}
    for e in root.children("etapas"):
        nombres = []
        for tool in e.get("herramientas", list):
            nombre = e.text(tool, f"{e.path}.herramientas")
            variantes = tool.values() if isinstance(tool, dict) else [tool]
            alias.update({slug(str(v)): nombre for v in variantes})
            nombres.append(nombre)
        etapas.append(Etapa(e.get("nombre", str), nombres))

    # Integridad: una herramienta vive en una sola etapa (es su clave primaria).
    conocidas: dict[str, str] = {}
    for etapa in etapas:
        if len(etapa.nombre) > 16:  # el rótulo de la columna se montaría sobre la siguiente
            errors.append(f"etapas: «{etapa.nombre}» es muy largo para el grafo (máx. 16 caracteres)")
        if not etapa.herramientas:
            errors.append(f"etapas: «{etapa.nombre}» no tiene herramientas")
        for tool in etapa.herramientas:
            if slug(str(tool)) in conocidas:
                errors.append(f"etapas: «{tool}» está repetida (ya aparece en {conocidas[slug(str(tool))]})")
            conocidas[slug(str(tool))] = etapa.nombre

    proyectos = []
    for r in root.children("proyectos"):
        titulo = r.get("titulo", str)
        tools = []
        # Integridad referencial: toda herramienta de un proyecto debe existir en el stack.
        for tool in r.get("herramientas", list):
            if slug(str(tool)) in alias:
                tools.append(alias[slug(str(tool))])
            else:
                errors.append(f"{r.path}.herramientas: «{tool}» no existe en ninguna etapa del stack")
        proyectos.append(
            Proyecto(
                slug=slug(titulo),
                titulo=titulo,
                anio=r.get("anio", int),
                estado=r.get("estado", str, ""),
                tipo=r.get("tipo", str),
                resumen=r.get("resumen", str),
                problema=r.get("problema", str, ""),
                solucion=r.get("solucion", str, ""),
                resultado=r.get("resultado", str, ""),
                herramientas=tools,
                metricas=_metricas(r.children("metricas", [])),
                enlaces=[Enlace(e.get("texto", str), e.get("url", str)) for e in r.children("enlaces", [])],
            )
        )
    slugs = [pr.slug for pr in proyectos]
    for dup in {s for s in slugs if slugs.count(s) > 1}:
        errors.append(f"proyectos: hay dos proyectos con el mismo título («{dup}»)")

    trayectoria = []
    for r in root.children("trayectoria", []):
        hito = Hito(
            tipo=r.get("tipo", str),
            rol=r.get("rol", str),
            lugar=r.get("lugar", str),
            inicio=r.get("inicio", str),
            fin=r.get("fin", str, ""),
            detalle=r.get("detalle", str, ""),
            pausas=[Pausa(x.get("inicio", str), x.get("fin", str)) for x in r.children("pausas", [])],
        )
        for i, pausa in enumerate(hito.pausas):
            where = f"{r.path}.pausas[{i}]"
            if not (_FECHA.match(pausa.inicio) and _FECHA.match(pausa.fin)):
                errors.append(f"{where}: las fechas deben tener formato AAAA-MM")
            elif not (hito.inicio < pausa.inicio <= pausa.fin and (not hito.fin or pausa.fin < hito.fin)):
                errors.append(f"{where}: la pausa ({pausa.inicio} – {pausa.fin}) debe quedar dentro del hito")
        if hito.tipo not in ("trabajo", "estudio"):
            errors.append(f"{r.path}.tipo: debe ser «trabajo» o «estudio», llegó «{hito.tipo}»")
        if not _FECHA.match(hito.inicio):
            errors.append(f"{r.path}.inicio: «{hito.inicio}» no tiene formato AAAA-MM")
        if hito.fin and not _FECHA.match(hito.fin):
            errors.append(f"{r.path}.fin: «{hito.fin}» no tiene formato AAAA-MM")
        elif hito.fin and _FECHA.match(hito.inicio) and hito.fin < hito.inicio:
            errors.append(f"{r.path}: termina ({hito.fin}) antes de empezar ({hito.inicio})")
        trayectoria.append(hito)

    portfolio = Portfolio(
        borrador=root.get("borrador", bool, False),
        perfil=perfil,
        contacto=contacto,
        cifras=_metricas(root.children("cifras", [])),
        etapas=etapas,
        proyectos=proyectos,
        trayectoria=trayectoria,
    )
    if errors:
        raise ContractError(errors)
    return portfolio
