from __future__ import annotations
from tuned.extensions import db
from tuned.models.base import BaseModel
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

class Resource(BaseModel):
    __tablename__ = 'resource'
    name: Mapped[str] = mapped_column(db.String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(db.String(500), nullable=True)
    file_type: Mapped[Optional[str]] = mapped_column(db.String(50), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(db.String(100), nullable=True, default='General')
    access_level: Mapped[str] = mapped_column(db.String(50), default='all', nullable=False)
    download_count: Mapped[int] = mapped_column(db.Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(db.Boolean, default=True, server_default='true', nullable=False)
    uploaded_by: Mapped[Optional[str]] = mapped_column(db.String(36), db.ForeignKey('users.id'), nullable=True)

    def __repr__(self) -> str:
        return f'<Resource {self.name}>'
