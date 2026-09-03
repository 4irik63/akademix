import os

# Токен бота — берём из переменной окружения BOT_TOKEN.
# Никогда не вписывайте токен прямо в код, если планируете выкладывать
# проект в открытый репозиторий (GitHub и т.п.).
BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_YOUR_TOKEN_HERE")

# ID чатов администраторов, между которыми распределяются заказы.
# Указывайте через запятую, например: "111111111,222222222"
# Узнать свой числовой ID можно через бота @userinfobot.
_admin_ids_raw = os.getenv("ADMIN_CHAT_IDS", "")
ADMIN_CHAT_IDS = [int(x.strip()) for x in _admin_ids_raw.split(",") if x.strip()]

# Путь к файлу базы данных SQLite
DB_PATH = os.getenv("DB_PATH", "orders.db")
