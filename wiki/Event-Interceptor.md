# 事件拦截器 (Event Interceptor)

## 定义

**事件拦截器**是在不修改节点代码的情况下添加横切关注点的机制。

## 核心思想

AOP (Aspect-Oriented Programming) 在事件系统中的应用：
- 日志记录
- 性能监控
- 错误处理
- 认证授权

## 实现拦截器

```python
from loom.runtime import Interceptor

class LoggingInterceptor(Interceptor):
    async def intercept(self, context, next_handler):
        # 前置处理
        print(f"Before: {context.event}")

        # 调用下一个处理器
        result = await next_handler()

        # 后置处理
        print(f"After: {result}")
        return result

# 注册拦截器
event_bus.register_interceptor(LoggingInterceptor())
```

## 常用拦截器

### 1. 性能拦截器

```python
class PerformanceInterceptor(Interceptor):
    async def intercept(self, context, next_handler):
        start = time.time()
        result = await next_handler()
        duration = time.time() - start
        print(f"Duration: {duration}s")
        return result
```

### 2. 错误拦截器

```python
class ErrorInterceptor(Interceptor):
    async def intercept(self, context, next_handler):
        try:
            return await next_handler()
        except Exception as e:
            print(f"Error: {e}")
            await self._notify_error(e)
            raise
```

### 3. 认证拦截器

```python
class AuthInterceptor(Interceptor):
    async def intercept(self, context, next_handler):
        if not self._is_authorized(context.event):
            raise UnauthorizedError()
        return await next_handler()
```

## 拦截器链

```python
# 按顺序注册
event_bus.register_interceptor(AuthInterceptor())
event_bus.register_interceptor(LoggingInterceptor())
event_bus.register_interceptor(PerformanceInterceptor())

# 执行顺序: Auth → Logging → Performance → Handler
```

## 相关概念

- → [事件总线](Event-Bus)
- → [可观测性](Observability)

## 代码位置

- `loom/runtime/interceptor.py`

## 反向链接

被引用于: [事件总线](Event-Bus) | [可观测性](Observability)
