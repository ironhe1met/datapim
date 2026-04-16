# Problems Log — DataPIM

Відомі граблі та їх фікси. Один рядок на проблему.

Формат: `YYYY-MM-DD | <симптом> | <фікс> | #тег #тег`

Перед початком будь-якої роботи на цьому проєкті — `grep` по цьому файлу
по ключових словах задачі.

Якщо проблема повторюється в кількох проєктах — винеси її в
`data/problems/<pipeline>.md` через `/problem promote`.

---

<!-- Приклади:
2026-04-08 | docker-compose не бачив .env в subdir | env_file: ../.env | #docker #compose
2026-04-08 | nginx 502 на /api | upstream був http:// замість unix: | #nginx #upstream
-->

2026-04-15 | категорія "протікає" з enriched у BUF блок | фікс: додано `buf_category_id` + `custom_category_id` колонки, resolved = custom ?? buf; BUF блок показує buf_category, форма і sidebar — resolved | #override-pattern #migration
2026-04-15 | фоновий XML-імпорт завис мовчки | причини: (1) uktzed String(50) переповнювався → StringDataRightTruncationError → вся транзакція rollback; (2) error_details містив datetime у raw dict → JSONB serialization fail. Фікс: міграція VARCHAR(255) + прибрано raw з errors (тільки id/sku/name) | #import #migration
2026-04-15 | FastAPI BackgroundTasks exception → silent failure | коли background coroutine кидає exception, він тільки логається в stderr (не в DB). Для довгих операцій треба обгортати всю логіку в try/except і записувати в ImportLog.status=failed перед re-raise | #background-task #error-handling
2026-04-16 | Ubuntu 20.04 (focal): `curl get.docker.com` не знаходить `docker-model-plugin` | пакет не існує для focal. Фікс: ігнорувати, docker-ce + docker-compose-plugin ставляться окремо через `apt install docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-buildx-plugin` | #docker #deploy #ubuntu-20
2026-04-16 | Ubuntu 20.04: `apt-get update` failed — repos changed Origin/Label/Suite | Фікс: `sudo apt-get update --allow-releaseinfo-change -y` перед будь-яким install | #apt #deploy #ubuntu-20
2026-04-16 | nginx 1.18 (Ubuntu 20.04): `http2 on;` не підтримується як окрема директива | Фікс: замінити на `listen 443 ssl http2;` (старий синтаксис). Нова директива підтримується з nginx 1.25+ | #nginx #deploy #ubuntu-20
2026-04-16 | certbot chicken-and-egg: nginx не стартує без cert, certbot не працює без nginx на :80 | Фікс: тимчасово замінити конфіг на HTTP-only (без SSL блоку), reload nginx, запустити certbot --webroot, повернути повний конфіг | #certbot #nginx #deploy
2026-04-16 | scp не працює на деяких серверах (`subsystem request failed on channel 0`) | SSH працює але scp заблокований. Фікс: копіювати через `cat file | ssh host "cat > /tmp/file"` або `ssh host "cat /remote/file" > local/file` | #scp #ssh #deploy
