- 对应源码：`backend/app/agent/errors.py`
- 核对日期：2026-10-04
- 阅读源码：[errors.py](../../../../backend/app/agent/errors.py)
- 所属目录：[目录说明](README.md)

# 可公开的执行错误类型

## 实际实现

AgentError 继承 Exception，保存 code、message、status_code；传给父类的也是已整理过的 message。invalid_output() 返回固定的 invalid_model_output/502，提示模型没有提供可展示的完整回答。

## 设计目的与调用链

Runtime、服务和中间件用它表达“已分类、可以跨 HTTP 边界返回”的错误；main.py 统一生成 ErrorResponse，流式路由则生成 run.failed。extract_answer 对非终态、仅隐藏内容或空答案调用 invalid_output。

## 安全边界

此类本身不会脱敏任意字符串，也不检查错误码是否属于枚举。安全性来自调用方只传固定允许消息，不能把 str(provider_exception)、提示词或完整工具参数塞进 message。上下文关联标识由请求/执行层补充，不在错误类型内保存用户健康原文。

## 修改注意

新增错误码需同时考虑 HTTP 状态、客户端恢复策略、Trace 终止原因和测试断言。不要用一个“成功答案字符串”代替 AgentError，否则前端会误判执行完成。

## 相关源码说明

- [backend/app/agent/runtime.py](runtime.py.md)
- [backend/app/main.py](../main.py.md)
- [backend/app/api/stream.py](../api/stream.py.md)
- [backend/tests/unit/test_runtime.py](../../tests/unit/test_runtime.py.md)

