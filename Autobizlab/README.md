# Autobizlab

Контур для публичного сайта с формой заявки на услуги, REST API на FastAPI, хранением данных в PostgreSQL и вспомогательными сервисами (pgAdmin, приватный Docker Registry, автообновление образов через Watchtower). Весь внешний трафик на приложение и API идёт через **один Nginx** на порту **80**.

## Содержание

- [Архитектура](#архитектура)
- [Требования](#требования)
- [Быстрый старт](#быстрый-старт)
- [Переменные окружения](#переменные-окружения)
- [Фронтенд](#фронтенд)
- [Бэкенд и API](#бэкенд-и-api)
- [Куда попадают заявки](#куда-попадают-заявки)
- [pgAdmin](#pgadmin)
- [Docker Registry](#docker-registry)
- [Watchtower](#watchtower)
- [Скрипты и миграции](#скрипты-и-миграции)
- [Безопасность и продакшен](#безопасность-и-продакшен)
- [Устранение неполадок](#устранение-неполадок)

## Архитектура

```mermaid
flowchart LR
  subgraph edge["Сеть edge"]
    Client[Клиент]
    Nginx[Nginx :80]
    Registry[Registry :5000]
    Watchtower[Watchtower]
  end
  subgraph internal["Сеть app_internal (internal)"]
    Backend[FastAPI backend :8080]
    Postgres[(PostgreSQL)]
    PgAdmin[pgAdmin]
  end
  Client --> Nginx
  Nginx -->|"/ статика"| Dist[frontend/dist]
  Nginx -->|"/api/"| Backend
  Nginx -->|"/docs, /openapi.json"| Backend
  Nginx -->|"/pgadmin/"| PgAdmin
  Nginx -->|"/v2/"| Registry
  Backend --> Postgres
  PgAdmin --> Postgres Watchtower -.->|обновление по меткам| Nginx
```

| Сервис        | Назначение |
|---------------|------------|
| **nginx**     | Статика сайта, прокси на API, pgAdmin, Registry (`/v2/`). |
| **backend**   | FastAPI (Uvicorn), порт 8080 **только внутри** compose. |
| **postgres**  | БД; порт **не** публикуется наружу. |
| **postgres-ensure-user** | Одноразовый контейнер при `up`: синхронизация роли с `POSTGRES_USER`. |
| **pgadmin**   | Веб-админка БД за Nginx: `/pgadmin/`. |
| **registry**  | Docker Distribution 2.x, базовая auth через `htpasswd`. |
| **watchtower**| Опционально обновляет образы с меткой `com.centurylinklabs.watchtower.enable=true`. |

## Требования

- Docker и Docker Compose v2
- Для сборки фронтенда: **Node.js 18+** и **npm**

## Быстрый старт

1. Склонируйте репозиторий и перейдите в каталог проекта.

2. Создайте файл окружения:

   ```bash
   cp .env.example .env
   ```

   Отредактируйте `.env`: задайте надёжные пароли и при необходимости имя БД и пользователя PostgreSQL.

3. Соберите фронтенд (Nginx монтирует **`frontend/dist`**):

   ```bash
   cd frontend
   npm ci
   npm run build
   cd ..
   ```

   Убедитесь, что после сборки существует каталог `frontend/dist` с `index.html`.

4. Запустите стек:

   ```bash
   docker compose --env-file .env up -d
   ```

5. Проверьте:

   - Сайт: `http://<хост>/`
   - Здоровье API: `http://<хост>/api/v1/health`
   - Документация API: `http://<хост>/docs` или `/redoc`

## Переменные окружения

Файл **`.env`** (шаблон — **`.env.example`**) используется Compose для подстановки в сервисы.

| Переменная | Где используется | Описание |
|------------|------------------|----------|
| `POSTGRES_USER` | postgres, backend, скрипт ensure-user | Пользователь БД. |
| `POSTGRES_PASSWORD` | postgres, backend, ensure-user | Пароль БД (обязателен). |
| `POSTGRES_DB` | postgres, backend | Имя базы данных. |
| `PGADMIN_DEFAULT_EMAIL` | pgadmin | Логин в веб-интерфейс pgAdmin. |
| `PGADMIN_DEFAULT_PASSWORD` | pgadmin | Пароль pgAdmin. |

**Важно:** в **`pgadmin/servers.json`** должны совпадать хост (всегда `postgres` внутри compose), имя БД (`MaintenanceDB`), пользователь (`Username`) и логика паролей с вашим `.env`. Если вы меняете `POSTGRES_USER` или `POSTGRES_DB`, обновите `servers.json` и при первом подключении в pgAdmin введите пароль из `POSTGRES_PASSWORD`.

Файл **`.env`** и **`registry/auth/htpasswd`** в репозитории не коммитятся (см. `.gitignore`).

## Фронтенд

- Расположение: **`frontend/`**
- Стек: **Vite 6**, **React 19**, **TypeScript**
- Продакшен-сборка выводится в **`frontend/dist/`**

Команды:

```bash
cd frontend
npm ci          # установка зависимостей
npm run dev     # разработка с hot-reload (Vite)
npm run build   # tsc + vite build → dist/
npm run preview # локальный просмотр собранного dist
```

### Переменные сборки (Vite)

При необходимости задайте ключ конфигурации сайта для подгрузки опций с API (бюджет-слайдер, список услуг):

```bash
VITE_ADMIN_CONFIG_KEY=your_config_key npm run build
```

По умолчанию используется ключ `default`. Запрос идёт на `GET /api/v1/admin-config/by-key/<ключ>`. Если конфиг не найден, форма работает со статическими подсказками.

Форма отправляет **`POST /api/v1/leads`** JSON в формате, описанном в бэкенде (`LeadSubmitPayload`: поля формы + технические метрики браузера).

## Бэкенд и API

- Расположение: **`backend/`**
- **Python 3.12**, **FastAPI**, **SQLAlchemy**, **PostgreSQL** (драйвер в URL: `postgresql+psycopg://…`)
- При старте приложения вызывается `create_all` для моделей (таблицы создаются при необходимости).

Базовые префиксы (снаружи те же пути через Nginx):

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/health` | Проверка работоспособности. |
| POST | `/api/v1/leads` | Приём заявки: форма + метрики в одной транзакции. |
| GET | `/api/v1/leads` | Список заявок (пагинация `skip`, `limit`). |
| GET/PATCH/DELETE | `/api/v1/leads/{id}` | Чтение, частичное обновление, удаление заявки. |
| … | `/api/v1/lead-metrics/…` | Метрики поведения, привязанные к лиду. |
| … | `/api/v1/admin-config/…` | CRUD/upsert конфигурации сайта (услуги, диапазон бюджета, extra UI). |

Полная схема запросов и ответов доступна в **Swagger**: `http://<хост>/docs`.

## Куда попадают заявки

Заявки **сохраняются в PostgreSQL** (таблица заявок и связанные метрики). **Отправки на e-mail в коде нет** — адрес в `PGADMIN_DEFAULT_EMAIL` это только учётная запись pgAdmin, а не «ящик для заявок». Для уведомлений на почту нужно отдельно реализовать рассылку (или внешнюю интеграцию).

## pgAdmin

- URL: `http://<хост>/pgadmin/`
- Учётные данные из `.env`: `PGADMIN_DEFAULT_EMAIL`, `PGADMIN_DEFAULT_PASSWORD`
- Преднастройка сервера: **`pgadmin/servers.json`**. При `PGADMIN_REPLACE_SERVERS_ON_STARTUP=True` список серверов при старте контейнера приводится к этому файлу.

## Docker Registry

- Клиент обращается к registry через **тот же хост и порт 80**, путь **`/v2/`** (Nginx проксирует на контейнер registry).
- Учётные записи: файл **`registry/auth/htpasswd`** (формат Apache `htpasswd`).

Пример (на машине с Docker):

```bash
docker login http://<ваш_хост>
docker tag myapp:latest <ваш_хост>/project/myapp:latest
docker push <ваш_хост>/project/myapp:latest
```

Добавить пользователя на хосте, где есть `htpasswd`:

```bash
htpasswd -B registry/auth/htpasswd <имя_пользователя>
```

При **HTTP без TLS** на клиенте Docker может понадобиться `insecure-registries` в `/etc/docker/daemon.json` (см. комментарии в `.env.example`).

## Watchtower

Сервис **watchtower** (образ `nickfedor/watchtower`) следит за контейнерами с меткой `com.centurylinklabs.watchtower.enable=true` и может подтягивать новые образы. Registry и сам watchtower помечены как `enable=false`, чтобы их не обновлять автоматически без явного намерения.

## Скрипты и миграции

В каталоге **`scripts/`** лежат вспомогательные shell/SQL-скрипты, в том числе:

- **`ensure-postgres-user.sh`** — используется сервисом `postgres-ensure-user` в Compose.
- SQL-файлы для ручных изменений схемы (например, под админ-конфиг), если вы их применяете вручную к БД.

Перед применением SQL убедитесь в бэкапе и в том, что скрипт соответствует текущей версии схемы.

## Безопасность и продакшен

- Не коммитьте `.env` и файлы с паролями registry.
- В продакшене рекомендуется **TLS** (отдельный reverse-proxy или сертификаты на Nginx), сильные пароли БД и pgAdmin.
- БД и backend **не** должны быть доступны из интернета напрямую; проект рассчитан на доступ через Nginx.
- Ограничьте доступ к `/docs` и `/redoc` при публичном деплое, если не хотите светить API.

## Устранение неполадок

| Симптом | Что проверить |
|---------|----------------|
| Пустая страница или404 на `/` | Выполнен ли `npm run build`, существует ли `frontend/dist/index.html`, смонтирован ли том `./frontend/dist` в nginx. |
| Ошибка при `POST /api/v1/leads` | Логи `docker compose logs backend`, доступность postgres, корректность `DATABASE_URL`. |
| pgAdmin не видит сервер / ошибка подключения | Соответствие `servers.json` и `.env` (имя БД, пользователь, пароль при подключении). |
| Healthcheck postgres сыпет FATAL в логах | Часто несовпадение `POSTGRES_USER` в `.env` и пользователя, созданного при первом init тома; см. комментарии в `docker-compose.yml` и скрипт ensure-user. |
| `docker push` к registry не работает | Логин, `htpasswd`, при HTTP — `insecure-registries`, прокси Nginx для `/v2/`. |

---

Лицензия и контакты проекта укажите здесь при необходимости.
