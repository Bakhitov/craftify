#!/usr/bin/env python3
"""
РАСШИРЕННЫЙ автотест системы agent-api
Проверяет ВСЕ эндпоинты с подробными логами и дополнительными проверками
"""

import asyncio
import aiohttp
import json
import io
import time
import sys
from typing import Dict, Any, List
from pathlib import Path


class DetailedAgentAPITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.test_results = []
        self.created_agent_id = None
        self.created_tool_id = None
        self.detailed_logs = []
        self.performance_metrics = []  # Новое: метрики производительности
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Any = None, execution_time: float = None):
        """Логирует результат теста с подробной информацией и метриками производительности"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "response_data": response_data,
            "execution_time": execution_time
        })
        
        print(f"{status} {test_name}")
        if details:
            print(f"    📋 {details}")
        if execution_time:
            print(f"    ⏱️ Время выполнения: {execution_time:.3f}s")
        
        # Подробные логи
        log_entry = {
            "test": test_name,
            "status": "PASS" if success else "FAIL",
            "details": details,
            "timestamp": time.time(),
            "execution_time": execution_time,
            "response_preview": str(response_data)[:200] if response_data else None
        }
        self.detailed_logs.append(log_entry)
        
        # Метрики производительности
        if execution_time:
            self.performance_metrics.append({
                "endpoint": test_name,
                "execution_time": execution_time,
                "success": success,
                "timestamp": time.time()
            })
    
    async def test_health_check(self):
        """Тест 1: Проверка здоровья API"""
        start_time = time.time()
        try:
            async with self.session.get(f"{self.base_url}/v1/health") as resp:
                data = await resp.json()
                elapsed = time.time() - start_time
                
                if resp.status == 200:
                    self.log_test("Health Check", True, 
                                f"Status: {data.get('status')}, Server response time: {resp.headers.get('x-process-time', 'N/A')}", 
                                data, elapsed)
                    return True
                else:
                    self.log_test("Health Check", False, f"HTTP {resp.status}", data, elapsed)
                    return False
        except Exception as e:
            elapsed = time.time() - start_time
            self.log_test("Health Check", False, f"Error: {str(e)}", None, elapsed)
            return False
    
    async def test_list_agents(self):
        """Тест 2: Получение списка агентов с детальным анализом"""
        start_time = time.time()
        try:
            async with self.session.get(f"{self.base_url}/v1/agents") as resp:
                agents = await resp.json()
                elapsed = time.time() - start_time
                
                if resp.status == 200:
                    static_agents = [a for a in agents if a.get('agent_type') == 'static']
                    dynamic_agents = [a for a in agents if a.get('agent_type') != 'static']
                    
                    static_names = [a.get('agent_id', a.get('name', 'Unknown')) for a in static_agents]
                    dynamic_names = [a.get('agent_id', a.get('name', 'Unknown')) for a in dynamic_agents[:5]]  # Первые 5
                    
                    details = f"Total: {len(agents)} | Static: {len(static_agents)} {static_names} | Dynamic: {len(dynamic_agents)} (показаны первые 5: {dynamic_names})"
                    
                    self.log_test("List Agents", True, details, {
                        "total_count": len(agents),
                        "static_count": len(static_agents),
                        "dynamic_count": len(dynamic_agents),
                        "static_agents": static_names,
                        "sample_dynamic": dynamic_names
                    }, elapsed)
                    return True, agents
                else:
                    self.log_test("List Agents", False, f"HTTP {resp.status}", None, elapsed)
                    return False, []
        except Exception as e:
            elapsed = time.time() - start_time
            self.log_test("List Agents", False, f"Error: {str(e)}", None, elapsed)
            return False, []
    
    async def test_static_agent_run(self):
        """Тест 3: Запуск статического агента с проверкой инструментов"""
        try:
            payload = {
                "message": "Найди последние новости о Python. Используй веб-поиск.",
                "stream": False,
                "model": "gpt-4.1"
            }
            
            start_time = time.time()
            async with self.session.post(
                f"{self.base_url}/v1/agents/web_agent/runs",
                json=payload
            ) as resp:
                result = await resp.json()
                elapsed = time.time() - start_time
                
                if resp.status == 200:
                    response_length = len(result.get('response', result.get('content', '')))
                    tools_used = result.get('formatted_tool_calls', [])
                    
                    details = f"Response: {response_length} chars, Time: {elapsed:.2f}s, Tools used: {len(tools_used)}"
                    if tools_used:
                        details += f", Tool calls: {tools_used[:2]}"  # Первые 2 вызова
                    
                    self.log_test("Static Agent Run (JSON)", True, details, {
                        "response_length": response_length,
                        "execution_time": elapsed,
                        "tools_used": len(tools_used),
                        "tool_calls": tools_used
                    }, elapsed)
                    return True
                else:
                    elapsed = time.time() - start_time
                    self.log_test("Static Agent Run (JSON)", False, f"HTTP {resp.status}", result, elapsed)
                    return False
        except Exception as e:
            elapsed = time.time() - start_time
            self.log_test("Static Agent Run (JSON)", False, f"Error: {str(e)}", None, elapsed)
            return False
    
    async def test_multipart_agent_run(self):
        """Тест 4: Запуск агента с файлом и детальный анализ обработки"""
        try:
            test_content = """# Тестовый документ для анализа агентом

