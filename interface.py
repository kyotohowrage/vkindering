import re
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
from datetime import datetime
from config import comunity_token, acces_token
from core import VkTools
from data_store import check_user, add_user, engine

class BotInterface():
    def __init__(self, comunity_token, acces_token):
        self.vk = vk_api.VkApi(token=comunity_token)
        self.longpoll = VkLongPoll(self.vk)
        self.vk_tools = VkTools(acces_token)
        self.params = {}
        self.worksheets = []
        self.keys = []
        self.offset = 0

    def message_send(self, user_id, message, attachment=None):
        self.vk.method('messages.send', {'user_id': user_id, 'message': message, 'random_id': get_random_id(), 'attachment': attachment})

    @staticmethod
    def _bdate_toyear(bdate):
        user_year = bdate.split('.')[2]
        now = datetime.now().year
        return now - int(user_year)

    def photos_for_send(self, worksheet):
        photos = self.vk_tools.get_photos(worksheet['id'])
        photo_string = ''
        for photo in photos:
            photo_string += f'photo{photo["owner_id"]}_{photo["id"]},'
        return photo_string

    def new_message(self, k):
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                event_text = event.text

                if k == 0:
                    if any(char.isdigit() for char in event_text):
                        self.message_send(event.user_id, 'Пожалуйста, введите имя и фамилию без чисел')
                    else:
                        return event_text

                if k == 1:
                    if event_text == "М" or event_text == "Ж":
                        return int(event_text)
                    else:
                        self.message_send(event.user_id, 'Неверный формат ввода пола. Введите М или Ж')

                if k == 2:
                    if any(char.isdigit() for char in event_text):
                        self.message_send(event.user_id, 'Неверно указан город. Введите название города без чисел')
                    else:
                        return event_text

                if k == 3:
                    pattern = r'^\d{2}\.\d{2}\.\d{4}$'
                    if not re.match(pattern, event_text):
                        self.message_send(event.user_id, 'Пожалуйста, введите вашу дату рождения в формате (ДД.ММ.ГГГГ)')
                    else:
                        return self._bdate_toyear(event_text)

    def send_mes_exc(self, event):
        if self.params['name'] is None:
            self.message_send(event.user_id, 'Введите ваше имя и фамилию')
            return self.new_message(0)

        if self.params['sex'] is None:
            self.message_send(event.user_id, 'Введите свой пол (М или Ж)')
            return self.new_message(1)

        elif self.params['city'] is None:
            self.message_send(event.user_id, 'Введите город')
            return self.new_message(2)

        elif self.params['year'] is None:
            self.message_send(event.user_id, 'Введите дату рождения (ДД.ММ.ГГГГ)')
            return self.new_message(3)

    def change_city(self, event):
        self.message_send(event.user_id, 'Введите новый город')
        city = self.new_message(2)
        self.params['city'] = city
        self.message_send(event.user_id, f'Город изменен на: {city}')

    def process_worksheet(self, engine, user_id, worksheet):
        if not check_user(engine, user_id, worksheet['id']):
            add_user(engine, user_id, worksheet['id'])
            return worksheet
        return None

    def get_profile(self, worksheets, event):
        while True:
            if worksheets:
                worksheet = worksheets.pop()
                result = self.process_worksheet(engine, event.user_id, worksheet)
                if result is not None:
                    yield result
            else:
                worksheets = self.vk_tools.search_worksheet(self.params, self.offset)

    def event_handler(self):
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                text = event.text.lower()
                if text == 'привет':
                    self.params = self.vk_tools.get_profile_info(event.user_id)
                    self.message_send(event.user_id, f'Привет, {self.params["name"]}!')
                    self.keys = self.params.keys()
                    for i in self.keys:
                        if self.params[i] is None:
                            self.params[i] = self.send_mes_exc(event)
                    self.message_send(event.user_id, 'Регистрация пройдена! Искать пару командой "Поиск"')
                elif text == 'поиск':
                    self.message_send(event.user_id, 'Начинаем поиск...')
                    msg = next(iter(self.get_profile(self.worksheets, event)))
                    if msg:
                        photo_string = self.photos_for_send(msg)
                        self.offset += 10
                        self.message_send(event.user_id, f'Имя: {msg["name"]} Ссылка: vk.com/id{msg["id"]}', attachment=photo_string)
                elif text == 'пока':
                    self.message_send(event.user_id, 'Увидимся!')
                elif text == 'поменять город':
                    self.change_city(event)
                elif text == 'помощь':
                    commands = [
                        'Привет - запуск бота',
                        'Поменять город - изменить город',
                        'Поиск - найти пару'
                        'Пока - завершение работы с ботом'
                    ]
                    self.message_send(event.user_id, 'Доступные команды:\n' + '\n'.join(commands))
                else:
                    self.message_send(event.user_id, 'Неизвестная команда')

if __name__ == '__main__':
    bot_interface = BotInterface(comunity_token, acces_token)
    bot_interface.event_handler()