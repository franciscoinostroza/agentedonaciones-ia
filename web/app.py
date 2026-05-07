from flask import Flask, render_template, request, jsonify
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_cliente, IA_MODEL, chat
from search.busqueda import buscar_unificado, CATEGORIAS
from database.empresas import EMPRESAS
from database import db

app = Flask(__name__)


@app.route("/")
def index():
    zonas = ["GBA / Conurbano Bonaerense", "CABA", "Córdoba", "Rosario", "Mendoza", "Mar del Plata", "Argentina (nacional)"]
    ia_disponible = get_cliente() is not None
    return render_template("index.html", zonas=zonas, ia_disponible=ia_disponible, ia_modelo=IA_MODEL)


# ─── BUSCAR ────────────────────────────────────────────────────

@app.route("/api/buscar", methods=["POST"])
def buscar():
    data = request.get_json()
    necesidad = data.get("necesidad", "").strip()
    zona = data.get("zona", "Argentina (nacional)")

    if not necesidad:
        return jsonify({"error": "Describí qué necesitás"}), 400

    # 1. Resultados locales (instantáneos)
    from search.busqueda import buscar_empresas_por_necesidad, buscar_empresas_local
    locales = buscar_empresas_por_necesidad(necesidad)
    for emp in locales:
        emp["match_score"] = 90
        emp["fuente"] = "BD Local"

    guardadas_previas = db.get_empresas_guardadas(necesidad, zona)
    nombres_previos = {e["nombre"] for e in guardadas_previas}

    formato = _formatear_empresas(locales)

    return jsonify({
        "resultados": formato,
        "guardadasPrevias": guardadas_previas,
        "zona": zona,
        "total": len(formato),
        "total_guardadas": len(guardadas_previas),
        "ia_pendiente": get_cliente() is not None,
    })


@app.route("/api/buscar-ia", methods=["POST"])
def buscar_ia():
    """Endpoint separado para búsqueda IA (más lento, para llamar después)"""
    data = request.get_json()
    necesidad = data.get("necesidad", "").strip()

    if not necesidad:
        return jsonify({"empresas": []})

    try:
        from search.ia_busqueda import buscar_empresas_con_ia
        resultado = buscar_empresas_con_ia(necesidad, max_resultados=12)
        empresas = resultado.get("empresas", []) if "error" not in resultado else []

        formato = []
        for emp in empresas:
            donan = emp.get("tipo_donacion", [])
            formato.append({
                "nombre": emp.get("nombre_empresa", emp.get("nombre", "")),
                "sitio_web": emp.get("web", ""),
                "email": emp.get("contacto", ""),
                "tiene_rse": 1,
                "categoria": emp.get("categoria", "general"),
                "donan": ", ".join(donan) if isinstance(donan, list) else str(donan),
                "notas": emp.get("notas", ""),
                "match_score": emp.get("match_score", 50),
                "fuente": "IA",
                "telefono": emp.get("telefono", ""),
            })
        return jsonify({"empresas": formato, "total": len(formato)})
    except Exception as e:
        return jsonify({"empresas": [], "error": str(e)})


def _formatear_empresas(lista):
    limpios = []
    for r in lista:
        donan = r.get("tipo_donacion", [])
        limpios.append({
            "nombre": r.get("nombre", r.get("nombre_empresa", "")),
            "sitio_web": r.get("web", r.get("sitio_web", "")),
            "email": r.get("contacto", ""),
            "tiene_rse": 1,
            "categoria": r.get("categoria", ""),
            "donan": ", ".join(donan) if isinstance(donan, list) else str(donan),
            "notas": r.get("notas", ""),
            "match_score": r.get("match_score", 0),
            "fuente": r.get("fuente", ""),
            "telefono": r.get("telefono", ""),
            "provincia": r.get("provincia", ""),
        })
    return limpios


# ─── GENERAR EMAIL ─────────────────────────────────────────────

