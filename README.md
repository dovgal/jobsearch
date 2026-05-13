# Job Search Consultation

Проект-консультант для поиска работы: стратегия, переупаковка CV/LinkedIn,
агрегация вакансий из множества каналов, адаптация резюме под конкретные
позиции, outreach hiring-менеджерам, контент-план для LinkedIn и подготовка
к интервью. Каждый этап обслуживает специализированный агент.

## Состав агентов

| Агент | Что делает | Что получает клиент |
|---|---|---|
| 🎯 `strategy-agent` | Читает CV, проводит 15+ уточняющих вопросов, делает 20+ web-запросов по индустрии, региону и зарплатам. Цитирует отраслевые отчёты с датами и ссылками. | Персональная стратегия на ~500 строк: 30+ целевых компаний (A/B/C), тренды, 3 нестандартных трека, помесячный план на 6 месяцев. |
| 📄 `base-cv-agent` | Переупаковывает CV под выбранное позиционирование. Поднимает iceberg-достижения, естественно распределяет ATS-ключевики, добивается ≥85% ATS-score. | Базовое CV, проходящее автоматический скрининг и читающееся как профиль уровнем выше. |
| 💼 `linkedin-agent` | Полностью переписывает профиль под стратегию и резюме. Headline под scan-test за 6 секунд (≤220 знаков), About с hook в первых 250 знаках. | Готовый к публикации LinkedIn-профиль. |
| 🔎 `vacancy-hunter` | Параллельно сканирует LinkedIn, Web3.career, hh.ru, CryptoJobsList, профильные TG-каналы, сайты рекрутинговых агентств. Скорит каждую вакансию по 12 параметрам. | Интерактивный HTML с 15–40 релевантными вакансиями — Apply/Skip/Need-info свайпом с телефона. |
| ✏️ `resume-agent` | Глубокая построчная адаптация резюме под Tier A вакансию. Каждый булет переписан под конкретный JD. | Заточенное резюме под одну вакансию. |
| 📚 `bulk-resume-agent` | Пакетная адаптация 10–20 откликов Tier B за один проход. | Папка адаптированных резюме. |
| 🤝 `outreach-agent` | Research нанимающих менеджеров и рекрутеров в целевых компаниях. Пишет персонализированное сообщение + follow-up. | Готовые к отправке сообщения. |
| 📝 `content-agent` | Посты в LinkedIn от имени клиента в его tone of voice. Поднимает видимость до момента, когда рекрутеры пишут сами. | Готовый контент-план + посты. |
| 🎤 `interview-coach` | Анализ вопросов конкретной компании + STAR-ответы под 30 типовых вопросов. Mock-интервью с разбором ответов. | Подготовка к интервью. |

## LLM-провайдеры

По умолчанию используется `ollama` (облачный endpoint Ollama Turbo), но через
конфиг можно переключить любого агента на:

- `anthropic` (Claude)
- `xai` (Grok)
- `google` (Gemini)
- `deepseek`
- `qwen` (DashScope / OpenRouter)
- `openrouter` (универсальный шлюз)
- любой OpenAI-совместимый endpoint

Каждому агенту можно задать свою модель — например, `strategy-agent` на
Claude Opus, а `bulk-resume-agent` на дешёвом Qwen.

## Быстрый старт

```bash
# 1. Зависимости
pip install -r requirements.txt

# 2. Скопировать конфиг и проставить ключи нужных провайдеров
cp .env.example .env

# 3. Положить исходное CV
mkdir -p input && cp my_cv.txt input/cv.txt

# 4. Запустить нужного агента
python main.py strategy           # 🎯 стратегия + интервью с клиентом
python main.py base-cv            # 📄 базовое резюме
python main.py linkedin           # 💼 LinkedIn-профиль
python main.py hunt               # 🔎 поиск вакансий + HTML
python main.py resume <job_id>    # ✏️ адаптация под Tier A
python main.py bulk-resume        # 📚 пакетная адаптация Tier B
python main.py outreach <job_id>  # 🤝 сообщения hiring-менеджерам
python main.py content            # 📝 LinkedIn-посты
python main.py interview <job_id> # 🎤 подготовка к интервью

# или весь пайплайн стратегия → CV → LinkedIn → охота
python main.py full
```

Все артефакты ложатся в `output/<session_id>/`.

## Конфигурация

`config/config.yaml`:

```yaml
default_provider: ollama
default_model: gpt-oss:120b      # модель в Ollama Turbo

providers:
  ollama:
    base_url: https://ollama.com
    api_key_env: OLLAMA_API_KEY
  anthropic:
    api_key_env: ANTHROPIC_API_KEY
    model: claude-opus-4-5
  xai:
    api_key_env: XAI_API_KEY
    model: grok-4
  google:
    api_key_env: GOOGLE_API_KEY
    model: gemini-2.5-pro
  deepseek:
    api_key_env: DEEPSEEK_API_KEY
    model: deepseek-chat
  qwen:
    api_key_env: DASHSCOPE_API_KEY
    model: qwen-max
  openrouter:
    api_key_env: OPENROUTER_API_KEY
    model: anthropic/claude-opus-4

# Переопределение провайдера/модели для конкретного агента
agents:
  strategy:
    provider: anthropic
    model: claude-opus-4-5
  bulk-resume:
    provider: qwen
    model: qwen-turbo
```

## Структура

```
.
├── main.py                   # CLI
├── config/
│   └── config.yaml
├── llm/                      # абстракция над провайдерами
├── agents/                   # 9 агентов
├── tools/                    # web search, ATS, HTML, скраперы
├── prompts/                  # системные промпты агентов
├── pipeline/                 # оркестратор сессии
├── input/                    # CV клиента
└── output/                   # артефакты
```

## Лицензия

MIT
