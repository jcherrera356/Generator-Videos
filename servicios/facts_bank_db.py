"""
Banco fijo de datos curiosos ("local"), guardado en la tabla
`videosApp.FactsBank` de SQL Server en vez de facts_bank.json. Es la fuente
"local" del pipeline y el respaldo final si Wikipedia/RAWG/Google Trends
fallan, así que se agrega/edita directo en la base de datos -- ya no hace
falta tocar código ni hacer commit para sumar un dato nuevo.

Sin respaldo local: si no hay conexión a SQL se lanza
sql_database.ErrorConexionSQL y el video no se genera, en vez de seguir con
una copia desactualizada.
"""

from servicios import sql_database


def get_all_facts() -> list[dict]:
    cn = sql_database.get_connection_required()
    try:
        cur = cn.cursor()
        cur.execute("SELECT id, category, keywords, texto FROM videosApp.FactsBank")
        return [
            {"id": row[0], "category": row[1], "keywords": row[2], "text": row[3]}
            for row in cur.fetchall()
        ]
    finally:
        cn.close()


def add_fact(id_: str, category: str, keywords: str, text: str) -> None:
    cn = sql_database.get_connection_required()
    try:
        cur = cn.cursor()
        cur.execute(
            "INSERT INTO videosApp.FactsBank (id, category, keywords, texto) VALUES (?, ?, ?, ?)",
            id_, category, keywords, text,
        )
        cn.commit()
    finally:
        cn.close()
