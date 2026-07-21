import logging
import json
import os
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters

# ==================== تنظیمات ====================
TOKEN = "8776670663:AAFu2h8ts-u70pCS6DvAZiEaFWYaL_gwe_4"
ADMIN_ID = 312928236

USERS_FILE = "users.json"
ORDERS_FILE = "orders.json"
PLANS_FILE = "plans.json"
PAYMENTS_FILE = "payments.json"
DISCOUNTS_FILE = "discounts.json"
SUPPORT_FILE = "support.json"

PHOTOS_DIR = "payment_photos"
os.makedirs(PHOTOS_DIR, exist_ok=True)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== مدیریت دیتا ====================

def load_json(file_path, default_data):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if type(data) != type(default_data):
                    save_json(file_path, default_data)
                    return default_data
                return data
        except:
            save_json(file_path, default_data)
            return default_data
    else:
        save_json(file_path, default_data)
        return default_data

def save_json(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def load_users():
    return load_json(USERS_FILE, {})

def save_users(users):
    save_json(USERS_FILE, users)

def load_plans():
    default_plans = [
        {"id": 1, "name": "پنل 1 گیگابایت", "price": 6000, "description": "پنل با حجم 1 گیگابایت", "is_active": True},
        {"id": 2, "name": "پنل 5 گیگابایت", "price": 27000, "description": "پنل با حجم 5 گیگابایت", "is_active": True},
        {"id": 3, "name": "پنل 10 گیگابایت", "price": 55000, "description": "پنل با حجم 10 گیگابایت", "is_active": True},
        {"id": 4, "name": "پنل با حجم 100 گیگابایت", "price": 450000, "description": "پنل ویژه با سرعت بالا", "is_active": True}
    ]
    return load_json(PLANS_FILE, default_plans)

def save_plans(plans):
    save_json(PLANS_FILE, plans)

def load_orders():
    return load_json(ORDERS_FILE, [])

def save_orders(orders):
    save_json(ORDERS_FILE, orders)

def load_payments():
    return load_json(PAYMENTS_FILE, [])

def save_payments(payments):
    save_json(PAYMENTS_FILE, payments)

def load_discounts():
    return load_json(DISCOUNTS_FILE, {})

def save_discounts(discounts):
    save_json(DISCOUNTS_FILE, discounts)

def load_support():
    return load_json(SUPPORT_FILE, [])

def save_support(messages):
    save_json(SUPPORT_FILE, messages)

def get_user(telegram_id):
    users = load_users()
    return users.get(str(telegram_id))

def update_user_balance(telegram_id, amount):
    users = load_users()
    user_id = str(telegram_id)
    
    if user_id not in users:
        users[user_id] = {
            "telegram_id": telegram_id,
            "balance": 0,
            "username": "",
            "first_name": "",
            "register_date": datetime.now().isoformat()
        }
    
    users[user_id]["balance"] += amount
    save_users(users)
    return users[user_id]["balance"]

def get_user_balance(telegram_id):
    user = get_user(telegram_id)
    return user["balance"] if user else 0

def add_user_order(telegram_id, plan_id, amount, plan_name, status="pending"):
    orders = load_orders()
    order = {
        "id": len(orders) + 1,
        "user_id": telegram_id,
        "plan_id": plan_id,
        "plan_name": plan_name,
        "amount": amount,
        "price": amount,
        "status": status,
        "date": datetime.now().isoformat(),
        "config": ""
    }
    orders.append(order)
    save_orders(orders)
    return order

def get_user_orders(telegram_id, status=None):
    orders = load_orders()
    user_orders = [o for o in orders if o["user_id"] == telegram_id]
    if status:
        return [o for o in user_orders if o["status"] == status]
    return user_orders

def get_pending_orders():
    orders = load_orders()
    return [o for o in orders if o["status"] == "pending"]

def update_order_status(order_id, status, config=""):
    orders = load_orders()
    for order in orders:
        if order["id"] == order_id:
            order["status"] = status
            if config:
                order["config"] = config
            save_orders(orders)
            return True
    return False

def get_plan_by_id(plan_id):
    plans = load_plans()
    for plan in plans:
        if plan["id"] == plan_id:
            return plan
    return None

# ==================== مدیریت تخفیف ====================

def create_discount_code(code, discount_type, value, max_uses=1):
    discounts = load_discounts()
    
    if code in discounts:
        return False, "کد تکراری است!"
    
    discounts[code] = {
        "code": code,
        "type": discount_type,
        "value": value,
        "max_uses": max_uses,
        "used_count": 0,
        "is_active": True,
        "created_at": datetime.now().isoformat(),
        "used_by": []
    }
    save_discounts(discounts)
    return True, "کد تخفیف با موفقیت ساخته شد!"

def get_discount(code):
    discounts = load_discounts()
    return discounts.get(code)

def use_discount(code, user_id):
    discounts = load_discounts()
    
    if code not in discounts:
        return False, "کد تخفیف نامعتبر است!"
    
    discount = discounts[code]
    
    if not discount["is_active"]:
        return False, "این کد تخفیف غیرفعال شده است!"
    
    if discount["used_count"] >= discount["max_uses"]:
        return False, "این کد تخفیف قبلاً استفاده شده است!"
    
    if user_id in discount["used_by"]:
        return False, "شما قبلاً از این کد استفاده کرده‌اید!"
    
    discount["used_count"] += 1
    discount["used_by"].append(user_id)
    save_discounts(discounts)
    
    return True, discount

def deactivate_discount(code):
    discounts = load_discounts()
    
    if code not in discounts:
        return False, "کد یافت نشد!"
    
    discounts[code]["is_active"] = False
    save_discounts(discounts)
    return True, "کد تخفیف غیرفعال شد!"

def calculate_discounted_price(price, code):
    discount_info = get_discount(code)
    if not discount_info or not discount_info["is_active"]:
        return price, 0
    
    if discount_info["type"] == "percent":
        discount_amount = int(price * discount_info["value"] / 100)
    else:
        discount_amount = min(discount_info["value"], price)
    
    final_price = price - discount_amount
    return final_price, discount_amount

# ==================== مدیریت پشتیبانی ====================

def add_support_message(user_id, message, is_from_admin=False, reply_to=None):
    support_messages = load_support()
    
    new_message = {
        "id": len(support_messages) + 1,
        "user_id": user_id,
        "message": message,
        "is_from_admin": is_from_admin,
        "reply_to": reply_to,
        "date": datetime.now().isoformat(),
        "is_read": False
    }
    support_messages.append(new_message)
    save_support(support_messages)
    return new_message

def get_user_messages(user_id):
    support_messages = load_support()
    return [m for m in support_messages if m["user_id"] == user_id]

def get_unread_messages():
    support_messages = load_support()
    return [m for m in support_messages if not m["is_read"] and not m["is_from_admin"]]

def mark_as_read(message_id):
    support_messages = load_support()
    for msg in support_messages:
        if msg["id"] == message_id:
            msg["is_read"] = True
            save_support(support_messages)
            return True
    return False

# ==================== دکمه‌ها ====================

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("💰 شارژ حساب", callback_data='charge')],
        [InlineKeyboardButton("🛍️ خرید پنل", callback_data='buy_plan')],
        [InlineKeyboardButton("🎫 کد تخفیف", callback_data='discount')],
        [InlineKeyboardButton("📋 پنل‌های من", callback_data='my_plans')],
        [InlineKeyboardButton("📊 موجودی من", callback_data='my_balance')],
        [InlineKeyboardButton("📞 پشتیبانی", callback_data='support')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_keyboard():
    keyboard = [
        [InlineKeyboardButton("📋 سفارشات در انتظار", callback_data='admin_pending_orders')],
        [InlineKeyboardButton("🎫 مدیریت تخفیف", callback_data='admin_discounts')],
        [InlineKeyboardButton("💬 پیام‌های پشتیبانی", callback_data='admin_support_messages')],
        [InlineKeyboardButton("📊 آمار فروش", callback_data='admin_stats')],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data='back_to_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_discounts_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ ساخت کد تخفیف جدید", callback_data='admin_create_discount')],
        [InlineKeyboardButton("📋 لیست کدهای تخفیف", callback_data='admin_list_discounts')],
        [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data='admin_panel')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_plans_keyboard(discount_code=None):
    plans = load_plans()
    keyboard = []
    
    for plan in plans:
        if plan.get("is_active", True):
            price = plan['price']
            price_text = f"{price:,} تومان"
            
            if discount_code:
                discounted_price, discount_amount = calculate_discounted_price(price, discount_code)
                if discount_amount > 0:
                    price_text = f"~~{price:,}~~ {discounted_price:,} تومان (تخفیف {discount_amount:,})"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{plan['name']} - {price_text}",
                    callback_data=f"buy_plan_{plan['id']}"
                )
            ])
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_menu')])
    return InlineKeyboardMarkup(keyboard)

