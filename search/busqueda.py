import time
import requests
from bs4 import BeautifulSoup
from database.empresas import EMPRESAS


CATEGORIAS = {
    "construccion": "Materiales y Construcción",
    "tecnologia": "Tecnología y Conectividad",
    "educacion": "Educación, Libros y Útiles",
    "alimentacion": "Alimentos y Bebidas",
    "general": "Donaciones Varias y Financiamiento",
}


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
            sinonimos = {
                "mueble": ["mueble", "mobiliario", "silla", "mesa", "muebles_banio", "estanteria"],
                "muebles": ["mueble", "mobiliario", "silla", "mesa", "muebles_banio", "estanteria"],
                "mobiliario": ["mueble", "mobiliario", "silla", "mesa", "muebles_banio"],
                "computadora": ["computadora", "pc", "notebook", "tablet", "computadoras", "informatica"],
                "pc": ["computadora", "pc", "notebook", "tablet", "computadoras", "informatica"],
                "baño": ["baño", "sanitario", "inodoro", "lavatorio", "banio", "construccion"],
                "banio": ["baño", "sanitario", "inodoro", "lavatorio", "banio"],
                "sanitario": ["baño", "sanitario", "inodoro", "lavatorio"],
                "libro": ["libro", "cuaderno", "utiles", "escolar", "biblioteca", "lectura"],
                "alimento": ["alimento", "comida", "leche", "fideo", "arroz", "aceite", "lacteo", "bebida"],
                "alimentos": ["alimento", "comida", "leche", "fideo", "arroz", "aceite", "lacteo", "bebida"],
                "comida": ["alimento", "comida", "leche", "fideo", "arroz", "aceite", "lacteo", "bebida"],
                "leche": ["alimento", "leche", "lacteo", "yogur"],
                "lacteo": ["alimento", "leche", "lacteo", "yogur"],
                "lacteos": ["alimento", "leche", "lacteo", "yogur"],
                "libros": ["libro", "cuaderno", "utiles", "escolar", "biblioteca", "lectura"],
                "utiles": ["libro", "cuaderno", "utiles", "escolar", "lapiz", "lapicera", "mochila"],
                "escolar": ["libro", "cuaderno", "utiles", "escolar", "lapiz", "lapicera", "mochila"],
                "material": ["material", "materiales", "construccion", "cemento", "obra"],
                "materiales": ["material", "materiales", "construccion", "cemento", "obra"],
            }

            match = False
            for kw in keywords:
                kw = kw.lower()
                kws = sinonimos.get(kw, [kw])
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
    necesidad = necesidad.lower()
    mapeo = {
        "baño": "construccion",
        "baños": "construccion",
        "sanitario": "construccion",
        "cemento": "construccion",
        "construccion": "construccion",
        "construcción": "construccion",
        "ladrillo": "construccion",
        "material": "construccion",
        "obra": "construccion",
        "ceramica": "construccion",
        "cerámica": "construccion",
        "ceramico": "construccion",
        "cerámico": "construccion",
        "pintura": "construccion",
        "computadora": "tecnologia",
        "tablet": "tecnologia",
        "tecnologia": "tecnologia",
        "tecnología": "tecnologia",
        "internet": "tecnologia",
        "wifi": "tecnologia",
        "router": "tecnologia",
        "pc": "tecnologia",
        "notebook": "tecnologia",
        "impresora": "tecnologia",
        "pantalla": "tecnologia",
        "proyector": "tecnologia",
        "informatica": "tecnologia",
        "informática": "tecnologia",
        "libro": "educacion",
        "cuaderno": "educacion",
        "utiles": "educacion",
        "útiles": "educacion",
        "escolar": "educacion",
        "lapiz": "educacion",
        "lápiz": "educacion",
        "lapicera": "educacion",
        "birome": "educacion",
        "mochila": "educacion",
        "educacion": "educacion",
        "educación": "educacion",
        "curso": "educacion",
        "capacitacion": "educacion",
        "capacitación": "educacion",
        "taller": "educacion",
        "biblioteca": "educacion",
        "comida": "alimentacion",
        "alimento": "alimentacion",
        "alimentacion": "alimentacion",
        "alimentación": "alimentacion",
        "leche": "alimentacion",
        "fideo": "alimentacion",
        "arroz": "alimentacion",
        "aceite": "alimentacion",
        "lacteo": "alimentacion",
        "lácteo": "alimentacion",
        "bebida": "alimentacion",
        "cocina": "alimentacion",
        "merendero": "alimentacion",
        "comedor": "alimentacion",
    }

    # Palabras que se buscan en todas las categorias (multi-categoria)
    mapeo_multi = {
        "mueble", "muebles", "mobiliario", "silla", "mesa", "estanteria",
        "dinero", "donacion", "donación", "financiamiento", "fondos",
        "logistica", "logística", "transporte", "envio",
        "niño", "niños", "infantil", "chico", "chicos", "joven", "jovenes",
        "limpieza", "equipamiento", "herramienta", "herramientas",
        "voluntario", "voluntariado",
    }

    # Palabras vacías (stop words) que no aportan a la búsqueda
    stopwords = {"de", "el", "la", "los", "las", "un", "una", "para", "en", "con", "del", "al", "por", "y", "o", "a", "que", "es", "se", "no", "su", "mi", "tu"}
    keywords_busqueda = [p for p in necesidad.split() if p.lower() not in stopwords]

    categoria_detectada = None
    for palabra, cat in mapeo.items():
        if palabra in necesidad:
            categoria_detectada = cat
            break

    usa_multi = any(p in necesidad for p in mapeo_multi)

    if categoria_detectada and not usa_multi:
        return buscar_empresas_local(categoria=categoria_detectada, keywords=keywords_busqueda)
    elif categoria_detectada and usa_multi:
        resultados_cat = buscar_empresas_local(categoria=categoria_detectada, keywords=keywords_busqueda)
        resultados_multi = buscar_empresas_local(keywords=keywords_busqueda)
        visto = {r["nombre"] for r in resultados_cat}
        for r in resultados_multi:
            if r["nombre"] not in visto:
                resultados_cat.append(r)
        return resultados_cat
    else:
        return buscar_empresas_local(keywords=keywords_busqueda)


