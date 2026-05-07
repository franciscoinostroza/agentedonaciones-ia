import json
import re
import requests
import sys
import os
from bs4 import BeautifulSoup
from config import chat, get_cliente
from database.empresas import EMPRESAS

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


def extraer_contenido_pagina(url, timeout=5):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        texto = soup.get_text(separator=" ", strip=True)
        texto = re.sub(r"\s+", " ", texto)
        return texto[:4000]
    except Exception:
        return ""


def analizar_con_ia(texto_pagina, necesidad_original, titulo="", url=""):
    if not texto_pagina:
        return None

    prompt = f"""Analizá esta pagina web en busca de empresas argentinas que puedan donar.

NECESIDAD: {necesidad_original}

TITULO: {titulo}
URL: {url}

CONTENIDO:
{texto_pagina[:4000]}

Si esta pagina MENCIONA empresas concretas que donan o tienen programas de RSE,
extrae los datos de CADA empresa (maximo 3). Si no hay ninguna empresa concreta
con programa de donaciones, respondé exactamente: NO_DONA

Respondé SOLO en JSON como array de empresas:
[{{
    "nombre_empresa": "Nombre real de la empresa",
    "rubro": "Rubro principal",
    "categoria": "construccion|tecnologia|educacion|alimentacion|general",
    "contacto": "email de contacto si aparece",
    "telefono": "telefono si aparece",
    "web": "sitio web de la empresa",
    "provincia": "Provincia o Nacional",
    "tipo_donacion": ["tipo1", "tipo2"],
    "notas": "resumen de que donan y como contactar (2 lineas)",
    "match_score": numero 1-100 que tan bien se ajusta a la necesidad
}}]"""

    resp = chat([
        {"role": "system", "content": "Sos analista de RSE. Extrae empresas que donan de cualquier pagina. Si la pagina menciona empresas concretas con programas de donacion, extraelas. Solo JSON array o NO_DONA."},
        {"role": "user", "content": prompt}
    ], temperature=0.2, max_tokens=3000)

    if resp is None or "NO_DONA" in resp:
        return None

    try:
        json_match = re.search(r'\[.*\]', resp, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            if isinstance(data, list) and len(data) > 0:
                return data[0]
            elif isinstance(data, dict):
                return data
    except:
        pass
    return None


def buscar_empresas_con_ia(necesidad, max_resultados=8):
    if not get_cliente():
        return {"error": "API key de DeepSeek no configurada", "empresas": []}

    print(_safe(f"\n  Analizando necesidad: '{necesidad}'..."))

    print("  Generando consultas de busqueda con IA...")
    consultas = generar_consultas_ia(necesidad)

    todos_resultados = []
    urls_vistas = set()

    for i, consulta in enumerate(consultas):
        print(_safe(f"  Buscando en web [{i+1}/{len(consultas)}]: {consulta[:70]}..."))
        resultados_web = buscar_web_ddg(consulta, max_results=6)
        for r in resultados_web:
            url = r["url"]
            if url in urls_vistas:
                continue
            urls_vistas.add(url)
            todos_resultados.append(r)

    print(f"  Encontrados {len(todos_resultados)} links. Analizando con IA...")

    empresas_encontradas = []
    for i, r in enumerate(todos_resultados[:max_resultados]):
        titulo = _safe(r['titulo'][:60] if r.get('titulo') else 'Sin titulo')
        print(f"  Analizando [{i+1}/{min(len(todos_resultados), max_resultados)}]: {titulo}...")

        contenido = extraer_contenido_pagina(r["url"])
        if not contenido:
            continue

        analisis = analizar_con_ia(
            contenido,
            necesidad,
            titulo=r["titulo"],
            url=r["url"],
        )

        if analisis and isinstance(analisis, dict):
            analisis.setdefault("categoria", "general")
            analisis.setdefault("contacto", "")
            analisis.setdefault("telefono", "")
            analisis.setdefault("provincia", "Argentina")
            analisis.setdefault("tipo_donacion", [])
            analisis.setdefault("notas", "")
            analisis.setdefault("match_score", 50)
            analisis["fuente"] = "IA"
            empresas_encontradas.append(analisis)

    empresas_encontradas.sort(key=lambda x: x.get("match_score", 0), reverse=True)

    return {
        "consultas_usadas": consultas,
        "total_links": len(todos_resultados),
        "empresas": empresas_encontradas,
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