def get_charge_amounts():
    keyboard = [
        [
            InlineKeyboardButton("۵۰,۰۰۰ تومان", callback_data='charge_50000'),
            InlineKeyboardButton("۱۰۰,۰۰۰ تومان", callback_data='charge_100000')
        ],
        [
            InlineKeyboardButton("۲۰۰,۰۰۰ تومان", callback_data='charge_200000'),
            InlineKeyboardButton("۵۰۰,۰۰۰ تومان", callback_data='charge_500000')
        ],
        [
            InlineKeyboardButton("۱,۰۰۰,۰۰۰ تومان", callback_data='charge_1000000'),
            InlineKeyboardButton("سایر", callback_data='charge_other')
        ],
        [InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== دستورات بات ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id == ADMIN_ID:
        await update.message.reply_text(
            "👋 سلام ادمین عزیز!\n\nبه پنل مدیریت خوش آمدید.\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=get_admin_keyboard()
        )
        return
    
    users = load_users()
    user_id = str(user.id)
    if user_id not in users:
        users[user_id] = {
            "telegram_id": user.id,
            "balance": 0,
            "username": user.username or "",
            "first_name": user.first_name or "",
            "register_date": datetime.now().isoformat()
        }
        save_users(users)
    
    balance = get_user_balance(user.id)
    balance_str = f"{balance:,}"
    
    welcome_text = f"""
🔥 به فروشگاه پنل خوش آمدید!

👋 سلام {user.first_name} عزیز
💰 موجودی شما: {balance_str} تومان

لطفاً یکی از گزینه‌های زیر را انتخاب کنید:
"""
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard())

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    if user.id == ADMIN_ID:
        await query.message.edit_text(
            "👋 سلام ادمین عزیز!\n\nبه پنل مدیریت خوش آمدید.",
            reply_markup=get_admin_keyboard()
        )
        return
    
    balance = get_user_balance(user.id)
    balance_str = f"{balance:,}"
    
    text = f"""
🔥 به فروشگاه پنل خوش آمدید!

👋 سلام {user.first_name} عزیز
💰 موجودی شما: {balance_str} تومان

لطفاً یکی از گزینه‌های زیر را انتخاب کنید:
"""
    await query.message.edit_text(text, reply_markup=get_main_keyboard())

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    balance = get_user_balance(user.id)
    balance_str = f"{balance:,}"
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_menu')]]
    
    await query.message.edit_text(
        f"💰 موجودی شما: {balance_str} تومان",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== پشتیبانی ====================

async def show_support_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    messages = get_user_messages(user_id)
    
    keyboard = [
        [InlineKeyboardButton("✉️ ارسال پیام جدید", callback_data='support_send')],
        [InlineKeyboardButton("📋 تاریخچه مکالمات", callback_data='support_history')],
        [InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_menu')]
    ]
    
    text = "📞 **پشتیبانی**\n\n"
    
    if messages:
        last_msg = messages[-1]
        if last_msg["is_from_admin"]:
            text += "📨 **آخرین پاسخ از پشتیبان:**\n"
            text += f"{last_msg['message'][:100]}...\n\n"
        else:
            text += "📤 **آخرین پیام شما:**\n"
            text += f"{last_msg['message'][:100]}...\n\n"
    
    text += "برای ارتباط با پشتیبانی، روی دکمه زیر کلیک کنید."
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

SUPPORT_SEND = 1
SUPPORT_REPLY = 2

async def support_send_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "✉️ **ارسال پیام به پشتیبانی**\n\n"
        "لطفاً پیام خود را بنویسید و ارسال کنید:\n"
        "(متن، عکس، فایل یا هر چیزی که نیاز دارید)\n\n"
        "🔹 برای لغو، دستور /cancel را بزنید."
    )
    
    return SUPPORT_SEND

async def support_send_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    message_text = ""
    if update.message.text:
        message_text = update.message.text
    elif update.message.caption:
        message_text = update.message.caption
    else:
        message_text = "📎 پیام شامل فایل است"
    
    add_support_message(user_id, message_text, is_from_admin=False)
    
    keyboard = [
        [InlineKeyboardButton("📞 بازگشت به پشتیبانی", callback_data='support')],
        [InlineKeyboardButton("🔙 منو", callback_data='back_to_menu')]
    ]
    
    await update.message.reply_text(
        "✅ **پیام شما با موفقیت ارسال شد!**\n\n"
        "پشتیبان به زودی پاسخ شما را خواهد داد.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    user_info = get_user(user_id)
    user_name = user_info.get("first_name", "کاربر") if user_info else "کاربر"
    
    admin_text = f"""
💬 **پیام جدید از پشتیبانی!**

👤 کاربر: {user_name}
🆔 آیدی: `{user_id}`
📝 پیام: {message_text}
📅 تاریخ: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
    
    keyboard_admin = [
        [InlineKeyboardButton("✉️ پاسخ به کاربر", callback_data=f"support_reply_{user_id}")]
    ]
    
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_text,
        reply_markup=InlineKeyboardMarkup(keyboard_admin),
        parse_mode='Markdown'
    )
    
    return ConversationHandler.END

async def support_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    messages = get_user_messages(user_id)
    
    if not messages:
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پشتیبانی", callback_data='support')]]
        await query.message.edit_text(
            "📋 شما هنوز هیچ پیامی با پشتیبانی نداشته‌اید.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    text = "📋 **تاریخچه مکالمات شما:**\n\n"
    
    for msg in messages[-20:]:
        date = datetime.fromisoformat(msg["date"]).strftime("%Y-%m-%d %H:%M")
        sender = "👤 شما" if not msg["is_from_admin"] else "🛡️ پشتیبان"
        text += f"{sender} - {date}\n"
        text += f"📝 {msg['message'][:150]}{'...' if len(msg['message']) > 150 else ''}\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به پشتیبانی", callback_data='support')]]
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ==================== پشتیبانی برای ادمین ====================

async def admin_support_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    if user.id != ADMIN_ID:
        await query.message.edit_text("❌ شما دسترسی ندارید!")
        return
    
    unread = get_unread_messages()
    for msg in unread:
        mark_as_read(msg["id"])
    
    support_messages = load_support()
    
    users_dict = {}
    for msg in support_messages:
        if msg["user_id"] not in users_dict:
            user_info = get_user(msg["user_id"])
            user_name = user_info.get("first_name", "کاربر") if user_info else "کاربر"
            users_dict[msg["user_id"]] = {
                "name": user_name,
                "messages": []
            }
        users_dict[msg["user_id"]]["messages"].append(msg)
    
    if not users_dict:
        await query.message.edit_text(
            "📭 هیچ پیامی در صندوق پشتیبانی وجود ندارد.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data='admin_panel')]
            ])
        )
        return
    
    text = "💬 **پیام‌های پشتیبانی:**\n\n"
    
    keyboard = []
    for user_id, info in users_dict.items():
        unread_count = len([m for m in info["messages"] if not m["is_read"] and not m["is_from_admin"]])
        status = f" ({unread_count} پیام جدید)" if unread_count > 0 else ""
        
        text += f"👤 {info['name']}\n"
        text += f"🆔 `{user_id}`\n"
        text += f"📊 تعداد پیام‌ها: {len(info['messages'])}{status}\n\n"
        
        keyboard.append([
            InlineKeyboardButton(
                f"💬 {info['name']}",
                callback_data=f"admin_support_user_{user_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data='admin_panel')])
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def admin_support_user_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split('_')[3])
    context.user_data['support_user_id'] = user_id
    
    messages = get_user_messages(user_id)
    
    if not messages:
        await query.message.edit_text("❌ پیامی برای این کاربر وجود ندارد!")
        return
    
    user_info = get_user(user_id)
    user_name = user_info.get("first_name", "کاربر") if user_info else "کاربر"
    
    text = f"💬 **مکالمه با {user_name}**\n\n"
    
    for msg in messages[-20:]:
        date = datetime.fromisoformat(msg["date"]).strftime("%Y-%m-%d %H:%M")
        sender = "👤 کاربر" if not msg["is_from_admin"] else "🛡️ شما (ادمین)"
        text += f"{sender} - {date}\n"
        text += f"📝 {msg['message'][:150]}{'...' if len(msg['message']) > 150 else ''}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("✉️ پاسخ به کاربر", callback_data=f"support_reply_{user_id}")],
        [InlineKeyboardButton("🔙 بازگشت به پیام‌ها", callback_data='admin_support_messages')]
    ]
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def support_reply_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split('_')[2])
    context.user_data['support_reply_user_id'] = user_id
    
    user_info = get_user(user_id)
    user_name = user_info.get("first_name", "کاربر") if user_info else "کاربر"
    
    await query.message.edit_text(
        f"✉️ **پاسخ به {user_name}**\n\n"
        "لطفاً پاسخ خود را تایپ کنید و ارسال کنید:\n\n"
        "🔹 برای لغو، دستور /cancel را بزنید."
    )
    
    return SUPPORT_REPLY

async def support_reply_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ شما دسترسی ندارید!")
        return ConversationHandler.END
    
    user_id = context.user_data.get('support_reply_user_id')
    if not user_id:
        await update.message.reply_text("❌ کاربری انتخاب نشده!")
        return ConversationHandler.END
    
    message_text = ""
    if update.message.text:
        message_text = update.message.text
    elif update.message.caption:
        message_text = update.message.caption
    else:
        message_text = "📎 پاسخ شامل فایل است"
    
    add_support_message(user_id, message_text, is_from_admin=True)
    
    try:
        keyboard = [
            [InlineKeyboardButton("📞 پشتیبانی", callback_data='support')],
            [InlineKeyboardButton("🔙 منو", callback_data='back_to_menu')]
        ]
        
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🛡️ **پاسخ پشتیبانی:**\n\n{message_text}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        await update.message.reply_text(
            f"✅ **پاسخ با موفقیت ارسال شد!**\n\n👤 کاربر: {user_id}"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ارسال: {str(e)}")
    
    context.user_data['support_reply_user_id'] = None
    return ConversationHandler.END

# ==================== شارژ حساب ====================

async def show_charge_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
💰 **شارژ حساب**

لطفاً مبلغ مورد نظر برای شارژ حساب خود را انتخاب کنید:

📌 پس از انتخاب مبلغ، شماره کارت برای واریز نمایش داده می‌شود.
"""
    await query.message.edit_text(text, reply_markup=get_charge_amounts(), parse_mode='Markdown')

CHARGE_AMOUNT, CHARGE_PHOTO = range(2)

async def charge_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == 'charge_other':
        await query.message.edit_text(
            "💰 لطفاً مبلغ مورد نظر خود را به تومان وارد کنید:\nمثال: 150000"
        )
        return CHARGE_AMOUNT
    
    amount = int(data.split('_')[1])
    context.user_data['charge_amount'] = amount
    
    keyboard = [
        [InlineKeyboardButton("✅ واریز کردم، عکس رو بفرستم", callback_data='send_photo')],
        [InlineKeyboardButton("🔙 انصراف", callback_data='back_to_menu')]
    ]
    
    text = f"""
💰 **مبلغ انتخاب شده:** {amount:,} تومان

📌 **شماره کارت برای واریز:**
`6219861958949868`
به نام **کوروش وجاهت**

✅ پس از واریز، روی دکمه زیر کلیک کنید و عکس رسید رو بفرستید.
"""
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return ConversationHandler.END

async def charge_send_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "📸 لطفاً عکس رسید واریزی خود را ارسال کنید:"
    )
    return CHARGE_PHOTO

# ==================== اصلاح شده: ارسال عکس به ادمین ====================

async def handle_charge_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        amount = context.user_data.get('charge_amount', 0)
        
        # دریافت عکس
        photo = update.message.photo[-1]
        file = await photo.get_file()
        
        # دانلود عکس
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"payment_{user.id}_{timestamp}.jpg"
        filepath = os.path.join(PHOTOS_DIR, filename)
        await file.download_to_drive(filepath)
        
        # ذخیره در دیتابیس
        payments = load_payments()
        payment_id = len(payments) + 1
        
        payment = {
            "id": payment_id,
            "user_id": user.id,
            "username": user.username or "",
            "first_name": user.first_name or "",
            "amount": amount,
            "photo": filename,
            "status": "pending",
            "date": datetime.now().isoformat()
        }
        payments.append(payment)
        save_payments(payments)
        
        # پیام به کاربر
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_menu')]]
        await update.message.reply_text(
            f"✅ عکس رسید شما با موفقیت ارسال شد!\n"
            f"💰 مبلغ: {amount:,} تومان\n\n"
            f"⏳ درخواست شما در انتظار تایید است.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # ========== ارسال به ادمین ==========
        admin_text = f"""
🆕 **درخواست شارژ جدید!**

👤 کاربر: {user.first_name}
🆔 آیدی: `{user.id}`
👤 یوزرنیم: @{user.username or 'ندارد'}
💰 مبلغ: {amount:,} تومان
📅 تاریخ: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        
        keyboard_admin = [
            [InlineKeyboardButton("✅ تایید شارژ", callback_data=f"confirm_{payment_id}")],
            [InlineKeyboardButton("❌ رد شارژ", callback_data=f"reject_{payment_id}")]
        ]
        
        # ارسال عکس به ادمین
        try:
            with open(filepath, 'rb') as photo_file:
                await context.bot.send_photo(
                    chat_id=ADMIN_ID,
                    photo=photo_file,
                    caption=admin_text,
                    reply_markup=InlineKeyboardMarkup(keyboard_admin),
                    parse_mode='Markdown'
                )
            print(f"✅ عکس به ادمین ارسال شد! payment_id: {payment_id}")
            
        except Exception as e:
            # اگه ارسال عکس FAILED شد، حداقل پیام متنی بفرست
            print(f"❌ خطا در ارسال عکس: {e}")
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"{admin_text}\n\n⚠️ عکس قابل ارسال نیست! لطفاً فایل رو چک کنید.",
                reply_markup=InlineKeyboardMarkup(keyboard_admin),
                parse_mode='Markdown'
            )
        
        return ConversationHandler.END
        
    except Exception as e:
        print(f"❌ خطا در handle_charge_photo: {e}")
        await update.message.reply_text("❌ خطایی رخ داد! لطفاً دوباره تلاش کنید.")
        return ConversationHandler.END

async def handle_charge_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = int(update.message.text.replace(',', ''))
        if amount < 1000:
            await update.message.reply_text("❌ حداقل مبلغ شارژ ۱,۰۰۰ تومان است.")
            return CHARGE_AMOUNT
        
        context.user_data['charge_amount'] = amount
        
        keyboard = [
            [InlineKeyboardButton("✅ واریز کردم، عکس رو بفرستم", callback_data='send_photo')],
            [InlineKeyboardButton("🔙 انصراف", callback_data='back_to_menu')]
        ]
        
        text = f"""
💰 **مبلغ انتخاب شده:** {amount:,} تومان

📌 **شماره کارت برای واریز:**
`6219861958949868`
به نام **کوروش وجاهت**

✅ پس از واریز، روی دکمه زیر کلیک کنید و عکس رسید رو بفرستید.
"""
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return CHARGE_AMOUNT

# ==================== خرید پنل ====================

async def show_buy_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    discount_code = context.user_data.get('discount_code')
    
    text = """
🛍️ **خرید پنل**

لطفاً یکی از پنل‌های زیر را انتخاب کنید:

📌 پس از انتخاب، موجودی شما بررسی می‌شود.
"""
    
    if discount_code:
        discount_info = get_discount(discount_code)
        if discount_info and discount_info["is_active"]:
            text += f"\n🎫 **کد تخفیف فعال:** `{discount_code}`"
    
    await query.message.edit_text(text, reply_markup=get_plans_keyboard(discount_code), parse_mode='Markdown')

async def buy_plan_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        plan_id = int(query.data.split('_')[2])
    except:
        await query.message.edit_text("❌ خطا در پردازش!")
        return
    
    user_id = query.from_user.id
    plan = get_plan_by_id(plan_id)
    
    if not plan:
        await query.message.edit_text("❌ پنل مورد نظر یافت نشد!")
        return
    
    discount_code = context.user_data.get('discount_code')
    final_price = plan["price"]
    discount_amount = 0
    
    if discount_code:
        discount_info = get_discount(discount_code)
        if discount_info and discount_info["is_active"]:
            final_price, discount_amount = calculate_discounted_price(plan["price"], discount_code)
    
    balance = get_user_balance(user_id)
    
    if balance >= final_price:
        new_balance = balance - final_price
        users = load_users()
        users[str(user_id)]["balance"] = new_balance
        save_users(users)
        
        order = add_user_order(user_id, plan_id, final_price, plan["name"], status="pending")
        
        if not order:
            await query.message.edit_text("❌ خطا در ثبت سفارش!")
            return
        
        if discount_code:
            context.user_data['discount_code'] = None
        
        keyboard = [
            [InlineKeyboardButton("📋 سفارشات من", callback_data='my_plans')],
            [InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_menu')]
        ]
        
        discount_text = ""
        if discount_amount > 0:
            discount_text = f"\n🎫 تخفیف: {discount_amount:,} تومان"
        
        await query.message.edit_text(
            f"✅ **خرید با موفقیت انجام شد!**\n\n"
            f"📦 پنل: {plan['name']}\n"
            f"💰 قیمت اصلی: {plan['price']:,} تومان{discount_text}\n"
            f"💳 مبلغ پرداختی: {final_price:,} تومان\n"
            f"💳 موجودی باقی‌مانده: {new_balance:,} تومان\n\n"
            f"🆔 شماره سفارش: {order['id']}\n"
            f"⏳ وضعیت: در انتظار ارسال",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        admin_text = f"""
🆕 **سفارش جدید!**

🆔 شماره سفارش: {order['id']}
👤 کاربر: {query.from_user.first_name}
🆔 آیدی: `{user_id}`
📦 پنل: {plan['name']}
💰 مبلغ پرداختی: {final_price:,} تومان
{'🎫 کد تخفیف: ' + discount_code if discount_code else ''}
📅 تاریخ: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
⏳ وضعیت: در انتظار ارسال
"""
        keyboard_admin = [
            [InlineKeyboardButton("📨 ارسال کانفیگ", callback_data=f"send_config_{order['id']}")]
        ]
        
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            reply_markup=InlineKeyboardMarkup(keyboard_admin),
            parse_mode='Markdown'
        )
        
    else:
        keyboard = [
            [InlineKeyboardButton("💰 شارژ حساب", callback_data='charge')],
            [InlineKeyboardButton("🔙 بازگشت به لیست", callback_data='buy_plan')],
            [InlineKeyboardButton("🏠 منو", callback_data='back_to_menu')]
        ]
        
        await query.message.edit_text(
            f"❌ **موجودی شما کافی نیست!**\n\n"
            f"📦 پنل: {plan['name']}\n"
            f"💰 قیمت: {final_price:,} تومان\n"
            f"💳 موجودی شما: {balance:,} تومان\n\n"
            f"لطفاً ابتدا حساب خود را شارژ کنید.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# ==================== پنل‌های من ====================

async def show_my_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    orders = get_user_orders(user_id)
    
    if not orders:
        keyboard = [
            [InlineKeyboardButton("🛍️ خرید پنل", callback_data='buy_plan')],
            [InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_menu')]
        ]
        await query.message.edit_text(
            "📋 شما هنوز هیچ سفارشی ثبت نکرده‌اید.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    text = "📋 **سفارشات شما:**\n\n"
    for order in reversed(orders[-20:]):
        date = datetime.fromisoformat(order["date"]).strftime("%Y-%m-%d %H:%M")
        
        status_emoji = {
            "pending": "⏳",
            "completed": "✅",
            "delivered": "📨"
        }
        status_text = {
            "pending": "در انتظار ارسال",
            "completed": "تکمیل شده",
            "delivered": "ارسال شده"
        }
        
        status = order.get("status", "pending")
        emoji = status_emoji.get(status, "❓")
        status_persian = status_text.get(status, "نامشخص")
        
        text += f"{emoji} #{order['id']} - {order['plan_name']}\n"
        text += f"   💰 {order['price']:,} تومان - {date}\n"
        text += f"   📌 وضعیت: {status_persian}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🛍️ خرید جدید", callback_data='buy_plan')],
        [InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_menu')]
    ]
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ==================== کد تخفیف ====================

async def show_discount_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("✅ اعمال کد تخفیف", callback_data='apply_discount')],
        [InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_menu')]
    ]
    
    await query.message.edit_text(
        "🎫 **کد تخفیف**\n\n"
        "اگر کد تخفیف دارید، روی دکمه زیر کلیک کنید و کد را وارد کنید.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

DISCOUNT_APPLY = 1

async def apply_discount_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "🎫 **اعمال کد تخفیف**\n\n"
        "لطفاً کد تخفیف خود را وارد کنید:\n"
        "(مثال: OFF10)\n\n"
        "🔹 برای لغو، دستور /cancel را بزنید."
    )
    
    return DISCOUNT_APPLY

async def apply_discount_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.upper().strip()
    user_id = update.effective_user.id
    
    success, result = use_discount(code, user_id)
    
    if not success:
        await update.message.reply_text(f"❌ {result}")
        return ConversationHandler.END
    
    discount = result
    context.user_data['discount_code'] = code
    
    discount_text = ""
    if discount["type"] == "percent":
        discount_text = f"{discount['value']}٪ تخفیف"
    else:
        discount_text = f"{discount['value']:,} تومان تخفیف"
    
    keyboard = [[InlineKeyboardButton("🛍️ خرید پنل با تخفیف", callback_data='buy_plan')]]
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_menu')])
    
    await update.message.reply_text(
        f"✅ **کد تخفیف با موفقیت اعمال شد!**\n\n"
        f"🎫 کد: `{code}`\n"
        f"💵 {discount_text}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return ConversationHandler.END

# ==================== پنل ادمین ====================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    if user.id != ADMIN_ID:
        await query.message.edit_text("❌ شما دسترسی ندارید!")
        return
    
    await query.message.edit_text(
        "👋 به پنل مدیریت خوش آمدید!\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=get_admin_keyboard()
    )

async def admin_pending_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    if user.id != ADMIN_ID:
        await query.message.edit_text("❌ شما دسترسی ندارید!")
        return
    
    orders = get_pending_orders()
    
    if not orders:
        await query.message.edit_text(
            "✅ هیچ سفارش در انتظاری وجود ندارد.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data='admin_panel')]
            ])
        )
        return
    
    text = "📋 **سفارشات در انتظار ارسال:**\n\n"
    for order in orders:
        user_info = get_user(order["user_id"])
        user_name = user_info.get("first_name", "ناشناس") if user_info else "ناشناس"
        date = datetime.fromisoformat(order["date"]).strftime("%Y-%m-%d %H:%M")
        
        text += f"🆔 #{order['id']} - {user_name}\n"
        text += f"   📦 {order['plan_name']}\n"
        text += f"   💰 {order['price']:,} تومان\n"
        text += f"   📅 {date}\n"
        text += f"   🆔 کاربر: `{order['user_id']}`\n\n"
    
    keyboard = []
    for order in orders:
        keyboard.append([
            InlineKeyboardButton(
                f"📨 ارسال کانفیگ برای سفارش #{order['id']}",
                callback_data=f"send_config_{order['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data='admin_panel')])
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    if user.id != ADMIN_ID:
        await query.message.edit_text("❌ شما دسترسی ندارید!")
        return
    
    orders = load_orders()
    total_orders = len(orders)
    pending_orders = len([o for o in orders if o["status"] == "pending"])
    delivered_orders = len([o for o in orders if o["status"] == "delivered"])
    total_revenue = sum([o["price"] for o in orders if o["status"] == "delivered"])
    
    users = load_users()
    total_users = len(users)
    
    discounts = load_discounts()
    total_discounts = len(discounts)
    
    support_messages = load_support()
    total_support = len(support_messages)
    unread_support = len([m for m in support_messages if not m["is_read"] and not m["is_from_admin"]])
    
    text = f"""
📊 **آمار فروش:**

👥 کاربران: {total_users} نفر
📦 کل سفارشات: {total_orders}
⏳ در انتظار ارسال: {pending_orders}
✅ تحویل شده: {delivered_orders}
💰 درآمد کل: {total_revenue:,} تومان
🎫 کدهای تخفیف: {total_discounts}
💬 پیام‌های پشتیبانی: {total_support}
📨 پیام‌های خوانده نشده: {unread_support}

📅 آخرین به‌روزرسانی: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data='admin_panel')]
    ]
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ==================== ارسال کانفیگ ====================

