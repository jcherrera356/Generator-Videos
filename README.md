# Generador de videos de datos curiosos

Genera videos verticales (1080x1920) listos para TikTok: voz narrada con IA,
subtítulos sincronizados estilo karaoke, fotos reales que van cambiando a
medida que se habla de cada idea, un fondo de pantalla completa basado en
esa misma foto (borrosa, con movimiento tipo Ken Burns), y un personaje
animado de cuerpo completo — brazos, piernas, ropa al azar — que hace una
acción distinta en cada video (caminar, saludar, señalar la imagen, o
gesticular al hablar), con la boca sincronizada al audio. Al final, sugiere
con IA un **título corto y hashtags** listos para pegar en TikTok. Todo
gratuito: sin costo por video ni claves de pago obligatorias (Pexels y Groq
tienen planes gratuitos permanentes).

> Para el avatar que transmite en vivo en TikTok LIVE, ve a la carpeta
> hermana `..\avatar-live\` (tiene su propio README).

> ¿Quieres generar videos desde el navegador sin tener el PC prendido? Ve a
> la sección **"Desplegar en la nube (Streamlit Cloud + Google Drive)"** más
> abajo.

## Toda la configuración en un solo lugar

Todas las API keys y credenciales (Pexels, Groq, RAWG, Google Drive) viven
en **un solo archivo local**, `.config/config.json` (no se sube a git — ver
`app_config.py`), en vez de repartidas en varios archivos sueltos:

```json
{
  "pexels_api_key": "...",
  "groq_api_key": "...",
  "rawg_api_key": "...",
  "gdrive": {
    "folder_id": "...",
    "client_id": "...",
    "client_secret": "...",
    "refresh_token": "..."
  }
}
```

Puedes omitir cualquier clave que no uses (por ejemplo, si no quieres
sincronizar con Drive, deja fuera `"gdrive"`) — cada parte del pipeline sigue
funcionando sin esa fuente en particular, usando su respaldo normal. En la
nube (Streamlit Cloud o Render), este archivo se arma solo a partir de los
secrets/variables de entorno — no hace falta crearlo a mano ahí.

## Uso

Haz doble clic en `generar_video.bat` — te deja elegir la fuente del dato
(Wikipedia, banco local, videojuegos/RAWG, o automático) con un menú.

También puedes llamarlo directo desde la terminal, pasando la fuente como
argumento (`wikipedia`, `local`, `games` o `auto`, por defecto `auto`):

```powershell
cd C:\Users\USUARIO\Documents\GitHub\Generator-Videos
python generate_video.py wikipedia
```

El video queda en la carpeta `output\` (ej. `dato_curioso_2026...mp4`), listo
para revisar y subir tú mismo (o vía la TikTok Content Posting API oficial —
ver sección de subida abajo). Junto a cada video se guarda un archivo `.txt`
del mismo nombre con el título y los hashtags sugeridos para esa publicación
— ábrelo y copia/pega directamente en TikTok al subir el video.

### Sincronizar con Google Drive (opcional, para compartir el registro con la app en la nube)

Si `.config/config.json` tiene la sección `"gdrive"` (ver más abajo "Toda la
configuración en un solo lugar"), entonces cada vez que corras
`generar_video.bat` o `python generate_video.py`:

1. Antes de generar, descarga desde Drive `used_facts.json`,
   `used_wikipedia.json` y `used_games.json` — así no repite un dato que ya
   se usó en la nube (o viceversa).
2. Después de generar, sube el video, su `.txt` de título/hashtags, y los 3
   registros actualizados a esa misma carpeta de Drive.

Si no tiene esa sección, el script sigue funcionando igual que antes, 100%
local, sin tocar Drive.

## De dónde sale cada dato (Wikipedia, banco local o videojuegos — sin repetir)

`generate_video.main(source=...)` acepta tres fuentes (la app de Streamlit
tiene un botón para cada una):

- `"wikipedia"` — un artículo aleatorio de la **API pública de Wikipedia**
  (sin API key). Registro de usados: `used_wikipedia.json`.
- `"local"` — el banco fijo `facts_bank.json` (35 datos escritos a mano).
  Registro: `used_facts.json` (se reinicia solo al agotarlos).
- `"games"` — un videojuego al azar de la **API de RAWG**, con sus propias
  capturas de pantalla reales (ver sección de RAWG más abajo). Registro:
  `used_games.json`.
- `"auto"` (el que usa `python generate_video.py` sin argumentos, por
  `generar_video.bat`) — **50% Wikipedia / 50% banco local**, al azar.

Las tres fuentes caen automáticamente al banco local si fallan (sin
internet, sin API key configurada, sin resultados nuevos tras varios
intentos, etc.) — el video nunca falla por esto. Puedes ajustar la
proporción de `"auto"` cambiando `WIKIPEDIA_PROBABILITY` en
`generate_video.py`. Los datos de Wikipedia usan la categoría `general`
para el ícono de respaldo (ver `visuals.py`) ya que pueden ser sobre
cualquier tema.

## Videojuegos (API gratuita de RAWG)

Para el botón/fuente `"games"`, cada video trae un juego al azar (de entre
los mejor calificados, para evitar juegos oscuros/poco interesantes), con
su descripción, calificación, Metascore, y **hasta 4 capturas de pantalla
reales del juego** — no se usa Pexels para estos, las imágenes vienen
directo de RAWG.

Para activarlo:

1. Entra a https://rawg.io/apidocs y crea una cuenta gratuita (puedes
   usar "Continue with Steam" si ya tienes cuenta de Steam, es solo un
   método de login más — no es obligatorio ni riesgoso, RAWG es un sitio
   confiable y conocido en la comunidad de videojuegos).
2. Genera tu API key gratuita (hasta 20,000 solicitudes/mes).
3. Pégala en `.config/config.json` (ver "Toda la configuración en un solo
   lugar" más abajo):
   ```json
   {"rawg_api_key": "TU_API_KEY_AQUI"}
   ```

### Nota legal de RAWG (atribución obligatoria)

El plan gratuito de RAWG es para **uso no comercial**, y sus términos
piden mencionar "RAWG" como fuente con un link activo donde se use su
data/imágenes. Por eso cada video de esta fuente agrega automáticamente
una línea de atribución al archivo `.txt` de título/hashtags:
`Datos e imágenes de videojuegos: RAWG (https://rawg.io)` — inclúyela en
la descripción del video al publicarlo. Si tu canal supera 100,000
usuarios activos/mes o 500,000 vistas de página al mes, sus términos
piden contactarlos para un licenciamiento comercial distinto.

## Título y hashtags sugeridos (IA, Groq)

Al terminar cada video, `generate_caption()` le pide a Groq (mismo servicio
usado en `..\avatar-live\`, reutiliza la key de `.config/config.json`) un
título corto y una tanda de hashtags en español basados en el dato del
video, y los guarda en un `.txt` junto al video. Si Groq no responde (sin
API key, sin internet, límite alcanzado), arma un título/hashtags genéricos
con reglas simples — el video se genera igual, solo con una sugerencia más
básica.

Para configurar/cambiar la API key de Groq, edita `.config/config.json` (ver
"Toda la configuración en un solo lugar" más abajo).

## Agregar más datos curiosos

Edita `facts_bank.json` y agrega objetos con este formato:

```json
{"id": "identificador-unico", "category": "espacio", "keywords": "night sky stars", "text": "El dato curioso redactado en un par de frases."}
```

- `category` decide qué ícono ilustrado aparece si no se consigue una foto
  real (ver sección de Pexels). Categorías disponibles: `espacio`, `oceano`,
  `animales`, `insectos`, `cuerpo`, `historia`, `tecnologia`, `clima`,
  `comida`, `general` (bombillo de idea — la usan los datos de Wikipedia).
  Para agregar una categoría nueva, súmale una función de dibujo en
  `visuals.py` (diccionario `_ICON_DRAWERS`).
- `keywords` es el término de búsqueda en **inglés** que se usa para buscar
  las fotos reales en Pexels (las búsquedas en inglés dan mejores resultados
  en su banco de imágenes). Se reutiliza para las varias fotos que van
  apareciendo a lo largo del video (una por oración, hasta 4).

## Fotos reales que cambian a medida que se habla (API gratuita de Pexels)

Cada video divide el guion por oraciones (hasta 4 tramos) y busca una foto
real distinta para cada una, así la imagen va cambiando junto con lo que se
está diciendo. La primera foto también se usa (borrosa y oscurecida) como
fondo de pantalla completa, para que el fondo tenga que ver con el tema en
vez de ser un degradado genérico. Si no hay conexión, no hay clave
configurada, o no se encuentra ninguna foto, el script cae automáticamente al
ícono ilustrado de la categoría como respaldo — nunca falla el video por esto.

Para activarlo (dos minutos, sin tarjeta de crédito):

1. Entra a https://www.pexels.com/api/ y crea una cuenta gratuita.
2. Copia tu API key gratuita.
3. Pégala en `.config/config.json` (ver "Toda la configuración en un solo
   lugar" más abajo):
   ```json
   {"pexels_api_key": "TU_API_KEY_AQUI"}
   ```

El plan gratuito de Pexels permite 200 solicitudes por hora / 20,000 al mes,
más que suficiente para generar un video por hora.

## El personaje animado

Cada video presenta un personaje de cuerpo completo dibujado con Pillow
(sin modelos de IA ni GPU): cabeza, torso, brazos y piernas articulados,
con la boca sincronizada al volumen real de la narración y parpadeo
ocasional. Todo esto vive en `visuals.py`.

- **Ropa al azar**: color de camisa, pantalón, piel y cabello se eligen al
  azar en cada video (ver `random_outfit()` y las listas `SHIRT_COLORS`,
  `PANTS_COLORS`, `SKIN_TONES`, `HAIR_COLORS`).
- **Una acción distinta por video**, elegida al azar entre:
  `camina` (ciclo de caminata con brazos y piernas alternados),
  `saluda` (un brazo se levanta y saluda),
  `senala` (señala hacia la foto/ícono de arriba),
  `explica` (gesticula con ambas manos al hablar).
  La lógica de cada acción (ángulos de brazos/piernas por segundo) está en
  `pose_for_action()`; agregar una acción nueva es sumar una entrada ahí y en
  la lista `ACTIONS`.
- Puedes mover o cambiar el tamaño del personaje y la tarjeta de fotos
  editando las constantes `ICON_POS` / `AVATAR_POS` en `generate_video.py`
  (`CHAR_CARD_W` / `CHAR_CARD_H` en `visuals.py` para sus proporciones).

Nota: `visuals.py` y `facts_bank.json` también existen (copiados) en
`..\avatar-live\`, porque el avatar en vivo usa el mismo personaje. Si
cambias el diseño del personaje o agregas datos curiosos aquí, copia los
mismos cambios allá si quieres que se reflejen también en el directo.

### Sobre el avatar fotorrealista (Wav2Lip) — legado, no usado por defecto

En una iteración anterior de este proyecto se armó un avatar con rostro
sintético (Stable Diffusion) y lip-sync real vía IA (Wav2Lip + GPU, ver
`generate_avatar_face.py`, `lipsync_avatar.py` y la carpeta `avatar_env\`).
Ese avatar es más realista pero **no puede** mover brazos, caminar, ni
cambiar de ropa — solo anima la boca sobre una foto fija. El pipeline
principal (`generate_video.py`) ya **no llama a estos archivos** — usa el
personaje animado de arriba. Quedan aquí por si quieres retomarlos o
combinarlos más adelante (por ejemplo generando el rostro con Wav2Lip y
pegándolo como "cabeza" del personaje animado). `avatar_env\` es un entorno
virtual de Python aparte (con PyTorch) de varios GB — bórralo sin problema
si no piensas usar esta parte.

## Agregar música de fondo (opcional)

Coloca archivos `.mp3` o `.wav` en la carpeta `music\`. El script elige uno al
azar en cada video, lo recorta a la duración de la narración y lo mezcla a bajo
volumen bajo la voz. Si la carpeta está vacía, el video se genera solo con la
narración, sin música.

Usa únicamente música libre de derechos, por ejemplo:
- YouTube Audio Library (studio.youtube.com → Audio Library)
- Pixabay Music (pixabay.com/music)
- Incompetech (incompetech.com)

## Cambiar la voz

El script usa `es-MX-JorgeNeural` por defecto. Para ver todas las voces en
español disponibles:

```powershell
edge-tts --list-voices | findstr "es-"
```

Y cambia la constante `VOICE` en `generate_video.py`.

## Automatizar la generación cada hora (opcional)

Si más adelante quieres que el script corra solo, sin que tengas que
ejecutarlo a mano, se puede registrar como tarea programada de Windows:

```powershell
schtasks /create /sc hourly /mo 1 /tn "GeneradorDatosCuriosos" /tr "powershell.exe -ExecutionPolicy Bypass -File C:\Users\USUARIO\Documents\ChicoTuf\generador-videos\run_hourly.ps1" /st 00:00
```

Esto solo *genera* videos en `output\` cada hora; no sube nada a ninguna
plataforma. Para quitarla:

```powershell
schtasks /delete /tn "GeneradorDatosCuriosos" /f
```

Los logs de cada ejecución quedan en `generation.log`.

## Subir a TikTok (API oficial)

Ya viene listo el flujo para publicar los videos generados usando la
**TikTok Content Posting API** oficial (no un bot, no Selenium — nada que
viole los Términos de Servicio de TikTok).

### Requisitos previos (los haces tú, una sola vez)

1. Entra a https://developers.tiktok.com/, crea una cuenta de desarrollador
   y registra una app.
2. En la configuración de tu app, agrega el producto **"Content Posting
   API"** y anota tu `Client Key` y `Client Secret`.
3. En "Redirect URI" de tu app, registra exactamente:
   `http://localhost:8721/callback`
   (o cambia el puerto en `tiktok_config.json` si ya usas ese puerto para
   otra cosa — deben coincidir los dos lados).
4. Completa `tiktok_config.json` con esos tres datos.

### Autorizar la app (una sola vez)

```powershell
python tiktok_auth.py
```

Esto abre tu navegador para que inicies sesión en TikTok y apruebes los
permisos. Guarda el token en `tiktok_tokens.json` (no lo compartas, da
acceso a publicar en tu cuenta).

### Subir los videos pendientes

```powershell
python upload_to_tiktok.py
```

Revisa la carpeta `output\` y sube todo lo que no se haya subido antes
(lleva registro en `uploaded.json`). Puedes correrlo cuantas veces quieras.

### Importante: modo "Solo yo" hasta que TikTok audite tu app

Mientras tu app no haya pasado la **auditoría** de TikTok for Developers,
la API solo te deja publicar en modo `SELF_ONLY`: el video sube directo a
tu cuenta, pero queda como **borrador privado** que tú mismo revisas y
publicas desde la app de TikTok en tu celular. Esto es una limitación de
TikTok, no de este script — es su forma de evitar spam de apps nuevas sin
revisar. Una vez que sometas tu app a auditoría y sea aprobada, cambias
`PRIVACY_LEVEL` a `"PUBLIC_TO_EVERYONE"` en `upload_to_tiktok.py` y a
partir de ahí sí se publica público y automático de punta a punta.

## Desplegar en la nube (Streamlit Cloud + Google Drive)

Además de correrlo en tu PC, puedes publicar una versión web con un botón
"Generar video" que funciona desde cualquier navegador, sin tener tu PC
prendido. Los videos y el registro de "no repetir" (`used_facts.json`,
`used_wikipedia.json`) se guardan en una carpeta de **Google Drive** que tú
elijas, para que sobrevivan aunque la app se reinicie en la nube.

> **Qué SÍ hace esto**: generar un video cada vez que tú le das clic al
> botón, desde cualquier lado, y guardarlo en tu Drive.
> **Qué NO hace**: generar solo cada hora sin que tú intervengas (Streamlit
> no es para automatización en segundo plano), ni subir a TikTok (esa parte
> sigue siendo solo para tu PC — ver sección de subida más arriba).

> ⚠️ **Nota importante**: la primera versión de esta guía usaba una "cuenta
> de servicio" de Google, pero **Google no permite que las cuentas de
> servicio creen archivos en un Drive personal** (solo tienen cuota de
> almacenamiento en cuentas de Google Workspace con "Shared Drives"). Por
> eso el método correcto de abajo autentica **como tú mismo** en su lugar.

> ⚠️ **Versión de Python**: si la app crashea al arrancar (en los logs se ve
> "Uvicorn server started" y después nada, con el healthcheck fallando con
> "connection reset by peer", sin ningún traceback de Python) revisa la
> versión de Python que está usando: Settings de la app → pestaña General →
> **Python version**. Streamlit Cloud puede asignar por defecto una versión
> muy nueva (ej. 3.14) que tiene bugs de compatibilidad con numpy/pandas/
> pyarrow en este entorno. Bájala a **3.11** y reinicia (Reboot). Un
> `runtime.txt` en el repo con `python-3.11` NO tiene efecto para apps ya
> creadas — hay que cambiarlo desde ahí.

### Paso 1: Crear las credenciales OAuth de Google (una sola vez)

1. Ve a https://console.cloud.google.com/ y crea un proyecto nuevo (o usa
   uno existente).
2. En el buscador de arriba, busca **"Google Drive API"** y haz clic en
   **Habilitar**.
3. Ve a **"Credenciales"** (menú izquierdo) → **"Crear credenciales"** →
   **"ID de cliente de OAuth"**.
   - Si te pide configurar la "Pantalla de consentimiento" primero, elige
     tipo **"Externo"**, pon cualquier nombre, tu correo, y guarda (no hace
     falta publicarla, con dejarla en modo "Prueba" alcanza).
4. Tipo de aplicación: **"Aplicación de escritorio"**. Créala.
5. Descarga el JSON de esa credencial (ícono de descarga) y guárdalo en la
   carpeta del proyecto como `oauth_client.json`.

### Paso 2: Autorizar tu cuenta (una sola vez, en tu PC)

```powershell
cd C:\Users\USUARIO\Documents\GitHub\Generator-Videos
python google_drive_auth.py
```

Se abre tu navegador — inicia sesión con la cuenta dueña de la carpeta de
Drive y acepta el permiso. Al terminar, la terminal imprime algo así:

```
[gdrive]
folder_id = "TU_ID_DE_CARPETA_AQUI"
client_id = "...apps.googleusercontent.com"
client_secret = "..."
refresh_token = "..."
```

**Guarda ese bloque completo**, lo necesitas en el paso 4.

### Paso 3: Compartir la carpeta de Drive y obtener su ID

Si la carpeta ya es tuya (como "Nuevos Videos"), no necesitas compartir
nada — ya es tuya. Solo copia el **ID de la carpeta** desde la URL:

`https://drive.google.com/drive/folders/`**`ESTE-ES-EL-ID`**`?usp=sharing`

Y reemplázalo en el `folder_id` del bloque que copiaste en el paso 2.

### Paso 4: Configurar los Secrets en Streamlit Cloud

1. Entra a https://share.streamlit.io/ e inicia sesión con tu cuenta de
   GitHub. **"New app"** → elige el repositorio `Generator-Videos` →
   archivo principal: `app.py` → Deploy.
2. Desde el panel de la app → **"Settings" → "Secrets"**, pega:

   ```toml
   [gdrive]
   folder_id = "EL-ID-DE-TU-CARPETA"
   client_id = "EL-CLIENT-ID-DEL-PASO-2"
   client_secret = "EL-CLIENT-SECRET-DEL-PASO-2"
   refresh_token = "EL-REFRESH-TOKEN-DEL-PASO-2"

   [pexels]
   api_key = "TU_API_KEY_DE_PEXELS"

   [groq]
   api_key = "TU_API_KEY_DE_GROQ"

   [rawg]
   api_key = "TU_API_KEY_DE_RAWG"
   ```

   (Las API keys son las mismas que ya tienes en `.config/config.json` —
   ábrelo y copia el valor de cada una.)

3. Guarda los secrets — la app se reinicia sola y queda lista.

### Limitaciones a tener en cuenta

- El plan gratuito de Streamlit Cloud tiene CPU/RAM compartida y limitada:
  generar un video puede tardar más ahí que en tu PC (varios minutos en vez
  de segundos/un minuto).
- La app se "duerme" tras un rato sin uso — la primera vez que la abres
  después de dormir tarda unos segundos extra en despertar, es normal.
- El `refresh_token` no expira mientras uses la app regularmente, pero si
  Google lo invalida (por ejemplo si revocas el acceso desde tu cuenta de
  Google), hay que correr `google_drive_auth.py` de nuevo y actualizar el
  secret en Streamlit.
- Nunca subas `oauth_client.json` a GitHub — ya está en el `.gitignore`,
  pero verifícalo si algo falla.

## Nota legal importante

Este proyecto **solo crea** los videos. No incluye (ni se debe agregar)
automatización de subida a TikTok mediante bots, Selenium o librerías no
oficiales, ya que eso viola los Términos de Servicio de TikTok y puede
resultar en el baneo de la cuenta. Para publicar de forma automatizada y
permitida, usa la **TikTok Content Posting API** oficial
(developers.tiktok.com), que requiere registrar una app y pasar la revisión
de TikTok.
