"""
Registro de "no repetir" compartido entre todos los equipos, guardado en la
tabla `videosApp.DatosUsados` de SQL Server (ver sql_database.py) en vez de
archivos used_*.json sincronizados por Google Drive. El schema `videosApp`
agrupa todas las tablas de este proyecto dentro de la base de datos
compartida, para distinguirlas de otras apps que vivan en el mismo server.

Una sola tabla para las 4 categorías (facts, games, wikipedia, trends),
separadas por la columna `categoria`, con UNIQUE (categoria, clave) para que
nunca quede una clave duplicada aunque dos procesos escriban a la vez.

A diferencia de las demás fuentes externas (Pexels, RAWG, etc.), esta NO
tiene respaldo silencioso: si no hay conexión a SQL (sin credenciales, sin
internet, el server gratuito de somee.com caído, etc.) se lanza un
RuntimeError y el video NO se genera -- es mejor avisar claramente que
generar un video sin poder registrar que ya se usó (arriesgando repetirlo).
"""

import pyodbc

from servicios import sql_database


def get_used_set(categoria: str) -> set[str]:
    cn = sql_database.get_connection_required()
    try:
        cur = cn.cursor()
        cur.execute("SELECT clave FROM videosApp.DatosUsados WHERE categoria = ?", categoria)
        return {row[0] for row in cur.fetchall()}
    finally:
        cn.close()


def clear(categoria: str) -> None:
    """Borra todo el registro de una categoría (para reiniciar el ciclo de
    "no repetir" cuando ya se agotó todo lo disponible, ej. facts_bank)."""
    cn = sql_database.get_connection_required()
    try:
        cur = cn.cursor()
        cur.execute("DELETE FROM videosApp.DatosUsados WHERE categoria = ?", categoria)
        cn.commit()
    finally:
        cn.close()


def mark_used(categoria: str, clave: str) -> None:
    cn = sql_database.get_connection_required()
    try:
        cur = cn.cursor()
        cur.execute(
            "INSERT INTO videosApp.DatosUsados (categoria, clave) VALUES (?, ?)",
            categoria, clave,
        )
        cn.commit()
    except pyodbc.IntegrityError:
        pass  # ya estaba marcada (otra corrida la insertó primero) -- no es un error
    finally:
        cn.close()
