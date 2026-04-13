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
