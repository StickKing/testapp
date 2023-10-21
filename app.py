import yaml
from pathlib import Path
from components import Loader
from db import DB


class App:
    """ Главное приложение """

    BASE_PATH = Path(__file__).parent
    components = ()

    def __init__(self) -> None:
        self.config = self.__get_config(True)
        self.db = DB(self.config["db"])

    def start(self):
        loader = Loader(self, self.config["db"])
        loader.run()

    def __get_config(self, debug=False):
        """ Метод чтения кофига """
        conf_path = self.BASE_PATH / "config"
        conf_name = {
            True: "config-dev.yaml",
            False: "config.yaml",
        }
        with open(conf_path / conf_name[debug]) as f:
            config = yaml.safe_load(f)
            return config


if __name__ == "__main__":
    t = App()
    t.start()
