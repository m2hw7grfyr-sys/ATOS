from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session


ModelT = TypeVar("ModelT")


class Repository(Generic[ModelT]):
    def __init__(self, db: Session, model: type[ModelT]):
        self.db = db
        self.model = model

    def get(self, item_id: int) -> ModelT | None:
        return self.db.get(self.model, item_id)

    def list(self) -> list[ModelT]:
        return list(self.db.scalars(select(self.model)).all())

    def add(self, item: ModelT) -> ModelT:
        self.db.add(item)
        self.db.flush()
        return item