SENDING_CONFIG = 1

async def admin_send_config_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    if user.id != ADMIN_ID:
        await query.message.edit_text("❌ شما دسترسی ندارید!")
        return
    
    try:
        order_id = int(query.data.split('_')[2])
    except:
        await query.message.edit_text("❌ خطا در پردازش!")
        return
    
    context.user_data['sending_order_id'] = order_id
    
    orders = load_orders()
    order = None
    for o in orders:
        if o["id"] == order_id:
            order = o
            break
    
    if not order:
        await query.message.edit_text("❌ سفارش یافت نشد!")
        return
    
    user_info = get_user(order["user_id"])
    user_name = user_info.get("first_name", "ناشناس") if user_info else "ناشناس"
    
    await query.message.edit_text(
        f"📨 **ارسال کانفیگ برای سفارش #{order_id}**\n\n"
        f"👤 کاربر: {user_name}\n"
        f"📦 پنل: {order['plan_name']}\n"
        f"💰 قیمت: {order['price']:,} تومان\n\n"
        f"✏️ لطفاً کانفیگ را ارسال کنید:\n\n"
        f"🔹 برای لغو، /cancel را بزنید.",
        parse_mode='Markdown'
    )
    
    return SENDING_CONFIG

async def admin_send_config_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ شما دسترسی ندارید!")
        return ConversationHandler.END
    
    order_id = context.user_data.get('sending_order_id')
    if not order_id:
        await update.message.reply_text("❌ سفارشی انتخاب نشده!")
        return ConversationHandler.END
    
    orders = load_orders()
    order = None
    for o in orders:
        if o["id"] == order_id:
            order = o
            break
    
    if not order:
        await update.message.reply_text("❌ سفارش یافت نشد!")
        return ConversationHandler.END
    
    config_text = update.message.text
    user_id = order["user_id"]
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ **کانفیگ سفارش #{order_id} شما ارسال شد!**\n\n"
                 f"📦 پنل: {order['plan_name']}\n\n"
                 f"🔑 **کانفیگ:**\n"
                 f"`{config_text}`",
            parse_mode='Markdown'
        )
        
        update_order_status(order_id, "delivered", config_text)
        
        await update.message.reply_text(
            f"✅ **کانفیگ با موفقیت ارسال شد!**\n\n"
            f"🆔 سفارش #{order_id}"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ارسال کانفیگ: {str(e)}")
    
    context.user_data['sending_order_id'] = None
    return ConversationHandler.END

async def admin_send_config_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ عملیات لغو شد.", reply_markup=get_admin_keyboard())
    context.user_data['sending_order_id'] = None
    return ConversationHandler.END

# ==================== تایید/رد شارژ ====================

async def admin_confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        payment_id = int(query.data.split('_')[1])
        
        payments = load_payments()
        payment = None
        for p in payments:
            if p["id"] == payment_id:
                payment = p
                break
        
        if not payment:
            await query.message.edit_text("❌ درخواست یافت نشد!")
            return
        
        new_balance = update_user_balance(payment["user_id"], payment["amount"])
        payment["status"] = "confirmed"
        save_payments(payments)
        
        await query.message.edit_text(
            f"✅ **شارژ کاربر تایید شد!**\n\n"
            f"👤 کاربر: {payment['first_name']}\n"
            f"💰 مبلغ: {payment['amount']:,} تومان\n"
            f"💳 موجودی جدید: {new_balance:,} تومان"
        )
        
        try:
            keyboard = [[InlineKeyboardButton("💰 مشاهده موجودی", callback_data='my_balance')]]
            await context.bot.send_message(
                chat_id=payment["user_id"],
                text=f"✅ **شارژ حساب شما تایید شد!**\n\n"
                     f"💰 مبلغ: {payment['amount']:,} تومان\n"
                     f"💳 موجودی جدید: {new_balance:,} تومان",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except:
            pass
            
    except Exception as e:
        print(f"❌ خطا: {e}")
        await query.message.edit_text(f"❌ خطا: {str(e)}")

async def admin_reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        payment_id = int(query.data.split('_')[1])
        
        payments = load_payments()
        payment = None
        for p in payments:
            if p["id"] == payment_id:
                payment = p
                break
        
        if not payment:
            await query.message.edit_text("❌ درخواست یافت نشد!")
            return
        
        payment["status"] = "rejected"
        save_payments(payments)
        
        await query.message.edit_text(
            f"❌ **شارژ کاربر رد شد!**\n\n"
            f"👤 کاربر: {payment['first_name']}\n"
            f"💰 مبلغ: {payment['amount']:,} تومان"
        )
        
        try:
            await context.bot.send_message(
                chat_id=payment["user_id"],
                text=f"❌ متأسفیم، درخواست شارژ شما رد شد."
            )
        except:
            pass
            
    except Exception as e:
        print(f"❌ خطا: {e}")
        await query.message.edit_text(f"❌ خطا: {str(e)}")

# ==================== مدیریت تخفیف (ادمین) ====================

async def admin_discounts_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    if user.id != ADMIN_ID:
        await query.message.edit_text("❌ شما دسترسی ندارید!")
        return
    
    await query.message.edit_text(
        "🎫 **مدیریت کدهای تخفیف**",
        reply_markup=get_admin_discounts_keyboard(),
        parse_mode='Markdown'
    )

CREATE_DISCOUNT_CODE, CREATE_DISCOUNT_TYPE, CREATE_DISCOUNT_VALUE, CREATE_DISCOUNT_USES = range(4)

async def admin_create_discount_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    if user.id != ADMIN_ID:
        await query.message.edit_text("❌ شما دسترسی ندارید!")
        return
    
    await query.message.edit_text(
        "🎫 **ساخت کد تخفیف جدید**\n\n"
        "لطفاً **کد تخفیف** را وارد کنید:\n"
        "(مثال: OFF10)\n\n"
        "🔹 برای لغو، /cancel را بزنید."
    )
    
    return CREATE_DISCOUNT_CODE

async def admin_create_discount_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.upper().strip()
    context.user_data['new_discount_code'] = code
    
    keyboard = [
        [InlineKeyboardButton("درصدی (۱۰٪)", callback_data='discount_type_percent')],
        [InlineKeyboardButton("مبلغ ثابت (۵۰,۰۰۰)", callback_data='discount_type_fixed')]
    ]
    
    await update.message.reply_text(
        f"🎫 **کد:** `{code}`\n\nلطفاً نوع تخفیف را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return CREATE_DISCOUNT_TYPE

async def admin_create_discount_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    discount_type = query.data.split('_')[2]
    context.user_data['new_discount_type'] = discount_type
    
    await query.message.edit_text(
        "🎫 لطفاً **مقدار تخفیف** را وارد کنید:\n"
        "(مثلاً 10 یا 50000)",
        parse_mode='Markdown'
    )
    
    return CREATE_DISCOUNT_VALUE

async def admin_create_discount_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        value = int(update.message.text.replace(',', ''))
        if value <= 0:
            await update.message.reply_text("❌ مقدار باید بیشتر از ۰ باشد!")
            return CREATE_DISCOUNT_VALUE
        
        context.user_data['new_discount_value'] = value
        
        await update.message.reply_text(
            "🎫 **تعداد دفعات استفاده** را وارد کنید:\n"
            "(1 = یکبار مصرف، 0 = نامحدود)"
        )
        
        return CREATE_DISCOUNT_USES
        
    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید!")
        return CREATE_DISCOUNT_VALUE

async def admin_create_discount_uses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        max_uses = int(update.message.text.replace(',', ''))
        if max_uses < 0:
            await update.message.reply_text("❌ تعداد نمی‌تواند منفی باشد!")
            return CREATE_DISCOUNT_USES
        
        code = context.user_data['new_discount_code']
        discount_type = context.user_data['new_discount_type']
        value = context.user_data['new_discount_value']
        
        success, message = create_discount_code(code, discount_type, value, max_uses if max_uses > 0 else 999999)
        
        if not success:
            await update.message.reply_text(f"❌ {message}")
            return ConversationHandler.END
        
        context.user_data['new_discount_code'] = None
        context.user_data['new_discount_type'] = None
        context.user_data['new_discount_value'] = None
        
        await update.message.reply_text(
            f"✅ **کد تخفیف با موفقیت ساخته شد!**\n\n"
            f"🎫 کد: `{code}`\n"
            f"📊 تعداد استفاده: {'نامحدود' if max_uses == 0 else f'{max_uses} بار'}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_discounts')]
            ]),
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید!")
        return CREATE_DISCOUNT_USES

async def admin_list_discounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    if user.id != ADMIN_ID:
        await query.message.edit_text("❌ شما دسترسی ندارید!")
        return
    
    discounts = load_discounts()
    
    if not discounts:
        await query.message.edit_text(
            "📋 هیچ کد تخفیفی ساخته نشده است.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_discounts')]
            ])
        )
        return
    
    text = "📋 **لیست کدهای تخفیف:**\n\n"
    
    for code, info in discounts.items():
        status = "✅ فعال" if info["is_active"] else "❌ غیرفعال"
        type_text = f"{info['value']}٪" if info["type"] == "percent" else f"{info['value']:,} تومان"
        uses_text = f"{info['used_count']}/{info['max_uses']}"
        
        text += f"🎫 `{code}`\n"
        text += f"   💵 {type_text} - {status}\n"
        text += f"   📊 استفاده: {uses_text}\n"
        text += f"   👥 کاربران: {len(info['used_by'])}\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_discounts')]]
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def admin_disable_discount_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    if user.id != ADMIN_ID:
        await query.message.edit_text("❌ شما دسترسی ندارید!")
        return
    
    code = query.data.split('_')[2]
    success, message = deactivate_discount(code)
    
    await query.message.edit_text(f"{'✅' if success else '❌'} {message}")
    await admin_list_discounts(update, context)

