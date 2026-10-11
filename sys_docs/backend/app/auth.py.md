# auth.py：服务端可信身份

- 对应源码：`backend/app/auth.py`
- 核对日期：2026-10-04
- 目录导航：[本目录说明](README.md)
- 源码：[auth.py](../../../backend/app/auth.py)

## current_user 如何工作

FastAPI 依赖 `current_user` 从 Settings 决定认证方式。在 local 模式直接返回 `local_user_id`，即当前服务只有一个固定本地身份；传入请求体 user_id 或 X-User-ID 不能切换 owner。local 适合回环地址上的单用户使用，不等同于登录系统。

token 模式读取 Authorization，要求符合代码中 `Bearer ` 前缀。取出 token 后遍历服务器的 API_TOKENS，使用 `secrets.compare_digest` 比较已配置秘密，成功时返回对应 user_id。缺失、前缀不符或比较不匹配时抛出 AgentError 的 unauthorized，HTTP 状态 401，不透露哪位用户或哪段凭据接近匹配。当前函数没有捕获 compare_digest 自身可能抛出的类型错误，因此不能概括为所有非法输入都由此返回 401。

`UserDependency` 用 Annotated[str, Depends(current_user)] 给路由声明参数，使身份来源统一且便于测试。

## 权限链路

身份验证只确认 owner，数据访问还要依靠 Service/Repository 的 user_id 过滤。路由将可信 user_id 传给业务服务或 RunContext；工具通过隐藏的 runtime context 获取它，而不是让模型在工具参数里填写。跨用户资源通常以 404 等方式表现，由具体路由/服务决定，不是本文件统一处理所有授权错误。

本实现没有注册、密码登录、token 刷新、角色管理或共享部署的完整认证后台。API_TOKENS 是静态配置映射，修改后需通过重新创建应用加载。不要在调试日志中打印 Authorization。

关联：[Settings](config.py.md)、[API 目录](api/README.md)、[健康工具集成测试](../tests/integration/test_health_tools.py.md)、[UI API 隔离测试](../tests/integration/test_ui_api.py.md)。
