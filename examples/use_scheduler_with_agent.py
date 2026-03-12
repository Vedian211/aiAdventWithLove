"""
Example: Using Scheduler with Agent

This demonstrates how an agent can use the scheduler MCP server
to manage reminders, periodic tasks, and get summaries through conversation.
"""

import os
import asyncio
from dotenv import load_dotenv
from aiadvent.agent.agent import Agent
from aiadvent.agent.mcp.config import MCPServerConfig


async def simulate_conversation(agent: Agent):
    """Simulate a conversation where user asks agent to manage tasks."""
    
    print("=" * 70)
    print("🤖 AI Agent with Scheduler")
    print("=" * 70)
    print()
    
    # Conversation 1: Create a reminder
    print("👤 User: Напомни мне через 2 минуты проверить почту")
    print()
    
    # Agent would detect this and call schedule_reminder tool
    result = await agent.call_mcp_tool(
        "schedule_reminder",
        {"message": "Проверить почту", "minutes_from_now": 2}
    )
    
    print(f"🤖 Agent: ✅ Создал напоминание на {result}")
    print()
    print("-" * 70)
    print()
    
    # Conversation 2: Create periodic task
    print("👤 User: Собирай статистику API каждые 5 минут")
    print()
    
    result = await agent.call_mcp_tool(
        "schedule_periodic_task",
        {
            "task_type": "data_collection",
            "interval_minutes": 5,
            "data": {"source": "api_stats"}
        }
    )
    
    print(f"🤖 Agent: ✅ Настроил периодический сбор данных: {result}")
    print()
    print("-" * 70)
    print()
    
    # Conversation 3: List tasks
    print("👤 User: Какие у меня активные задачи?")
    print()
    
    result = await agent.call_mcp_tool(
        "list_scheduled_tasks",
        {"status": "active"}
    )
    
    import json
    tasks_data = json.loads(result) if isinstance(result, str) else result
    print(f"🤖 Agent: 📋 У вас {tasks_data.get('total', 0)} активных задач:")
    for task in tasks_data.get("tasks", []):
        task_type = task["type"]
        next_run = task["next_run"]
        if task_type == "reminder":
            message = task["data"].get("message", "")
            print(f"   - 🔔 Напоминание: {message} (в {next_run})")
        else:
            print(f"   - 📊 {task_type} (следующий запуск: {next_run})")
    print()
    print("-" * 70)
    print()
    
    # Conversation 4: Wait for reminder
    print("⏳ Ожидание выполнения напоминания (2 минуты)...")
    print("   (В реальности worker выполнит задачу и покажет уведомление)")
    print()
    await asyncio.sleep(5)  # Simulate waiting
    print("🔔 НАПОМИНАНИЕ: Проверить почту")
    print()
    print("-" * 70)
    print()
    
    # Conversation 5: Get summary
    print("👤 User: Покажи summary за сегодня")
    print()
    
    result = await agent.call_mcp_tool(
        "get_summary",
        {"period": "day"}
    )
    
    summary_data = json.loads(result) if isinstance(result, str) else result
    print(f"🤖 Agent: 📊 Summary за день:")
    print(f"   ✓ Всего выполнений: {summary_data.get('total_executions', 0)}")
    print(f"   ✓ Успешных: {summary_data.get('successful', 0)}")
    print(f"   ✓ Ошибок: {summary_data.get('failed', 0)}")
    print(f"   ✓ Успешность: {summary_data.get('success_rate', 0)}%")
    
    if summary_data.get('task_types'):
        print(f"   \n   Типы задач:")
        for task_type, count in summary_data['task_types'].items():
            print(f"      - {task_type}: {count} раз")
    print()
    print("-" * 70)
    print()
    
    # Conversation 6: Cancel a task
    print("👤 User: Отмени задачу сбора статистики")
    print()
    
    # Get task ID from list
    tasks_result = await agent.call_mcp_tool(
        "list_scheduled_tasks",
        {"status": "active"}
    )
    tasks_data = json.loads(tasks_result) if isinstance(tasks_result, str) else tasks_result
    
    # Find data_collection task
    task_to_cancel = None
    for task in tasks_data.get("tasks", []):
        if task["type"] == "data_collection":
            task_to_cancel = task["id"]
            break
    
    if task_to_cancel:
        result = await agent.call_mcp_tool(
            "cancel_task",
            {"task_id": task_to_cancel}
        )
        print(f"🤖 Agent: ✅ Задача #{task_to_cancel} отменена")
    else:
        print(f"🤖 Agent: ℹ️ Задача сбора данных не найдена")
    
    print()
    print("=" * 70)
    print("✅ Демонстрация завершена!")
    print()
    print("💡 Для полноценной работы запустите worker:")
    print("   python -m aiadvent.scheduler.cli start")
    print("=" * 70)


async def main():
    print("🚀 Scheduler with Agent Example")
    print()
    
    # Load environment
    load_dotenv()
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_key:
        print("❌ OPENAI_API_KEY not set in .env")
        return
    
    # Configure scheduler MCP server
    scheduler_config = MCPServerConfig(
        command="python",
        args=["-m", "aiadvent.mcp_server.scheduler_server"]
    )
    
    # Create agent with scheduler
    print("1️⃣  Creating agent with scheduler...")
    agent = Agent(
        api_key=openai_key,
        model="gpt-4o-mini",
        system_prompt="You are a helpful assistant with task scheduling capabilities.",
        mcp_server_configs=[scheduler_config]
    )
    print("✅ Agent created")
    print()
    
    # Initialize MCP
    print("2️⃣  Initializing scheduler MCP...")
    await agent.init_mcp()
    print("✅ Scheduler initialized")
    print()
    
    # Show available tools
    print("3️⃣  Available scheduler tools:")
    tools = agent.get_mcp_tools()
    for i, tool in enumerate(tools, 1):
        print(f"   {i}. {tool['name']}")
    print()
    
    # Run conversation simulation
    print("4️⃣  Starting conversation simulation...")
    print()
    await simulate_conversation(agent)
    
    # Cleanup
    print()
    print("5️⃣  Cleaning up...")
    if agent.mcp_clients:
        for client in agent.mcp_clients.values():
            try:
                await client.disconnect()
            except Exception as e:
                pass  # Ignore cleanup errors
    print("✅ Disconnected from MCP servers")


if __name__ == "__main__":
    asyncio.run(main())
