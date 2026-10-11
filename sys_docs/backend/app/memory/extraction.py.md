# extraction.py：保守的显式偏好语法

- 对应源码：`backend/app/memory/extraction.py`
- 核对日期：2026-10-04
- 阅读：[源码](../../../../backend/app/memory/extraction.py) · [目录说明](README.md)

## 允许保存的内容

| key | 当前允许值 |
| --- | --- |
| response_style | concise、detailed |
| language | zh、en |
| diet_preference | light、vegetarian、no_spicy |
| exercise_preference | walking、running、swimming、cycling、yoga |

PreferenceKey 是类型 Literal；ALLOWED_VALUES 是运行时白名单；PHRASES 把“简短的回答、详细的回答、清淡饮食、素食、不辣的食物、散步、跑步、游泳、骑行、瑜伽”映射到对应值。FORGET_KEYS 映射“回答风格、语言偏好、饮食偏好、运动偏好”四种删除目标。

## extract_preferences(text) 的算法

先检查整段是否含英文单双引号、中文引号、反引号或 >；只要包含任一字符，整段返回 []，避免引用文档/代码被当作用户保存授权。这是保守字符串规则，不是完整语法树或 prompt injection 检测器，合法混合引用也可能被忽略。

按中文句号、中文/英文分号、换行切句；去首尾空白和末尾 !/！/英文句点。每句使用 fullmatch：

- “请记住（可选冒号） 我（可选现在）（可选更）喜欢/偏好＋精确短语”；
- “以后请用中文/英文回答”；
- “请忘记（可选冒号） 我的精确偏好类别”。

只有整句匹配且命中词表才生成变化。同一段多次写同 key 时字典后值覆盖前值；删除用 value=None。返回 [{key,value},…]，不返回用户原句，不联网、不调用模型、不存储数据。

## 安全边界与实际限制

“请记住我体重70kg”“我不喜欢跑步”“忽略规则”等不会变成自由文本记忆。否定偏好不自动反推正面偏好；复合描述、同义词或疑问表达可能无法匹配。标点切分也不包含英文问号、中文逗号等所有符号，不应宣称任意自然语言都能理解。

[MemoryService](../services/memory.py.md) 接收变化并落库；[中间件](middleware.py.md) 仅将本次用户消息送入此函数，不将检索片段或助手文本当用户授权。[测试](../../tests/integration/test_memory.py.md) 明确覆盖健康事实、否定、引用和恶意指令不写入。扩展 PHRASES 必须评估是否会把事实或引述误认成保存意愿。
