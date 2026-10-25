# Finance Manager

Финансовый менеджер (расходы, бюджеты, категории). Одностраничное веб-приложение
на Streamlit, написанное в функциональном стиле: чистые функции, иммутабельные
данные, замыкания, рекурсия, мемоизация.

Учебный проект по курсу функционального программирования (Python 3.11+).

## Запуск

```bash
python -m venv .venv
. .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app/main.py
```

После запуска приложение открывается на <http://localhost:8501>.
В fish-оболочке активация: `source .venv/bin/activate.fish`.

## Проверки качества

```bash
pytest -q
ruff check .
black --check .
```

## Структура проекта

```
Finance_Manager/
├── app/
│   ├── main.py            # Streamlit UI (меню, страницы)
│   ├── main_old.py        # первая консольная версия
│   └── core/
│       ├── domain.py      # иммутабельные модели (frozen dataclass)
│       ├── transforms.py  # чистые функции и замыкания-фильтры
│       ├── recursion.py   # обход иерархии категорий
│       ├── memo.py        # прогноз расходов + lru_cache + замер времени
│       ├── ftypes.py      # Maybe (Some/Nothing) и Either (Right/Left)
│       ├── validation.py  # safe_category, validate_transaction, check_budget
│       ├── lazy.py        # ленивые вычисления (лаба 5, пока пусто)
│       ├── frp.py         # шина событий (лаба 6, пока пусто)
│       ├── compose.py     # compose / pipe (лаба 7, пока пусто)
│       ├── service.py     # BudgetService / ReportService (лаба 7, пока пусто)
│       └── report.py      # отчёты (пока пусто)
├── data/
│   └── seed.json          # 3 счёта, 17 категорий, 100 транзакций, 3 бюджета
├── tests/
│   ├── test_lab1.py
│   ├── test_lab2.py
│   ├── test_lab3.py
│   ├── test_lab4.py
│   └── test_lab4_ui.py   # проверки страниц Streamlit
├── .streamlit/config.toml # тёмная тема
├── generate.py            # TODO: описать назначение
├── pyproject.toml         # настройки pytest
└── requirements.txt
```

## Навигация по лабораторным

Меню открывается кнопкой **☰ Menu** в левом верхнем углу.

| Лаба | Тема | Страница меню | Где нажимать | Код | Тесты |
|---|---|---|---|---|---|
| 1 | Чистые функции, неизменяемость, HOF | Overview, Data | Overview: счётчики и баланс. Data: кнопка **+ Add transaction** | `load_seed`, `add_transaction`, `update_budget`, `account_balance` в `core/transforms.py` | `tests/test_lab1.py` |
| 2 | Замыкания и рекурсия | Functional Core, Pipelines | Functional Core: выбор категории и расходы по дереву. Pipelines: фильтры | `by_category`, `by_date_range`, `by_amount_range` в `core/transforms.py`; `flatten_categories`, `sum_expenses_recursive` в `core/recursion.py` | `tests/test_lab2.py` |
| 3 | Мемоизация | Reports | Reports → блок **Forecast (cached)** → кнопка **Measure cache** | `forecast_expenses` (`@lru_cache`), `forecast_raw`, `measure_ms` в `core/memo.py` | `tests/test_lab3.py` |
| 4 | Maybe / Either | Functional Core, Reports | Functional Core → внизу **Transaction validation pipeline**: выберите счёт, категорию, сумму и дату, шаги проверки покажут ✅ / ❌ / ⏭ (пропущен). Пункты с ⚠ дают заведомо неверные данные. Кнопка **Add to data** добавляет валидную транзакцию. Reports → **Budget check (Either)** | `Some/Nothing`, `Right/Left` в `core/ftypes.py`; `safe_category`, `validate_transaction`, `check_budget` в `core/validation.py` | `tests/test_lab4.py`, `tests/test_lab4_ui.py` |

## Описание основных функций

Все функции принимают и возвращают кортежи (`tuple`), входные данные не меняются.

- `load_seed(path)` читает `seed.json` и возвращает `(accounts, categories, transactions, budgets)`.
- `add_transaction(trans, t)` возвращает новый кортеж с добавленной транзакцией.
- `update_budget(budgets, bid, new_limit)` возвращает новый кортеж бюджетов с изменённым лимитом.
- `account_balance(trans, acc_id)` считает сумму движений по счёту через `reduce`.
- `by_category(cat_id)`, `by_date_range(start, end)`, `by_amount_range(min, max)` возвращают предикаты (замыкания) для `filter`.
- `flatten_categories(cats, root)` рекурсивно собирает категорию и всех её потомков.
- `sum_expenses_recursive(cats, trans, root_id)` рекурсивно суммирует расходы по ветке категорий.
- `forecast_expenses(cat_id, trans, period)` среднемесячные расходы за последние `period` месяцев, результат кэшируется (`lru_cache`, поэтому `trans` обязан быть кортежем).
- `measure_ms(func, *args)` возвращает пару `(результат, время в мс)`.
- `Some(x)` / `Nothing()` (Maybe) и `Right(x)` / `Left(err)` (Either) имеют `map`, `bind`, `get_or_else`; отсутствие значения и ошибки передаются через контейнеры, без `try/except`.
- `safe_category(cats, cat_id)` возвращает `Some(категория)` или `Nothing()`.
- `validate_transaction(t, accs, cats)` возвращает `Right(t)` или `Left({...})`: счёт существует, категория существует и знак суммы подходит.
- `check_budget(b, trans)` возвращает `Right(b)` или `Left({...})`, если расходы превысили лимит.

## Данные

Формат дат `YYYY-MM-DD`. Доходы положительные, расходы отрицательные.
Начальный остаток счёта хранится в поле `balance`, текущий баланс равен
`balance` плюс сумма транзакций по счёту.

## Вклад участников

| Участник | Что сделал |
|---|---|
| [имя друга] | `app/core/*`, тесты, `seed.json` |
| [ваше имя] | UI в `app/main.py`: Overview, Data, Reports, тема, интеграция с `core` |