# ==================== مدیریت کلیک‌ها ====================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == 'back_to_menu':
        await back_to_menu(update, context)
    elif data == 'charge':
        await show_charge_options(update, context)
    elif data.startswith('charge_'):
        await charge_selected(update, context)
    elif data == 'send_photo':
        await charge_send_photo(update, context)
    elif data == 'buy_plan':
        await show_buy_plans(update, context)
    elif data.startswith('buy_plan_'):
        await buy_plan_selected(update, context)
    elif data == 'discount':
        await show_discount_menu(update, context)
    elif data == 'apply_discount':
        await apply_discount_start(update, context)
    elif data == 'my_plans':
        await show_my_plans(update, context)
    elif data == 'my_balance':
        await show_balance(update, context)
    elif data == 'support':
        await show_support_menu(update, context)
    elif data == 'support_send':
        await support_send_start(update, context)
    elif data == 'support_history':
        await support_history(update, context)
    elif data == 'admin_panel':
        await admin_panel(update, context)
    elif data == 'admin_pending_orders':
        await admin_pending_orders(update, context)
    elif data == 'admin_stats':
        await admin_stats(update, context)
    elif data == 'admin_discounts':
        await admin_discounts_menu(update, context)
    elif data == 'admin_create_discount':
        await admin_create_discount_start(update, context)
    elif data == 'admin_list_discounts':
        await admin_list_discounts(update, context)
    elif data.startswith('disable_discount_'):
        await admin_disable_discount_code(update, context)
    elif data.startswith('discount_type_'):
        await admin_create_discount_type(update, context)
    elif data == 'admin_support_messages':
        await admin_support_messages(update, context)
    elif data.startswith('admin_support_user_'):
        await admin_support_user_messages(update, context)
    elif data.startswith('support_reply_'):
        await support_reply_start(update, context)
    elif data.startswith('confirm_'):
        await admin_confirm_payment(update, context)
    elif data.startswith('reject_'):
        await admin_reject_payment(update, context)
    elif data.startswith('send_config_'):
        await admin_send_config_start(update, context)
    else:
        await query.answer("دستور نامعتبر!")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ عملیات لغو شد.", reply_markup=get_main_keyboard())
    context.user_data['sending_order_id'] = None
    context.user_data['discount_code'] = None
    context.user_data['support_reply_user_id'] = None
    return ConversationHandler.END

