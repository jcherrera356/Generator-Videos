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

## Arquitectura en capas (monolítica)

El código está organizado en capas, cada una en su propia carpeta. Cada capa
solo conoce a las de más abajo (nunca al revés), así que un cambio en una
integración externa (p. ej. cambiar de Pexels a otra API de fotos) no
obliga a tocar la capa de presentación ni la de aplicación.

| Capa | Carpeta | Contiene |
|---|---|---|
| **Presentación** | `presentacion/` | `app.py` (UI de Streamlit) y `cli.py` (entrada por consola, la que usa `generar_video.bat`) |
| **Aplicación** | `aplicacion/` | `generador_pipeline.py` (orquesta todo el proceso de generar un video) y `drive_sync.py` (sincronización con Google Drive, compartida por los dos puntos de entrada) |
| **Dominio** | `dominio/` | `visuals.py` (reglas de dibujo: íconos por categoría, personaje animado) |
| **Servicios** | `servicios/` | Adaptadores a APIs externas: `wikipedia_facts.py`, `rawg_games.py`, `google_trends.py`, `wikimedia_commons.py`, `pexels_photos.py`, `groq_client.py`, `drive_storage.py` |
| **Datos** | `datos/` | `app_config.py`, que lee/escribe el único archivo de configuración local (`.config/config.json`) |

Los archivos de datos/estado (`facts_bank.json`, `used_*.json`, `.config/`,
`output/`, `tmp/`, `music/`) quedan en la raíz del proyecto — son datos y
estado en tiempo de ejecución, no código, así que no forman parte de las
capas.

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
python presentacion\cli.py wikipedia
```

El video queda en la carpeta `output\` (ej. `dato_curioso_2026...mp4`), listo
para revisar y subir tú mismo (o vía la TikTok Content Posting API oficial —
ver sección de subida abajo). Junto a cada video se guarda un archivo `.txt`
del mismo nombre con el título y los hashtags sugeridos para esa publicación
— ábrelo y copia/pega directamente en TikTok al subir el video.

### Sincronizar con Google Drive (opcional, para compartir el registro con la app en la nube)

Si `.config/config.json` tiene la sección `"gdrive"` (ver más abajo "Toda la
configuración en un solo lugar"), entonces cada vez que corras
`generar_video.bat` o `python presentacion\cli.py`:

1. Antes de generar, descarga desde Drive `used_facts.json`,
   `used_wikipedia.json` y `used_games.json` — así no repite un dato que ya
   se usó en la nube (o viceversa).
2. Después de generar, sube el video, su `.txt` de título/hashtags, y los 3
   registros actualizados a esa misma carpeta de Drive.

Si no tiene esa sección, el script sigue funcionando igual que antes, 100%
local, sin tocar Drive.

## De dónde sale cada dato (Wikipedia, banco local, videojuegos o tendencias — sin repetir)

`generador_pipeline.main(source=...)` acepta cuatro fuentes (la app de
Streamlit tiene un botón para cada una, y `generar_video.bat` un menú):

- `"wikipedia"` — un artículo aleatorio de la **API pública de Wikipedia**
  (sin API key). Registro de usados: `used_wikipedia.json`.
- `"local"` — el banco fijo `facts_bank.json` (35 datos escritos a mano).
  Registro: `used_facts.json` (se reinicia solo al agotarlos).
- `"games"` — un videojuego al azar de la **API de RAWG**, con sus propias
  capturas de pantalla reales (ver sección de RAWG más abajo). Registro:
  `used_games.json`.
- `"trending"` — un tema en tendencia **ahora mismo en Google** (últimas 24h,
  Colombia) vía el RSS público de Google Trends, con el dato curioso
  redactado por IA (Groq) a partir del tema y titulares de noticias
  relacionadas. Si el tema es muy ambiguo o no hay contexto suficiente, la
  IA lo descarta y se prueba con el siguiente tema de la lista. Registro:
  `used_trends.json`. Ver `servicios/google_trends.py`.
- `"auto"` (el que usa `python presentacion\cli.py` sin argumentos, por
  `generar_video.bat`) — **50% Wikipedia / 50% banco local**, al azar.

Las cuatro fuentes caen automáticamente al banco local si fallan (sin
internet, sin API key configurada, sin resultados nuevos tras varios
intentos, etc.) — el video nunca falla por esto. Puedes ajustar la
proporción de `"auto"` cambiando `WIKIPEDIA_PROBABILITY` en
`aplicacion/generador_pipeline.py`. Los datos de Wikipedia y de tendencias
usan la categoría `general` para el ícono de respaldo (ver
`dominio/visuals.py`) ya que pueden ser sobre cualquier tema.

### Duración del video (15 a 30 segundos)

Sin importar la fuente, el texto narrado se recorta (respetando oraciones
completas, nunca a media frase) para que el video dure entre 15 y 30
segundos — `trim_to_duration_budget()` y la constante `MAX_SCRIPT_CHARS` en
`aplicacion/generador_pipeline.py` (calibrado a la velocidad real de la voz
`VOICE`). Los datos de RAWG y de tendencias le piden a la IA que redacte 2-3
oraciones bien desarrolladas usando a fondo el contexto que consiguió
(descripción del juego, titulares de noticias, etc.) para apuntar a ese
rango de forma natural, en vez de depender solo del recorte.

### Tendencias (Google Trends)

Usa el RSS público `https://trends.google.com/trending/rss`, el reemplazo
de Google para su antigua función "Daily Trends" (la librería `pytrends` y
su endpoint viejo dejaron de funcionar). Sin API key. Solo trae ~10-20
temas de las últimas 24h, así que una categoría puntual puede no tener nada
casi cualquier día — en ese caso cae al banco local como siempre, el video
nunca falla por esto. El país se fija en la constante `COUNTRY` de
`servicios/google_trends.py` (por defecto `"CO"`, Colombia).

