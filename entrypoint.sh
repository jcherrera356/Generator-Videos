#!/bin/sh
set -e

mkdir -p /app/.streamlit

{
  echo "[gdrive]"
  echo "folder_id = \"${GDRIVE_FOLDER_ID}\""
  echo "client_id = \"${GDRIVE_CLIENT_ID}\""
  echo "client_secret = \"${GDRIVE_CLIENT_SECRET}\""
  echo "refresh_token = \"${GDRIVE_REFRESH_TOKEN}\""
  echo ""
  if [ -n "${PEXELS_API_KEY}" ]; then
    echo "[pexels]"
    echo "api_key = \"${PEXELS_API_KEY}\""
    echo ""
  fi
  if [ -n "${GROQ_API_KEY}" ]; then
    echo "[groq]"
    echo "api_key = \"${GROQ_API_KEY}\""
    echo ""
  fi
  if [ -n "${RAWG_API_KEY}" ]; then
    echo "[rawg]"
    echo "api_key = \"${RAWG_API_KEY}\""
    echo ""
  fi
} > /app/.streamlit/secrets.toml

exec streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true
