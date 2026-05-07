import sqlite3
import os
import json

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "iea.db")

os.makedirs(DB_DIR, exist_ok=True)


def _conectar():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def inicializar():
    conn = _conectar()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS empresas_guardadas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nicho           TEXT NOT NULL,
            zona            TEXT NOT NULL DEFAULT '',
            nombre          TEXT NOT NULL,
            sitio_web       TEXT,
            email           TEXT,
            tiene_rse       INTEGER DEFAULT 0,
            direccion       TEXT,
            telefono        TEXT,
            contacto_nombre TEXT,
            fuente          TEXT,
            categoria       TEXT,
            tipo_donacion   TEXT,
            notas           TEXT,
            match_score     INTEGER DEFAULT 0,
            idea_referencia TEXT,
            asunto          TEXT,
            cuerpo          TEXT,
            fecha           TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS historial (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa         TEXT NOT NULL,
            nicho           TEXT,
            sitio_web       TEXT,
            email_empresa   TEXT,
            asunto          TEXT,
            cuerpo          TEXT,
            idea_referencia TEXT,
            estado          TEXT DEFAULT 'enviado',
            fecha           TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS emails_referencia (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo          TEXT,
            contenido       TEXT NOT NULL,
            fecha           TEXT DEFAULT (datetime('now','localtime'))
        );
    """)
    conn.commit()
    conn.close()


# ─── Empresas guardadas ───

def get_empresas_guardadas(nicho=None, zona=None):
    conn = _conectar()
    if nicho and zona:
        rows = conn.execute(
            "SELECT * FROM empresas_guardadas WHERE lower(nicho)=lower(?) AND lower(zona)=lower(?) ORDER BY fecha DESC",
            (nicho, zona)
        ).fetchall()
    elif nicho:
        rows = conn.execute(
            "SELECT * FROM empresas_guardadas WHERE lower(nicho)=lower(?) ORDER BY fecha DESC",
            (nicho,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM empresas_guardadas ORDER BY fecha DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_empresa_guardada(data):
    conn = _conectar()
    exists = conn.execute(
        "SELECT id FROM empresas_guardadas WHERE lower(nicho)=lower(?) AND lower(zona)=lower(?) AND lower(nombre)=lower(?)",
        (data.get("nicho", ""), data.get("zona", ""), data.get("nombre", ""))
    ).fetchone()
    if exists:
        conn.close()
        return exists["id"]
    cur = conn.execute(
        """INSERT INTO empresas_guardadas
           (nicho, zona, nombre, sitio_web, email, tiene_rse, direccion, telefono, contacto_nombre, fuente,
            categoria, tipo_donacion, notas, match_score)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (data.get("nicho", ""), data.get("zona", ""), data.get("nombre", ""), data.get("sitio_web"),
         data.get("email"), data.get("tiene_rse", 0), data.get("direccion"), data.get("telefono"),
         data.get("contacto_nombre"), data.get("fuente"), data.get("categoria"),
         data.get("tipo_donacion"), data.get("notas"), data.get("match_score", 0))
    )
    rid = cur.lastrowid
    conn.commit()
    conn.close()
    return rid


def update_empresa_guardada_email(id, data):
    conn = _conectar()
    conn.execute(
        "UPDATE empresas_guardadas SET idea_referencia=?, asunto=?, cuerpo=? WHERE id=?",
        (data.get("idea_referencia", ""), data.get("asunto", ""), data.get("cuerpo", ""), id)
    )
    conn.commit()
    conn.close()


def delete_empresa_guardada(id):
    conn = _conectar()
    conn.execute("DELETE FROM empresas_guardadas WHERE id=?", (id,))
    conn.commit()
    conn.close()


# ─── Historial ───

def get_historial():
    conn = _conectar()
    rows = conn.execute("SELECT * FROM historial ORDER BY fecha DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_historial(data):
    conn = _conectar()
    cur = conn.execute(
        """INSERT INTO historial (empresa, nicho, sitio_web, email_empresa, asunto, cuerpo, idea_referencia, estado)
           VALUES (?,?,?,?,?,?,?,?)""",
        (data.get("empresa", ""), data.get("nicho", ""), data.get("sitio_web", ""),
         data.get("email_empresa", ""), data.get("asunto", ""), data.get("cuerpo", ""),
         data.get("idea_referencia", ""), data.get("estado", "enviado"))
    )
    rid = cur.lastrowid
    conn.commit()
    conn.close()
    return rid


def update_historial(id, data):
    conn = _conectar()
    if "estado" in data:
        conn.execute("UPDATE historial SET estado=? WHERE id=?", (data["estado"], id))
    conn.commit()
    conn.close()


def delete_historial(id):
    conn = _conectar()
    conn.execute("DELETE FROM historial WHERE id=?", (id,))
    conn.commit()
    conn.close()


# ─── Emails de referencia ───

def get_emails_referencia():
    conn = _conectar()
    rows = conn.execute("SELECT * FROM emails_referencia ORDER BY fecha DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_email_referencia(data):
    conn = _conectar()
    cur = conn.execute(
        "INSERT INTO emails_referencia (titulo, contenido) VALUES (?,?)",
        (data.get("titulo", ""), data.get("contenido", ""))
    )
    rid = cur.lastrowid
    conn.commit()
    conn.close()
    return rid


def delete_email_referencia(id):
    conn = _conectar()
    conn.execute("DELETE FROM emails_referencia WHERE id=?", (id,))
    conn.commit()
    conn.close()


inicializar()
