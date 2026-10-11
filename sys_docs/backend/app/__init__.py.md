# app/__init__.py：Python 包标识

- 对应源码：`backend/app/__init__.py`
- 核对日期：2026-10-04
- 目录导航：[本目录说明](README.md)
- 源码：[__init__.py](../../../backend/app/__init__.py)

当前文件仅提供包说明 docstring，没有函数、类、导出聚合或初始化代码。它将 app 明确标识为 Python 包，支持 `app.main`、`app.config` 等导入路径及打包规则。

设计上将资源创建留给 [main.py](main.py.md) 的 create_app/lifespan，避免导入包就连接模型、读取健康数据或打开数据库。不要为方便导出而在这里导入有启动副作用的模块。它不负责 CLI、版本解析或插件注册。
