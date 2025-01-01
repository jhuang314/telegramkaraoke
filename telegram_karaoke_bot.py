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
import prettytable as pt
import whisper

from telegram import ForceReply, Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CallbackContext, CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from telegram.constants import ParseMode

from contract_interaction import call_contract_mint
from generate_nft import create_upload_nft
from process_audio import concatenate_audio, compare_audios

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN') or ''

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

#transcriber = whisper.load_model('medium.en')

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
#   leaderboard: [
#     {
#       score: number,
#       song_id: str,
#       username: (username) str,
#     }
#   ]
# }


_USER_DATA_WALLET_KEY = 'wallet_addrs'
_USER_DATA_GAME_KEY = 'games'
_USER_DATA_LEADERBOARD_KEY = 'leaderboard'

_LEADERBOARD = []

# Disable minting nfts (to save test coins)
_SKIP_NFT = False

#TXN_SCAN_URL = 'https://sepolia.etherscan.io/tx/'
TXN_SCAN_URL = 'https://opbnb-testnet.bscscan.com/tx/'

SONG_SELECTION, LYRICS, SCORE = range(3)

SONG_1 = [
    {
        'lyrics': 'Joy to the world, the Lord has come',
    },
    {
        'lyrics': 'Let earth receive her King',
    },
    {
        'lyrics': 'Let every heart prepare Him room',
    },
    {
        'lyrics': 'And heaven and nature sing, and heaven and nature sing',
    },
    {
        'lyrics': 'And heaven, and heaven and nature sing',
    },
    {
        'lyrics': 'Joy to the earth, the Savior reigns',
    },
    {
        'lyrics': 'Let men their songs employ',
    },
    {
        'lyrics': 'While fields and floods, rocks, hills, and plains',
    },
    {
        'lyrics': 'Repeat the sounding joy, repeat the sounding joy',
    },
    {
        'lyrics': 'Repeat, repeat the sounding joy',
    },
    {
        'lyrics': 'No more let sins and sorrows grow',
    },
    {
        'lyrics': 'Nor thorns infest the ground',
    },
    {
        'lyrics': 'He comes to make His blessings flow',
    },
    {
        'lyrics': 'Far as the curse is found, far as the curse is found',
    },
    {
        'lyrics': 'Far as, far as the curse is found',
    },
    {
        'lyrics': 'He rules the world with truth and grace',
    },
    {
        'lyrics': 'And makes the nations prove',
    },
    {
        'lyrics': 'The glories of His righteousness',
    },
    {
        'lyrics': 'And wonders of His love, and wonders of His love',
    },
    {
        'lyrics': 'And wonders, wonders of His love',
    },
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

SONG_3 = [
    {
        'lyrics': 'Dashing through the snow',
    },
    {
        'lyrics': 'In a one-horse open sleigh',
    },
    {
        'lyrics': 'All the fields we go',
    },
    {
        'lyrics': 'Laughing all the way',
    },
    {
        'lyrics': 'Bells on bobtails ring',
    },
    {
        'lyrics': 'Making spirits bright',
    },
    {
        'lyrics': 'What fun it is to ride and sing',
    },
    {
        'lyrics': 'A sleighing song tonight',
    },
    {
        'lyrics': 'Oh! Jingle bells, jingle bells',
    },
    {
        'lyrics': 'Jingle all the way',
    },
    {
        'lyrics': 'Oh, what fun it is to ride',
    },
    {
        'lyrics': 'In a one-horse open sleigh, hey',
    },
    {
        'lyrics': 'Jingle bells, jingle bells',
    },
    {
        'lyrics': 'Jingle all the way',
    },
    {
        'lyrics': 'Oh, what fun it is to ride',
    },
    {
        'lyrics': 'In a one-horse open sleigh',
    },
]

SONG_4 = [
    {
        'lyrics': 'Jingle bells, jingle bells',
    },
    {
        'lyrics': 'Jingle all the way',
    },
    {
        'lyrics': 'Oh, what fun it is to ride',
    },
    {
        'lyrics': 'In a one-horse open sleigh, hey',
    },
    {
        'lyrics': 'Jingle bells, jingle bells',
    },
    {
        'lyrics': 'Jingle all the way',
    },
    {
        'lyrics': 'Oh, what fun it is to ride',
    },
    {
        'lyrics': 'In a one-horse open sleigh',
    },
]

SONG_5 = [
    {
        'lyrics': 'You are my fire',
    },
    {
        'lyrics': 'The one desire',
    },
    {
        'lyrics': 'Believe when I say',
    },
    {
        'lyrics': 'I want it that way',
    },
    {
        'lyrics': 'But we are two worlds apart',
    },
    {
        'lyrics': 'Can\'t reach to your heart',
    },
    {
        'lyrics': 'When you say',
    },
    {
        'lyrics': 'That I want it that way',
    },
    {
        'lyrics': 'Tell me why',
    },
    {
        'lyrics': 'Ain\'t nothing but a heartache',
    },
    {
        'lyrics': 'Tell me why',
    },
    {
        'lyrics': 'Ain\'t nothing but a mistake',
    },
    {
        'lyrics': 'Tell me why',
    },
    {
        'lyrics': 'I never wanna hear you say',
    },
    {
        'lyrics': 'I want it that way',
    },
    {
        'lyrics': 'Am I your fire',
    },
    {
        'lyrics': 'Your one desire',
    },
    {
        'lyrics': 'Yes I know it\'s too late',
    },
    {
        'lyrics': 'But I want it that way',
    },
    {
        'lyrics': 'Tell me why',
    },
    {
        'lyrics': 'Ain\'t nothing but a heartache',
    },
    {
        'lyrics': 'Tell me why',
    },
    {
        'lyrics': 'Ain\'t nothing but a mistake',
    },
    {
        'lyrics': 'Tell me why',
    },
    {
        'lyrics': 'I never wanna hear you say',
    },
    {
        'lyrics': 'I want it that way',
    },
    {
        'lyrics': 'Now I can see that we\'re falling apart',
    },
    {
        'lyrics': 'From the way that it used to be, yeah',
    },
    {
        'lyrics': 'No matter the distance',
    },
    {
        'lyrics': 'I want you to know',
    },
    {
        'lyrics': 'That deep down inside of me',
    },
    {
        'lyrics': 'You are my fire',
    },
    {
        'lyrics': 'The one desire',
    },
    {
        'lyrics': 'You are',
    },
    {
        'lyrics': 'You are, you are, you are',
    },
    {
        'lyrics': 'Don\'t wanna hear you say',
    },
    {
        'lyrics': 'Ain\'t nothing but a heartache',
    },
    {
        'lyrics': 'Ain\'t nothing but a mistake (don\'t wanna hear you say)',
    },
    {
        'lyrics': 'I never wanna hear you say (oh, yeah)',
    },
    {
        'lyrics': 'I want it that way',
    },
    {
        'lyrics': 'Tell me why',
    },
    {
        'lyrics': 'Ain\'t nothing but a heartache',
    },
    {
        'lyrics': 'Tell me why',
    },
    {
        'lyrics': 'Ain\'t nothing but a mistake',
    },
    {
        'lyrics': 'Tell me why',
    },
    {
        'lyrics': 'I never wanna hear you say (don\'t wanna hear you say)',
    },
    {
        'lyrics': 'I want it that way',
    },
    {
        'lyrics': 'Tell me why',
    },
    {
        'lyrics': 'Ain\'t nothing but a heartache',
    },
    {
        'lyrics': 'Ain\'t nothing but a mistake',
    },
    {
        'lyrics': 'Tell me why',
    },
    {
        'lyrics': 'I never wanna hear you say (never wanna hear you say)',
    },
    {
        'lyrics': 'I want it that way',
    },
    {
        'lyrics': '\'Cause I want it that way',
    },
]

SONGS = {
    'Joy to the world': SONG_1,
    'Silent Night': SONG_2,
    'Jingle Bells': SONG_3,
    'Jingle Bells (chorus)': SONG_4,
    'I want it that way': SONG_5,
}

SONG_REFERENCES = {
    'Joy to the world': 'data/mp3/joytotheworld.mp3',
    'Silent Night': 'data/mp3/silentnight.mp3',
    'Jingle Bells': 'data/mp3/jinglebells.mp3',
    'Jingle Bells (chorus)': 'data/mp3/jinglebellschorus.mp3',
    'I want it that way': 'data/mp3/iwantitthatway.mp3',
}


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""

    addr = context.user_data.get(_USER_DATA_WALLET_KEY, {}).get(update.effective_user.id)
    if not addr:
        logging.info(f"user wallet not yet registered")
        await update.message.reply_text("Time to connect your wallet! Use '/register 0x...' to begin your karaoke journey")
        return

    keyboard = [
        [InlineKeyboardButton("Jingle Bells (chorus)", callback_data='button_Jingle Bells (chorus)')],
        [InlineKeyboardButton("Jingle Bells", callback_data='button_Jingle Bells')],
        [InlineKeyboardButton("Joy to the world", callback_data='button_Joy to the world')],
        [InlineKeyboardButton("Silent Night", callback_data='button_Silent Night')],
        [InlineKeyboardButton("I want it that way", callback_data='button_I want it that way')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Pick a tune that makes your soul sing!', reply_markup=reply_markup)

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

    return LYRICS


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        """
    🎤 Welcome to the Telegram Karaoke Bot Game\! 🎤

    Get ready to unleash your inner diva \(or dude\!\) with this electrifying bot\!

    Here's how to play:

    1\. ✨ Level Up\! ✨ Use '/register' to receive your FREE performance NFT and get ready to shine\!
    2\. Let the Music Play\! Start the fun with '/start' to begin the game\.
    3\. Choose Your Tunes\! Select a song from our awesome library\.
    4\. Showtime\! When the lyric appears, record your most fabulous voice message\.
    5\. 🌟 Rock the Scoreboard\! 🌟 Earn a score and unlock exclusive NFTs to show off your vocal prowess\!
    6\. Checkout the leaderboard\! Use '/leaderboard' to see the highscores\.
    7\. Cancel anytime\! Use '/cancel' to abort the current game\.

    Scoring:

    We aim for perfection \(100,000 points\!\), but we're all human, right? We deduct points for:

    🎤 Lyrical Slip\-ups: Those pesky missed words can really throw off the rhythm\!
    🎵 Pitch Imperfections: A little off\-key? No worries\! We'll try to be understanding \(mostly\)\.
    🎶 Rhythm Rumble: Can you keep the beat? Let's see if you can stay on track\!

    Get ready to sing your heart out and become a karaoke legend\!

    Telegram Karaoke NFT Site

    Visit [https://dub\.sh/tgkaraokesite](https://dub.sh/tgkaraokesite) to see the global list of Karaoke Performance NFTs\!
        """,
        parse_mode=ParseMode.MARKDOWN_V2,
    )

async def register_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /register is issued."""
    cmd = update.message.text.strip()
    addr = cmd.removeprefix('/register').strip()
    logging.info(f"received address: '{addr}'")

    if re.match(r"^0x[a-fA-F0-9]{40}$", addr):
        if _USER_DATA_WALLET_KEY not in context.user_data:
            context.user_data[_USER_DATA_WALLET_KEY] = {}
        context.user_data[_USER_DATA_WALLET_KEY][update.effective_user.id] = addr
        await update.message.reply_text(f"Your wallet '{addr}' is now linked! Let the karaoke fun begin!")
    else:
        await update.message.reply_text("Invalid wallet address format. Please use the format 0x...")

async def get_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /current_wallet is issued."""
    addr = context.user_data.get(_USER_DATA_WALLET_KEY, {}).get(update.effective_user.id)
    if addr:
        await update.message.reply_text(f"Wallet address registered: {addr}")
    else:
        await update.message.reply_text("No wallets registered yet. Please use command: /register 0x...")


async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /leaderboard is issued."""
    scores = _LEADERBOARD

    scores = sorted(scores, key=lambda s: s['score'], reverse=True)

    table = pt.PrettyTable(['Score', 'Song', 'Player'])
    table.align['Score'] = 'l'
    table.align['Song'] = 'r'
    table.align['Player'] = 'r'

    for score in scores:
        table.add_row([f"{score['score']:06}", score['song_id'], score['username']])

    await update.message.reply_text(f'<pre>{table}</pre>', parse_mode=ParseMode.HTML)

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

async def score_performance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Scores the whole performance."""
    await update.message.reply_text(f"You rocked it! Scoring your performance now...")

    user_id = update.effective_user.id
    game_info = context.user_data[_USER_DATA_GAME_KEY][user_id]

    # concatenate all audio files together
    logging.info(f"concatenate song lines")
    concatenated_song, concatenated_filename = concatenate_audio(game_info['recordings'])
    logging.info(f"concat done")

    # score the performance
    score = compare_audios(SONG_REFERENCES[game_info['song_id']], concatenated_filename)
    await update.message.reply_text(f"Your Score: {score}")

    await update.message.reply_audio(concatenated_song, caption='Your whole performance')


    _LEADERBOARD.append({
        'score': score,
        'song_id': game_info['song_id'],
        'username': update.message.from_user.first_name,
    })

    # mint the nft
    if _SKIP_NFT:
        logging.info(f"skipping generating nft image and metadata")
        return

    addr = context.user_data.get(_USER_DATA_WALLET_KEY, {}).get(update.effective_user.id)
    if not addr:
        logging.info(f"user wallet not yet registered")
        await update.message.reply_text("No wallets registered yet. Please use command: /register 0x...")

    logging.info(f"generating nft image and metadata")
    json_cid = create_upload_nft(score, game_info['song_id'])

    logging.info(f"minting nft for {json_cid}")
    receipt = call_contract_mint(addr, f"ipfs://{json_cid}")

    if receipt:
        txn_hash = receipt['transactionHash'].to_0x_hex()
        logging.info(f"minting nft receipt tx: {txn_hash}")
        await update.message.reply_text(
            f"""You just earned a shiny NFT\! Check it out here:

[https://dub\.sh/tgkaraokesite](https://dub.sh/tgkaraokesite)

[Txn: {txn_hash}]({TXN_SCAN_URL}{txn_hash})
        """,
            parse_mode=ParseMode.MARKDOWN_V2,
        )



def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("register", register_wallet_command))
    application.add_handler(CommandHandler("current_wallet", get_wallet_command))
    application.add_handler(CommandHandler("leaderboard", show_leaderboard))

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


    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
