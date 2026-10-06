"""
Capa de presentación: punto de entrada por consola (el que usa
generar_video.bat). Elige la fuente del dato por argumento de línea de
comandos, corre el pipeline (aplicacion/generador_pipeline.py) y, si hay
credenciales de Google Drive configuradas, sincroniza el registro de "no
repetir" antes y después (aplicacion/drive_sync.py).

Uso: python presentacion/cli.py [wikipedia|local|games|trending|auto] [categoria]

`categoria` solo aplica con "trending" (una de google_trends.CATEGORIES,
ej. "Videojuegos", "Moda") -- si no se pasa, usa cualquier tema de tendencia.
"""

import sys
from pathlib import Path

# Para poder importar "aplicacion", "servicios", etc. como paquetes de nivel
# superior sin importar desde dónde se invoque este script (doble clic en el
# .bat, `python presentacion/cli.py`, etc.), se agrega la raíz del proyecto
# al sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aplicacion import drive_sync, generador_pipeline  # noqa: E402


def main() -> None:
    source = sys.argv[1] if len(sys.argv) > 1 else "auto"
    trend_category = sys.argv[2] if len(sys.argv) > 2 else None
    try:
        service, folder_id = drive_sync.load_drive_service_from_config()
        if service:
            print("[+] Sincronizando registro de datos ya usados desde Google Drive...")
            drive_sync.sync_state_from_drive(service, folder_id)

        out_path = generador_pipeline.main(source, trend_category)

        if service:
            print("[+] Subiendo video y registro actualizado a Google Drive...")
            drive_sync.push_results_to_drive(service, folder_id, out_path, out_path.with_suffix(".txt"))
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
