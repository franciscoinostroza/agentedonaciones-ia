import json
import re
import sys
from config import chat, get_cliente

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS


def _safe(text):
    if text is None:
        return ""
    try:
        return str(text).encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8", errors="replace")
    except Exception:
        return str(text)


def generar_consultas_ia(necesidad):
    prompt = f"""Un merendero argentino (IEA) necesita: {necesidad}

Genera exactamente 6 consultas de busqueda web para encontrar EMPRESAS ESPECIFICAS
argentinas que puedan DONAR estos recursos. Cada consulta debe nombrar rubros o tipos
de empresa concretos. Ejemplos de buen formato:
- "fundacion ARCOR donacion alimentos comedores"
- "empresas lacteas donan leche merenderos Argentina"
- "Techint RSE donacion materiales construccion"

Responde SOLO en JSON:
{{"consultas": ["consulta1", "consulta2", "consulta3", "consulta4", "consulta5", "consulta6"]}}"""

    resp = chat([
        {"role": "system", "content": "Sos experto en fundraising argentino. Genera consultas web especificas que nombren rubros y tipos de empresa concretos. Solo JSON."},
        {"role": "user", "content": prompt}
    ], temperature=0.5, max_tokens=800)

    try:
        data = json.loads(resp)
        consultas = data.get("consultas", [])
        if consultas:
            return consultas
    except:
        pass

    return [
        f"empresas {necesidad} donan fundaciones Argentina",
        f"programa donaciones {necesidad} empresas argentinas",
        f"fabrica {necesidad} responsabilidad social Argentina",
        f"empresa {necesidad} donacion comedores merenderos",
        f"industria {necesidad} RSE Argentina donaciones",
        f"{necesidad} donacion organizaciones sociales Argentina",
    ]


def buscar_web_ddg(consulta, max_results=6):
    resultados = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(f"{consulta} Argentina", max_results=max_results):
                resultados.append({
                    "titulo": r.get("title", ""),
                    "url": r.get("href", ""),
                    "descripcion": r.get("body", ""),
                })
    except Exception:
        pass
    return resultados


def analizar_snippets_con_ia(snippets, necesidad_original):
    if not snippets:
        return []

    listado = "\n".join(
        f"- [{s['titulo'][:100]}] {s['descripcion'][:200]}\n  URL: {s['url']}"
        for s in snippets[:20]
    )

    prompt = f"""Sos experto en RSE argentina. Analizá estos resultados de busqueda web
y extraé SOLO empresas argentinas que tengan programas de donacion.

NECESIDAD del merendero IEA: {necesidad_original}

RESULTADOS:
{listado[:5000]}

Extrae maximo 5 empresas. Si el resultado NO describe una empresa que done, ignorá.
Si no encontrás ninguna empresa, respondé: NO_DONA

Respondé SOLO JSON array:
[{{
    "nombre_empresa": "nombre real",
    "rubro": "rubro",
    "categoria": "construccion|tecnologia|educacion|alimentacion|general",
    "contacto": "email o contacto si aparece",
    "telefono": "telefono si aparece",
    "web": "url",
    "provincia": "provincia",
    "tipo_donacion": ["tipo1"],
    "notas": "1-2 lineas sobre que donan",
    "match_score": numero 1-100
}}]"""

    resp = chat([
        {"role": "system", "content": "Extrae empresas argentinas con programas de donacion. Solo JSON array o NO_DONA."},
        {"role": "user", "content": prompt}
    ], temperature=0.3, max_tokens=3000)

    if resp is None or "NO_DONA" in resp:
        return []

    try:
        json_match = re.search(r'\[.*\]', resp, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            if isinstance(data, list):
                return data
    except:
        pass
    return []


def buscar_empresas_con_ia(necesidad, max_resultados=8):
    if not get_cliente():
        return {"error": "API key no configurada", "empresas": []}

    print(_safe(f"\n  Analizando necesidad: '{necesidad}'..."))

    print("  Generando consultas de busqueda con IA...")
    consultas = generar_consultas_ia(necesidad)

    todos_snippets = []
    urls_vistas = set()

    for i, consulta in enumerate(consultas):
        print(_safe(f"  Buscando en web [{i+1}/{len(consultas)}]: {consulta[:70]}..."))
        resultados_web = buscar_web_ddg(consulta, max_results=6)
        for r in resultados_web:
            url = r["url"]
            if url in urls_vistas:
                continue
            urls_vistas.add(url)
            todos_snippets.append(r)

    print(f"  Encontrados {len(todos_snippets)} links. Analizando con IA...")

    empresas = analizar_snippets_con_ia(todos_snippets, necesidad)

    for emp in empresas:
        emp.setdefault("categoria", "general")
        emp.setdefault("contacto", "")
        emp.setdefault("telefono", "")
        emp.setdefault("provincia", "Argentina")
        emp.setdefault("tipo_donacion", [])
        emp.setdefault("notas", "")
        emp.setdefault("match_score", 50)
        emp["fuente"] = "IA"

    empresas.sort(key=lambda x: x.get("match_score", 0), reverse=True)

    return {
        "consultas_usadas": consultas,
        "total_links": len(todos_snippets),
        "empresas": empresas[:max_resultados],
    }


def analizar_necesidad_completa_ia(necesidad):
    """Usa IA para entender la necesidad y devolver recomendaciones completas"""
    prompt = f"""Sos un asesor experto en fundraising para un merendero comunitario argentino llamado IEA.

El merendero necesita: {necesidad}

Analizá esta necesidad y respondé con un JSON con esta estructura exacta:
{{
    "categorias_relevantes": ["categoria1", "categoria2"],
    "palabras_clave_utiles": ["kw1", "kw2", "kw3"],
    "tipos_empresa_sugeridos": ["tipo1", "tipo2"],
    "estrategia_recomendada": "Estrategia de 2-3 oraciones sobre cómo encarar el pedido",
    "prioridad": "alta|media|baja",
    "consejos": ["consejo1", "consejo2"]
}}"""

    resp = chat([
        {"role": "system", "content": "Sos experto en fundraising para ONGs argentinas. Respondé solo JSON valido."},
        {"role": "user", "content": prompt}
    ], temperature=0.3, max_tokens=600)

    if resp is None:
        return _fallback_analisis(necesidad)

    try:
        json_match = re.search(r'\{.*\}', resp, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return data
    except Exception:
        pass

    return _fallback_analisis(necesidad)


def _fallback_analisis(necesidad):
    return {
        "categorias_relevantes": ["general"],
        "palabras_clave_utiles": [necesidad],
        "tipos_empresa_sugeridos": [],
        "estrategia_recomendada": f"Buscar empresas que trabajen con donaciones de {necesidad}.",
        "prioridad": "media",
        "consejos": ["Personalizar cada solicitud", "Contactar por multiples canales"],
    }
