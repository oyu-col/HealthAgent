- 对应源码：`benchmark/__init__.py`
- 核对日期：2026-10-11
- 阅读源码：[__init__.py](../../benchmark/__init__.py)
- 所属目录：[目录说明](README.md)

# Benchmark 包入口与生产边界

## 实际作用

文件只有模块文档字符串，声明这是独立的合成领域评测包，不属于生产请求路径。它使benchmark成为显式Python包，便于runner和测试以benchmark.schema、benchmark.report等路径导入。

## 为什么保持轻量

导入benchmark不应启动服务、创建数据库、读模型配置或发起网络请求。实际模型与存储生命周期由[runner.py](runner.py.md)显式管理。不要在此处加入自动跑分、全局模型客户端或加载.env的代码，否则单元测试导入评测模块就会产生外部行为。

## 验证与限制

本文件不实现判分或注册逻辑，也不是CLI入口；执行入口是runner.py或report.py的main。包能导入不等于案例正确或评测成功。

