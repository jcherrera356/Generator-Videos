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

## Arquitectura en capas (monolítica)

El código está organizado en capas, cada una en su propia carpeta. Cada capa
solo conoce a las de más abajo (nunca al revés), así que un cambio en una
integración externa (p. ej. cambiar de Pexels a otra API de fotos) no
obliga a tocar la capa de presentación ni la de aplicación.

| Capa | Carpeta | Contiene |
|---|---|---|
| **Presentación** | `presentacion/` | `cli.py` (entrada por consola, la que usa `generar_video.bat`) |
| **Aplicación** | `aplicacion/` | `generador_pipeline.py` (orquesta todo el proceso de generar un video) y `drive_sync.py` (sube el video resultante a Google Drive) |
| **Dominio** | `dominio/` | `visuals.py` (reglas de dibujo: íconos por categoría, personaje animado) |
| **Servicios** | `servicios/` | Adaptadores a APIs externas: `wikipedia_facts.py`, `rawg_games.py`, `google_trends.py`, `wikimedia_commons.py`, `pexels_photos.py`, `pixabay_photos.py`, `groq_client.py`, `drive_storage.py`, `sql_database.py`/`usados_db.py` (registro de "no repetir" en SQL Server) |
| **Datos** | `datos/` | `app_config.py`, que lee/escribe el único archivo de configuración local (`.config/config.json`) |

Los archivos de datos/estado (`.config/`, `output/`, `tmp/`, `music/`)
quedan en la raíz del proyecto — son datos y estado en tiempo de ejecución,
no código, así que no forman parte de las capas. El banco de datos
curiosos fijos (antes `facts_bank.json`) y el registro de "no repetir"
viven en SQL Server, no en archivos locales (ver sección de SQL Server más
abajo).

## Toda la configuración en un solo lugar

Todas las API keys y credenciales (Pexels, Groq, RAWG, Google Drive) viven
en **un solo archivo local**, `.config/config.json` (no se sube a git — ver
`app_config.py`), en vez de repartidas en varios archivos sueltos:

```json
{
  "pexels_api_key": "...",
  "groq_api_key": "...",
  "rawg_api_key": "...",
  "sql_server": {
    "server": "...",
    "database": "...",
    "user": "...",
    "password": "..."
  },
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
funcionando sin esa fuente en particular, usando su respaldo normal.

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

### Sincronizar con Google Drive (opcional)

Si `.config/config.json` tiene la sección `"gdrive"` (ver más abajo "Toda la
configuración en un solo lugar"), después de generar cada video
`generar_video.bat` / `python presentacion\cli.py` sube el video y su `.txt`
de título/hashtags a esa carpeta de Drive. Si no tiene esa sección, el
script sigue funcionando igual, 100% local, sin tocar Drive.

(El registro de "no repetir" ya no pasa por Drive — ver la sección de SQL
Server más abajo.)

**Para configurarlo** (una sola vez):

1. En https://console.cloud.google.com/ crea un proyecto (o usa uno
   existente) y habilita la **"Google Drive API"**.
2. Ve a **"Credenciales"** → **"Crear credenciales"** → **"ID de cliente de
   OAuth"** (tipo de aplicación: **"Aplicación de escritorio"**).
   - Si pide configurar antes la "Pantalla de consentimiento", elige tipo
     **"Externo"**, pon cualquier nombre/correo, y déjala en modo "Prueba".
3. Descarga el JSON de esa credencial y guárdalo como
   `setup_google_drive/oauth_client.json`.
4. Corre:
   ```powershell
   python setup_google_drive\google_drive_auth.py
   ```
   Se abre tu navegador — inicia sesión con la cuenta dueña de la carpeta
   de Drive y acepta el permiso. Al terminar, imprime (y guarda en
   `setup_google_drive/gdrive_secrets_RESULTADO.txt`) un bloque `"gdrive"`
   listo para pegar en `.config/config.json`.
5. Completa `folder_id` con el ID de tu carpeta de Drive — lo sacas de su
   URL: `https://drive.google.com/drive/folders/`**`ESTE-ES-EL-ID`**`?usp=sharing`.

(`google_drive_auth.py` y `oauth_client.json` viven en `setup_google_drive/`
porque solo hace falta correrlos una vez, o de nuevo si Google invalida el
`refresh_token` — no son parte del pipeline que corre con cada video.)

## De dónde sale cada dato (Wikipedia, banco local, videojuegos o tendencias — sin repetir)

`generador_pipeline.main(source=...)` acepta cuatro fuentes (`generar_video.bat`
las ofrece en un menú):

