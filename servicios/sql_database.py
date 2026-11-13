"""
Conexión a la base de datos SQL Server donde se guarda el registro de "no
repetir" (datos_usados), reemplazando los archivos used_*.json + Google
Drive -- esos archivos se sobrescribían completos en cada corrida, así que
si dos equipos generaban video casi al mismo tiempo uno podía pisar el
progreso del otro y terminaba repitiendo datos. La tabla con restricción
UNIQUE (categoria, clave) evita el duplicado sin importar cuántos procesos
escriban a la vez.

Requiere credenciales en .config/config.json (ver app_config.py) como:
{"sql_server": {"server": "...", "database": "...", "user": "...", "password": "..."}}
Si no están configuradas, get_connection() devuelve None y quien llame debe
seguir funcionando sin registro (ver servicios/usados_db.py).
"""

import pyodbc

from datos import app_config


def get_connection() -> pyodbc.Connection | None:
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
