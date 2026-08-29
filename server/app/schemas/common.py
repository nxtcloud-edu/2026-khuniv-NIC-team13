from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    code: str = Field(default="SUCCESS")
    message: str = "OK"
    data: T | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    code: str = Field(default="ERROR")
    message: str
    data: object | None = None


class ApiResponse(BaseModel):
    success: bool
    code: str
    message: str
    data: Any = None


class HealthData(BaseModel):
    status: str
    app: str
    env: str


def success_response(data: Any = None, message: str = "OK", code: str = "SUCCESS") -> dict[str, Any]:
    return {"success": True, "code": code, "message": message, "data": data}


def error_response(code: str, message: str, data: Any = None) -> dict[str, Any]:
    return {"success": False, "code": code, "message": message, "data": data}
