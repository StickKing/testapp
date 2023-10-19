from abc import (
    ABC,
    abstractmethod
)


class Component(ABC):
    """ Базовый класс компонента """

    @abstractmethod
    def run(self):
        """ Метод запуска компонента """
