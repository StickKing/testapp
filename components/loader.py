import asyncio
import aiohttp
import logging
from time import sleep
from sqlalchemy import select
from dateutil.parser import parse
from pprint import pprint

# from ssl import SSLContext, PROTOCOL_TLS

from .base import Component


logging.basicConfig(level=logging.INFO,
                    filename="get_vac.log",
                    filemode="a",
                    format="%(asctime)s %(levelname)s %(message)s")


# Определяем переменную с типом опыта
EXPERIENCE = [
    'Нет опыта',
    'От 1 года до 3 лет',
]

URL = 'https://api.hh.ru/vacancies'


class Loader(Component):
    """Компонент выгрузки вакансий из hh"""

    def __init__(self, app, config: dict) -> None:
        super().__init__(app, config)
        self.session = self.app.db()

    async def _get_page(self, category, session) -> tuple[int]:
        params = {
            'text': category.name[0],
            'area': '1',
            'per_page': '100',
            'page': 0
        }
        async with session.get(URL, params=params, ssl=False) as responce:
            if responce.status == 200:
                data = await responce.json()
                pages = int(data['pages'])
                return (category, pages)
            else:
                logging.error(f"{category} - страницы не были получены")
                return (category, 0)

    async def _get_all_page(self) -> None:
        """ Метод получения всех страниц вакансий """
        categories = self.session.scalars(select(self.app.db.Category))
        connector = aiohttp.TCPConnector(
            limit=0,
            # ssl=SSLContext(protocol=PROTOCOL_TLS)
        )
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for category in categories:
                task = asyncio.create_task(
                    self._get_page(category, session)
                )
                tasks.append(task)
            cat_pages = []
            for cat_page in asyncio.as_completed(tasks):
                res = await cat_page
                cat_pages.append(res)
        connector.close()
        return cat_pages

    async def _get_pagination(self, request_count: int) -> list[list]:
        """ Метод пагинации запросов на указанной колличество
        в группе """
        cat_pages = await self._get_all_page()
        all_params = []
        sub_list = []
        index = 0

        for cat_page in cat_pages:
            for page in range(cat_page[1]):
                params = {
                    'text': cat_page[0].name[0],
                    'area': '1',
                    'per_page': '100',
                    'page': page,
                    'category': cat_page[0],
                }
                if index == request_count:
                    all_params.append(sub_list.copy())
                    sub_list = list()
                    index = 0
                else:
                    sub_list.append(params)
                    index += 1
        return all_params

    def complete_vacancy(self, data: dict, category) -> list:
        """ Метод подготавливающий список вакансий,
        которые необходимо добавить в БД """
        vacancies = []
        # Получаю все hh id для проверки на дубли
        hh_id = self.session.scalars(select(self.app.db.Vacancy.hh_id))
        hh_id = tuple(i for i in hh_id)
        for vacancy in data:
            # pprint(all(i in vacancy['name'].lower() for i in category.name))
            pprint(vacancy['experience']['name'])
            if (all(i in vacancy['name'].lower() for i in category.name) and
                    vacancy['experience']['name'] in EXPERIENCE):
                if int(vacancy['id']) not in hh_id:
                    if vacancy['address'] and vacancy['address']['metro']:
                        metro = vacancy['address']['metro'].get(
                            'station_name',
                            None
                        )
                    else:
                        metro = "Метро не указано"
                    if vacancy['salary']:
                        from_sal = vacancy['salary'].get('from', None)
                        to_sal = vacancy['salary'].get('to', None)
                        curr_sal = vacancy['salary']['currency']
                        if from_sal and to_sal:
                            salary = '{0} до {1} {2}'.format(
                                vacancy['salary']['from'],
                                vacancy['salary']['to'],
                                curr_sal
                            )
                        elif from_sal:
                            salary = f"{from_sal} {curr_sal}"
                        else:
                            salary = f"До {to_sal} {curr_sal}"
                    else:
                        salary = "ЗП не указана"
                    new_vac = self.app.db.Vacancy(
                        hh_id=vacancy['id'],
                        name=vacancy['name'],
                        employer=vacancy['employer']['name'],
                        published_at=parse(vacancy['published_at']).date(),
                        experience=vacancy['experience']['name'],
                        metro_station=metro,
                        salary=salary,
                        url=f"{vacancy['alternate_url']}?from=share_android",
                    )
                    if new_vac.category:
                        new_vac.category.append(category)
                    else:
                        new_vac.category = [category]
                    vacancies.append(new_vac)
                else:
                    # Если был найден дубликат вакансии, то стоит
                    # проверить к какой категории она относится, и
                    # если текущей категории нет в её списке категорий
                    # то добавляем её
                    command = select(self.app.db.Vacancy).where(
                        self.app.db.Vacancy.hh_id == int(vacancy['id'])
                    )
                    vac = self.session.scalar(command)
                    if category not in vac.category:
                        category.vacancy.append(vac)
                        vacancies.append(category)
        return vacancies

    async def fetch_vacancy(self, session, params: dict) -> None:
        """Метод получающая по API вакансии и добавляющая их в БД"""
        category = params.pop('category')

        async with session.get(URL, params=params) as responce:
            if responce.status == 200:
                # Получаю данные из запроса
                data = await responce.json()
                # Получаю список вакансий и добавляю в БД
                vacancies = self.complete_vacancy(
                    data['items'],
                    category
                )
                self.session.add_all(vacancies)
                self.session.commit()
            else:
                text = await responce.json()
                full_name = " ".join(category.name)
                info = "{} - ошибка запроса: {} - ответ: {}".format(
                    full_name,
                    responce.status,
                    text
                )
                logging.error(info)

    async def load_data(self, params: dict) -> None:
        """ Метод создания и запуска task-ов одной
        страницы(полученой после пагинации) """
        connector = aiohttp.TCPConnector(
            limit=0,
            # ssl=SSLContext(protocol=PROTOCOL_TLS)
        )
        tasks = []
        async with aiohttp.ClientSession(connector=connector) as session:
            for par in params:
                tasks.append(
                    asyncio.create_task(
                        self.fetch_vacancy(session, par)
                    )
                )
            await asyncio.gather(*tasks)
        connector.close()

    def run(self):
        """Метод запуска основной функциональности"""
        params = asyncio.run(self._get_pagination(8))
        print(len(params) * 8)
        if params:
            sleep(1)
            for par in params:
                asyncio.run(self.load_data(par))
                sleep(1)


if __name__ == "__main__":
    pass
