# Loom Studio 设计文档

## 一、概述

### 1.1 核心目标

Loom Studio 是一个**实时可视化调试器**，旨在将 Loom 框架中"不可见的自组织过程"转化为直观的视觉体验。

**设计理念**：
- **非侵入式**：零代码修改，通过事件流被动观测
- **实时性**：毫秒级延迟的事件流可视化
- **分形一致性**：UI 结构映射运行时节点拓扑
- **协议优先**：基于 CloudEvents 标准，与传输层无关

### 1.2 核心价值

| 用户角色 | 痛点 | Loom Studio 解决方案 |
|---------|------|---------------------|
| **开发者** | Agent 黑盒执行，无法理解决策过程 | 实时显示 ReAct 循环、工具调用链 |
| **架构师** | 复杂的 Crew/Router 编排难以调试 | 可视化节点拓扑和消息流转 |
| **研究者** | 记忆系统（Metabolic Memory）行为不透明 | 展示记忆新陈代谢过程和 PSO 状态 |
| **运维人员** | 生产环境问题难以复现 | 事件回放和时间旅行调试 |

### 1.3 技术栈选型

```
前端：React + TypeScript + D3.js/Cytoscape.js
后端：FastAPI (Python) + WebSocket
数据层：EventStore (已有) + Redis (可选，用于分布式部署)
协议：CloudEvents 1.0 + WebSocket Binary Protocol
```

---

## 二、架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Loom Studio (前端)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  拓扑视图     │  │  时间线视图   │  │  状态检查器   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  记忆浏览器   │  │  日志面板     │  │  性能监控     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↕ WebSocket
┌─────────────────────────────────────────────────────────────┐
│                   Studio Server (FastAPI)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Event Stream │  │ Query API    │  │ Replay Engine│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                      Loom 核心框架                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              StudioInterceptor (新增)                 │   │
│  │  - 捕获所有事件并转发到 Studio Server                 │   │
│  │  - 零性能开销（异步非阻塞）                            │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Dispatcher  │  │  EventStore  │  │  Nodes       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件

#### 2.2.1 StudioInterceptor（框架侧）

**文件位置**：`loom/kernel/interceptors/studio.py`

```python
class StudioInterceptor(Interceptor):
    """
    Studio 拦截器：捕获所有事件并转发到 Studio Server

    特性：
    - 异步非阻塞：使用 asyncio.create_task 避免影响主流程
    - 可选启用：通过环境变量 LOOM_STUDIO_ENABLED 控制
    - 批量发送：缓冲事件批量发送，减少网络开销
    """

    def __init__(self, studio_url: str = "ws://localhost:8765"):
        self.studio_url = studio_url
        self.ws: Optional[WebSocketClientProtocol] = None
        self.event_buffer: List[CloudEvent] = []
        self.buffer_size = 10
        self.enabled = os.getenv("LOOM_STUDIO_ENABLED", "false") == "true"

        if self.enabled:
            asyncio.create_task(self._connect())

    async def _connect(self):
        """建立 WebSocket 连接"""
        try:
            self.ws = await websockets.connect(self.studio_url)
            logger.info(f"Connected to Loom Studio at {self.studio_url}")
        except Exception as e:
            logger.warning(f"Failed to connect to Studio: {e}")
            self.enabled = False

    async def pre_invoke(self, event: CloudEvent) -> Optional[CloudEvent]:
        """捕获事件（pre阶段）"""
        if self.enabled and self.ws:
            # 添加时间戳和阶段标记
            enriched_event = event.model_copy(deep=True)
            enriched_event.extensions["studio_phase"] = "pre"
            enriched_event.extensions["studio_timestamp"] = time.time()

            # 异步发送，不阻塞主流程
            asyncio.create_task(self._send_event(enriched_event))

        return event  # 不修改原事件

    async def post_invoke(self, event: CloudEvent) -> None:
        """捕获事件（post阶段）"""
        if self.enabled and self.ws:
            enriched_event = event.model_copy(deep=True)
            enriched_event.extensions["studio_phase"] = "post"
            enriched_event.extensions["studio_timestamp"] = time.time()

            asyncio.create_task(self._send_event(enriched_event))

    async def _send_event(self, event: CloudEvent):
        """发送事件到 Studio Server"""
        try:
            self.event_buffer.append(event)

            # 批量发送
            if len(self.event_buffer) >= self.buffer_size:
                await self._flush_buffer()
        except Exception as e:
            logger.error(f"Failed to send event to Studio: {e}")

    async def _flush_buffer(self):
        """批量发送缓冲区事件"""
        if not self.event_buffer:
            return

        batch = {
            "type": "event_batch",
            "events": [e.model_dump() for e in self.event_buffer]
        }

        await self.ws.send(json.dumps(batch))
        self.event_buffer.clear()
```

