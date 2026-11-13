"""
Conexión a la base de datos SQL Server donde viven las tablas de este
proyecto (schema `videosApp`): `DatosUsados` (registro de "no repetir") y
`FactsBank` (banco de datos curiosos fijos). Reemplazan los archivos locales
used_*.json y facts_bank.json -- antes se sincronizaban a mano o por Google
Drive, lo que podía perder datos si dos equipos corrían casi al mismo
tiempo; la base de datos evita ese problema (restricciones UNIQUE, cada
escritura es atómica).

Usa pymssql en vez de pyodbc a propósito: pymssql trae su propio driver
(FreeTDS) empaquetado en el wheel de pip, sin depender de que el sistema
operativo tenga instalado el driver ODBC de Microsoft -- necesario para que
esto funcione en Streamlit Cloud (su contenedor gratuito no permite agregar
el repositorio de paquetes de Microsoft, así que pyodbc no conectaría ahí).

Requiere credenciales en .config/config.json (local) o en los Secrets de
Streamlit (en la nube, ver presentacion/app.py) como:
{"sql_server": {"server": "...", "database": "...", "user": "...", "password": "..."}}

IMPORTANTE para quien use servicios/usados_db.py o facts_bank_db.py: pymssql
usa placeholders %s (no ? como pyodbc), con los parámetros siempre en una
tupla: cur.execute("... WHERE x = %s", (valor,)).
"""

import pymssql

from datos import app_config


class ErrorConexionSQL(RuntimeError):
    pass


def get_connection() -> pymssql.Connection | None:
    """Devuelve la conexión, o None si no hay credenciales o falla la
    conexión. Para el caso en que SIEMPRE hace falta la base de datos (no
    hay respaldo local razonable), usar get_connection_required()."""
    cfg = app_config.get_sql_server_config()
    if not cfg:
        return None
    try:
        return pymssql.connect(
            server=cfg["server"],
            database=cfg["database"],
            user=cfg["user"],
            password=cfg["password"],
            login_timeout=15,
        )
    except pymssql.Error:
        return None


def get_connection_required() -> pymssql.Connection:
    """Igual que get_connection(), pero lanza ErrorConexionSQL con un
    mensaje claro en vez de devolver None -- para las tablas que no tienen
    (o ya no tienen) un respaldo local, donde es mejor detener el video con
    un error explícito que seguir sin poder leer/registrar datos."""
    cn = get_connection()
    if not cn:
        raise ErrorConexionSQL(
            "No se pudo conectar a la base de datos SQL (revisa internet y las "
            "credenciales 'sql_server' en .config/config.json o en los Secrets "
            "de Streamlit)."
        )
    return cn
