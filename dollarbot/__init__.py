import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from decouple import config
import requests

from datetime import datetime
from persiantools.jdatetime import JalaliDateTime
from persiantools import digits

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

# Emoji icons for different asset types
ASSET_ICONS = {
    "usd": "💵",
    "eur": "💶",
    "cad": "💵",
    "bitcoin": "₿",
    "ethereum": "Ξ",
    "thether": "₮",
    "shiba ino": "🐕",
    "gold": "🏆",
}


def convert_to_persian_date(english_date_str):
    """Convert 'last update : 18:55 24 March 2025' to Persian format"""
    try:
        # Extract the date part
        date_part = english_date_str.replace("last update : ", "")

        # Parse the English datetime
        dt = datetime.strptime(date_part, "%H:%M %d %B %Y")

        # Convert to Jalali (Persian) datetime
        jalali_dt = JalaliDateTime(dt)

        # Persian month names
        persian_months = {
            1: "فروردین",
            2: "اردیبهشت",
            3: "خرداد",
            4: "تیر",
            5: "مرداد",
            6: "شهریور",
            7: "مهر",
            8: "آبان",
            9: "آذر",
            10: "دی",
            11: "بهمن",
            12: "اسفند",
        }

        # Format components
        time = digits.en_to_fa(jalali_dt.strftime("%H:%M"))
        day = digits.en_to_fa(str(jalali_dt.day))
        month = persian_months[jalali_dt.month]
        year = digits.en_to_fa(str(jalali_dt.year))

        return f"{time} {day} {month} {year}"
    except Exception as e:
        logger.error(f"Error converting date: {e}")
        return english_date_str  # fallback to original if conversion fails


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="سلام! من ربات قیمت‌های لحظه‌ای هستم. برای دریافت قیمت‌ها از دستور /latest استفاده کنید.",
    )


def fetch_current_price():
    current = requests.post(
        "https://admin.alanchand.com/api/home",
        json=dict(lang="en"),
        headers={"Content-Type": "application/json", "TE": "trailers"},
    ).json()
    return current


def _get_display_name(current_price: dict):
    slug = current_price.get("slug")
    name = current_price.get("fname", current_price.get("name"))
    if slug == "usdt":
        price = current_price.get("price")[0].get("toman")
    else:
        price = current_price.get("price")[0].get("price")
    return slug, name, price


def format_price(price):
    """Format price with commas and convert to Persian digits"""
    try:
        price = float(price)
        formatted = "{:,.0f}".format(price)
        return digits.en_to_fa(formatted)
    except:
        return price


def create_message():
    all_current_price = fetch_current_price()

    update_time_str = all_current_price.get("updatedSync")
    persian_update_time = convert_to_persian_date(update_time_str)

    fiat_price = [
        _get_display_name(p)
        for p in all_current_price.get("arz")
        if p.get("slug") in ("usd", "eur", "cad")
    ]
    crypto_price = [
        _get_display_name(p)
        for p in all_current_price.get("crypto")
        if p.get("name")
        in (
            "bitcoin",
            "ethereum",
            "binance coin",
            # "shiba ino",
            "tether",
        )
    ]
    gold_price = [_get_display_name(p) for p in all_current_price.get("gold")]

    # Build the message with formatting
    message_parts = []

    # Add fiat prices
    message_parts.append("\n<b>💵 ارزهای خارجی:</b>")
    for slug, name, price in fiat_price:
        icon = "•"
        message_parts.append(f"{icon} <b>{name}</b>: {format_price(price)} تومان")

    # Add crypto prices
    message_parts.append("\n<b>🪙 ارزهای دیجیتال:</b>")
    for slug, name, price in sorted(crypto_price, key=lambda x: x[0] != "usdt"):
        icon = ASSET_ICONS.get(name.lower(), "•")
        message_parts.append(
            f"{icon} <b>{name}</b>: {format_price(price)} {'تومان' if slug == 'usdt' else 'دلار'}"
        )

    # Add gold prices
    message_parts.append("\n<b>🏆 طلا و سکه:</b>")
    for slug, name, price in gold_price:
        icon = ASSET_ICONS.get(slug.lower(), "•")
        message_parts.append(f"{icon} <b>{name}</b>: {format_price(price)} تومان")

    # Add footer
    message_parts.append("\n")
    message_parts.append(f"🔄 آخرین بروزرسانی: {persian_update_time}")

    return "\n".join(message_parts)


async def current_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = create_message()
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=message, parse_mode="HTML"
    )


if __name__ == "__main__":
    application = ApplicationBuilder().token(config("TELEGRAM_BOT_API_KEY")).build()

    start_handler = CommandHandler("start", start)
    current_handler = CommandHandler("latest", current_price)
    application.add_handler(start_handler)
    application.add_handler(current_handler)

    application.run_polling()