**Categoría**: elegible en `generar_video.bat` (submenú tras elegir
"Tendencias"), en la app de Streamlit (selector), o como segundo argumento
de `python presentacion\cli.py` — Videojuegos, Noticias, Moda,
Entretenimiento, Tecnología, Deportes, Negocios, Salud o Ciencia (lista
completa en `google_trends.CATEGORIES`). Como Google no deja filtrar su RSS
por categoría (se probó con varios parámetros, los ignora todos), la IA
clasifica cada tema al mismo tiempo que redacta el dato y descarta los que
no coincidan.

```powershell
python presentacion\cli.py trending Videojuegos
```

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
  `dominio/visuals.py` (diccionario `_ICON_DRAWERS`).
- `keywords` es el término de búsqueda en **inglés** que se usa para buscar
  las fotos reales en Pexels (las búsquedas en inglés dan mejores resultados
  en su banco de imágenes). Se reutiliza para las varias fotos que van
  apareciendo a lo largo del video (una por oración, hasta 4).

## Fotos reales que cambian a medida que se habla (Wikimedia Commons + Pexels)

Cada video divide el guion por oraciones (hasta 4 tramos) y busca una foto
real distinta para cada una, así la imagen va cambiando junto con lo que se
está diciendo. La primera foto también se usa (borrosa y oscurecida) como
fondo de pantalla completa, para que el fondo tenga que ver con el tema en
vez de ser un degradado genérico. Si no se encuentra ninguna foto, el script
cae automáticamente al ícono ilustrado de la categoría como respaldo — nunca
falla el video por esto. (Los videos de la fuente `"games"` no pasan por
aquí — usan directo las capturas reales de RAWG, ver sección de arriba).

Se busca en dos fuentes, en este orden:

1. **Wikimedia Commons** (`servicios/wikimedia_commons.py`) — el banco de
   imágenes de Wikipedia. Sin API key, sin registro. Es la fuente
   **principal** porque, a diferencia de un banco de fotos de stock, sí
   tiene fotos reales de personas, lugares y eventos específicos (útil sobre
   todo para `"wikipedia"` y `"trending"`, donde el tema suele ser algo muy
   puntual). La mayoría de sus fotos son de uso libre pero piden atribución
   — por eso se agrega automáticamente una línea al `.txt` del video cuando
   las fotos vienen de aquí.