## Введение
Этот файл создан для тестирования возможностей агента по анализу текстовых документов.

## Содержание
- Технические данные: Python 3.12, FastAPI, Docker
- Статистика: 1000 пользователей, 500 запросов в день
- Статус: Активный проект

## Заключение
Документ содержит структурированную информацию для анализа."""
            
            data = aiohttp.FormData()
            data.add_field('message', 'Проанализируй содержимое файла. Выдели ключевые данные и статистику.')
            data.add_field('stream', 'false')
            data.add_field('model', 'gpt-4.1')
            data.add_field('files', 
                          io.BytesIO(test_content.encode('utf-8')),
                          filename='test_document.md',
                          content_type='text/markdown')
            
            start_time = time.time()
            async with self.session.post(
                f"{self.base_url}/v1/agents/agno_assist/runs/multipart",
                data=data
            ) as resp:
                result = await resp.json()
                elapsed = time.time() - start_time
                
                if resp.status == 200:
                    response_length = len(result.get('response', result.get('content', '')))
                    
                    details = f"File processed: test_document.md ({len(test_content)} bytes), Response: {response_length} chars, Time: {elapsed:.2f}s"
                    
                    self.log_test("Multipart Agent Run", True, details, {
                        "file_size": len(test_content),
                        "response_length": response_length,
                        "execution_time": elapsed,
                        "file_type": "markdown"
                    }, elapsed)
                    return True
                else:
                    elapsed = time.time() - start_time
                    text = await resp.text()
                    self.log_test("Multipart Agent Run", False, f"HTTP {resp.status}: {text[:200]}", None, elapsed)
                    return False
        except Exception as e:
            elapsed = time.time() - start_time
            self.log_test("Multipart Agent Run", False, f"Error: {str(e)}", None, elapsed)
            return False
    
    async def test_streaming_response(self):
        """Тест 5: Стриминговый ответ с анализом производительности"""
        try:
            payload = {
                "message": "Расскажи подробно о преимуществах Python для разработки API",
                "stream": True,
                "model": "gpt-4.1"
            }
            
            chunks_received = 0
            total_content = ""
            start_time = time.time()
            first_chunk_time = None
            
            async with self.session.post(
                f"{self.base_url}/v1/agents/web_agent/runs",
                json=payload
            ) as resp:
                if resp.status == 200:
                    async for chunk in resp.content.iter_chunked(1024):
                        if chunk:
                            if first_chunk_time is None:
                                first_chunk_time = time.time() - start_time
                            chunks_received += 1
                            total_content += chunk.decode('utf-8', errors='ignore')
                            if chunks_received >= 15:  # Больше чанков для анализа
                                break
                    
                    total_time = time.time() - start_time
                    avg_chunk_time = total_time / chunks_received if chunks_received > 0 else 0
                    
                    details = f"Chunks: {chunks_received}, Content: {len(total_content)} chars, First chunk: {first_chunk_time:.2f}s, Avg chunk time: {avg_chunk_time:.3f}s"
                    
                    self.log_test("Streaming Response", True, details, {
                        "chunks_received": chunks_received,
                        "content_length": len(total_content),
                        "first_chunk_time": first_chunk_time,
                        "total_time": total_time,
                        "avg_chunk_time": avg_chunk_time
                    }, total_time)
                    return True
                else:
                    total_time = time.time() - start_time
                    self.log_test("Streaming Response", False, f"HTTP {resp.status}", None, total_time)
                    return False
        except Exception as e:
            total_time = time.time() - start_time
            self.log_test("Streaming Response", False, f"Error: {str(e)}", None, total_time)
            return False
    
    async def test_dynamic_agents_list(self):
        """Тест 6: Анализ динамических агентов"""
        start_time = time.time()
        try:
            async with self.session.get(f"{self.base_url}/v1/dynamic-agents") as resp:
                agents = await resp.json()
                elapsed = time.time() - start_time
                if resp.status == 200:
                    active_agents = [a for a in agents if a.get('is_active', False)]
                    inactive_agents = [a for a in agents if not a.get('is_active', False)]
                    
                    models_used = {}
                    for agent in active_agents:
                        model = agent.get('model_config', {}).get('id', 'unknown')
                        models_used[model] = models_used.get(model, 0) + 1
                    
                    details = f"Total: {len(agents)}, Active: {len(active_agents)}, Inactive: {len(inactive_agents)}, Models: {dict(models_used)}"
                    
                    self.log_test("Dynamic Agents List", True, details, {
                        "total_agents": len(agents),
                        "active_count": len(active_agents),
                        "inactive_count": len(inactive_agents),
                        "models_distribution": models_used,
                        "sample_agents": [a.get('agent_id', 'Unknown') for a in active_agents[:3]]
                    }, elapsed)
                    return True, agents
                else:
                    self.log_test("Dynamic Agents List", False, f"HTTP {resp.status}", None, elapsed)
                    return False, []
        except Exception as e:
            elapsed = time.time() - start_time
            self.log_test("Dynamic Agents List", False, f"Error: {str(e)}", None, elapsed)
            return False, []
    
    async def test_create_dynamic_agent(self):
        """Тест 7: Создание динамического агента с валидацией"""
        try:
            timestamp = int(time.time())
            agent_data = {
                "name": "Detailed AutoTest Agent",
                "agent_id": f"detailed_autotest_agent_{timestamp}",
                "description": "Агент созданный расширенным автотестом для детальной проверки функциональности",
                "instructions": "Ты специализированный агент для автоматического тестирования. Отвечай структурированно и включай технические детали.",
                "model_config": {
                    "id": "gpt-4.1",
                    "type": "openai"
                },
                "tools_config": [
                    {"name": "calculator", "enabled": True},
                    {"name": "time_analyzer", "enabled": True}
                ],
                "knowledge_config": {},
                "memory_config": {"enabled": True},
                "storage_config": {},
                "settings": {
                    "test_mode": True,
                    "created_by": "detailed_autotest",
                    "version": "1.0"
                }
            }
            
            async with self.session.post(
                f"{self.base_url}/v1/dynamic-agents",
                json=agent_data
            ) as resp:
                result = await resp.json()
                if resp.status == 201:
                    self.created_agent_id = result.get('agent_id')
                    
                    # Проверяем что все поля сохранились
                    validation_details = []
                    if result.get('name') == agent_data['name']:
                        validation_details.append("✓ Name")
                    if result.get('description') == agent_data['description']:
                        validation_details.append("✓ Description")
                    if result.get('model_config', {}).get('id') == agent_data['model_config']['id']:
                        validation_details.append("✓ Model")
                    
                    details = f"Created: {self.created_agent_id}, Validation: {', '.join(validation_details)}"
                    
                    self.log_test("Create Dynamic Agent", True, details, {
                        "agent_id": self.created_agent_id,
                        "validation_passed": len(validation_details),
                        "total_validations": 3,
                        "agent_data": result
                    })
                    return True, result
                else:
                    text = await resp.text()
                    self.log_test("Create Dynamic Agent", False, f"HTTP {resp.status}: {text[:200]}")
                    return False, None
        except Exception as e:
            self.log_test("Create Dynamic Agent", False, f"Error: {str(e)}")
            return False, None
    
    async def test_dynamic_agent_run(self):
        """Тест 8: Запуск динамического агента с инструментами"""
        if not self.created_agent_id:
            self.log_test("Dynamic Agent Run", False, "No agent created")
            return False
        
        try:
            payload = {
                "message": "Привет! Это детальный тест автоматической системы. Вычисли 15 * 23 и проанализируй текущее время.",
                "stream": False,
                "model": "gpt-4.1"
            }
            
            start_time = time.time()
            async with self.session.post(
                f"{self.base_url}/v1/agents/{self.created_agent_id}/runs",
                json=payload
            ) as resp:
                result = await resp.json()
                elapsed = time.time() - start_time
                
                if resp.status == 200:
                    response_content = result.get('response', result.get('content', '')) or ''
                    response_length = len(response_content)
                    tools_used = result.get('formatted_tool_calls', []) or []
                    
                    details = f"Response: {response_length} chars, Time: {elapsed:.2f}s, Tools: {len(tools_used)}"
                    if tools_used:
                        details += f", Used: {[t.split('(')[0] for t in tools_used]}"
                    
                    self.log_test("Dynamic Agent Run", True, details, {
                        "response_length": response_length,
                        "execution_time": elapsed,
                        "tools_used": len(tools_used),
                        "tool_calls": tools_used
                    })
                    return True
                else:
                    text = await resp.text()
                    self.log_test("Dynamic Agent Run", False, f"HTTP {resp.status}: {text[:200]}")
                    return False
        except Exception as e:
            self.log_test("Dynamic Agent Run", False, f"Error: {str(e)}")
            return False
    
    async def test_update_dynamic_agent(self):
        """Тест 9: Обновление агента с проверкой кэша"""
        if not self.created_agent_id:
            self.log_test("Update Dynamic Agent", False, "No agent created")
            return False
        
        try:
            update_data = {
                "name": "Updated Detailed AutoTest Agent",
                "agent_id": self.created_agent_id,
                "description": "Обновленный агент детального автотеста с дополнительными возможностями",
                "instructions": "Ты обновленный специализированный агент для автоматического тестирования. Теперь ты включаешь еще больше технических деталей и метрик.",
                "model_config": {
                    "id": "gpt-4.1",
                    "type": "openai"
                },
                "tools_config": [
                    {"name": "calculator", "enabled": True},
                    {"name": "time_analyzer", "enabled": True},
                    {"name": "text_generator", "enabled": True}
                ],
                "knowledge_config": {},
                "memory_config": {"enabled": True},
                "storage_config": {},
                "settings": {
                    "test_mode": True,
                    "created_by": "detailed_autotest",
                    "version": "2.0",
                    "updated": True,
                    "update_timestamp": time.time()
                }
            }
            
            async with self.session.put(
                f"{self.base_url}/v1/dynamic-agents/{self.created_agent_id}",
                json=update_data
            ) as resp:
                result = await resp.json()
                if resp.status == 200:
                    # Проверяем обновления
                    name_updated = result.get('name') == update_data['name']
                    tools_updated = len(result.get('tools_config', [])) == len(update_data['tools_config'])
                    settings_updated = result.get('settings', {}).get('version') == "2.0"
                    
                    validation_score = sum([name_updated, tools_updated, settings_updated])
                    
                    details = f"Updated: {result.get('name')}, Validation: {validation_score}/3 checks passed"
                    
                    self.log_test("Update Dynamic Agent", True, details, {
                        "validation_score": validation_score,
                        "name_updated": name_updated,
                        "tools_updated": tools_updated,
                        "settings_updated": settings_updated
                    })
                    return True
                else:
                    text = await resp.text()
                    self.log_test("Update Dynamic Agent", False, f"HTTP {resp.status}: {text[:200]}")
                    return False
        except Exception as e:
            self.log_test("Update Dynamic Agent", False, f"Error: {str(e)}")
            return False
    
    async def test_dynamic_tools_list(self):
        """Тест 10: Анализ динамических инструментов"""
        try:
            async with self.session.get(f"{self.base_url}/v1/dynamic-tools/") as resp:
                tools = await resp.json()
                if resp.status == 200:
                    active_tools = [t for t in tools if t.get('is_active', False)]
                    
                    # Анализ типов инструментов
                    tool_types = {}
                    for tool in active_tools:
                        func_name = tool.get('function_name', 'unknown')
                        tool_types[func_name] = tool_types.get(func_name, 0) + 1
                    
                    tool_names = [t.get('tool_id', 'Unknown') for t in active_tools]
                    
                    details = f"Total: {len(tools)}, Active: {len(active_tools)}, Types: {list(tool_types.keys())}, Tools: {tool_names}"
                    
                    self.log_test("Dynamic Tools List", True, details, {
                        "total_tools": len(tools),
                        "active_tools": len(active_tools),
                        "tool_types": tool_types,
                        "tool_names": tool_names
                    })
                    return True
                else:
                    self.log_test("Dynamic Tools List", False, f"HTTP {resp.status}")
                    return False
        except Exception as e:
            self.log_test("Dynamic Tools List", False, f"Error: {str(e)}")
            return False
    
    async def test_cache_stats(self):
        """Тест 11: Детальная статистика кэширования"""
        try:
            async with self.session.get(f"{self.base_url}/v1/cache/stats") as resp:
                stats = await resp.json()
                if resp.status == 200:
                    hit_rate = stats.get('hit_rate', 0)
                    cache_size = stats.get('size', 0)
                    hits = stats.get('hits', 0)
                    misses = stats.get('misses', 0)
                    
                    details = f"Hit rate: {hit_rate:.2%}, Size: {cache_size}, Hits: {hits}, Misses: {misses}"
                    
                    self.log_test("Cache Stats", True, details, stats)
                    return True
                else:
                    self.log_test("Cache Stats", False, f"HTTP {resp.status}")
                    return False
        except Exception as e:
            self.log_test("Cache Stats", False, f"Error: {str(e)}")
            return False
    
    async def test_mcp_tools_status(self):
        """Тест 12: Статус MCP инструментов"""
        try:
            async with self.session.get(f"{self.base_url}/v1/mcp/status") as resp:
                status = await resp.json()
                if resp.status == 200:
                    mcp_status = status.get('status', 'unknown')
                    transports = status.get('available_transports', [])
                    
                    details = f"MCP Status: {mcp_status}, Transports: {transports}"
                    
                    self.log_test("MCP Tools Status", True, details, status)
                    return True
                else:
                    self.log_test("MCP Tools Status", False, f"HTTP {resp.status}")
                    return False
        except Exception as e:
            self.log_test("MCP Tools Status", False, f"Error: {str(e)}")
            return False
    
    async def test_agent_sessions(self):
        """Тест 13: Сессии агентов"""
        if not self.created_agent_id:
            self.log_test("Agent Sessions", False, "No agent created")
            return False
        
        try:
            async with self.session.get(f"{self.base_url}/v1/agents/{self.created_agent_id}/sessions") as resp:
                sessions = await resp.json()
                if resp.status == 200:
                    session_count = len(sessions) if isinstance(sessions, list) else 0
                    
                    details = f"Sessions found: {session_count}"
                    
                    self.log_test("Agent Sessions", True, details, {
                        "session_count": session_count,
                        "agent_id": self.created_agent_id
                    })
                    return True
                else:
                    self.log_test("Agent Sessions", False, f"HTTP {resp.status}")
                    return False
        except Exception as e:
            self.log_test("Agent Sessions", False, f"Error: {str(e)}")
            return False
    
    async def cleanup_test_agent(self):
        """Очистка: Удаление тестового агента"""
        if not self.created_agent_id:
            return True
        
        try:
            async with self.session.delete(
                f"{self.base_url}/v1/dynamic-agents/{self.created_agent_id}"
            ) as resp:
                if resp.status == 204:
                    self.log_test("Cleanup Test Agent", True, f"Deleted {self.created_agent_id}")
                    return True
                else:
                    self.log_test("Cleanup Test Agent", False, f"HTTP {resp.status}")
                    return False
        except Exception as e:
            self.log_test("Cleanup Test Agent", False, f"Error: {str(e)}")
            return False
    
    def print_performance_report(self):
        """Выводит детальный отчет о производительности"""
        print("\n" + "=" * 80)
        print("⚡ ОТЧЕТ О ПРОИЗВОДИТЕЛЬНОСТИ ЭНДПОИНТОВ")
        print("=" * 80)
        
        if not self.performance_metrics:
            print("❌ Нет данных о производительности")
            return
        
        # Сортируем по времени выполнения
        sorted_metrics = sorted(self.performance_metrics, key=lambda x: x['execution_time'])
        
        print(f"\n📊 Анализ времени выполнения ({len(sorted_metrics)} эндпоинтов):")
        print("-" * 80)
        
        # Таблица результатов
        print(f"{'№':<3} {'Эндпоинт':<35} {'Время (сек)':<15} {'Статус':<8} {'Категория':<15}")
        print("-" * 80)
        
        categories = {
            "Health Check": "Системные",
            "List Agents": "Базовые API", 
            "Cache Stats": "Системные",
            "Static Agent Run (JSON)": "AI Агенты",
            "Multipart Agent Run": "AI Агенты",
            "Streaming Response": "AI Агенты", 
            "Dynamic Agents List": "Базовые API",
            "Create Dynamic Agent": "CRUD",
            "Dynamic Agent Run": "AI Агенты",
            "Update Dynamic Agent": "CRUD",
            "Agent Sessions": "Базовые API",
            "Dynamic Tools List": "Базовые API",
            "MCP Tools Status": "Системные"
        }
        
        for i, metric in enumerate(sorted_metrics, 1):
            endpoint = metric['endpoint']
            time_val = metric['execution_time']
            status = "✅ OK" if metric['success'] else "❌ FAIL"
            category = categories.get(endpoint, "Прочие")
            
            # Цветовая индикация времени
            if time_val < 0.1:
                time_display = f"🟢 {time_val:.3f}"
            elif time_val < 1.0:
                time_display = f"🟡 {time_val:.3f}"
            elif time_val < 10.0:
                time_display = f"🟠 {time_val:.3f}"
            else:
                time_display = f"🔴 {time_val:.3f}"
            
            print(f"{i:<3} {endpoint:<35} {time_display:<15} {status:<8} {category:<15}")
        
        # Статистика по категориям
        print(f"\n📈 Статистика по категориям:")
        print("-" * 50)
        
        category_stats = {}
        for metric in self.performance_metrics:
            endpoint = metric['endpoint']
            category = categories.get(endpoint, "Прочие")
            if category not in category_stats:
                category_stats[category] = []
            category_stats[category].append(metric['execution_time'])
        
        for category, times in category_stats.items():
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            count = len(times)
            
            print(f"{category:<15}: Среднее: {avg_time:.3f}s | Мин: {min_time:.3f}s | Макс: {max_time:.3f}s | Тестов: {count}")
        
        # Общая статистика
        all_times = [m['execution_time'] for m in self.performance_metrics]
        total_time = sum(all_times)
        avg_time = total_time / len(all_times)
        fastest = min(all_times)
        slowest = max(all_times)
        
        print(f"\n🏆 Общая статистика производительности:")
        print("-" * 50)
        print(f"⚡ Самый быстрый эндпоинт: {fastest:.3f}s")
        print(f"🐌 Самый медленный эндпоинт: {slowest:.3f}s") 
        print(f"📊 Среднее время: {avg_time:.3f}s")
        print(f"⏱️ Общее время тестирования: {total_time:.3f}s")
        
        # Рекомендации
        print(f"\n💡 Рекомендации по оптимизации:")
        print("-" * 50)
        
        slow_endpoints = [m for m in sorted_metrics if m['execution_time'] > 10.0]
        if slow_endpoints:
            print("🔴 Медленные эндпоинты (>10s):")
            for endpoint in slow_endpoints:
                print(f"   - {endpoint['endpoint']}: {endpoint['execution_time']:.3f}s")
            print("   💡 Рекомендация: Рассмотреть кэширование или оптимизацию AI модели")
        
        medium_endpoints = [m for m in sorted_metrics if 1.0 < m['execution_time'] <= 10.0]
        if medium_endpoints:
            print("🟠 Средние эндпоинты (1-10s):")
            for endpoint in medium_endpoints:
                print(f"   - {endpoint['endpoint']}: {endpoint['execution_time']:.3f}s")
            print("   💡 Рекомендация: Нормальное время для AI операций")
        
        fast_endpoints = [m for m in sorted_metrics if m['execution_time'] <= 1.0]
        if fast_endpoints:
            print("🟢 Быстрые эндпоинты (<1s):")
            for endpoint in fast_endpoints:
                print(f"   - {endpoint['endpoint']}: {endpoint['execution_time']:.3f}s")
            print("   💡 Отличная производительность!")
    
    def print_detailed_summary(self):
        """Выводит детальную сводку тестирования"""
        print("\n" + "=" * 80)
        print("📊 ДЕТАЛЬНЫЙ АНАЛИЗ РЕЗУЛЬТАТОВ АВТОТЕСТИРОВАНИЯ")
        print("=" * 80)
        
        # Группировка по категориям
        categories = {
            "Базовые API": ["Health Check", "List Agents", "Cache Stats"],
            "Статические агенты": ["Static Agent Run (JSON)", "Multipart Agent Run", "Streaming Response"],
            "Динамические агенты": ["Dynamic Agents List", "Create Dynamic Agent", "Dynamic Agent Run", "Update Dynamic Agent", "Agent Sessions"],
            "Инструменты": ["Dynamic Tools List", "MCP Tools Status"],
            "Очистка": ["Cleanup Test Agent"]
        }
        
        for category, tests in categories.items():
            print(f"\n🔍 {category}:")
            category_results = [r for r in self.test_results if r['test'] in tests]
            passed = sum(1 for r in category_results if r['success'])
            total = len(category_results)
            
            print(f"    Результат: {passed}/{total} тестов пройдено ({passed/total*100:.1f}%)")
            
            for result in category_results:
                status = "✅" if result['success'] else "❌"
                print(f"    {status} {result['test']}")
                if result['details']:
                    print(f"        └─ {result['details']}")
        
        # Общая статистика
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['success'])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\n📈 ОБЩАЯ СТАТИСТИКА:")
        print(f"    Всего тестов: {total_tests}")
        print(f"    ✅ Пройдено: {passed_tests}")
        print(f"    ❌ Провалено: {failed_tests}")
        print(f"    📊 Процент успеха: {success_rate:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ ДЕТАЛИ НЕУДАЧНЫХ ТЕСТОВ:")
            for result in self.test_results:
                if not result['success']:
                    print(f"    🔥 {result['test']}: {result['details']}")
        
        return success_rate == 100.0
    
    async def run_all_tests(self):
        """Запуск всех тестов с детальной отчетностью"""
        print("🚀 Запуск ДЕТАЛЬНОГО автотеста системы agent-api")
        print("=" * 80)
        
        start_time = time.time()
        
        # Расширенная последовательность тестов
        tests = [
            ("Базовые API", [
                self.test_health_check,
                self.test_list_agents,
                self.test_cache_stats,
            ]),
            ("Статические агенты", [
                self.test_static_agent_run,
                self.test_multipart_agent_run,
                self.test_streaming_response,
            ]),
            ("Динамические агенты", [
                self.test_dynamic_agents_list,
                self.test_create_dynamic_agent,
                self.test_dynamic_agent_run,
                self.test_update_dynamic_agent,
                self.test_agent_sessions,
            ]),
            ("Инструменты", [
                self.test_dynamic_tools_list,
                self.test_mcp_tools_status,
            ]),
        ]
        
        # Запуск тестов по категориям
        for category_name, category_tests in tests:
            print(f"\n🔍 Тестирование: {category_name}")
            print("-" * 50)
            
            for test_func in category_tests:
                await test_func()
                await asyncio.sleep(0.3)  # Небольшая задержка
        
        # Очистка
        print(f"\n🧹 Очистка")
        print("-" * 50)
        await self.cleanup_test_agent()
        
        elapsed_time = time.time() - start_time
        
        # Отчет о производительности
        self.print_performance_report()
        
        # Детальная сводка
        success = self.print_detailed_summary()
        
        print(f"\n⏱️ Общее время выполнения: {elapsed_time:.2f} секунд")
        print("=" * 80)
        
        return success


async def main():
    """Главная функция детального автотеста"""
    print("🔧 ДЕТАЛЬНЫЙ автотест системы agent-api")
    print("🔍 Проверяет ВСЕ эндпоинты с подробными логами")
    print("📊 Включает анализ производительности и валидацию данных")
    print("Убедитесь что сервер запущен на http://localhost:8000")
    print()
    
    async with DetailedAgentAPITester() as tester:
        success = await tester.run_all_tests()
        
        if success:
            print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
            print("✨ Система agent-api полностью функциональна!")
            exit(0)
        else:
            print("💥 НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛИЛИСЬ!")
            print("🔧 Требуется дополнительная диагностика!")
            exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 