# ==================== اجرای بات ====================

async def run_bot():
    application = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(60.0)
        .read_timeout(60.0)
        .write_timeout(60.0)
        .pool_timeout(60.0)
        .build()
    )
    
    commands = [
        BotCommand("start", "شروع 🚀"),
        BotCommand("cancel", "لغو ❌"),
    ]
    await application.bot.set_my_commands(commands)
    print("✅ دستورات بات تنظیم شد!")
    
    send_config_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_send_config_start, pattern='^send_config_')
        ],
        states={
            SENDING_CONFIG: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_send_config_message)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    charge_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(charge_selected, pattern='^charge_'),
            CallbackQueryHandler(charge_send_photo, pattern='^send_photo$')
        ],
        states={
            CHARGE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_charge_amount)],
            CHARGE_PHOTO: [MessageHandler(filters.PHOTO, handle_charge_photo)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    discount_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(apply_discount_start, pattern='^apply_discount$')
        ],
        states={
            DISCOUNT_APPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_discount_code)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    create_discount_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_create_discount_start, pattern='^admin_create_discount$')
        ],
        states={
            CREATE_DISCOUNT_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_create_discount_code)],
            CREATE_DISCOUNT_TYPE: [CallbackQueryHandler(admin_create_discount_type, pattern='^discount_type_')],
            CREATE_DISCOUNT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_create_discount_value)],
            CREATE_DISCOUNT_USES: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_create_discount_uses)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    support_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(support_send_start, pattern='^support_send$')
        ],
        states={
            SUPPORT_SEND: [MessageHandler(filters.ALL, support_send_message)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    support_reply_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(support_reply_start, pattern='^support_reply_')
        ],
        states={
            SUPPORT_REPLY: [MessageHandler(filters.ALL, support_reply_message)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(charge_conv)
    application.add_handler(send_config_conv)
    application.add_handler(discount_conv)
    application.add_handler(create_discount_conv)
    application.add_handler(support_conv)
    application.add_handler(support_reply_conv)
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    print("=" * 50)
    print("🤖 بات فروشگاه پنل روشن شد!")
    print(f"👤 آیدی ادمین: {ADMIN_ID}")
    print("✅ منوی خرید فعال شد")
    print("✅ سیستم پشتیبانی فعال شد")
    print("✅ کد تخفیف فعال شد")
    print("=" * 50)
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query"]
    )
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 بات متوقف شد.")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == '__main__':
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n🛑 بات متوقف شد.")