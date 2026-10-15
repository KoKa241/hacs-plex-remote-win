# Plex PC Remote

Локальный пульт для **Plex HTPC на Windows 10/11**: Python-сервер на компьютере + интеграция Home Assistant + карточка пульта + экспорт телевизора в Apple Home через HomeKit Bridge.

**Питание управляет только приложением Plex.** Первое нажатие открывает Plex HTPC, следующее закрывает. Выключения, сна, перезагрузки и Wake-on-LAN в проекте нет. Plex Media Server не закрывается.

## Что есть

- Стрелки, OK/Enter, назад/Esc, главная, информация.
- Play/Pause, отдельные Play и Pause, Stop, перемотка ±10 секунд, предыдущий/следующий элемент.
- Громкость **внутри Plex**, mute, субтитры, смена аудиодорожки, полный экран.
- Реальный статус процесса, обновление каждые 5 секунд и сразу после команды.
- Настройка URL и токена через интерфейс HA, повторная настройка при изменении IP/токена.
- `media_player` с классом `tv` и `remote`, объединённые в одно устройство.
- Кнопки навигации Apple Remote обрабатываются автоматически, только для соответствующей TV-сущности.

Это управление клавиатурой, поэтому название фильма, позиция, фактическая пауза и уровень громкости не считываются. Сущность показывает `on`/`off`, а при недоступном сервере — `unavailable`. Уровень громкости и состояние mute не выдумываются: используются кнопки. При passthrough звука громкость может регулироваться только ресивером.

## 1. Windows-сервер

Нужны Python 3.11+ и **Plex HTPC**. Обычный Plex for Windows и браузерная версия этим профилем не поддерживаются. Запустите Plex HTPC хотя бы один раз, войдите в аккаунт и закройте приложение перед установкой раскладки.

Скопируйте проект, например, в `C:\PlexRemote`. В PowerShell:

```powershell
cd C:\PlexRemote
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r server\requirements.txt
.\.venv\Scripts\python.exe -m server.setup
.\.venv\Scripts\python.exe -m server.app
```

Если Plex установлен в другом месте:

```powershell
.\.venv\Scripts\python.exe -m server.setup --plex-path "D:\Apps\Plex HTPC\Plex HTPC.exe"
```

Установщик создаёт `server/config.json` с уникальным ID компьютера и случайным API-токеном. Скопируйте токен в настройку интеграции HA. Файл исключён из Git; не публикуйте его. При повторном запуске setup существующий конфиг сохраняется — путь тогда меняйте непосредственно в нём.

Setup устанавливает `server/keyboard.json` в `%LOCALAPPDATA%\Plex HTPC\inputmaps\keyboard.json`. Существующий файл сохраняется рядом как `keyboard.backup-….json.bak`. Используется своя раскладка: F1–F12 и Ctrl+F1–F4 для команд, стрелки/Enter/Esc для навигации. Она заменяет пользовательские сочетания; при необходимости объедините их вручную с резервной копией. После изменения раскладки перезапустите Plex.

Разрешите входящий TCP **8321** только от IP Home Assistant. Пример команды в PowerShell администратора (замените IP):

```powershell
New-NetFirewallRule -DisplayName "Plex PC Remote from HA" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8321 -RemoteAddress 192.168.1.20 -Profile Private
```

API использует Bearer-токен и обычный HTTP: это вариант для доверенной домашней сети. Не пробрасывайте порт в интернет. Для внешнего доступа используйте доступ к самому Home Assistant/VPN. Интеграция также принимает HTTPS URL, если вы настроите TLS-прокси.

### Автозапуск

Сначала проверьте запуск сервера в консоли. Затем остановите его Ctrl+C и выполните от обычного пользователя:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\register-startup.ps1
Start-ScheduledTask -TaskName "Plex PC Remote"
```

Задача запускается **при входе пользователя**. Сервер должен работать в интерактивном сеансе того же пользователя, что и Plex, с одинаковыми правами; не устанавливайте его как Windows Service. Заблокированный экран, UAC и отключённый RDP-сеанс могут препятствовать управлению. Если Windows запрещает активацию окна, команда вернёт ошибку; активируйте Plex локально и повторите.

Удалить автозапуск:

```powershell
Unregister-ScheduledTask -TaskName "Plex PC Remote" -Confirm:$false
```

При закрытии сервер сначала отправляет WM_CLOSE окнам выбранного Plex HTPC.exe. Через 5 секунд он завершает оставшиеся процессы **этого же исполняемого файла**, если приложение не закрылось самостоятельно.

## 2. Home Assistant

Поддерживаемая минимальная версия HA: **2025.6**.

### Сейчас: ручная установка

1. Скопируйте `custom_components/plex_pc_remote` в `/config/custom_components/plex_pc_remote` на HA.
2. Перезапустите Home Assistant.
3. Настройки → Устройства и службы → Добавить интеграцию → **Plex PC Remote**.
4. Введите `http://IP_КОМПЬЮТЕРА:8321` и токен из `server/config.json`.
5. В устройстве появятся TV и Remote. Обычно их ID: `media_player.plex_pc_tv` и `remote.plex_pc_remote`; проверьте фактические ID.

