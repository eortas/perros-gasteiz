# 🐾 Perros Gasteiz - Scraper + Bot de Telegram

Scraper automático del listado de perros en adopción del Centro de Protección Animal (CPA) de Vitoria-Gasteiz.

## 🔧 Instalación local

```bash
# Clonar el repo
git clone https://github.com/eortas/perros-gasteiz.git
cd perros-gasteiz

# Instalar dependencias
pip install requests beautifulsoup4 pandas

# Configurar variables de entorno
# Crear un archivo .env (NUNCA subirlo a GitHub):
echo "TELEGRAM_API=tu_bot_token" >> .env
echo "TELEGRAM_CHAT_ID=@tu_canal_o_chat_id" >> .env

# Ejecutar
python scraper.py
```

## 🤖 Notificaciones Telegram

El scraper envía automáticamente:
- 🆕 **Perros nuevos** que aparecen en el catálogo
- ❌ **Perros desaparecidos** (posiblemente adoptados o dados de baja)

### Configurar el bot de Telegram

1. Habla con [@BotFather](https://t.me/BotFather) en Telegram y crea un bot nuevo
2. Obtén el token API (formato: `123456:ABC-DEF...`)
3. Crea un canal o grupo y añade el bot como administrador
4. Obtén el chat ID (por ejemplo, `@micanal` o el ID numérico)
5. Configura los secretos en GitHub → Settings → Secrets and variables → Actions:
   - `TELEGRAM_API` → el token del bot
   - `TELEGRAM_CHAT_ID` → el ID del canal/grupo

## ⏱️ Automatización con GitHub Actions

El workflow `.github/workflows/scrape.yml` se ejecuta manualmente desde la pestaña Actions o mediante una petición externa de cron-job.org.

⚠️ **IMPORTANTE**: Antes del primer despliegue, añade los secretos en GitHub:
1. Ve a tu repositorio en GitHub
2. Settings → Secrets and variables → Actions
3. Añade `TELEGRAM_API` y `TELEGRAM_CHAT_ID`

## 📁 Estructura

```
perros_gasteiz/
├── .env                     # (IGNORADO) Token y chat ID de Telegram
├── .gitignore               # Archivos ignorados por git
├── scraper.py               # Script de scraping principal
├── telegram_bot.py          # Módulo de notificaciones Telegram
├── perros_vitoria_historico.csv  # Histórico de todos los perros detectados
├── fotos_perros/            # (IGNORADO) Fotos descargadas
└── .github/workflows/
    └── scrape.yml           # GitHub Action programado