- `"wikipedia"` — un artículo aleatorio de la **API pública de Wikipedia**
  (sin API key). Categoría de registro: `wikipedia`.
- `"local"` — el banco fijo guardado en `videosApp.FactsBank` (51 datos
  escritos a mano). Categoría: `facts` (se reinicia sola al agotarlos).
- `"games"` — un videojuego al azar de la **API de RAWG**, con sus propias
  capturas de pantalla reales (ver sección de RAWG más abajo). Categoría:
  `games`.
- `"trending"` — un tema en tendencia **ahora mismo en Google** (últimas 24h,
  Colombia) vía el RSS público de Google Trends, con el dato curioso
  redactado por IA (Groq) a partir del tema y titulares de noticias
  relacionadas. Si el tema es muy ambiguo o no hay contexto suficiente, la
  IA lo descarta y se prueba con el siguiente tema de la lista. Categoría:
  `trends`. Ver `servicios/google_trends.py`.
- `"auto"` (el que usa `python presentacion\cli.py` sin argumentos, por
  `generar_video.bat`) — **50% Wikipedia / 50% banco local**, al azar.

### Base de datos SQL Server (banco de datos + registro de "no repetir")

Dos tablas en el schema `videosApp` (lo agrupa aparte de otras apps que
vivan en el mismo server compartido):

- **`videosApp.FactsBank`** — el banco fijo de datos curiosos (reemplaza
  `facts_bank.json`). Se agrega/edita directo en la base de datos, sin
  tocar código ni hacer commit. Ver `servicios/facts_bank_db.py`.
- **`videosApp.DatosUsados`** — el registro de "no repetir" para las 4
  fuentes (reemplaza los antiguos `used_*.json` + Google Drive, que podían
  perder datos si dos equipos generaban video casi al mismo tiempo y uno
  pisaba el progreso del otro). Ver `servicios/usados_db.py`.

**A propósito, sin respaldo local:** si no hay conexión a SQL (sin
credenciales, sin internet, el server gratuito de somee.com caído, etc.),
el video **no se genera** — se corta con un mensaje de error claro, en vez
de seguir en silencio sin poder leer el banco de datos o registrar lo ya
usado (y arriesgar repetir algo).

Crea el schema y las tablas una sola vez:

```sql
CREATE SCHEMA videosApp;
GO

CREATE TABLE videosApp.FactsBank (
    id NVARCHAR(150) NOT NULL PRIMARY KEY,
    category NVARCHAR(50) NOT NULL,
    keywords NVARCHAR(300) NOT NULL,
    texto NVARCHAR(MAX) NOT NULL,
    fecha_agregado DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
)

CREATE TABLE videosApp.DatosUsados (
    id INT IDENTITY(1,1) PRIMARY KEY,
    categoria NVARCHAR(20) NOT NULL,
    clave NVARCHAR(700) NOT NULL,
    fecha_agregado DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_DatosUsados_categoria_clave UNIQUE (categoria, clave)
)
```

Y agrega las credenciales en `.config/config.json` (ver `"sql_server"` más
arriba).

Las fuentes externas (Wikipedia/RAWG/Trends) siguen cayendo al banco local
(`"local"`) si fallan (sin internet, sin API key configurada, sin resultados
nuevos tras varios intentos, etc.) — eso nunca tumba el video. La única
dependencia dura es SQL Server: sin conexión a la base de datos no hay
banco local al cual caer, así que el video se corta ahí (ver nota de arriba).
Puedes ajustar la
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
nunca falla por esto. El país/alcance se fija en la constante `COUNTRY` de
`servicios/google_trends.py` — por defecto `"GLOBAL"` (temas mundiales, en
cualquier idioma; la IA siempre traduce el dato al español). Cámbiala por
un código de 2 letras (`"CO"`, `"MX"`, `"US"`, etc.) si prefieres un país
puntual.

**Categoría**: elegible en `generar_video.bat` (submenú tras elegir
"Tendencias") o como segundo argumento de `python presentacion\cli.py` —
Videojuegos, Noticias, Moda,
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

Se agregan directo en la tabla `videosApp.FactsBank` (SQL Server) — ya no
hace falta editar ningún archivo ni hacer commit. Desde Python:

```python
from servicios import facts_bank_db
facts_bank_db.add_fact(
    id_="identificador-unico",
    category="espacio",
    keywords="night sky stars",
    text="El dato curioso redactado en un par de frases.",
)
```

O directo en SQL:

```sql
INSERT INTO videosApp.FactsBank (id, category, keywords, texto)
VALUES ('identificador-unico', 'espacio', 'night sky stars', 'El dato curioso redactado en un par de frases.')
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

## Fotos reales que cambian a medida que se habla (Pixabay + Wikimedia Commons + Pexels)

Cada video divide el guion por oraciones (hasta 4 tramos) y busca una foto
real distinta para cada una, así la imagen va cambiando junto con lo que se
está diciendo. La primera foto también se usa (borrosa y oscurecida) como
fondo de pantalla completa, para que el fondo tenga que ver con el tema en
vez de ser un degradado genérico. Si no se encuentra ninguna foto, el script
cae automáticamente al ícono ilustrado de la categoría como respaldo — nunca
falla el video por esto. (Los videos de la fuente `"games"` no pasan por
aquí — usan directo las capturas reales de RAWG, ver sección de arriba).

Se combinan tres fuentes, en este orden, completando entre todas las fotos
que falten (no es "la primera que traiga algo se queda con todo" — si una
fuente trae 1 de las 3 fotos necesarias, las otras 2 fuentes completan el
resto):

1. **Pixabay** (`servicios/pixabay_photos.py`, API gratuita) — fuente
   **principal**. Para evitar que su búsqueda, bastante laxa (puede traer
   una foto que solo coincide en una palabra suelta de varias, ej. buscar
   "deadpool cosplay" y traer una foto etiquetada solo "cosplay" sin
   relación real), se descarta cualquier resultado cuyas etiquetas no
   contengan TODAS las palabras significativas de la búsqueda.
2. **Wikimedia Commons** (`servicios/wikimedia_commons.py`) — el banco de
   imágenes de Wikipedia, sin API key. Completa lo que falte, sobre todo
   útil para personas, lugares y eventos específicos, o personajes de
   franquicias con copyright buscando fotos reales de cosplay/actores en
   vez del personaje con derechos de autor (ver banco local). La mayoría de
   sus fotos son de uso libre pero piden atribución — por eso se agrega
   automáticamente una línea al `.txt` del video cuando las fotos vienen de
   aquí.
3. **Pexels** (API gratuita) — completa lo que aún falte.

Si con la frase completa no alcanza para juntar todas las fotos
necesarias, se vuelve a intentar con cada palabra suelta de la búsqueda por
separado (en las tres fuentes), para sumar variedad en vez de quedarse
corto o repetir.

Para activar Pexels y/o Pixabay (dos minutos cada una, sin tarjeta de
crédito):

- Pexels: https://www.pexels.com/api/ → copia tu API key → en
  `.config/config.json` (ver "Toda la configuración en un solo lugar" más
  abajo): `{"pexels_api_key": "TU_API_KEY_AQUI"}`. Plan gratuito: 200
  solicitudes por hora / 20,000 al mes.
- Pixabay: https://pixabay.com/api/docs/ (crea cuenta, la API key aparece
  arriba de esa misma página) → `{"pixabay_api_key": "TU_API_KEY_AQUI"}`.

No hace falta tener las tres — el pipeline sigue funcionando igual con
cualquier combinación, y si ninguna está configurada o ninguna encuentra
nada, cae al ícono ilustrado.

> ⚠️ **Google Images** no tiene API gratuita real para esto — su "Custom
> Search API" oficial solo da 100 consultas gratis al día (después cobra) y
> requiere configurar un "Programmable Search Engine" en Google Cloud.
> Scrapear Google Images directamente violaría sus términos de servicio, así
> que no se implementó.

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

Nota: `visuals.py` también existe (copiado) en `..\avatar-live\`, porque el
avatar en vivo usa el mismo personaje. Si cambias el diseño del personaje
aquí, copia los mismos cambios allá si quieres que se reflejen también en
el directo. `facts_bank.json` ya no existe en este repo (los datos viven
en `videosApp.FactsBank`, ver arriba) — si `avatar-live` todavía depende de
su propia copia de ese archivo, revisa si sigue sirviéndole tal cual o si
conviene que lea de la misma base de datos.

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

## Nota legal importante

Este proyecto **solo crea** los videos. No incluye (ni se debe agregar)
automatización de subida a TikTok mediante bots, Selenium o librerías no
oficiales, ya que eso viola los Términos de Servicio de TikTok y puede
resultar en el baneo de la cuenta. Para publicar de forma automatizada y
permitida, usa la **TikTok Content Posting API** oficial
(developers.tiktok.com), que requiere registrar una app y pasar la revisión
de TikTok.