2. **Pexels** (API gratuita) — respaldo para cuando Commons no encuentra
   nada razonable (temas genéricos tipo "océano" o "animales", donde sí
   sobran fotos de stock). Para activarlo (dos minutos, sin tarjeta de
   crédito):

   1. Entra a https://www.pexels.com/api/ y crea una cuenta gratuita.
   2. Copia tu API key gratuita.
   3. Pégala en `.config/config.json` (ver "Toda la configuración en un
      solo lugar" más abajo):
      ```json
      {"pexels_api_key": "TU_API_KEY_AQUI"}
      ```
   El plan gratuito de Pexels permite 200 solicitudes por hora / 20,000 al
   mes, más que suficiente para generar un video por hora.

Si no configuras Pexels, el pipeline sigue funcionando igual — solo usa
Commons, y si tampoco encuentra nada, cae al ícono ilustrado.

## El personaje animado

Cada video presenta un personaje de cuerpo completo dibujado con Pillow
(sin modelos de IA ni GPU): cabeza, torso, brazos y piernas articulados,
con la boca sincronizada al volumen real de la narración y parpadeo
ocasional. Todo esto vive en `dominio/visuals.py`.

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
  editando las constantes `ICON_POS` / `AVATAR_POS` en
  `aplicacion/generador_pipeline.py` (`CHAR_CARD_W` / `CHAR_CARD_H` en
  `dominio/visuals.py` para sus proporciones).

Nota: `visuals.py` y `facts_bank.json` también existen (copiados) en
`..\avatar-live\`, porque el avatar en vivo usa el mismo personaje. Si
cambias el diseño del personaje o agregas datos curiosos aquí, copia los
mismos cambios allá si quieres que se reflejen también en el directo.

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

Y cambia la constante `VOICE` en `aplicacion/generador_pipeline.py`.

## Desplegar en la nube (Streamlit Cloud + Google Drive)

Además de correrlo en tu PC, puedes publicar una versión web con un botón
"Generar video" que funciona desde cualquier navegador, sin tener tu PC
prendido. Los videos y el registro de "no repetir" (`used_facts.json`,
`used_wikipedia.json`) se guardan en una carpeta de **Google Drive** que tú
elijas, para que sobrevivan aunque la app se reinicie en la nube.

> **Qué SÍ hace esto**: generar un video cada vez que tú le das clic al
> botón, desde cualquier lado, y guardarlo en tu Drive.
> **Qué NO hace**: generar solo cada hora sin que tú intervengas (Streamlit
> no es para automatización en segundo plano), ni subir a TikTok (eso se
> hace aparte, manualmente, desde los videos que quedan en tu Drive).

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
5. Descarga el JSON de esa credencial (ícono de descarga) y guárdalo como
   `setup_google_drive/oauth_client.json`.

### Paso 2: Autorizar tu cuenta (una sola vez, en tu PC)

```powershell
cd C:\Users\USUARIO\Documents\GitHub\Generator-Videos
python setup_google_drive\google_drive_auth.py
```

(Este script y `oauth_client.json` viven en `setup_google_drive/` porque
solo hace falta correrlos una vez, o de nuevo si Google invalida el
`refresh_token` — no son parte del pipeline que corre con cada video.)

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

### Paso 4: Subir `.config/config.json` y desplegar

`presentacion/app.py` lee la configuración directo de `.config/config.json`
(lo mismo que usa el `.bat` local) en vez de pedir los Secrets de
Streamlit — así no hay que pegar nada a mano ahí. Para esto:

> ⚠️ **El repo DEBE ser privado.** `.config/config.json` tiene tus API keys
> y, lo más sensible, el `refresh_token` de Google Drive — con eso cualquiera
> tendría acceso a tu carpeta de Drive. Si el repo es público, **no subas
> este archivo** (el `.gitignore` original lo protegía justo por esto).
> Para hacerlo privado: Settings del repo en GitHub → "Danger Zone" →
> "Change visibility" → "Private".

1. Con el repo ya en privado, agrega `.config/config.json` a git (está
   excluido de `.gitignore` a propósito) y súbelo:
   ```powershell
   git add .config/config.json
   git commit -m "Agrega config para Streamlit Cloud"
   git push
   ```
2. Entra a https://share.streamlit.io/ e inicia sesión con tu cuenta de
   GitHub. **"New app"** → autoriza acceso a repos privados si lo pide →
   elige el repositorio `Generator-Videos` → archivo principal:
   `presentacion/app.py` → Deploy. (Si ya tenías esta app desplegada desde
   antes de la reorganización en capas, entra a **Settings → General →
   Main file path** y cámbialo a `presentacion/app.py`).

No hace falta tocar la pestaña "Secrets" para nada.

### Limitaciones a tener en cuenta

- El plan gratuito de Streamlit Cloud tiene CPU/RAM compartida y limitada:
  generar un video puede tardar más ahí que en tu PC (varios minutos en vez
  de segundos/un minuto).
- La app se "duerme" tras un rato sin uso — la primera vez que la abres
  después de dormir tarda unos segundos extra en despertar, es normal.
- El `refresh_token` no expira mientras uses la app regularmente, pero si
  Google lo invalida (por ejemplo si revocas el acceso desde tu cuenta de
  Google), hay que correr `setup_google_drive/google_drive_auth.py` de
  nuevo, actualizar `.config/config.json`, y volver a hacer `git push`.
- Si alguna vez vuelves a hacer el repo público, **saca `.config/config.json`
  de git primero** (`git rm --cached .config/config.json`, agrégalo de
  nuevo al `.gitignore`, y regenera todas las credenciales — el
  `refresh_token` viejo queda en el historial de git para siempre aunque
  borres el archivo).
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
