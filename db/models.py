from typing import List
from typing import Optional
from sqlalchemy import (
    create_engine,
    select,
    func,
    Table,
    Column,
    ForeignKey,
    Integer,
    String,
    DateTime,
    PickleType,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    mapped_column,
    Mapped,
    relationship,
    Session,
)


class Base(DeclarativeBase):
    """Базовая таблица БД. Абстрактный класс."""
    __abstract__ = True

    id: Mapped[int] = mapped_column(
        nullable=False,
        unique=True, primary_key=True,
        autoincrement=True
    )
    create_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    @classmethod
    def get(cls, id: int):
        """ Метод возвращающий запрос поиска данных по id """
        return select(cls).where(cls.id == id)

    @classmethod
    def get_all(cls):
        """ Метод возвращающий запрос для получения всех данных"""
        return select(cls)


category_vacancy = Table(
    "category_vacancy",
    Base.metadata,
    Column("category_id", ForeignKey("Category.id"), primary_key=True),
    Column("vacancy_id", ForeignKey("Vacancy.id"), primary_key=True),
)


class Category(Base):
    """Таблица категорий искомых вакансий"""
    __tablename__ = "Category"
    name: Mapped[PickleType] = mapped_column(PickleType, nullable=False)
    vacancy: Mapped[List["Vacancy"]] = relationship(
        secondary=category_vacancy,
        back_populates="category",
        cascade="all, delete-orphan",
        single_parent=True
    )


class Vacancy(Base):
    """Таблица вакансий с hh"""
    __tablename__ = "Vacancy"
    hh_id: Mapped[int] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    employer: Mapped[str] = mapped_column(String(255), nullable=False)
    published_at: Mapped[Date] = mapped_column(Date)
    experience: Mapped[str] = mapped_column(String(50), nullable=True)
    metro_station: Mapped[str] = mapped_column(String(255), nullable=True)
    salary: Mapped[str] = mapped_column(String(255), nullable=True)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    view: Mapped[bool] = mapped_column(Boolean, default=False)
    category: Mapped[List[Category]] = relationship(
        secondary=category_vacancy,
        back_populates="vacancy",
    )

    def __repr__(self) -> str:
        return f"name = {0}, employer = {1}, url = {2}".format(
            self.name,
            self.employer,
            self.url
        )
