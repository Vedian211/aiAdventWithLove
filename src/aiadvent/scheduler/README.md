# Scheduler - Планировщик задач

Модуль для управления отложенными и периодическими задачами.

## Возможности

- ⏰ **Напоминания** - одноразовые уведомления в заданное время
- 🔄 **Периодические задачи** - выполнение задач по расписанию
- 💾 **Хранение в SQLite** - все задачи и результаты сохраняются
- 📊 **Агрегированная статистика** - summary по выполненным задачам
- 🤖 **Интеграция с агентом** - управление через MCP

## Установка

```bash
pip install -e .
```

## Использование

### 1. Запуск worker

Worker выполняет задачи в фоне:

```bash
scheduler start
```

Worker проверяет задачи каждые 10 секунд и выполняет те, что пора запустить.

### 2. Использование с агентом

```python
import asyncio
from aiadvent.agent.agent import Agent
from aiadvent.agent.mcp.config import MCPServerConfig

async def main():
    # Конфигурация scheduler MCP
    scheduler_config = MCPServerConfig(
        command="python",
        args=["-m", "aiadvent.mcp_server.scheduler_server"]
    )
    
    # Создание агента
    agent = Agent(
        api_key="your-key",
        mcp_server_configs=[scheduler_config]
    )
    
    # Инициализация
    await agent.init_mcp()
    
    # Создать напоминание
    result = await agent.call_mcp_tool(
        "schedule_reminder",
        {"message": "Проверить почту", "minutes_from_now": 5}
    )
    
    # Создать периодическую задачу
    result = await agent.call_mcp_tool(
        "schedule_periodic_task",
        {
            "task_type": "data_collection",
            "interval_minutes": 10,
            "data": {"source": "api"}
        }
    )
    
    # Получить список задач
    result = await agent.call_mcp_tool(
        "list_scheduled_tasks",
        {"status": "active"}
    )
    
    # Получить summary
    result = await agent.call_mcp_tool(
        "get_summary",
        {"period": "day"}
    )

asyncio.run(main())
```

### 3. Запуск примера

```bash
python examples/use_scheduler_with_agent.py
```

## MCP Tools

### schedule_reminder
Создать одноразовое напоминание.

**Параметры:**
- `message` (string) - текст напоминания
- `minutes_from_now` (integer) - через сколько минут

**Пример:**
```json
{
  "message": "Позвонить клиенту",
  "minutes_from_now": 30
}
```

### schedule_periodic_task
Создать периодическую задачу.

**Параметры:**
- `task_type` (string) - тип задачи
- `interval_minutes` (integer) - интервал в минутах
- `data` (object) - дополнительные данные

**Пример:**
```json
{
  "task_type": "data_collection",
  "interval_minutes": 15,
  "data": {"source": "api_stats"}
}
```

### list_scheduled_tasks
Получить список задач.

**Параметры:**
- `status` (string, optional) - фильтр по статусу: "active", "completed", "cancelled"

### cancel_task
Отменить задачу.

**Параметры:**
- `task_id` (integer) - ID задачи

### get_summary
Получить статистику выполнения.

**Параметры:**
- `period` (string, optional) - период: "hour", "day", "week"

## Архитектура

```
scheduler/
├── storage.py           # SQLite хранилище
├── task_scheduler.py    # Управление задачами
├── worker.py            # Фоновый worker
└── cli.py               # CLI команды

mcp_server/
└── scheduler_server.py  # MCP сервер

examples/
└── use_scheduler_with_agent.py  # Пример использования
```

## База данных

SQLite база `scheduler.db` содержит:

**scheduled_tasks** - задачи
- id, type, schedule, data, next_run, status, created_at

**task_results** - результаты выполнения
- id, task_id, executed_at, result, status

## Типы задач

- `reminder` - одноразовое напоминание
- `data_collection` - сбор данных
- Любой кастомный тип

## Статусы задач

- `active` - активная задача
- `completed` - выполнена (для одноразовых)
- `cancelled` - отменена

## Примеры использования

### Напоминание через 1 час
```python
await agent.call_mcp_tool(
    "schedule_reminder",
    {"message": "Встреча с командой", "minutes_from_now": 60}
)
```

### Сбор метрик каждые 5 минут
```python
await agent.call_mcp_tool(
    "schedule_periodic_task",
    {
        "task_type": "data_collection",
        "interval_minutes": 5,
        "data": {"source": "system_metrics"}
    }
)
```

### Дневной отчет
```python
result = await agent.call_mcp_tool(
    "get_summary",
    {"period": "day"}
)
```

## Расширение

Для добавления новых типов задач:

1. Добавьте обработчик в `worker.py`:
```python
async def _execute_custom_task(self, data: Dict[str, Any]):
    # Ваша логика
    return {"result": "success"}
```

2. Добавьте в `execute_task()`:
```python
elif task_type == "custom_task":
    result = await self._execute_custom_task(data)
```

## Troubleshooting

**Worker не запускается:**
- Проверьте, что установлены все зависимости: `pip install -e .`
- Убедитесь, что БД доступна для записи

**Задачи не выполняются:**
- Проверьте, что worker запущен: `scheduler start`
- Проверьте логи worker

**MCP сервер не подключается:**
- Убедитесь, что путь к модулю правильный
- Проверьте, что все зависимости установлены
