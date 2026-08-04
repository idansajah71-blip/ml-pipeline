from typing import TypeVar, Generic, List, Optional
from pydantic import BaseModel
from math import ceil

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = 1
    per_page: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        return self.per_page


class PaginatedResult(BaseModel, Generic[T]):
    items: List[T] = []
    total: int = 0
    page: int = 1
    per_page: int = 20

    @property
    def pages(self) -> int:
        return ceil(self.total / self.per_page) if self.per_page > 0 else 0

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def next_page(self) -> Optional[int]:
        return self.page + 1 if self.has_next else None

    @property
    def prev_page(self) -> Optional[int]:
        return self.page - 1 if self.has_prev else None


def paginate_query(query, params: PaginationParams):
    return query.offset(params.offset).limit(params.limit)


def create_paginated_response(items: list, total: int, params: PaginationParams) -> dict:
    result = PaginatedResult(
        items=items,
        total=total,
        page=params.page,
        per_page=params.per_page,
    )
    return {
        "items": result.items,
        "total": result.total,
        "page": result.page,
        "per_page": result.per_page,
        "pages": result.pages,
        "has_next": result.has_next,
        "has_prev": result.has_prev,
    }
