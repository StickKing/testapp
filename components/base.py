from abc import (
    ABC,
    abstractmethod
)


class Component(ABC):
    """ Базовый класс компонента """

    def __init__(self, app, config: dict) -> None:
        self.app = app
        self.config = config


    @abstractmethod
    def run(self) -> None:
        """ Метод запуска компонента """