def buscar_empresas_web(query, provincia=None):
    resultados = []

    motores = {
        "Google": "https://www.google.com/search?q={}",
        "Bing": "https://www.bing.com/search?q={}",
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    busquedas = [
        f'empresas donan {query} organizaciones sociales comedores Argentina',
        f'donaciones de {query} para merenderos Argentina fundaciones',
        f'responsabilidad social empresaria donacion {query} Argentina',
    ]

    if provincia:
        busquedas = [f'{b} {provincia}' for b in busquedas]

    links_vistos = set()

    for busqueda in busquedas[:2]:
        try:
            url = motores["Google"].format(requests.utils.quote(busqueda))
            resp = requests.get(url, headers=headers, timeout=15)

            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml")

                for div in soup.find_all(["div", "a"]):
                    link = div.get("href", "")
                    if link.startswith("http") and "google" not in link:
                        if link not in links_vistos:
                            links_vistos.add(link)
                            resultados.append({
                                "fuente": "Web",
                                "url": link,
                                "busqueda": busqueda,
                            })

                for g in soup.select(".g, .yuRUbf"):
                    titulo = g.get_text(strip=True)[:120]
                    if titulo and titulo not in [r.get("titulo", "") for r in resultados]:
                        pass

            time.sleep(1)

        except Exception:
            continue

    return resultados[:20]


def mostrar_resultados(resultados):
    if not resultados:
        print("\n  ✖ No se encontraron empresas para esta búsqueda.\n")
        return

    print(f"\n  ✔ Se encontraron {len(resultados)} empresa(s):\n")
    for i, emp in enumerate(resultados, 1):
        if "fuente" in emp and emp["fuente"] == "Web":
            print(f"  {i}. [WEB] {emp['url']}")
            continue

        fuente = emp.get("fuente", "")
        match = emp.get("match_score", 0)
        barra = "█" * (match // 10) + "░" * (10 - match // 10) if match else ""

        print(f"  {'─' * 60}")
        print(f"  {i}. {emp.get('nombre', emp.get('nombre_empresa', 'Sin nombre'))}  [{fuente}]")
        if match:
            print(f"     Match:          [{barra}] {match}%")
        print(f"     Rubro:          {emp.get('rubro', '')}")
        print(f"     Categoría:      {CATEGORIAS.get(emp.get('categoria', ''), emp.get('categoria', ''))}")
        print(f"     Contacto:       {emp.get('contacto', 'No disponible')}")
        if emp.get("telefono"):
            print(f"     Teléfono:       {emp['telefono']}")
        print(f"     Web:            {emp.get('web', emp.get('sitio', ''))}")
        print(f"     Provincia:      {emp.get('provincia', 'Argentina')}")
        donan = emp.get('tipo_donacion', [])
        if isinstance(donan, list):
            print(f"     Donan:          {', '.join(donan)}")
        else:
            print(f"     Donan:          {donan}")
        print(f"     Notas:          {emp.get('notas', '')}")
    print(f"  {'─' * 60}\n")


def exportar_csv(resultados, archivo="empresas_donantes.csv"):
    import csv
    with open(archivo, "w", newline="", encoding="utf-8") as f:
        campos = ["nombre", "rubro", "categoria", "contacto", "telefono", "web", "provincia", "tipo_donacion", "notas"]
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for emp in resultados:
            if "fuente" in emp and emp["fuente"] == "Web":
                continue
            row = {c: emp.get(c, "") for c in campos}
            row["tipo_donacion"] = ", ".join(emp.get("tipo_donacion", []))
            writer.writerow(row)
    print(f"\n  ✔ Datos exportados a {archivo}\n")


def buscar_unificado(necesidad, usar_ia=True):
    """Busca en BD local y web con IA. Combina y rankea todo."""
    resultados = []

    # 1. Búsqueda local
    locales = buscar_empresas_por_necesidad(necesidad)
    for emp in locales:
        emp["fuente"] = "BD Local"
        emp["match_score"] = 90
        resultados.append(emp)

    # 2. Búsqueda IA en web
    if usar_ia:
        from config import get_cliente
        if get_cliente():
            from search.ia_busqueda import buscar_empresas_con_ia
            ia = buscar_empresas_con_ia(necesidad, max_resultados=12)
            if "error" not in ia:
                for emp in ia.get("empresas", []):
                    nombre_ia = emp.get("nombre_empresa", "").lower().strip()
                    duplicado = False
                    for r in resultados:
                        if r.get("nombre", "").lower().strip() == nombre_ia:
                            duplicado = True
                            break
                    if not duplicado and nombre_ia:
                        emp["fuente"] = "IA"
                        emp["nombre"] = emp.get("nombre_empresa", emp.get("nombre", ""))
                        resultados.append(emp)

    # 3. Ordenar por match_score descendente
    resultados.sort(key=lambda x: x.get("match_score", 0), reverse=True)

    return resultados
