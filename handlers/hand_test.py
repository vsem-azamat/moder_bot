from aiogram import types
from aiogram.types.message import ParseMode
from aiogram.utils.markdown import hlink

from aiogram.types import InputFile
from aiogram.dispatcher.filters import Command

from app import dp, bot
from filters import SuperAdmins
from db.sql_aclhemy import db
import random
import datetime
from defs import genButton


@dp.message_handler(Command('test', prefixes='!/'), SuperAdmins())
async def test(message: types.Message):
    q = db.check_user(message.from_user.id)
    # q = await db.welcome_message(-1001198485843)
    await message.answer(q)


@dp.message_handler(Command('json'), SuperAdmins())
async def json(message: types.Message):
    await message.reply(message)
