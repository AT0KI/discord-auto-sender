<div align="center">
  <img src="banner.svg" alt="Discord Auto Sender" width="100%"/>

  <br/>
  <br/>

  <a href="../../releases/latest">
    <img src="https://img.shields.io/github/v/release/ATOKI/discord-auto-sender?style=for-the-badge&logo=github&color=5865F2&labelColor=1e1f22&label=Download" alt="Download"/>
  </a>
  &nbsp;
  <a href="../../releases">
    <img src="https://img.shields.io/github/downloads/ATOKI/discord-auto-sender/total?style=for-the-badge&color=23a55a&labelColor=1e1f22&label=Total+Downloads" alt="Downloads"/>
  </a>
  &nbsp;
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-949ba4?style=for-the-badge&labelColor=1e1f22" alt="License"/>
  </a>
</div>

# Discord Auto Sender

Десктопное приложение для автоматической отправки сообщений в Discord каналы по расписанию.

**Made by ATOKI**

---

## Возможности

- Автоматическая отправка текста и фото в выбранный канал
- Настраиваемый интервал от 1 до 120 минут
- Несколько каналов — переключайся между ними в один клик
- Прогресс-бар и таймер обратного отсчёта до следующей отправки
- Лог всех отправок с временем
- Все настройки сохраняются между запусками
- Поддержка горячих клавиш (Ctrl+A/C/X/V/Z) на любой раскладке клавиатуры
- Тёмная тема в стиле Discord

---

## Установка и запуск

### Вариант 1 — готовый exe
Скачай `discord_sender.exe` из раздела [Releases](../../releases) и запусти.

### Вариант 2 — из исходников

**Требования:** Python 3.8+

```bash
pip install requests Pillow
python discord_sender.py
```

---

## Сборка exe

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=icon.ico --add-data "icon.ico;." discord_sender.py
```

Готовый файл появится в папке `dist/`.

---

## Как получить токен

1. Открой свой профиль на сайте [discord.com](https://discord.com) в браузере
2. Нажми `F12` → вкладка **Network (Сеть)**
3. Обнови страницу — `F5`
4. В строке фильтра введи `/api`
5. Кликни на любой запрос к `discord.com/api/...`
6. Справа открой **Headers → Request Headers**
7. Найди строку `Authorization` — это твой токен

> ⚠️ Не передавай токен третьим лицам — он даёт полный доступ к аккаунту.

---

## Как найти ID канала

1. Discord → **Настройки** (шестерёнка) → **Расширенные**
2. Включи **Режим разработчика**
3. Правой кнопкой на нужный канал → **Копировать ID канала**

---

## Хранение данных

Все настройки сохраняются в:
```
C:\Users\ИМЯ\AppData\Roaming\DiscordAutoSender\config.json
```

---

## Предупреждение

Использование user token для автоматических действий нарушает [правила Discord (ToS)](https://discord.com/terms). Используй на свой страх и риск.

---

## Зависимости

- [requests](https://pypi.org/project/requests/)
- [Pillow](https://pypi.org/project/Pillow/)
