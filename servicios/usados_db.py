"""
Registro de "no repetir" compartido entre todos los equipos, guardado en la
tabla `videosApp.DatosUsados` de SQL Server (ver sql_database.py) en vez de
archivos used_*.json sincronizados por Google Drive. El schema `videosApp`
agrupa todas las tablas de este proyecto dentro de la base de datos
compartida, para distinguirlas de otras apps que vivan en el mismo server.

Una sola tabla para las 4 categorías (facts, games, wikipedia, trends),
separadas por la columna `categoria`, con UNIQUE (categoria, clave) para que
nunca quede una clave duplicada aunque dos procesos escriban a la vez.

Si no hay conexión (sin credenciales, sin internet, el server gratuito de
somee.com caído, etc.) get_used_set() devuelve un set vacío y mark_used() no
hace nada -- el pipeline sigue funcionando, solo que esa corrida puntual no
filtra repetidos.
"""

import pyodbc

from servicios import sql_database


def get_used_set(categoria: str) -> set[str]:
    cn = sql_database.get_connection()
    if not cn:
        return set()
    try:
        cur = cn.cursor()
        cur.execute("SELECT clave FROM videosApp.DatosUsados WHERE categoria = ?", categoria)
        return {row[0] for row in cur.fetchall()}
    except pyodbc.Error:
        return set()
    finally:
        cn.close()


def clear(categoria: str) -> None:
    """Borra todo el registro de una categoría (para reiniciar el ciclo de
    "no repetir" cuando ya se agotó todo lo disponible, ej. facts_bank.json)."""
    cn = sql_database.get_connection()
    if not cn:
        return
    try:
        cur = cn.cursor()
        cur.execute("DELETE FROM videosApp.DatosUsados WHERE categoria = ?", categoria)
        cn.commit()
    except pyodbc.Error:
        pass
    finally:
        cn.close()


def mark_used(categoria: str, clave: str) -> None:
    cn = sql_database.get_connection()
    if not cn:
        return
    try:
        cur = cn.cursor()
        cur.execute(
            "INSERT INTO videosApp.DatosUsados (categoria, clave) VALUES (?, ?)",
            categoria, clave,
        )
        cn.commit()
    except pyodbc.IntegrityError:
        pass  # ya estaba marcada (otra corrida la insertó primero) -- no es un error
    except pyodbc.Error:
        pass
    finally:
        cn.close()
