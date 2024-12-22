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

from telegram import ForceReply, Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CallbackContext, CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from telegram.constants import ParseMode

from contract_interaction import call_contract_mint
from generate_nft import create_upload_nft
from process_audio import concatenate_audio

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

# user_data structure
# {
#   wallet_addrs: {user_id -> addr},
#   games: {
#     game_id: <user_id> -> {
#       song_id: <song_id>
#       song_index: number
#       recordings: ['filenames.ogg'...]
#       score: number
#     }
#   }
# }

# Maps user id to etherium wallet address
_USER_DATA_WALLET_KEY = 'wallet_addrs'
_USER_DATA_GAME_KEY = 'games'

# Disable minting nfts (to save test coins)
_SKIP_NFT = True

SONG_SELECTION, LYRICS, SCORE = range(3)

SONG_1 = [
    {
        'lyrics': 'Happy Birthday to you',
    },
    {
        'lyrics': 'Happy Birthday to you',
    },
    {
        'lyrics': 'Happy Birthday Dear Bob',
    },
    {
        'lyrics': 'Happy Birthday to you',
    }
]

SONG_2 = [
    {
        'lyrics': 'Silent night, holy night',
    },
    {
        'lyrics': 'All is calm, all is bright',
    },
    {
        'lyrics': 'Round yon Virgin, Mother and Child',
    },
    {
        'lyrics': 'Holy Infant so tender and mild',
    },
    {
        'lyrics': 'Sleep in heavenly peace',
    },
    {
        'lyrics': 'Sleep in heavenly peace',
    },
]

SONGS = {
    'Happy Birthday': SONG_1,
    'Silent Night': SONG_2,
}


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""

    keyboard = [
        [InlineKeyboardButton("Happy Birthday", callback_data='button_Happy Birthday')],
        [InlineKeyboardButton("Silent Night", callback_data='button_Silent Night')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Please pick a song:', reply_markup=reply_markup)

    # user = update.effective_user
    # await update.message.reply_html(
    #     rf"Hi {user.mention_html()}!",
    #     reply_markup=ForceReply(selective=True),
    # )
    return SONG_SELECTION

async def song_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the selected song."""
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    selected_song = query.data.split("_")[1]
    logger.info(f"User {user_id} selected song {selected_song}")

    song = SONGS[selected_song]

    await update.callback_query.message.edit_text(
        f"{selected_song} is a great choice! Here are your lyrics:\n{song[0]['lyrics']}",
    )

    if _USER_DATA_GAME_KEY not in context.user_data:
        context.user_data[_USER_DATA_GAME_KEY] = {}

    context.user_data[_USER_DATA_GAME_KEY][user_id] = {
        'song_id': selected_song,
        'song_index': 0,
        'recordings': [],
        'score': 0,
    }

    # await update.message.reply_text(
    #     f"Great choice! Here are your lyrics:\n{selected_song}",
    #     reply_markup=ReplyKeyboardRemove(),
    # )

    return LYRICS

# async def button_selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     query = update.callback_query
#     await query.answer()
#     await query.edit_message_text(f'You selected option: {query.data.split("_")[1]}')

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

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user

    logger.info("User %s canceled the conversation.", user.first_name)

    await update.message.reply_text(
        "Bye! I hope we can talk again some day.", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def process_lyrics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process lyric, and sends the next one."""
    # context.user_data[_USER_DATA_GAME_KEY][user_id] = {
    #     'song_id': selected_song,
    #     'song_index': 0,
    #     'recordings': [],
    #     'score': 0,
    # }
    user_id = update.effective_user.id
    game_info = context.user_data[_USER_DATA_GAME_KEY][user_id]

    logging.info(f"Received voice message: {update.message.voice.file_id}")
    voice = update.message.voice
    voice_file = await context.bot.get_file(voice.file_id)

    f = await voice_file.download_to_drive(f'{voice.file_id}.ogg')
    game_info['recordings'].append(f'{voice.file_id}.ogg')
    game_info['song_index'] += 1

    song = SONGS[game_info['song_id']]

    if game_info['song_index'] >= len(song):
        await score_performance(update, context)
        return ConversationHandler.END

    await update.message.reply_text(f"{song[game_info['song_index']]['lyrics']}")

    return LYRICS

async def score_performance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Scores the whole performance."""
    await update.message.reply_text(f"Nice performance! Scoring...")

    user_id = update.effective_user.id
    game_info = context.user_data[_USER_DATA_GAME_KEY][user_id]

    # concatenate all audio files together
    concatenate_audio(game_info['recordings'])


    # score the performance

    # mint the nft


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

    if _SKIP_NFT:
        logging.info(f"skipping generating nft image and metadata")
        return

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
    #application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("register", register_wallet_command))
    application.add_handler(CommandHandler("current_wallet", get_wallet_command))

    # Karaoke game state handlers
    karaoke_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states = {
            SONG_SELECTION: [CallbackQueryHandler(song_selection, pattern='^button_')],
            LYRICS: [MessageHandler(filters.VOICE, process_lyrics)],
        },
        fallbacks = [CommandHandler('cancel', cancel)],
    )
    application.add_handler(karaoke_handler)


    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Add handler for voice messages
    application.add_handler(MessageHandler(filters.VOICE, get_voice))

    # application.add_handler(CallbackQueryHandler(button_selection_handler, pattern='^button_'))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
