"""Only allowlisted messages cross HTTP/log boundaries."""


class AgentError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def invalid_output() -> AgentError:
    return AgentError("invalid_model_output", "模型未返回可展示的完整回答。", 502)
