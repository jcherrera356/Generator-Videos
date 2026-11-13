"""
Conexión a la base de datos SQL Server donde viven las tablas de este
proyecto (schema `videosApp`): `DatosUsados` (registro de "no repetir") y
`FactsBank` (banco de datos curiosos fijos). Reemplazan los archivos locales
used_*.json y facts_bank.json -- antes se sincronizaban a mano o por Google
Drive, lo que podía perder datos si dos equipos corrían casi al mismo
tiempo; la base de datos evita ese problema (restricciones UNIQUE, cada
escritura es atómica).

Requiere credenciales en .config/config.json (ver app_config.py) como:
{"sql_server": {"server": "...", "database": "...", "user": "...", "password": "..."}}
"""

import pyodbc

from datos import app_config


class ErrorConexionSQL(RuntimeError):
    pass


def get_connection() -> pyodbc.Connection | None:
    """Devuelve la conexión, o None si no hay credenciales o falla la
    conexión. Para el caso en que SIEMPRE hace falta la base de datos (no
    hay respaldo local razonable), usar get_connection_required()."""
    cfg = app_config.get_sql_server_config()
    if not cfg:
        return None
    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={cfg['server']};"
        f"DATABASE={cfg['database']};"
        f"UID={cfg['user']};"
        f"PWD={cfg['password']};"
        "TrustServerCertificate=yes;"
        "Encrypt=no;"
    )
    try:
        return pyodbc.connect(conn_str, timeout=15)
    except pyodbc.Error:
        return None


def get_connection_required() -> pyodbc.Connection:
    """Igual que get_connection(), pero lanza ErrorConexionSQL con un
    mensaje claro en vez de devolver None -- para las tablas que no tienen
    (o ya no tienen) un respaldo local, donde es mejor detener el video con
    un error explícito que seguir sin poder leer/registrar datos."""
    cn = get_connection()
    if not cn:
        raise ErrorConexionSQL(
            "No se pudo conectar a la base de datos SQL (revisa internet y las "
            "credenciales 'sql_server' en .config/config.json)."
        )
    return cn
