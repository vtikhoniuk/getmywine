# Data Model Changes: Нормализация названий вин

**Feature**: 013-normalize-wine-names | **Date**: 2026-02-10

## Existing Entity: Wine

Схема таблицы `wines` **не меняется**. Все поля, типы, constraints и индексы остаются прежними.

### Изменение данных в поле `name`

| Аспект | До | После |
|--------|-----|-------|
| Содержимое name | «Вино Malbec, Luigi Bosca, 2024» | «Malbec» |
| Префикс | Содержит «Вино» / «Игристое вино» / «Шампанское» | Без префикса |
| Producer в name | Дублируется (Luigi Bosca) | Только в поле producer |
| Vintage в name | Дублируется (2024) | Только в поле vintage_year |
| Уникальность | Все 50 name уникальны | Все 50 нормализованных name уникальны (проверено) |

### Поля, используемые для матчинга в миграции

Миграция идентифицирует записи по текущему (старому) `name` и обновляет на нормализованный. Маппинг `old_name → new_name` хардкодится в миграции для всех 50 вин.

### Поле `embedding` (Vector(1536))

Пересчитывается **отдельным шагом** после миграции names. Text representation для эмбеддинга строится из полей: name, wine_type, country, region, grape_varieties, sweetness, body, description, tasting_notes, food_pairings. Изменение name влияет на embedding — пересчёт обязателен.

## Нормализационная карта (50 вин)

### Pattern A — `{prefix} {name}, {producer}, {year}` (36 вин)

| # | Нормализованное name |
|---|---------------------|
| 0 | Malbec |
| 1 | Петрикор Красное |
| 2 | El Picaro |
| 4 | Clarendelle by Haut-Brion Rouge |
| 5 | Герцъ |
| 6 | Renome Каберне Фран – Мерло |
| 8 | Chianti Castiglioni |
| 10 | El Recio |
| 11 | Merlot Reserve |
| 12 | Sassi Chiusi |
| 13 | Pure Malbec |
| 14 | Pfefferer Sun |
| 15 | Misty Cliff Sauvignon Blanc |
| 16 | Urban Riesling |
| 17 | Pfefferer |
| 19 | Gavi Il Valentino |
| 20 | Рислинг |
| 21 | Петрикор Совиньон Блан |
| 22 | Losung Muskat Ottonel |
| 23 | Paddle Creek Sauvignon Blanc |
| 24 | Le Rime |
| 25 | Remole Bianco |
| 26 | Ballet Blanc. Красная Горка. |
| 29 | Розе Красная Горка |
| 30 | Pfefferer Pink |
| 31 | Mare & Grill Vinho Verde Rose |
| 32 | Alie Rose |
| 33 | Tenuta Regaleali Le Rose |
| 34 | Clarendelle a par Haut-Brion Rose |
| 35 | Cotes du Rhone Rose |
| 36 | Pinot Noir Rose |
| 37 | Coeur du Rouet |
| 38 | Carolina Reserva Rose |
| 40 | Ros'Aura |
| 41 | Zweigelt Rose |
| 46 | Балаклава Брют Резерв |

### Pattern B — `{prefix} {name_with_producer}, {year}` (8 вин)

| # | Нормализованное name |
|---|---------------------|
| 3 | Barbera d'Asti Luca Bosio |
| 7 | Hacienda Lopez de Haro Reserva |
| 9 | Усадьба Мезыбь. Каберне Совиньон/ Каберне Фран/ Мерло |
| 18 | Loco Cimbali Orange |
| 27 | Le Grand Noir Winemaker's Selection Chardonnay |
| 39 | Cielo Pinot Grigio Rose |
| 44 | Bruni Asti |
| 48 | Шумринка розовое |

### Pattern C — `{prefix} {name}, {producer}` без year (4 вина)

| # | Нормализованное name |
|---|---------------------|
| 28 | Crab & More White Zinfandel |
| 43 | Prosecco Superiore Valdobbiadene Quartese Brut |
| 45 | Le Black Creation Brut в подарочной упаковке |
| 47 | Tener Sauvignon Chardonnay |

### Pattern D — `{prefix} {name_with_producer}` без year (2 вина)

| # | Нормализованное name |
|---|---------------------|
| 42 | Bruni Prosecco Brut |
| 49 | Santa Carolina Brut |

## Validation Rules

1. **name NOT LIKE 'Вино %'** — ни одно name не начинается с «Вино»
2. **name NOT LIKE 'Игристое вино %'** — ни одно name не начинается с «Игристое вино»
3. **name NOT LIKE 'Шампанское %'** — ни одно name не начинается с «Шампанское»
4. **COUNT(DISTINCT name) = 50** — все нормализованные name уникальны
5. **producer IS NOT NULL** для всех 50 записей
6. **vintage_year IS NOT NULL** для 44 записей (6 NV-вин имеют NULL)
