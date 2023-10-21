from typing import Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Category, Vacancy


class DB:
    """ Компонент для работы с БД """
    def __init__(self, config: dict) -> None:
        self.config = config
        self.Category = Category
        self.Vacancy = Vacancy
        path = self.config["path"]
        engine = create_engine(f"sqlite:///{path}vacancy.db")
        self.Session = sessionmaker(engine)

    def __call__(self) -> Session:
        """ Метод созвращающий сессию """
        return self.Session()
