import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.i18n import I18n, SimpleI18nMiddleware
from aiohttp import web 
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from sqlalchemy.ext.asyncio import create_async_engine

from db import Base
from handlers.commands import register_commands
from handlers.messages import register_messages
from handlers.callbacks import register_callbacks
from middlewares.db_check import DBCheck
from app.routes import check_crypto_payment, check_yookassa_payment
from tasks import register
import glv

glv.bot = Bot(glv.config['BOT_TOKEN'], default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def create_tables():
    # Убедитесь, что DB_URL указан правильно (например, "sqlite+aiosqlite:///bot.db")
    engine = create_async_engine(glv.config['DB_URL'])
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def on_startup(bot: Bot):
    if glv.config.get('WEBHOOK_URL'):
        await bot.set_webhook(f"{glv.config['WEBHOOK_URL']}/webhook")
    asyncio.create_task(register())
    logging.info("Bot started in %s mode", "WEBHOOK" if glv.config.get('WEBHOOK_URL') else "LONG POLLING")

def setup_routers():
    register_commands(dp)
    register_messages(dp)
    register_callbacks(dp)

def setup_middlewares():
    i18n = I18n(path=Path(__file__).parent.parent / 'locales', default_locale='en', domain='bot')
    i18n_middleware = SimpleI18nMiddleware(i18n=i18n)
    i18n_middleware.setup(dp)
    dp.message.middleware(DBCheck())

async def main():
    setup_routers()
    setup_middlewares()
    dp.startup.register(create_tables)
    dp.startup.register(on_startup)
    if glv.config.get('WEBHOOK_URL'):
        app = web.Application()
        app.router.add_post("/cryptomus_payment", check_crypto_payment)
        app.router.add_post("/yookassa_payment", check_yookassa_payment)

        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=glv.bot,
        )
        webhook_requests_handler.register(app, path="/webhook")

        setup_application(app, dp, bot=glv.bot)
        await web._run_app(app, host="0.0.0.0", port=glv.config['WEBHOOK_PORT'])
    else:
        await glv.bot.delete_webhook()
        await dp.start_polling(glv.bot)

if __name__ == "__main__":
    asyncio.run(main())
