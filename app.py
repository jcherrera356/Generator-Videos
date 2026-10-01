"""Version minima temporal para diagnosticar el crash de Streamlit Cloud.

No importa drive_storage, generate_video ni rawg_games -- solo streamlit.
Si esto tambien falla el healthcheck, el problema es de la plataforma,
no de nuestro codigo (RAWG, Google Drive, etc.). Restaurar app.py original
(guardado en app_full_backup.py.txt) una vez diagnosticado.
"""

import streamlit as st

st.title("Diagnostico")
st.write("Si ves esto, la app arranco bien.")
