- 对应源码：`backend/tests/unit/test_config.py`
- 核对日期：2026-10-04
- 阅读源码：[test_config.py](../../../../backend/tests/unit/test_config.py)
- 所属目录：[目录说明](README.md)

# 配置校验与敏感信息保护单元测试

## 测试目的与范围

验证 Settings 接受哪些配置、拒绝哪些危险或无效值，以及启动错误是否脱敏。测试使用 _env_file=None 或临时 .env，不依赖项目真实配置，更不读取真实模型密钥。

## 具体测试组与断言意义

| 测试 | 核心断言 |
| --- | --- |
| test_mode_must_be_explicit | 未明确 model_mode 会校验失败，防止静默选真实模型或 fake。 |
| test_invalid_settings | 参数化覆盖未知模式、步骤/输入/重试/委派/并发上下限、非有限超时、空用户、无效时区、非 HTTP URL、URL 内用户名密码和查询串。 |
| test_provider_has_no_implicit_credentials | 仅设置无关 OPENAI_API_KEY 仍不足以通过 provider 模式配置。 |
| test_provider_requires_key | provider 的缺失、空串和纯空格密钥均拒绝。 |
| test_provider_config_and_secret_repr | 完整合成配置可用，时区默认 Asia/Shanghai，repr 不包含合成秘密或 provider 域名。 |
| test_env_path_is_project_root_and_explicit_files_work | 默认 env_file 固定项目根；显式临时文件可加载中文用户，即使改变当前工作目录。 |
| test_startup_error_does_not_disclose_invalid_value | load_settings 捕获底层异常后不输出合成敏感字符串，并 suppress 异常上下文。 |

## 输入、依赖与边界

pytest.parametrize 提供边界值，monkeypatch 修改/恢复环境与 cwd，tmp_path 创建仅供本用例使用的配置。用例证明配置程序的行为，不证明合成 URL 可以联网，也不验证真实凭据。
部分测试直接构造 Settings，区别于运行服务时读取项目根 .env 的正常路径；不要把测试便利写法传播成生产隐式配置。

## 维护建议

新增 Settings 字段时，为有实际后果的范围和跨字段约束补充用例；不要只测试默认值。继续用虚构密钥，并断言错误信息不回显非法输入原值。可在 backend 下针对性运行 pytest tests/unit/test_config.py；本说明编写时未重新执行测试。

## 相关源码说明

- [backend/app/config.py](../../app/config.py.md)
- [backend/tests/conftest.py](../conftest.py.md)