**启用方式**：

```python
# 方式1：环境变量
export LOOM_STUDIO_ENABLED=true
export LOOM_STUDIO_URL=ws://localhost:8765

# 方式2：代码配置
app = LoomApp()
app.dispatcher.add_interceptor(StudioInterceptor(studio_url="ws://localhost:8765"))
```

#### 2.2.2 Studio Server（后端服务）

**文件位置**：`loom/studio/server.py`

Studio Server 是一个独立的 FastAPI 应用，提供三大核心功能：

##### A. 实时事件流 (Event Stream)

```python
from fastapi import FastAPI, WebSocket
from fastapi.websockets import WebSocketDisconnect
import asyncio
from typing import Set

app = FastAPI()

class ConnectionManager:
    """管理所有 WebSocket 连接"""
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.event_queue: asyncio.Queue = asyncio.Queue()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    async def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """广播事件到所有连接的前端"""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)

        # 清理断开的连接
        self.active_connections -= disconnected

manager = ConnectionManager()

@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    """前端连接：接收实时事件流"""
    await manager.connect(websocket)
    try:
        while True:
            # 保持连接活跃
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)

@app.websocket("/ws/ingest")
async def ingest_endpoint(websocket: WebSocket):
    """框架连接：接收来自 StudioInterceptor 的事件"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()

            if data["type"] == "event_batch":
                # 处理批量事件
                for event in data["events"]:
                    # 存储到 EventStore
                    await event_store.append(event)

                    # 广播到所有前端
                    await manager.broadcast({
                        "type": "event",
                        "data": event
                    })
    except WebSocketDisconnect:
        pass
```

##### B. 查询 API (Query API)

```python
from fastapi import Query
from typing import Optional, List

@app.get("/api/events")
async def get_events(
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    trace_id: Optional[str] = None,
    node_id: Optional[str] = None,
    event_type: Optional[str] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None
):
    """
    查询历史事件

    支持的过滤条件：
    - trace_id: 追踪特定调用链
    - node_id: 过滤特定节点的事件
    - event_type: 过滤事件类型（如 agent.thought）
    - start_time/end_time: 时间范围
    """
    filters = {}
    if trace_id:
        filters["traceparent__contains"] = trace_id
    if node_id:
        filters["source__contains"] = node_id
    if event_type:
        filters["type"] = event_type
    if start_time:
        filters["time__gte"] = start_time
    if end_time:
        filters["time__lte"] = end_time

    events = await event_store.get_events(
        limit=limit,
        offset=offset,
        **filters
    )

    return {"events": events, "total": len(events)}

@app.get("/api/topology")
async def get_topology():
    """
    获取节点拓扑结构

    返回格式：
    {
        "nodes": [
            {"id": "agent_1", "type": "AgentNode", "role": "Researcher"},
            {"id": "tool_1", "type": "ToolNode", "name": "calculator"}
        ],
        "edges": [
            {"from": "agent_1", "to": "tool_1", "count": 5}
        ]
    }
    """
    # 从事件流中推断拓扑
    events = await event_store.get_events(limit=1000)

    nodes = {}
    edges = {}

    for event in events:
        source = event.get("source")
        subject = event.get("subject")

        # 记录节点
        if source and source not in nodes:
            nodes[source] = {
                "id": source,
                "type": _infer_node_type(event),
                "metadata": {}
            }

        # 记录边（调用关系）
        if source and subject:
            edge_key = f"{source}->{subject}"
            edges[edge_key] = edges.get(edge_key, 0) + 1

    return {
        "nodes": list(nodes.values()),
        "edges": [
            {"from": k.split("->")[0], "to": k.split("->")[1], "count": v}
            for k, v in edges.items()
        ]
    }

@app.get("/api/memory/{node_id}")
async def get_memory(node_id: str):
    """
    获取节点的记忆状态

    通过分析事件流重建记忆状态
    """
    # 查找该节点的所有记忆相关事件
    events = await event_store.get_events(
        source__contains=node_id,
        type__in=["memory.add", "memory.consolidate"]
    )

    memory_entries = []
    for event in events:
        if event["type"] == "memory.add":
            memory_entries.append(event["data"])

    return {"node_id": node_id, "memory": memory_entries}
```