@app.route("/api/generar-email", methods=["POST"])
def generar_email():
    data = request.get_json()
    empresa = data.get("empresa", {})
    necesidad = data.get("necesidad", "").strip()
    guardada_id = data.get("guardadaId")

    if not empresa or not necesidad:
        return jsonify({"error": "Faltan datos"}), 400

    nombre = empresa.get("nombre", "")
    donan = empresa.get("donan", empresa.get("tipo_donacion", ""))
    sitio = empresa.get("sitio_web", empresa.get("web", ""))

    prompt = f"""Sos asistente de la Asociación Civil Integrar Educar Amar (IEA), una ONG que brinda
apoyo escolar y merienda diaria a 50 niños en situación de vulnerabilidad en Argentina.

Empresa a contactar:
- Nombre: {nombre}
- Rubro: {necesidad}
- Sitio web: {sitio}
- Tipo de donación que ofrece: {donan}

Generá:
1. Una "idea de referencia" (2-3 oraciones): por qué esta empresa podría donar, qué pedirle
2. Un email de solicitud de donación que:
   - Conecte el rubro con lo que necesita IEA
   - Use español rioplatense, emotivo pero profesional
   - Mencione logros concretos
   - Cierre con llamado a la acción
   - Firme: Asociación Civil Integrar Educar Amar | abigailntevez@gmail.com

Devolvé ÚNICAMENTE JSON:
{{"idea_referencia": "...", "asunto": "...", "cuerpo": "..."}}"""

    resp = chat([
        {"role": "system", "content": "Sos redactor de emails de fundraising para ONGs. Solo JSON."},
        {"role": "user", "content": prompt}
    ], temperature=0.75, max_tokens=2000)

    import re, json
    try:
        match = re.search(r'\{.*\}', resp, re.DOTALL)
        email_data = json.loads(match.group()) if match else {}
    except:
        email_data = {"idea_referencia": "", "asunto": "", "cuerpo": ""}

    if guardada_id:
        db.update_empresa_guardada_email(guardada_id, email_data)

    return jsonify({
        "nombre": nombre,
        "sitio_web": sitio,
        "email": empresa.get("email", ""),
        "tiene_rse": True,
        "idea_referencia": email_data.get("idea_referencia", ""),
        "asunto": email_data.get("asunto", ""),
        "cuerpo": email_data.get("cuerpo", ""),
    })


# ─── EMPRESAS GUARDADAS ────────────────────────────────────────

@app.route("/api/empresas-guardadas", methods=["GET", "POST"])
def empresas_guardadas():
    if request.method == "GET":
        nicho = request.args.get("nicho")
        return jsonify(db.get_empresas_guardadas(nicho))
    if request.method == "POST":
        data = request.get_json()
        rid = db.add_empresa_guardada(data)
        return jsonify({"id": rid})


@app.route("/api/empresas-guardadas/<int:id>", methods=["DELETE"])
def eliminar_empresa_guardada(id):
    db.delete_empresa_guardada(id)
    return jsonify({"ok": True})


# ─── HISTORIAL ─────────────────────────────────────────────────

@app.route("/api/historial", methods=["GET", "POST", "PATCH"])
def historial_handler():
    if request.method == "GET":
        return jsonify(db.get_historial())
    if request.method == "POST":
        data = request.get_json()
        rid = db.add_historial(data)
        return jsonify({"id": rid})
    if request.method == "PATCH":
        # Usamos query param para el id
        return jsonify({"ok": True})


@app.route("/api/historial/<int:id>", methods=["PATCH", "DELETE"])
def historial_item(id):
    if request.method == "PATCH":
        data = request.get_json()
        db.update_historial(id, data)
        return jsonify({"ok": True})
    if request.method == "DELETE":
        db.delete_historial(id)
        return jsonify({"ok": True})


# ─── EMAILS DE REFERENCIA ──────────────────────────────────────

@app.route("/api/emails-referencia", methods=["GET", "POST"])
def emails_referencia():
    if request.method == "GET":
        return jsonify(db.get_emails_referencia())
    if request.method == "POST":
        data = request.get_json()
        rid = db.add_email_referencia(data)
        return jsonify({"id": rid})


@app.route("/api/emails-referencia/<int:id>", methods=["DELETE"])
def eliminar_email_referencia(id):
    db.delete_email_referencia(id)
    return jsonify({"ok": True})


# ─── IA STATUS ────────────────────────────────────────────────

@app.route("/api/ia-status")
def ia_status():
    return jsonify({
        "activa": get_cliente() is not None,
        "modelo": IA_MODEL,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
