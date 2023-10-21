from typing import List
from typing import Optional
from sqlalchemy import (
    create_engine,
    select,
    func,
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
        Integer,
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


class Category(Base):
    """Таблица категорий искомых вакансий"""
    __tablename__ = "Category"
    name: Mapped[PickleType] = mapped_column(PickleType, nullable=False)
    no_search: Mapped[PickleType] = mapped_column(PickleType, nullable=True)
    vacanciHH: Mapped[List["Vacancy"]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan"
    )


class Vacancy(Base):
    """Таблица вакансий с hh"""
    __tablename__ = "Vacancy"
    hh_id: Mapped[int] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    employer: Mapped[str] = mapped_column(String(255), nullable=False)
    published_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True))
    experience: Mapped[str] = mapped_column(String(50), nullable=True)
    metro_station: Mapped[str] = mapped_column(String(255), nullable=True)
    salary: Mapped[str] = mapped_column(String(255), nullable=True)
    url: Mapped[str] = mapped_column(nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("Category.id"))
    category: Mapped["Category"] = relationship(back_populates="vacanciHH")

    def __repr__(self) -> str:
        return f"name = {self.name}, employer = {self.employer}, url = {self.url}"


if __name__ == "__main__":
    engine = create_engine("sqlite:///./vacancy.db", echo=True) 
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        jun = Category(name=['junior'])
        jun_py = Category(name=['junior', 'python'])
        jun_dev = Category(name=['junior', 'devops'])
        jun_sre = Category(name=['junior', 'sre'])
        bac_py = Category(name=['backend', 'python'])
        dev = Category(name=['devops'])
        sre = Category(name=['sre'])
        session.add_all([jun, sre, jun_py, jun_dev, jun_sre, bac_py, dev, sre])
        session.commit()
        command = select(Category)
        cat = session.scalars(command)
        for i in cat:
            print(i.name, ' '.join(i.name))