##### C. 回放引擎 (Replay Engine)

```python
class ReplayEngine:
    """事件回放引擎：时间旅行调试"""

    def __init__(self, event_store):
        self.event_store = event_store
        self.replay_sessions: Dict[str, ReplaySession] = {}

    async def create_replay_session(
        self,
        trace_id: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> str:
        """
        创建回放会话

        Args:
            trace_id: 要回放的调用链ID
            start_time: 起始时间（可选）
            end_time: 结束时间（可选）

        Returns:
            session_id: 回放会话ID
        """
        # 获取该 trace 的所有事件
        events = await self.event_store.get_events(
            traceparent__contains=trace_id,
            time__gte=start_time,
            time__lte=end_time
        )

        # 按时间排序
        events.sort(key=lambda e: e.get("time", 0))

        session_id = str(uuid.uuid4())
        self.replay_sessions[session_id] = ReplaySession(
            session_id=session_id,
            events=events,
            current_index=0
        )

        return session_id

    async def step_forward(self, session_id: str) -> Optional[dict]:
        """前进一步"""
        session = self.replay_sessions.get(session_id)
        if not session or session.current_index >= len(session.events):
            return None

        event = session.events[session.current_index]
        session.current_index += 1

        return {
            "event": event,
            "index": session.current_index,
            "total": len(session.events)
        }

    async def step_backward(self, session_id: str) -> Optional[dict]:
        """后退一步"""
        session = self.replay_sessions.get(session_id)
        if not session or session.current_index <= 0:
            return None

        session.current_index -= 1
        event = session.events[session.current_index]

        return {
            "event": event,
            "index": session.current_index,
            "total": len(session.events)
        }

    async def jump_to(self, session_id: str, index: int) -> Optional[dict]:
        """跳转到指定位置"""
        session = self.replay_sessions.get(session_id)
        if not session or index < 0 or index >= len(session.events):
            return None

        session.current_index = index
        event = session.events[index]

        return {
            "event": event,
            "index": index,
            "total": len(session.events)
        }

# API 端点
@app.post("/api/replay/create")
async def create_replay(trace_id: str):
    """创建回放会话"""
    session_id = await replay_engine.create_replay_session(trace_id)
    return {"session_id": session_id}

@app.post("/api/replay/{session_id}/step")
async def replay_step(session_id: str, direction: str = "forward"):
    """单步执行"""
    if direction == "forward":
        result = await replay_engine.step_forward(session_id)
    else:
        result = await replay_engine.step_backward(session_id)

    return result or {"error": "No more events"}

@app.post("/api/replay/{session_id}/jump")
async def replay_jump(session_id: str, index: int):
    """跳转到指定位置"""
    result = await replay_engine.jump_to(session_id, index)
    return result or {"error": "Invalid index"}
```

---

## 三、前端组件设计

### 3.1 拓扑视图 (Topology View)

**技术选型**：Cytoscape.js（图可视化库）

**功能**：
- 实时显示节点拓扑结构
- 节点类型区分（Agent/Tool/Crew/Router）
- 边的粗细表示调用频率
- 点击节点查看详细信息

**实现示例**：

