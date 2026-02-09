# Экспорт дизайн-токенов из Figma

> Исследование проведено: январь 2026

## Индустриальный стандарт: W3C DTCG

**Важная новость:** В октябре 2025 года Design Tokens Community Group выпустила первую стабильную версию спецификации (2025.10). Спецификацию разрабатывали представители Adobe, Google, Microsoft, Meta, Figma, Salesforce, Shopify и других компаний.

Формат DTCG:
- JSON-файлы с расширением `.tokens` или `.tokens.json`
- Свойства токенов имеют префикс `$` (например, `$value`, `$type`)
- Открытый стандарт без привязки к вендору

---

## Нативные возможности Figma

**Текущая ситуация:**
- В Dev Mode можно просматривать переменные, их алиасы и финальные значения
- **Нативный экспорт/импорт переменных в формате W3C DTCG анонсирован на Schema 2025 и выйдет в ноябре 2026**
- Пока нативного экспорта нет — нужны плагины

---

## Топ плагинов для экспорта (золотой стандарт)

| Плагин | Особенности | Ссылка |
|--------|-------------|--------|
| **Tokens Studio for Figma** | ~2M+ пользователей. Главный инструмент индустрии. 21 тип токенов, экспорт в Variables/Styles, синхронизация с GitHub, поддержка тем | https://www.figma.com/community/plugin/843461159747178978/tokens-studio-for-figma |
| **Design Tokens (W3C) Export** | Экспорт по стандарту W3C DTCG, каждый Mode = отдельный JSON | https://www.figma.com/community/plugin/1377982390646186215/design-tokens-w3c-export |
| **Figma Token Exporter** | Экспорт в CSS, SASS, Less. Выбор коллекций и тем | https://www.figma.com/community/plugin/1345069854741911632/figma-token-exporter |
| **Variable Export - CSS & JSON** | Мгновенный экспорт в CSS/JSON, мульти-коллекции | https://www.figma.com/community/plugin/1578013095771807283/variable-export-css-json |
| **Design Tokens Manager** | Экспорт по DTCG, Manifest.json для связей между файлами | https://www.figma.com/community/plugin/1263743870981744253/design-tokens-manager |

---

## Рекомендуемый пайплайн (Best Practice 2025/2026)

```
┌─────────────┐     ┌──────────────────┐     ┌────────────────┐     ┌─────────────┐
│   Figma     │ ──► │  Tokens Studio   │ ──► │ Style          │ ──► │ CSS/SCSS/   │
│  Variables  │     │  или W3C Export  │     │ Dictionary     │     │ JS/iOS/     │
│             │     │  (JSON)          │     │ (Transform)    │     │ Android     │
└─────────────┘     └──────────────────┘     └────────────────┘     └─────────────┘
```

### Шаг 1: Настройка в Figma
- Создайте коллекции Variables для цветов, spacing, typography
- Используйте Modes для светлой/тёмной темы (Light/Dark)
- Применяйте алиасы: `color/primary → color/blue/500`

### Шаг 2: Экспорт через плагин
- **Tokens Studio** — если нужна синхронизация с Git и полный контроль
- **Design Tokens (W3C) Export** — если хотите стандартный формат без сложностей

### Шаг 3: Трансформация через Style Dictionary

```bash
npm install style-dictionary
```

Style Dictionary конвертирует JSON-токены в:
- CSS Custom Properties (`--color-primary: #3B82F6`)
- SCSS Variables (`$color-primary: #3B82F6`)
- JavaScript/TypeScript
- iOS Swift / Android XML

---

## Практические рекомендации для темной/светлой темы

1. **В Figma**: создайте Collection "Colors" с двумя Modes: `Light` и `Dark`

2. **При экспорте**: получите 2 JSON-файла (по одному на тему)

3. **В CSS** (результат трансформации):

```css
:root {
  --color-background: #ffffff;
  --color-text: #1a1a1a;
}

[data-theme="dark"] {
  --color-background: #1a1a1a;
  --color-text: #ffffff;
}
```

---

## Автоматизация (CI/CD)

Для крупных проектов настройте GitHub Actions:
1. Дизайнер меняет токены → Tokens Studio создаёт PR
2. GitHub Action запускает Style Dictionary
3. Генерируются CSS/SCSS файлы автоматически

---

## Источники

- Design Tokens Community Group — W3C: https://www.w3.org/community/design-tokens/
- Design Tokens Specification Stable Release: https://www.w3.org/community/design-tokens/2025/10/28/design-tokens-specification-reaches-first-stable-version/
- Tokens Studio Documentation: https://docs.tokens.studio
- Style Dictionary GitHub: https://github.com/style-dictionary/style-dictionary
- Design System Mastery 2025/2026 Playbook: https://www.designsystemscollective.com/design-system-mastery-with-figma-variables-the-2025-2026-best-practice-playbook-da0500ca0e66
- Variables in Dev Mode — Figma Help: https://help.figma.com/hc/en-us/articles/27882809912471-Variables-in-Dev-Mode
- Style Dictionary Tutorial Series: https://www.alwaystwisted.com/articles/a-design-tokens-workflow-part-1
