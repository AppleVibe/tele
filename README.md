# tele-ru

[🇷🇺 Русский](README.md) · [🇬🇧 English](README.en.md)

Русская сборка [tele](https://github.com/nitreojs/tele) — форка Telegram Desktop.

Этот репозиторий — не самостоятельный форк, а **очередь патчей** поверх [tdesktop](https://github.com/telegramdesktop/tdesktop): тег апстрима зафиксирован в `UPSTREAM`, поверх него накатываются патчи из `patches/`, и всё это собирается в GitHub Actions.

Взяли [nitreojs/tele](https://github.com/nitreojs/tele) и добавили то, чего в нём не было:

- **русский интерфейс** для всего, что tele добавляет к Telegram Desktop — страницы настроек, названия и описания опций, меню, диалоги, уведомления;
- **свои ссылки и ключ обновлений** — приложение обновляется из этого репозитория, а не из авторского;
- **пустой адрес сервера tele по умолчанию** — чтобы отчёты о падении и бейджи по умолчанию никуда не уходили.

Сам Telegram Desktop остаётся английским: переводятся только надстройки tele. Язык включается сам, если в Telegram выбран русский (`Настройки → Язык`), и выключается при любом другом.

## Скачать

Последнюю сборку берём из [релизов](../../releases/latest). Они не трогают установленный Telegram и его данные.

| платформа | файл | что делать |
| --- | --- | --- |
| Linux x64 | `tele-<версия>-linux64.zip` | распаковать туда, куда есть запись (например `~/.local/opt/tele`), и запустить `./tele`. Данные идут в `~/.local/share/tele`, приложение добавляет себя в меню. |
| Windows x64 | `tele-<версия>-win64.zip` | распаковать в любое место и запустить `tele.exe`. Данные хранятся рядом с exe, приложение добавляет себя в меню «Пуск». |
| macOS (Apple Silicon и Intel) | `tele-<версия>-macos.dmg` | перетащить в «Программы» и один раз выполнить команду ниже: сборка не нотаризована. Данные идут в `~/Library/Application Support/tele`. |

```bash
xattr -dr com.apple.quarantine /Applications/tele.app
```

### Linux Mint / Ubuntu

```bash
mkdir -p ~/.local/opt/tele
unzip tele-*-linux64.zip -d ~/.local/opt/tele
chmod +x ~/.local/opt/tele/tele
~/.local/opt/tele/tele
```

Первый запуск создаёт ярлык в меню приложений. Если не хватает библиотек, доустановите зависимости сборки Telegram Desktop:

```bash
sudo apt install libgl1 libxcb-cursor0 libxkbcommon-x11-0 libxcb-icccm4 libxcb-keysyms1 \
  libxcb-shape0 libxcb-xinerama0 libxcb-render-util0 libdbus-1-3 libopenh264-7
```

## Обновления

Приложение само проверяет релизы этого репозитория раз в 3 часа, скачивает новую сборку в фоне и предлагает перезапуститься. Фид подписан ключом ed25519, поэтому сборка не из этого репозитория не установится. Отключается в `Настройки → tele → Обновления`.

Первую сборку нужно поставить вручную: автообновление подхватывается со следующей. В установленном клиенте автора вшиты его ключ и его адрес — они не могут скачать эту сборку.

## Что переведено

Перевод работает через один модуль — `tele/tele_i18n.cpp`. Все строки tele проходят через `Tele::Lower()`, и там же подставляется русский текст. Около 1700 строк: страницы и группы настроек, все опции tele с описаниями, пункты меню, диалоги, уведомления, ошибки.

Если строки нет в таблице, показывается английский оригинал — приложение не ломается и не показывает пустоту.

## Сборка

Сборка полностью в GitHub Actions:

- **Build** — на каждый push в `main` собирает Windows, Linux и macOS и публикует релиз;
- **Sync** — раз в 3 часа проверяет новый релиз tdesktop и открывает issue, если патчи перестали накатываться.

### Секреты репозитория

| секрет | зачем |
| --- | --- |
| `TDESKTOP_API_ID` | `api_id` с [my.telegram.org](https://my.telegram.org) — **свой**, чужие использовать нельзя |
| `TDESKTOP_API_HASH` | `api_hash` оттуда же |
| `TELE_UPDATE_KEY` | приватный ключ ed25519, которым подписывается фид автообновления |
| `TELE_BOT_TOKEN` | необязательно: бот для уведомлений о сборках |
| `TELE_NOTIFY_CHAT` | необязательно: куда эти уведомления слать |

Публичная половина ключа лежит в `ci/update-public-key.pem` и вшита в `tele/tele_updater.cpp`. Если менять ключ — менять в трёх местах сразу, иначе обновления перестанут устанавливаться.

### Локальная сборка

```bash
git clone https://github.com/AppleVibe/tele-ru.git
git clone https://github.com/telegramdesktop/tdesktop.git
cd tele-ru
python3 tele.py checkout
```

Дальше — по документации самого tdesktop для вашей платформы (`docs/building-linux.md` из тега в `UPSTREAM`). Конфигурировать с `-D DESKTOP_APP_DISABLE_AUTOUPDATE=ON`, `TELE_BUILD` оставить `0`.

### Как поправить перевод

1. `python3 tele.py checkout` — развернуть дерево tdesktop;
2. править `Telegram/SourceFiles/tele/tele_i18n.cpp` в дереве tdesktop (не патч руками);
3. закоммитить с `feat:` или `fix:`;
4. `python3 tele.py export` — патчи перегенерируются;
5. запушить.

## Структура

```
UPSTREAM                      тег tdesktop, на который накатываются патчи
patches/tdesktop/*.patch      патчи к самому tdesktop
patches/Telegram/lib_ui/      патчи к сабмодулю
tele.py                       checkout / continue / export / apply
ci/                           сборка, релизы, подписи, заметки
.github/workflows/            build, sync, canary, promote, announce
```

## Благодарности

- [telegramdesktop/tdesktop](https://github.com/telegramdesktop/tdesktop) — основа, из которой собирается каждая сборка.
- [nitreojs/tele](https://github.com/nitreojs/tele) — форк, взятый за основу. Вся функциональность tele — его работа; здесь добавлен русский интерфейс и переключены ссылки обновлений.
- **Перевод на русский язык** — [@acaff](https://t.me/acaff): меню и подменю tele, названия и описания всех настроек.
- [materialgram](https://github.com/kukuruzka165/materialgram), [freshGram](https://github.com/Snowy-Fluffy/freshGram) — идеи, которые tele вобрал в себя.

## Лицензия

Как и у tdesktop и tele — GPL-3.0 с дополнительными исключениями. См. `LEGAL` в исходниках tdesktop.

---

Русская сборка и перевод: [@acaff](https://t.me/acaff) · [AppleVibe](https://github.com/AppleVibe).
Если строка осталась английской или переведена криво — пишите в [issues](../../issues) или в телеграм.
