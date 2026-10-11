- 对应源码：`backend/app/api/memory.py`
- 核对日期：2026-10-04
- 阅读源码：[memory.py](../../../../backend/app/api/memory.py)
- 所属目录：[目录说明](README.md)

# 显式长期偏好管理接口

## 定位与设计目的

/api/memory 提供查看、修改和忘记偏好，补充对话内的有限句式提取。这里只管理 allowlist 偏好，不保存身体指标、病史或完整对话。

## 输入输出和主要函数

- get_memory：memory.list(user_id) 获取当前用户偏好，同时返回 ALLOWED_VALUES 的排序列表供前端生成选项。
- update_memory：PUT /{key}；路径 key 由 PreferenceKey 枚举校验，body 为 PreferenceRequest，value 长度 1–32，额外字段被禁止；交给 memory.update 后以 changes 包装返回。
- delete_memory：DELETE /{key}；向同一 update 方法传 value=None，表示删除该键。

## 真实边界

value 虽是字符串且通过长度校验，仍需 MemoryService 检查该 key 的允许值。响应 changes 是实际服务结果，不能仅凭发出请求就显示已记住。
所有操作都使用服务端身份；没有任意 JSON Memory 编辑、全量健康事实删除或跨用户偏好查询。删除接口本身没有额外 confirm 参数；当前显式确认由前端交互提供，后端接收已授权的删除请求。

## 关联与修改注意

自动提取和手工接口最终进入同一个 MemoryService，因此修改允许枚举要同步 extraction、服务验证和前端中文标签。test_memory 关注提取、持久化、来源及隔离；前端 Memory.tsx 负责允许值选择和确认忘记。

## 相关源码说明

- [backend/app/memory/extraction.py](../memory/extraction.py.md)
- [backend/app/services/memory.py](../services/memory.py.md)
- [backend/tests/integration/test_memory.py](../../tests/integration/test_memory.py.md)
- [frontend/src/components/Memory.tsx](../../../frontend/src/components/Memory.tsx.md)

