from .base import Component


class Notificator(Component):
    """Компонент уведомлений"""

    notify_url = ""

    def notify_new_vacancy(self) -> None:
        """Метод уведомления о новых вакансиях"""
        pass

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