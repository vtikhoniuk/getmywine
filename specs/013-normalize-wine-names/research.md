# Research: Нормализация названий вин

**Feature**: 013-normalize-wine-names | **Date**: 2026-02-10

## R-001: Стратегия нормализации name в wines_seed.json

**Decision**: Алгоритмическая нормализация на основе существующих полей producer и vintage_year. Функция `normalize_wine_name(name, producer, vintage_year)` применяется и к seed-файлу, и в миграции.

**Rationale**: Алгоритм использует структуру данных: producer и vintage_year всегда выделяются запятой (`, producer`, `, year`) в паттернах A/C. В паттернах B/D producer встроен в name без запятой — алгоритм естественно его не удаляет. Проверено на всех 50 винах: 100% корректных результатов, все 50 нормализованных имён уникальны.

**Алгоритм**:
1. Удалить категорийный префикс (самый длинный первым): «Игристое вино » → «Шампанское » → «Вино »
2. Удалить `, {vintage_year}` с конца строки (если vintage_year не None)
3. Удалить `, {producer}` с конца строки (если совпадает)
4. Trim пробелы

**Почему работает для всех 4 паттернов**:
- Pattern A (`{prefix} {name}, {producer}, {year}`): шаг 2 убирает year, шаг 3 убирает producer → остаётся name
- Pattern B (`{prefix} {name_with_producer}, {year}`): шаг 2 убирает year, шаг 3 не срабатывает (producer без запятой) → остаётся name_with_producer
- Pattern C (`{prefix} {name}, {producer}`): шаг 2 не срабатывает (нет year), шаг 3 убирает producer → остаётся name
- Pattern D (`{prefix} {name_with_producer}`): шаги 2-3 не срабатывают → остаётся name_with_producer

**Alternatives considered**:
- Ручная нормализация (хардкод-маппинг 50 вин): отвергнут — алгоритм покрывает все случаи, проще поддерживать при добавлении вин
- Regex-based парсинг без структурированных полей: отвергнут — не различает Pattern A и B

## R-002: Подход к миграции БД

**Decision**: Alembic-миграция применяет алгоритм `normalize_wine_name()` (R-001) ко всем записям в таблице wines. Для каждой записи: SELECT id, name, producer, vintage_year → вычислить normalized name → UPDATE name WHERE id.

**Rationale**: Алгоритм из R-001 доказано работает на всех 50 винах. Миграция не зависит от seed-файла — она работает с данными в БД напрямую, используя уже заполненные поля producer и vintage_year для нормализации.

**Alternatives considered**:
- Хардкод-маппинг old_name → new_name в миграции: отвергнут — алгоритм надёжнее и не требует ручного обновления при изменении каталога
- SQL UPDATE с regex: отвергнут — SQL regex не различает паттерны B/D
- Полный reseed (DELETE + INSERT): отвергнут — потерялись бы существующие эмбеддинги

**Downgrade**: Миграция downgrade не требуется (данные можно восстановить из старого seed), но для безопасности можно сохранить old names в таблице или просто не поддерживать downgrade (необратимая миграция данных).

## R-003: Пересчёт эмбеддингов

**Decision**: Использовать существующий скрипт `generate_embeddings.py` после миграции names, с доработкой для обновления эмбеддингов в БД (а не создания нового файла).

**Rationale**: Скрипт `backend/app/scripts/generate_embeddings.py` уже генерирует эмбеддинги из seed-данных. После нормализации names, text representation для эмбеддинга изменится → нужен пересчёт. Текущий скрипт сохраняет результат в файл; нужно добавить опцию обновления в БД через `wine_repo.update_embedding()`.

**Alternatives considered**:
- Генерация эмбеддингов прямо в миграции (как 012): отвергнут — FR-005 clarification требует двухфазного подхода
- Новый standalone скрипт: избыточно — можно расширить существующий

## R-004: Упрощение _extract_wines_from_response()

**Decision**: Заменить 3-уровневый matching на прямой поиск `wine.name` в тексте ответа LLM (один уровень).

**Rationale**: После нормализации wine.name содержит именно то, что LLM вернёт в ответе (системный промпт требует «ТОЧНО как в каталоге»). Три уровня (strip «Вино», strip year) были workaround для ненормализованных имён и станут мёртвым кодом.

**Alternatives considered**:
- Оставить 3 уровня: отвергнут — мёртвый код, маскирует ошибки
- 2 уровня (exact + lowercase): отвергнут — LLM инструктирован использовать точное имя

**Риск**: Если LLM не воспроизведёт name точно (опечатка, перефразирование), matching не сработает. Митигация: промпт явно требует «ТОЧНО как в каталоге»; нормализованные короткие имена проще воспроизвести точно, чем длинные «Вино Malbec, Luigi Bosca, 2024».

## R-005: Анализ 4 паттернов name

**Decision**: Документирована полная нормализационная карта 50 вин.

| Паттерн | Кол-во | Правило нормализации |
|---------|--------|---------------------|
| A: `{prefix} {name}, {producer}, {year}` | 36 | Удалить prefix, producer, year → оставить name |
| B: `{prefix} {name_with_producer}, {year}` | 8 | Удалить prefix и year → оставить name_with_producer |
| C: `{prefix} {name}, {producer}` (no year) | 4 | Удалить prefix и producer → оставить name |
| D: `{prefix} {name_with_producer}` (no year) | 2 | Удалить prefix → оставить name_with_producer |

**Особые случаи**:
- Wine #39 «Cielo Pinot Grigio Rose » — trailing space, trimming при нормализации
- Wine #26 «Ballet Blanc. Красная Горка.» — trailing period, оставляется как есть (часть имени)
- Wine #45 «Le Black Creation Brut в подарочной упаковке» — «в подарочной упаковке» остаётся как часть имени (отличает от другой комплектации)

## R-006: Влияние на format_wine_catalog_for_prompt()

**Decision**: Изменений не требуется.

**Rationale**: Функция уже использует `wine.name` напрямую. После нормализации name в БД, промпт автоматически получит нормализованные имена. Формат `[{i}] {wine.name}` продолжает работать корректно.

## R-007: Влияние на format_wine_photo_caption()

**Decision**: Изменений не требуется.

**Rationale**: Функция формирует caption из отдельных полей: `wine.name`, `wine.region`, `wine.country`, grapes, sweetness, price. После нормализации name, caption станет короче и точнее (без дублирования producer/year в name).

## R-008: Существующие реализованные FR

**Decision**: FR-007 (ресайз + белый фон), FR-008 (настраиваемая высота), FR-009 (caption из отдельных полей) уже реализованы и протестированы. Новая работа не требуется.

**Подтверждение**:
- `prepare_wine_photo()` в sender.py — реализует FR-007/FR-008
- `telegram_wine_photo_height` в config.py — реализует FR-008
- `format_wine_photo_caption()` в formatters.py — реализует FR-009
- Тесты в test_bot_sender.py обновлены
