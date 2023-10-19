import asyncio
import aiohttp
import logging
from sqlalchemy import create_engine
from dateutil.parser import parse
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from datetime import datetime
from ssl import SSLContext, PROTOCOL_TLS
from settings import URL, DB_PATH, EXPERIENCE, USER_ID, URL_SEND_MESSAGE
from models import Category, Vacancy
from view import VacancyView
from requests import post as req_post
from time import sleep


logging.basicConfig(level=logging.INFO,
                    filename="get_vac.log",
                    filemode="a",
                    format="%(asctime)s %(levelname)s %(message)s"
                    )


def event_about_new_vacancy() -> None:
    """Функция получения свежеопубликованных вакансий
    и отправка их в чат пользователю"""
    # Получаю вакансии за сегодняшний день
    today = datetime.today().date()
    command = select(Vacancy).where(
        Vacancy.published_at == today
    ).where(
        Vacancy.view is False
    )
    new_vacancy = db_session.scalars(command)
    # Если вакансии есть отправляем их пользователю
    if new_vacancy.all():
        command = select(Vacancy).where(
            Vacancy.published_at == today
        ).where(
            Vacancy.view is False
        )

        new_vacancy = db_session.scalars(command)
        vac_view = VacancyView(db_session)
        message = vac_view.view_vacancy(new_vacancy)

        # Отправляем сообщение с новыми вакансиями
        message = "Появились новые вакансии:\n\n" + message
        while message:
            data = {
                    "chat_id": USER_ID,
                    "text": message[:4050]
                }
            req_post(
                    URL_SEND_MESSAGE,
                    data=data
                )
            message = message[4050:]

        # Изменяем флаг в БД
        command = update(Vacancy).where(
            Vacancy.published_at == today
        ).where(
            Vacancy.view is False
        ).values(
            view=True
        )
        db_session.execute(command)
        db_session.commit()
        message = "Появились новые вакансии:\n\n" + message


# Функции выгружающие данные по API
def complete_vacancy(data: dict, category: Category) -> list[Vacancy]:
    """Функция подготавливающая список вакансий,
    которые необходимо добавить в БД"""
    vacancies = []
    # Получаю все hh id для проверки на дубли
    hh_id = db_session.scalars(select(Vacancy.hh_id))
    hh_id = tuple(i for i in hh_id)
    for vacancy in data:
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
                new_vac = Vacancy(
                    hh_id=vacancy['id'],
                    name=vacancy['name'],
                    employer=vacancy['employer']['name'],
                    published_at=parse(vacancy['published_at']).date(),
                    experience=vacancy['experience']['name'],
                    metro_station=metro,
                    salary=salary,
                    url=f"{vacancy['alternate_url']}?from=share_android",
                )
                new_vac.category.append(category)
                vacancies.append(new_vac)
            else:
                # Если был найден дубликат вакансии, то стоит
                # проверить к какой категории она относится, и
                # если текущей категории нет в её списке категорий
                # то добавляем её
                command = select(Vacancy).where(
                    Vacancy.hh_id == int(vacancy['id'])
                )
                vac = db_session.scalar(command)
                if category not in vac.category:
                    category.vacancy.append(vac)
                    vacancies.append(category)
    return vacancies


async def fetch_vacancy(session, params: dict) -> None:
    """Функция получающая по API вакансии и добавляющая их в БД"""
    category = params.pop('category')

    async with session.get(URL, params=params) as responce:
        if responce.status == 200:
            # Получаю данные из запроса
            data = await responce.json()
            data = data['items']
            # Получаю список вакансий и добавляю в БД
            vacancies = complete_vacancy(
                data,
                category
            )
            db_session.add_all(vacancies)
            db_session.commit()
        else:
            text = await responce.json()
            full_name = " ".join(category.name)
            info = "{} - ошибка запроса: {} - ответ: {}".format(
                full_name,
                responce.status,
                text
            )
            logging.error(info)


async def load_data(params):
    connector = aiohttp.TCPConnector(limit=0,
                                     ssl=SSLContext(protocol=PROTOCOL_TLS)
                                     )
    tasks = []
    async with aiohttp.ClientSession(connector=connector) as session:
        for par in params:
            tasks.append(
                asyncio.create_task(
                    fetch_vacancy(session, par)
                )
            )
        await asyncio.gather(*tasks)

    connector.close()


# Функции для получения параметров
async def get_page(category, session) -> tuple[Category, int]:
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


async def get_all_page() -> None:
    categories = db_session.scalars(select(Category))
    connector = aiohttp.TCPConnector(limit=0,
                                     ssl=SSLContext(protocol=PROTOCOL_TLS)
                                     )
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for category in categories:
            task = asyncio.create_task(
                get_page(category, session)
            )
            tasks.append(task)
        cat_pages = []
        for cat_page in asyncio.as_completed(tasks):
            res = await cat_page
            cat_pages.append(res)
    connector.close()
    return cat_pages


async def get_params(request_count: int):
    cat_pages = await get_all_page()
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


def main():
    """Основаная функция модуля"""
    params = asyncio.run(get_params(8))
    if params:
        sleep(1)

        for par in params:
            asyncio.run(load_data(par))
            sleep(0.2)

        event_about_new_vacancy()


if __name__ == "__main__":
    engine = create_engine(f"sqlite:///{DB_PATH}vacancy.db", echo=False)
    db_session = Session(engine)

    main()

    db_session.close()
