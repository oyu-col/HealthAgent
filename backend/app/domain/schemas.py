from datetime import datetime
from typing import Annotated, Any, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

MetricType = Literal["weight", "heart_rate", "sleep_duration", "steps"]
MetricUnit = Literal["kg", "bpm", "hours", "count"]
ShortText = Annotated[str, Field(min_length=1, max_length=200)]


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class ToolResult(DomainModel):
    success: bool
    data: Any = None
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False

    @classmethod
    def ok(cls, data: Any) -> "ToolResult":
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, code: str, message: str, retryable: bool = False) -> "ToolResult":
        return cls(success=False, error_code=code, error_message=message, retryable=retryable)


class MetricInput(DomainModel):
    metric_type: MetricType
    value: float = Field(ge=0)
    unit: MetricUnit
    measured_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def compatible_unit(self) -> Self:
        units = {"weight": "kg", "heart_rate": "bpm", "sleep_duration": "hours", "steps": "count"}
        if self.unit != units[self.metric_type]:
            raise ValueError("unit does not match metric_type")
        if self.metric_type in {"weight", "heart_rate"} and self.value <= 0:
            raise ValueError("must be positive")
        if self.metric_type == "steps" and not self.value.is_integer():
            raise ValueError("steps must be integral")
        if self.metric_type == "sleep_duration" and self.value > 24:
            raise ValueError("sleep duration must be at most 24 hours")
        return self


class NutritionInfo(DomainModel):
    calories: float | None = Field(default=None, ge=0)
    protein_g: float | None = Field(default=None, ge=0)
    fat_g: float | None = Field(default=None, ge=0)
    carbohydrate_g: float | None = Field(default=None, ge=0)


class DietInput(DomainModel):
    food_name: ShortText
    amount: ShortText
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"]
    timestamp: AwareDatetime | None = None
    nutrition_info: NutritionInfo | None = None


class ExerciseInput(DomainModel):
    exercise_type: ShortText
    duration: float = Field(gt=0, le=1440, description="分钟")
    distance: float | None = Field(default=None, ge=0, description="公里")
    calories: float | None = Field(default=None, ge=0, description="用户提供的 kcal，不自动估算")
    timestamp: AwareDatetime | None = None


class QueryInput(DomainModel):
    start: AwareDatetime | None = None
    end: AwareDatetime | None = None
    metric_type: MetricType | None = None
    limit: int = Field(default=100, ge=1, le=200)

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.start and self.end and self.start > self.end:
            raise ValueError("start must precede end")
        return self


def iso_utc(value: datetime) -> str:
    from datetime import UTC

    return value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")
