from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import os
from typing import Callable

TELEGRAM_API_TOKEN = os.environ.get('TELEGRAM_API_TOKEN')
VERIFY_COMMAND = 'start'


class VerifierCallback:
    callback: Callable[[bool], None]
    phone_number: str

    def __init__(self, phone_number, callback: Callable[[bool], None]):
        self.phone_number = phone_number
        self.callback = callback


"""
Flow of the TelegramBot Verifier
1. Two handlers are added
    a. Verify command for /start to prompt user to share his contact settings
    b. Message handler for getting the actual contact (which includes the users phone number)
2. When a user is in the verify process, we must register a 
2. When a user send /start he is requested to share his contact info (including number)
3. We then receive the number and must compare it with the users details
"""


class TelegramBot:
    verified_cbs = {}
    application: Application

    @classmethod
    def initialize(cls):
        """Initialize the Telegram bot."""
        if not TELEGRAM_API_TOKEN:
            raise ValueError("Telegram API token is missing!")

        cls.application = Application.builder().token(TELEGRAM_API_TOKEN).build()

        cls.application.add_handler(CommandHandler(VERIFY_COMMAND, cls.request_contact))
        cls.application.add_handler(MessageHandler(filters.CONTACT, cls.process_contact))

    @classmethod
    def start(cls):
        cls.application.run_polling(allowed_updates=Update.ALL_TYPES, close_loop=True)

    @classmethod
    async def request_contact(cls, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        print(f'Start command from: {update.update_id}')
        contact_keyboard = KeyboardButton("Share your contact", request_contact=True)
        custom_keyboard = [[contact_keyboard]]
        reply_markup = ReplyKeyboardMarkup(custom_keyboard)
        await update.message.reply_text("Please share your contact", reply_markup=reply_markup)

    @classmethod
    async def process_contact(cls, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        contact = update.message.contact
        contact_user_id = contact.user_id
        update_user_id = update.message.from_user.id
        phone_number = cls.normalize_phone_number(contact.phone_number)
        print(f"Received phone number: {phone_number}")
        try:
            vc: VerifierCallback = cls.verified_cbs[phone_number]
        except:
            print(f"Could not find VerifierCallback")
            await update.message.reply_text(f"Could not verify number: unset VerifierCallback")
            return

        # We must validate that the contacts' user_id is the same as the senders to make sure that he is the contact
        if contact_user_id != update_user_id:
            await update.message.reply_text(f"Could not verify number: user_id mismatch")
            await vc.callback(False)
            del cls.verified_cbs[phone_number]
            return

        await update.message.reply_text(f"Verified! You can return to discord")
        await vc.callback(True)
        del cls.verified_cbs[phone_number]

    @classmethod
    def register_cb(cls, vc: VerifierCallback):
        cls.verified_cbs[vc.phone_number] = vc

    @classmethod
    def normalize_phone_number(cls, phone_number):
        # Return only last 9 digits
        return phone_number[-9:]
