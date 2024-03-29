from sqlalchemy import create_engine, select, insert, update, delete
from sqlalchemy.orm import sessionmaker

from .alchemy_decl import Admins, Base, Commands, Users, Chats, ChatLinks

from defs import genButton


class SqlAlchemy:
    def __init__(self):
        self.engine = create_engine('sqlite:///db/moder_bot.db')
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)
        self.s = self.session()

        self.conn = self.engine.connect()

    def conv_dict(self, query) -> dict:
        """
        Converts the query result to a dict
        """
        return [dict(i) for i in query][0]

    def check_exists(self, id_tg):
        return True if self.s.query(Users).filter(Users.id_tg == id_tg).first() else False

    def execute(self, sql):
        return self.conn.execute(sql)

    def check_user(self, id_tg: int) -> dict:
        """
        return -> dict
            keys: black_list, verify

        *return will be empty dict, if user doesn't exist in the DB
        """
        q = self.s.query(Users.black_list, Users.verify).filter(Users.id_tg == id_tg)
        return self.conv_dict(q) if self.check_exists(id_tg) else {}

    async def check_verify(self, id_tg: int) -> bool:
        """
        Checks the "verify" status of the User
        """
        return self.s.query(Users.verify).filter(Users.id_tg == id_tg).first()[0]

    async def change_verify(self, id_tg: int, state: bool) -> None:
        """
        Changes to verify status of the User
        """
        q = update(Users).where(Users.id_tg == id_tg).values(verify=state)
        self.conn.execute(q)

    async def change_black_list(self, id_tg: int, state: bool = True) -> None:
        """
        Changes to black_list status of the User
        """
        q = update(Users.black_list).where(Users.id_tg == id_tg).values(black_list=state)
        self.conn.execute(q)

    async def welcome_message(self, id_tg_chat: int, return_: bool = True):
        """
        return -> dict:
        {'text':          Welcome text}
        {'time_delete':   Auto-delete time message}
        {'state_func':    State of welcome message/func}
        {'state_test':    State of welcome test}

        If chat doesn't exist in the DB,
        to will be created new row with text from "texts/welcome.txt"
        """
        q = self.s.query(Chats.text, Chats.time_delete, Chats.state_func, Chats.state_test).filter(
            Chats.id_tg_chat == id_tg_chat)
        if q.first() is None:
            f = open('data/welcome.txt', encoding='utf-8', mode='r').read()
            welcome = Chats(id_tg_chat=id_tg_chat, text=f)
            self.s.add(welcome)
            self.s.commit()
        return self.conv_dict(q) if return_ is True else None

    async def welcome_command(self, id_tg_chat: int, text: str) -> str:
        """
        Work with table 'Chats'
        message params: 
             _: change state_func
        {text}: change welcome text
            -t: change state_test
            -m: change message text
        """
        message = None
        if len(text.split()) > 1:
            message = text.partition(" ")[2]
        param = text.split(" ")[0].strip()
        welc_info = await self.welcome_message(id_tg_chat)

        # change state_func
        if param.lower() in ["", "on", "off"]:
            value = {'on': True, 'off': False}.get(param.lower(), {True: False, False: True}[welc_info['state_func']])
            request = update(Chats).where(Chats.id_tg_chat == id_tg_chat).values(state_func=value)
            self.engine.execute(request)

            return "Приветствие %s!" % {True: 'включено', False: 'отключено'}[value]

        # change state_test
        elif param == '-b':
            value = {1: 0, 0: 1}.get(welc_info['state_test'], 1)
            request = update(Chats).where(Chats.id_tg_chat == id_tg_chat).values(state_test=value)
            self.engine.execute(request)

            if welc_info['state_func'] is False:
                add_text = "\nНо приветствие в этом чате отключено."
            else:
                add_text = ""
            return f"<b>Кнопка</b> в приветствии %s!" % {True: 'активирована', False: 'деактивирована'}[value] + add_text

        elif param == '-d':
            value = {2: 0, 0: 2}.get(welc_info['state_test'], 2)
            request = update(Chats).where(Chats.id_tg_chat == id_tg_chat).values(state_test=value)
            self.engine.execute(request)

            if welc_info['state_func'] is False:
                add_text = "\nНо приветствие в этом чате отключено."
            else:
                add_text = ""
            return f"<b>Кнопки</b> в приветствии %s!" % {2: 'активированы', 0: 'деактивированы'}[value] + add_text

        elif param == '-t':
            try:
                value = int(message)
                if 10 <= value <= 900:
                    request = update(Chats).where(Chats.id_tg_chat == id_tg_chat).values(time_delete=value)
                    self.engine.execute(request)
                    return f"Время автоудаления приветствия установлено: {value} с."
                elif 0 <= value <= 10:
                    return "Минимальное время автоудаления 10 секунд."
                elif value >= 900:
                    return "Минимальное время автоудаления 900 секунд."
                else:
                    raise ValueError
            except TypeError:
                return f"Вы не задали время автоудаления."
            except ValueError:
                return f"Вы некорректно задали параметр."

        elif param == '-s':
            request = self.s.query(Chats.text, Chats.time_delete, Chats.state_func, Chats.state_test, Chats.db_admins).\
                filter(Chats.id_tg_chat == id_tg_chat).first()
            text = f"""
<b>Текст приветствие:</b>
{request[0]}
            
<b>Время автоудаления:</b> {request[1]}
<b>Приветствие:</b> {(request[2])}
<b>Кнопка:</b> {request[3]}
<b>Глобальные админы:</b> {request[4]}   
            """
            return text

        # change message text
        else:
            request = update(Chats).where(Chats.id_tg_chat == id_tg_chat).values(text=text)
            self.engine.execute(request)
            return f"<b>Приветствие отредактировано!</b> \n\n{text}"

    async def add_new_user(self, id_tg: int, state_test: bool = True):
        """
        Add the user to the DB if it doesn't exist
        """
        if not self.check_exists(id_tg):
            state = {False: True}.get(state_test, False)
            user = Users(id_tg=id_tg, verify=state)
            self.s.add(user)
            self.s.commit()

    async def command_list(self):
        q = self.s.query(Commands.command, Commands.state).all()
        l_commands_states = [f'{name}: ' + {1: '✅', 0: '❌'}.get(state) for name, state in q]
        return genButton.inline_b(l_commands_states, [f"comm_{int(state)}_{name}" for name, state in q])

    async def command_update_state(self, command: str, state: bool) -> None:
        request = update(Commands).where(Commands.command == command).values(state=state)
        self.s.execute(request)
        self.s.commit()

    async def check_command_state(self, command: str) -> bool:
        """
        Checks the "state" status of the Commands
        """
        return True if self.s.query(Commands.state).filter(Commands.command == command).first()[0] is not None else False

    async def check_chat(self, id_tg_chat: int):
        """
        Add the chat to the DB if it doesn't exist
        """
        q = self.s.query(Chats.id).filter(Chats.id_tg_chat == id_tg_chat).first()
        if q is None:
            chat = Chats(id_tg_chat=id_tg_chat)
            self.s.add(chat)
            self.s.commit()

    async def check_gl_admins(self, id_tg: int):
        return True if self.s.query(Admins).filter(Admins.id_tg == id_tg).first() else False

    async def get_gl_admins(self):
        q = self.s.query(Admins.id_tg).all()
        return [id_admin for id_admin in q]

    async def check_chat_db_admins_state(self, id_tg: int, id_chat: int):
        """
        return -> bools[]:
        - admin_state
            .. 1 - Is admin
            .. 0 - Is not admin
        - chat_state
            .. 0 - Only chat admins
            .. 1 - Chat admins + db admins
            .. 3 - Only db admins
        """
        await self.check_chat(id_chat)
        chat_state = self.s.query(Chats.db_admins).filter(Chats.id_tg_chat == id_chat).first()[0]
        try:
            admin_state = self.s.query(Admins.state).filter(Admins.id_tg == id_tg).first()
        except TypeError:
            admin_state = False
        return admin_state, chat_state

    async def settings_gl_admins(self, id_tg: int, message: str) -> str:
        """
        Add or remove the user from the global admins
        """
        admin_state = await db.check_gl_admins(id_tg)
        try:
            _, command, admin_id = message.split()
            match command:
                case 'add':
                    if admin_state:
                        return "Такой глобальный администратор уже в базе данных!"
                    else:
                        admin = Admins(id_tg=id_tg)
                        self.s.add(admin)
                        self.s.commit()
                        return "Новый глобальный администратор добавлен!"

                case 'del':
                    if admin_state:
                        request = delete(Admins).where(Admins.id_tg == id_tg)
                        self.s.execute(request)
                        self.s.commit()
                        return "Администратор удален!"
                    else:
                        return "Такого администратора нет в базе данных!"

                case 'off' | 'on':
                    state = {'off': False, 'on': True}.get(command, None)
                    if admin_state:
                        request = update(Admins).where(Admins.id_tg == id_tg).values(state=state)
                        self.conn.execute(request)
                        return f"Администратор получил статус: {command}"
                    else:
                        return "Такого администратора нет в базе данных!"

                case _:
                    raise IndexError

        except IndexError:
            return "Команда некорректно использована :(\n\nПример:\n/admin add {id_tg}\n/admin del {id_tg}"

    async def get_chat_links(self):
        q = self.s.query(ChatLinks.text, ChatLinks.link).all()
        return await genButton.inline_b([text for text, _ in q], [link for _, link in q], row_w=2, url=True)

    async def get_chat_list(self):
        q = self.s.query(Chats.id_tg_chat).all()
        return [chat_id for chat_id in q]

db = SqlAlchemy()