```typescript
import Cytoscape from 'cytoscape';
import { useEffect, useRef } from 'react';

interface TopologyViewProps {
  nodes: Array<{id: string, type: string, metadata: any}>;
  edges: Array<{from: string, to: string, count: number}>;
}

export const TopologyView: React.FC<TopologyViewProps> = ({ nodes, edges }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<any>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // 初始化 Cytoscape
    cyRef.current = Cytoscape({
      container: containerRef.current,
      elements: [
        // 节点
        ...nodes.map(node => ({
          data: {
            id: node.id,
            label: node.id,
            type: node.type
          }
        })),
        // 边
        ...edges.map(edge => ({
          data: {
            source: edge.from,
            target: edge.to,
            weight: edge.count
          }
        }))
      ],
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'background-color': (ele: any) => {
              const type = ele.data('type');
              return type === 'AgentNode' ? '#4CAF50' :
                     type === 'ToolNode' ? '#2196F3' :
                     type === 'CrewNode' ? '#FF9800' : '#9C27B0';
            },
            'width': 60,
            'height': 60
          }
        },
        {
          selector: 'edge',
          style: {
            'width': (ele: any) => Math.min(ele.data('weight'), 10),
            'line-color': '#ccc',
            'target-arrow-color': '#ccc',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier'
          }
        }
      ],
      layout: {
        name: 'cose',  // 力导向布局
        animate: true
      }
    });

    // 点击节点事件
    cyRef.current.on('tap', 'node', (evt: any) => {
      const node = evt.target;
      console.log('Node clicked:', node.data());
      // 触发详情面板
    });

  }, [nodes, edges]);

  return <div ref={containerRef} style={{ width: '100%', height: '600px' }} />;
};
```

### 3.2 时间线视图 (Timeline View)

**技术选型**：D3.js + React

**功能**：
- 按时间顺序展示所有事件
- 支持事件类型过滤
- 支持时间范围缩放
- 点击事件查看详情

**实现示例**：

```typescript
import * as d3 from 'd3';
import { useEffect, useRef } from 'react';

interface TimelineEvent {
  id: string;
  type: string;
  time: number;
  source: string;
  data: any;
}

export const TimelineView: React.FC<{events: TimelineEvent[]}> = ({ events }) => {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || events.length === 0) return;

    const svg = d3.select(svgRef.current);
    const width = 1200;
    const height = 400;
    const margin = { top: 20, right: 20, bottom: 30, left: 50 };

    // 清空之前的内容
    svg.selectAll('*').remove();

    // 时间比例尺
    const xScale = d3.scaleTime()
      .domain([
        new Date(Math.min(...events.map(e => e.time * 1000))),
        new Date(Math.max(...events.map(e => e.time * 1000)))
      ])
      .range([margin.left, width - margin.right]);

    // 事件类型映射到Y轴
    const eventTypes = Array.from(new Set(events.map(e => e.type)));
    const yScale = d3.scaleBand()
      .domain(eventTypes)
      .range([margin.top, height - margin.bottom])
      .padding(0.1);

    // 绘制X轴（时间轴）
    svg.append('g')
      .attr('transform', `translate(0,${height - margin.bottom})`)
      .call(d3.axisBottom(xScale));

    // 绘制Y轴（事件类型）
    svg.append('g')
      .attr('transform', `translate(${margin.left},0)`)
      .call(d3.axisLeft(yScale));

    // 绘制事件点
    svg.selectAll('circle')
      .data(events)
      .enter()
      .append('circle')
      .attr('cx', d => xScale(new Date(d.time * 1000)))
      .attr('cy', d => (yScale(d.type) || 0) + (yScale.bandwidth() / 2))
      .attr('r', 5)
      .attr('fill', d => {
        // 根据事件类型着色
        if (d.type.includes('agent')) return '#4CAF50';
        if (d.type.includes('tool')) return '#2196F3';
        if (d.type.includes('error')) return '#F44336';
        return '#9E9E9E';
      })
      .attr('opacity', 0.7)
      .on('click', (event, d) => {
        console.log('Event clicked:', d);
        // 显示事件详情
      })
      .on('mouseover', function() {
        d3.select(this).attr('r', 8).attr('opacity', 1);
      })
      .on('mouseout', function() {
        d3.select(this).attr('r', 5).attr('opacity', 0.7);
      });

  }, [events]);

  return (
    <svg ref={svgRef} width={1200} height={400} />
  );
};
```

### 3.3 记忆浏览器 (Memory Browser)

**功能**：
- 展示 Agent 的记忆状态
- 支持分层记忆可视化（Session/Working/Long-term）
- 展示 Metabolic Memory 的新陈代谢过程
- 显示 PSO（项目状态对象）

**实现示例**：

