#!/usr/bin/env python
# pylint: disable=unused-argument


"""
Telegram Karaoke Bot to score performances and reward with nfts.
"""

import io
import logging
import os
import re

from dotenv import load_dotenv
import whisper

from telegram import ForceReply, Update
from telegram.ext import Application, CallbackContext, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

from contract_interaction import call_contract_mint
from generate_nft import create_upload_nft

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN') or ''

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

transcriber = whisper.load_model('medium.en')

# Maps user id to etherium wallet address
_USER_DATA_WALLET_KEY = 'wallet_addrs'


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")

async def register_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /register is issued."""
    cmd = update.message.text.strip()
    addr = cmd.removeprefix('/register').strip()
    logging.info(f"received address: '{addr}'")

    if re.match(r"^0x[a-fA-F0-9]{40}$", addr):
        if _USER_DATA_WALLET_KEY not in context.user_data:
            context.user_data[_USER_DATA_WALLET_KEY] = {}
        context.user_data[_USER_DATA_WALLET_KEY][update.effective_user.id] = addr
        await update.message.reply_text(f"Wallet address registered successfully: {addr}")
    else:
        await update.message.reply_text("Invalid wallet address format. Please use the format 0x...")

async def get_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /register is issued."""
    addr = context.user_data.get(_USER_DATA_WALLET_KEY, {}).get(update.effective_user.id)
    if addr:
        await update.message.reply_text(f"Wallet address registered: {addr}")
    else:
        await update.message.reply_text("No wallets registered yet. Please use command: /register 0x...")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    await update.message.reply_text(update.message.text)


async def get_voice(update: Update, context: CallbackContext) -> None:
    addr = context.user_data.get(_USER_DATA_WALLET_KEY, {}).get(update.effective_user.id)
    if not addr:
        await update.message.reply_text("No wallets registered yet. Please use command: /register 0x...")
        return


    logging.info(f"Received voice message: {update.message.voice.file_id}")
    voice = update.message.voice
    voice_file = await context.bot.get_file(voice.file_id)

    f = await voice_file.download_to_drive('voice.ogg')


    results = transcriber.transcribe('voice.ogg')
    logging.info(f"transcription results: {results}")

    await update.message.reply_text(f"nice voice! I think you said: {results['text']}")

    logging.info(f"generating nft image and metadata")
    json_cid = create_upload_nft(results['text'], 'test song')

    logging.info(f"minting nft for {json_cid}")
    receipt = call_contract_mint(addr, f"ipfs://{json_cid}")

    if receipt:
        txn_hash = receipt['transactionHash'].to_0x_hex()
        logging.info(f"minting nft receipt tx: {txn_hash}")
        await update.message.reply_text(
            f"minted nft for you: [{txn_hash}](https://sepolia.etherscan.io/tx/{txn_hash})",
            parse_mode=ParseMode.MARKDOWN_V2,
        )


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("register", register_wallet_command))
    application.add_handler(CommandHandler("current_wallet", get_wallet_command))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Add handler for voice messages
    application.add_handler(MessageHandler(filters.VOICE, get_voice))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
