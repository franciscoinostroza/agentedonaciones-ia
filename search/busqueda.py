import difflib
import re
import time

from database.empresas import EMPRESAS


CATEGORIAS = {
    "construccion": "Materiales y Construcci\u00f3n",
    "tecnologia": "Tecnolog\u00eda y Conectividad",
    "educacion": "Educaci\u00f3n, Libros y \u00datiles",
    "alimentacion": "Alimentos y Bebidas",
    "general": "Donaciones Varias y Financiamiento",
}

SINONIMOS = {
    "mueble": ["mueble", "mobiliario", "silla", "mesa", "muebles_banio", "estanteria"],
    "muebles": ["mueble", "mobiliario", "silla", "mesa", "muebles_banio", "estanteria"],
    "mobiliario": ["mueble", "mobiliario", "silla", "mesa", "muebles_banio"],
    "computadora": ["computadora", "pc", "notebook", "tablet", "computadoras", "informatica"],
    "computadoras": ["computadora", "pc", "notebook", "tablet", "computadoras", "informatica"],
    "pc": ["computadora", "pc", "notebook", "tablet", "computadoras", "informatica"],
    "baño": ["baño", "sanitario", "inodoro", "lavatorio", "banio", "construccion"],
    "baños": ["baño", "sanitario", "inodoro", "lavatorio", "banio", "construccion"],
    "banio": ["baño", "sanitario", "inodoro", "lavatorio", "banio"],
    "sanitario": ["baño", "sanitario", "inodoro", "lavatorio"],
    "sanitarios": ["baño", "sanitario", "inodoro", "lavatorio"],
    "inodoro": ["baño", "sanitario", "inodoro", "lavatorio"],
    "inodoros": ["baño", "sanitario", "inodoro", "lavatorio"],
    "lavatorio": ["baño", "sanitario", "inodoro", "lavatorio"],
    "lavatorios": ["baño", "sanitario", "inodoro", "lavatorio"],
    "libro": ["libro", "cuaderno", "utiles", "escolar", "biblioteca", "lectura"],
    "libros": ["libro", "cuaderno", "utiles", "escolar", "biblioteca", "lectura"],
    "alimento": ["alimento", "comida", "leche", "fideo", "arroz", "aceite", "lacteo", "bebida"],
    "alimentos": ["alimento", "comida", "leche", "fideo", "arroz", "aceite", "lacteo", "bebida"],
    "comida": ["alimento", "comida", "leche", "fideo", "arroz", "aceite", "lacteo", "bebida"],
    "leche": ["alimento", "leche", "lacteo", "yogur"],
    "lacteo": ["alimento", "leche", "lacteo", "yogur"],
    "lacteos": ["alimento", "leche", "lacteo", "yogur"],
    "utiles": ["libro", "cuaderno", "utiles", "escolar", "lapiz", "lapicera", "mochila"],
    "escolar": ["libro", "cuaderno", "utiles", "escolar", "lapiz", "lapicera", "mochila"],
    "herramienta": ["herramienta", "herramientas", "ferreteria", "equipamiento"],
    "herramientas": ["herramienta", "herramientas", "ferreteria", "equipamiento"],
    "material": ["material", "materiales", "construccion", "cemento", "obra"],
    "materiales": ["material", "materiales", "construccion", "cemento", "obra"],
}

_PREFIJOS_DESCARTABLES = [
    "fundacion", "fundaci\u00f3n", "grupo", "asociacion", "asociaci\u00f3n",
    "camara", "c\u00e1mara", "banco de", "banco",
]
_SUFIJOS_DESCARTABLES = [
    "s.a.", "s.a", "s.r.l.", "srl", "s.a.c.i.f.", "sacif",
    "sa", "argentina", "de argentina",
]

_CACHE = {}
_CACHE_TTL = 600


