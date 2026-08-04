from typing import TypeVar, Generic, Optional
from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: str = ""
    errors: list[str] = []


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    pages: int = 0


def success_response(data=None, message="Success") -> dict:
    return {"success": True, "data": data, "message": message}


def error_response(message="Error", errors=None) -> dict:
    return {"success": False, "message": message, "errors": errors or []}
