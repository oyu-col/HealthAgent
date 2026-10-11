- 对应源码：`backend/app/api/session.py`
- 核对日期：2026-10-04
- 阅读源码：[session.py](../../../../backend/app/api/session.py)
- 所属目录：[目录说明](README.md)

# 可信会话配置查询

## 功能与设计目的

`GET /api/session` 是前端进入工作空间时的身份与能力探测接口。SessionResponse 仅返回当前可信 user_id、model_mode、timezone、memory_enabled，使 UI 能展示演示模式、显示时间和偏好功能状态。

## 关键执行过程

current_session 先通过 UserDependency 获取已认证身份，再从 app.state.settings 读取三项可公开配置，构造 Pydantic 响应。这里的 session 指浏览器当前连接上下文，不会创建聊天 thread，也没有登录 cookie 或服务端会话令牌生成。

## 权限与隐私边界

客户端不能通过 query/body 指定用户身份；不返回 API token、模型密钥、provider URL 或完整 Settings。token 模式下凭据验证失败由依赖/全局异常边界处理。memory_enabled 表明配置开关，不代表偏好表中一定有数据。

## 调用者与验证

前端 App 在初次连接和更换凭据时调用本接口，之后 remount 工作空间以隔离旧用户数据。test_ui_api 验证返回真实身份而不泄露秘密，并验证 token 认证行为。扩展字段应只加入 UI 真正需要的公开能力，不直接序列化整个配置对象。

## 相关源码说明

- [backend/app/auth.py](../auth.py.md)
- [backend/app/config.py](../config.py.md)
- [frontend/src/App.tsx](../../../frontend/src/App.tsx.md)
- [backend/tests/integration/test_ui_api.py](../../tests/integration/test_ui_api.py.md)