Закрепите IP компьютера в DHCP. Изменить адрес/токен можно в меню интеграции → Перенастроить. При недоступном компьютере HA повторяет подключение, но не включает компьютер.

### Установка через HACS

1. В HACS откройте меню → Пользовательские репозитории.
2. Добавьте `https://github.com/KoKa241/hacs-plex-remote-win` с типом **Integration**.
3. Найдите **Plex PC Remote**, скачайте и перезапустите Home Assistant.
4. Добавьте интеграцию через Настройки → Устройства и службы, укажите URL Windows-сервера и токен.

Это пользовательский репозиторий HACS; добавление в общий каталог не выполнялось. Windows-сервер устанавливается отдельно: HACS скачивает только интеграцию. Карточку добавьте по инструкции ниже.

## 3. Карточка пульта

Откройте `examples/remote-card.yaml`. Замените оба entity_id, если HA присвоил другие имена. Панель HA → Редактировать → Добавить карточку → Вручную → вставьте содержимое файла. Файл в JSON-синтаксисе, который также является допустимым YAML.

Карточка использует только стандартные tile/grid/button — дополнительных карточек из HACS не нужно. Она **не добавляется автоматически** в ваши существующие панели. Верхняя плитка показывает состояние, кнопка «Питание» делает атомарный toggle на сервере, не полагаясь на устаревшее состояние HA.

Для автоматизации можно вызвать:

```yaml
action: remote.send_command
target:
  entity_id: remote.plex_pc_remote
data:
  command: back
```

Все команды: `turn_on`, `turn_off`, `toggle`, `focus`, `up`, `down`, `left`, `right`, `select`, `back`, `home`, `info`, `play_pause`, `play`, `pause`, `stop`, `seek_backward`, `seek_forward`, `previous`, `next`, `volume_down`, `volume_up`, `mute`, `subtitles`, `audio`, `fullscreen`.

`num_repeats` поддерживает 1–20 повторов, `delay_secs` — 0–5 секунд; удержание клавиши не поддерживается. Повторы `toggle`/`mute` будут переключать состояние несколько раз, поэтому используйте их осознанно.

## 4. Apple Home / HomeKit

1. В Home Assistant добавьте **HomeKit Bridge**.
2. Перед сопряжением выберите в параметрах режим **Accessory** и единственную сущность `media_player.plex_pc_tv` (ваш фактический ID).
3. Добавьте аксессуар в приложении «Дом» по QR-коду HA.
4. Откройте пульт Apple TV в Пункте управления iPhone и выберите Plex PC.

Альтернатива настройки YAML — `examples/homekit.yaml`. Выберите UI или YAML, не создавайте два аксессуара для одной сущности.

В «Доме» будет телевизор: включение открывает Plex, выключение закрывает. Стрелки, OK, назад и доступные дополнительные кнопки пульта iPhone передаются через события HomeKit. Play/Pause и громкость идут через стандартные действия media_player. Дополнительная автоматизация не требуется. Набор видимых кнопок зависит от iOS; субтитры, дорожки и полный экран доступны в карточке HA. Это не AirPlay-приёмник.

См. [официальную документацию HomeKit Bridge](https://www.home-assistant.io/integrations/homekit/): телевизору нужен режим Accessory; управление пультом доступно в Пункте управления.

## Проверка и диагностика

На Windows проверить API без команды:

```powershell
$config = Get-Content .\server\config.json | ConvertFrom-Json
Invoke-RestMethod http://127.0.0.1:8321/api/status -Headers @{Authorization="Bearer $($config.token)"}
```

- `401`: токен не совпадает.
- `409`: Plex закрыт, не готов или Windows не позволяет отправить ввод.
- `503`: ошибка Windows; смотрите `server/config.log` (журнал с ротацией).
- HA показывает `unavailable`: проверьте сервер, IP, частный профиль сети и firewall.
- Стрелки работают, дополнительные кнопки нет: проверьте установку inputmap и перезапустите Plex HTPC.
- Громкость не меняется: проверьте audio passthrough и управление громкостью ресивера.

Локальные автоматические проверки:

```sh
python -m pip install -r requirements-dev.txt
python -m pytest
ruff check .
```

Тесты проверяют API, авторизацию, запрет посторонних команд, последовательность переключений и отказ отправки клавиш без фокуса на тестовом backend. Реальные Win32-вызовы, Plex HTPC, загрузку в HA и сопряжение с iPhone нужно проверить на целевых устройствах; текущая среда разработки — macOS.

Документация: [Plex HTPC Input Maps](https://support.plex.tv/articles/plex-htpc-input-maps/), [Media player entity](https://developers.home-assistant.io/docs/core/entity/media-player/), [требования HACS](https://www.hacs.xyz/docs/publish/integration/).