```typescript
interface MemoryEntry {
  role: string;
  content: string;
  timestamp: number;
  tier: string;
  importance?: number;
}

export const MemoryBrowser: React.FC<{nodeId: string}> = ({ nodeId }) => {
  const [memory, setMemory] = useState<MemoryEntry[]>([]);
  const [pso, setPso] = useState<any>(null);

  useEffect(() => {
    // 获取记忆数据
    fetch(`/api/memory/${nodeId}`)
      .then(res => res.json())
      .then(data => {
        setMemory(data.memory);
        setPso(data.pso);
      });
  }, [nodeId]);

  // 按层级分组
  const groupedMemory = memory.reduce((acc, entry) => {
    const tier = entry.tier || 'session';
    if (!acc[tier]) acc[tier] = [];
    acc[tier].push(entry);
    return acc;
  }, {} as Record<string, MemoryEntry[]>);

  return (
    <div className="memory-browser">
      <h3>记忆状态 - {nodeId}</h3>

      {/* 分层记忆 */}
      {Object.entries(groupedMemory).map(([tier, entries]) => (
        <div key={tier} className="memory-tier">
          <h4>{tier.toUpperCase()} Memory ({entries.length})</h4>
          <div className="memory-entries">
            {entries.map((entry, idx) => (
              <div key={idx} className="memory-entry">
                <span className="role">{entry.role}</span>
                <span className="content">{entry.content.substring(0, 100)}...</span>
                {entry.importance && (
                  <span className="importance">
                    重要性: {(entry.importance * 100).toFixed(0)}%
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* PSO 状态 */}
      {pso && (
        <div className="pso-state">
          <h4>项目状态对象 (PSO)</h4>
          <pre>{JSON.stringify(pso, null, 2)}</pre>
        </div>
      )}
    </div>
  );
};
```

---

## 四、实现路线图

### 阶段 1：核心基础设施（2-3周）

**目标**：建立基本的事件捕获和传输机制

**任务**：
1. 实现 `StudioInterceptor`
   - 事件捕获逻辑
   - WebSocket 客户端连接
   - 批量发送机制

2. 实现 Studio Server 基础框架
   - FastAPI 应用搭建
   - WebSocket 双向通信
   - EventStore 集成

3. 前端项目初始化
   - React + TypeScript 项目搭建
   - WebSocket 客户端封装
   - 基础 UI 框架

**验收标准**：
- 能够捕获并实时传输事件到前端
- 前端能够接收并显示原始事件数据

### 阶段 2：可视化组件（3-4周）

**目标**：实现核心可视化功能

**任务**：
1. 拓扑视图
   - Cytoscape.js 集成
   - 节点拓扑推断算法
   - 交互功能（缩放、拖拽、点击）

2. 时间线视图
   - D3.js 时间轴实现
   - 事件过滤和搜索
   - 时间范围缩放

3. 记忆浏览器
   - 记忆状态展示
   - 分层记忆可视化
   - PSO 状态显示

**验收标准**：
- 三个核心视图功能完整
- 实时更新流畅（<100ms 延迟）

### 阶段 3：高级功能（2-3周）

**目标**：实现调试和分析功能

**任务**：
1. 回放引擎
   - 时间旅行调试
   - 单步执行
   - 断点功能

2. 性能监控
   - Token 使用统计
   - 响应时间分析
   - 瓶颈识别

3. 查询和过滤
   - 高级事件查询
   - 调用链追踪
   - 导出功能

**验收标准**：
- 支持完整的调试工作流
- 性能数据准确可靠

---

## 五、关键技术挑战与解决方案

### 5.1 性能优化

**挑战**：高频事件流可能导致前端卡顿

**解决方案**：
1. **事件批量处理**：后端批量发送，前端批量渲染
2. **虚拟滚动**：时间线和日志面板使用虚拟列表
3. **Web Worker**：在后台线程处理事件解析
4. **增量更新**：拓扑图使用增量更新而非全量重绘

### 5.2 分布式部署

**挑战**：多个 Loom 实例如何共享 Studio

**解决方案**：
1. **Redis Pub/Sub**：使用 Redis 作为事件中转
2. **会话隔离**：每个 Loom 实例有独立的 session_id
3. **多租户支持**：Studio Server 支持多个实例同时连接

### 5.3 数据持久化

**挑战**：大量事件数据的存储和查询

**解决方案**：
1. **时序数据库**：使用 InfluxDB 或 TimescaleDB
2. **数据压缩**：事件内容压缩存储
3. **自动清理**：定期清理过期数据（默认保留7天）

