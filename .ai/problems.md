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