def _normalizar_nombre(nombre):
    n = nombre.lower().strip()
    n = re.sub(r'[^\w\s]', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    for s in _SUFIJOS_DESCARTABLES:
        if n.endswith(" " + s):
            n = n[:-len(s) - 1]
        elif n.endswith(s):
            n = n[:-len(s)]
    for p in _PREFIJOS_DESCARTABLES:
        if n.startswith(p + " "):
            n = n[len(p) + 1:]
        elif n.startswith(p):
            n = n[len(p):]
    return n.strip()


def _es_duplicado(nombre1, nombre2, umbral=0.85):
    n1 = _normalizar_nombre(nombre1)
    n2 = _normalizar_nombre(nombre2)
    if not n1 or not n2:
        return False
    if n1 == n2:
        return True
    if len(n1) < 5 or len(n2) < 5:
        return n1 in n2 or n2 in n1
    if n1 in n2 or n2 in n1:
        return True
    return difflib.SequenceMatcher(None, n1, n2).ratio() >= umbral


def _normalizar_empresa(emp, fuente="", score=0):
    if isinstance(emp.get("tipo_donacion"), str):
        donacion = [d.strip() for d in emp["tipo_donacion"].split(",") if d.strip()]
    elif isinstance(emp.get("tipo_donacion"), list):
        donacion = emp["tipo_donacion"]
    else:
        donacion = []
    return {
        "nombre": emp.get("nombre") or emp.get("nombre_empresa", ""),
        "rubro": emp.get("rubro", ""),
        "categoria": emp.get("categoria", "general"),
        "contacto": emp.get("contacto") or emp.get("email", ""),
        "telefono": emp.get("telefono", ""),
        "web": emp.get("web") or emp.get("sitio_web") or emp.get("sitio", ""),
        "provincia": emp.get("provincia", "Argentina"),
        "tipo_donacion": donacion,
        "notas": emp.get("notas", ""),
        "fuente": emp.get("fuente", fuente),
        "match_score": emp.get("match_score", score),
    }


def resultados_a_dicts(resultados):
    return [
        {
            "nombre": r["nombre"],
            "rubro": r["rubro"],
            "categoria": r["categoria"],
            "contacto": r["contacto"],
            "telefono": r["telefono"],
            "web": r["web"],
            "provincia": r["provincia"],
            "tipo_donacion": r["tipo_donacion"],
            "notas": r["notas"],
            "fuente": r["fuente"],
            "match_score": r["match_score"],
        }
        for r in resultados
    ]


def buscar_empresas_local(categoria=None, rubro=None, keywords=None, provincia=None):
    resultados = []
    for emp in EMPRESAS:
        if categoria and emp["categoria"] != categoria:
            continue
        if rubro and rubro.lower() not in emp["rubro"].lower():
            continue
        if provincia and provincia.lower() not in emp["provincia"].lower():
            continue
        if keywords:
            match = False
            for kw in keywords:
                kw = kw.lower()
                kws = SINONIMOS.get(kw, [kw])
                for skw in kws:
                    if (skw in emp["nombre"].lower()
                        or skw in emp["rubro"].lower()
                        or skw in emp.get("notas", "").lower()
                        or any(skw in td.lower() for td in emp.get("tipo_donacion", []))):
                        match = True
                        break
                if match:
                    break
            if not match:
                continue
        resultados.append(emp)
    return resultados


def buscar_empresas_por_necesidad(necesidad):
    """Retorna (resultados, keywords, categoria_detectada)."""
    necesidad = necesidad.lower()
    mapeo = {
        "ba\u00f1o": "construccion",
        "ba\u00f1os": "construccion",
        "sanitario": "construccion",
        "cemento": "construccion",
        "construccion": "construccion",
        "construcci\u00f3n": "construccion",
        "ladrillo": "construccion",
        "material": "construccion",
        "obra": "construccion",
        "ceramica": "construccion",
        "cer\u00e1mica": "construccion",
        "ceramico": "construccion",
        "cer\u00e1mico": "construccion",
        "pintura": "construccion",
        "computadora": "tecnologia",
        "tablet": "tecnologia",
        "tecnologia": "tecnologia",
        "tecnolog\u00eda": "tecnologia",
        "internet": "tecnologia",
        "wifi": "tecnologia",
        "router": "tecnologia",
        "pc": "tecnologia",
        "notebook": "tecnologia",
        "impresora": "tecnologia",
        "pantalla": "tecnologia",
        "proyector": "tecnologia",
        "informatica": "tecnologia",
        "inform\u00e1tica": "tecnologia",
        "libro": "educacion",
        "cuaderno": "educacion",
        "utiles": "educacion",
        "\u00fatiles": "educacion",
        "escolar": "educacion",
        "lapiz": "educacion",
        "l\u00e1piz": "educacion",
        "lapicera": "educacion",
        "birome": "educacion",
        "mochila": "educacion",
        "educacion": "educacion",
        "educaci\u00f3n": "educacion",
        "curso": "educacion",
        "capacitacion": "educacion",
        "capacitaci\u00f3n": "educacion",
        "taller": "educacion",
        "biblioteca": "educacion",
        "comida": "alimentacion",
        "alimento": "alimentacion",
        "alimentacion": "alimentacion",
        "alimentaci\u00f3n": "alimentacion",
        "leche": "alimentacion",
        "fideo": "alimentacion",
        "arroz": "alimentacion",
        "aceite": "alimentacion",
        "lacteo": "alimentacion",
        "l\u00e1cteo": "alimentacion",
        "bebida": "alimentacion",
        "cocina": "alimentacion",
        "merendero": "alimentacion",
        "comedor": "alimentacion",
    }

    mapeo_multi = {
        "mueble", "muebles", "mobiliario", "silla", "mesa", "estanteria",
        "dinero", "donacion", "donaci\u00f3n", "financiamiento", "fondos",
        "logistica", "log\u00edstica", "transporte", "envio",
        "ni\u00f1o", "ni\u00f1os", "infantil", "chico", "chicos", "joven", "jovenes",
        "limpieza", "equipamiento", "herramienta", "herramientas",
        "voluntario", "voluntariado",
    }

    stopwords = {"de", "el", "la", "los", "las", "un", "una", "para", "en", "con", "del", "al", "por", "y", "o", "a", "que", "es", "se", "no", "su", "mi", "tu"}
    keywords_busqueda = [p for p in necesidad.split() if p.lower() not in stopwords]

    categoria_detectada = None
    for palabra, cat in mapeo.items():
        if palabra in necesidad:
            categoria_detectada = cat
            break

    usa_multi = any(p in necesidad for p in mapeo_multi)

    if categoria_detectada and not usa_multi:
        resultados = buscar_empresas_local(categoria=categoria_detectada, keywords=keywords_busqueda)
    elif categoria_detectada and usa_multi:
        resultados_cat = buscar_empresas_local(categoria=categoria_detectada, keywords=keywords_busqueda)
        resultados_multi = buscar_empresas_local(keywords=keywords_busqueda)
        visto = {r["nombre"] for r in resultados_cat}
        for r in resultados_multi:
            if r["nombre"] not in visto:
                resultados_cat.append(r)
        resultados = resultados_cat
    else:
        resultados = buscar_empresas_local(keywords=keywords_busqueda)

    return resultados, keywords_busqueda, categoria_detectada


def _calcular_score_local(emp, keywords, categoria_detectada):
    if not keywords:
        return 90
    score = 50
    matched_count = 0
    name_matched = False
    for kw in keywords:
        kws = SINONIMOS.get(kw.lower(), [kw.lower()])
        kw_match = False
        for skw in kws:
            if skw in emp["nombre"].lower():
                name_matched = True
            if (skw in emp.get("nombre", "").lower()
                or skw in emp.get("rubro", "").lower()
                or skw in emp.get("notas", "").lower()
                or any(skw in td.lower() for td in emp.get("tipo_donacion", []))):
                kw_match = True
                break
        if kw_match:
            matched_count += 1
    score += min(matched_count * 6, 30)
    if name_matched:
        score += 15
    if categoria_detectada and emp.get("categoria") == categoria_detectada:
        score += 10
    if emp.get("categoria") == "general" and categoria_detectada and categoria_detectada != "general":
        score -= 25
    return max(0, min(100, score))


def mostrar_resultados(resultados):
    if not resultados:
        print("\n  \u2716 No se encontraron empresas para esta b\u00fasqueda.\n")
        return

    print(f"\n  \u2714 Se encontraron {len(resultados)} empresa(s):\n")
    for i, emp in enumerate(resultados, 1):
        match = emp["match_score"]
        barra = "\u2588" * (match // 10) + "\u2591" * (10 - match // 10) if match else ""

        print(f"  {'\u2500' * 60}")
        print(f"  {i}. {emp['nombre'] or 'Sin nombre'}  [{emp['fuente']}]")
        if match:
            print(f"     Match:          [{barra}] {match}%")
        print(f"     Rubro:          {emp['rubro']}")
        print(f"     Categor\u00eda:      {CATEGORIAS.get(emp['categoria'], emp['categoria'])}")
        print(f"     Contacto:       {emp['contacto'] or 'No disponible'}")
        if emp["telefono"]:
            print(f"     Tel\u00e9fono:       {emp['telefono']}")
        print(f"     Web:            {emp['web']}")
        print(f"     Provincia:      {emp['provincia']}")
        print(f"     Donan:          {', '.join(emp['tipo_donacion']) if emp['tipo_donacion'] else '\u2014'}")
        print(f"     Notas:          {emp['notas']}")
    print(f"  {'\u2500' * 60}\n")


def exportar_csv(resultados, archivo="empresas_donantes.csv"):
    import csv
    with open(archivo, "w", newline="", encoding="utf-8") as f:
        campos = ["nombre", "rubro", "categoria", "contacto", "telefono", "web", "provincia", "tipo_donacion", "notas", "fuente", "match_score"]
        writer = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        writer.writeheader()
        for emp in resultados:
            row = {c: emp.get(c, "") for c in campos}
            row["tipo_donacion"] = ", ".join(emp.get("tipo_donacion", []))
            writer.writerow(row)
    print(f"\n  \u2714 Datos exportados a {archivo}\n")


def _cache_key(necesidad, usar_ia, solo_ia, incluir_guardadas):
    return f"{necesidad.lower().strip()}|{usar_ia}|{solo_ia}|{incluir_guardadas}"


def _cache_get(key):
    entry = _CACHE.get(key)
    if entry and (time.time() - entry[0]) < _CACHE_TTL:
        return entry[1]
    if entry:
        del _CACHE[key]
    return None


def _cache_set(key, resultados):
    _CACHE[key] = (time.time(), resultados)


def _ya_incluido(resultados, nombre, fuente):
    """Verifica si una empresa ya est\u00e1 en resultados con fuzzy matching."""
    for r in resultados:
        if _es_duplicado(r["nombre"], nombre):
            if r["match_score"] < fuente:
                r["match_score"] = fuente
            return True
    return False


def buscar_unificado(necesidad, usar_ia=True, solo_ia=False, incluir_guardadas=True, on_progress=None):
    """Busca en BD local, guardadas y web con IA. Combina y rankea todo."""
    ck = _cache_key(necesidad, usar_ia, solo_ia, incluir_guardadas)
    cached = _cache_get(ck)
    if cached is not None:
        return cached

    resultados = []

    # Extraer keywords y categoria para scoring (sin ejecutar busqueda local)
    from database.empresas import EMPRESAS as _emp
    necesidad_lower = necesidad.lower()
    _mapeo = {
        "ba\u00f1o": "construccion", "ba\u00f1os": "construccion", "sanitario": "construccion",
        "cemento": "construccion", "construccion": "construccion", "construcci\u00f3n": "construccion",
        "ladrillo": "construccion", "material": "construccion", "obra": "construccion",
        "ceramica": "construccion", "cer\u00e1mica": "construccion", "ceramico": "construccion",
        "cer\u00e1mico": "construccion", "pintura": "construccion",
        "computadora": "tecnologia", "tablet": "tecnologia", "tecnologia": "tecnologia",
        "tecnolog\u00eda": "tecnologia", "internet": "tecnologia", "wifi": "tecnologia",
        "router": "tecnologia", "pc": "tecnologia", "notebook": "tecnologia",
        "impresora": "tecnologia", "pantalla": "tecnologia", "proyector": "tecnologia",
        "informatica": "tecnologia", "inform\u00e1tica": "tecnologia",
        "libro": "educacion", "cuaderno": "educacion", "utiles": "educacion",
        "\u00fatiles": "educacion", "escolar": "educacion", "lapiz": "educacion",
        "l\u00e1piz": "educacion", "lapicera": "educacion", "birome": "educacion",
        "mochila": "educacion", "educacion": "educacion", "educaci\u00f3n": "educacion",
        "curso": "educacion", "capacitacion": "educacion", "capacitaci\u00f3n": "educacion",
        "taller": "educacion", "biblioteca": "educacion",
        "comida": "alimentacion", "alimento": "alimentacion", "alimentacion": "alimentacion",
        "alimentaci\u00f3n": "alimentacion", "leche": "alimentacion", "fideo": "alimentacion",
        "arroz": "alimentacion", "aceite": "alimentacion", "lacteo": "alimentacion",
        "l\u00e1cteo": "alimentacion", "bebida": "alimentacion", "cocina": "alimentacion",
        "merendero": "alimentacion", "comedor": "alimentacion",
    }
    _stopwords = {"de", "el", "la", "los", "las", "un", "una", "para", "en", "con", "del", "al", "por", "y", "o", "a", "que", "es", "se", "no", "su", "mi", "tu"}
    keywords = [p for p in necesidad.split() if p.lower() not in _stopwords]
    categoria_detectada = None
    for palabra, cat in _mapeo.items():
        if palabra in necesidad_lower:
            categoria_detectada = cat
            break

    # 1. B\u00fasqueda local
    if not solo_ia:
        locales, _, _ = buscar_empresas_por_necesidad(necesidad)
        for emp in locales:
            score = _calcular_score_local(emp, keywords, categoria_detectada)
            resultados.append(_normalizar_empresa(emp, fuente="BD Local", score=score))

    # 2. Empresas guardadas en SQLite
    if incluir_guardadas and not solo_ia:
        try:
            from database import db
            guardadas = db.get_empresas_guardadas()
            for g in guardadas:
                score = _calcular_score_local(g, keywords, categoria_detectada)
                if score <= 0:
                    continue
                norm = _normalizar_empresa(g, fuente="Guardada", score=max(score, g.get("match_score", 50)))
                if not _ya_incluido(resultados, norm["nombre"], norm["match_score"]) and norm["nombre"]:
                    resultados.append(norm)
        except Exception:
            pass

    # 3. B\u00fasqueda IA en web
    if usar_ia:
        from config import get_cliente
        if get_cliente():
            from search.ia_busqueda import buscar_empresas_con_ia
            ia = buscar_empresas_con_ia(necesidad, max_resultados=12, on_progress=on_progress)
            if "error" not in ia:
                for emp in ia.get("empresas", []):
                    norm = _normalizar_empresa(emp, fuente="IA", score=emp.get("match_score", 50))
                    if not _ya_incluido(resultados, norm["nombre"], norm["match_score"]) and norm["nombre"]:
                        resultados.append(norm)

    # 4. Ordenar por match_score descendente
    resultados.sort(key=lambda x: x.get("match_score", 0), reverse=True)

    _cache_set(ck, resultados)
    return resultados
