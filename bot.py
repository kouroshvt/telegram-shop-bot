import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

# ==================== تنظیمات ====================
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 312928236))
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not all([TOKEN, SUPABASE_URL, SUPABASE_KEY]):
    raise Exception("❌ توکن یا اطلاعات Supabase تنظیم نشده! .env رو چک کن.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ==================== توابع دیتابیس ====================

def get_user(telegram_id):
    try:
        result = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ get_user: {e}")
        return None

def create_user(telegram_id, username, first_name):
    try:
        data = {
            "telegram_id": telegram_id,
            "username": username or "",
            "first_name": first_name or "",
            "balance": 0
        }
        result = supabase.table("users").insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ create_user: {e}")
        return None

def get_balance(telegram_id):
    try:
        result = supabase.table("users").select("balance").eq("telegram_id", telegram_id).execute()
        return result.data[0]["balance"] if result.data else 0
    except Exception as e:
        return 0

def update_balance(telegram_id, amount):
    try:
        user = get_user(telegram_id)
        if not user:
            return None
        new_balance = user["balance"] + amount
        result = supabase.table("users").update({"balance": new_balance}).eq("telegram_id", telegram_id).execute()
        return result.data[0]["balance"] if result.data else None
    except Exception as e:
        print(f"❌ update_balance: {e}")
        return None

def get_plans():
    try:
        result = supabase.table("plans").select("*").eq("is_active", True).execute()
        return result.data
    except Exception as e:
        print(f"❌ get_plans: {e}")
        return []

def get_plan_by_id(plan_id):
    try:
        result = supabase.table("plans").select("*").eq("id", plan_id).eq("is_active", True).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        return None

def add_order(user_id, plan_id, plan_name, price):
    try:
        data = {
            "user_id": user_id,
            "plan_id": plan_id,
            "plan_name": plan_name,
            "price": price,
            "status": "pending",
            "date": datetime.now().isoformat()
        }
        result = supabase.table("orders").insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ add_order: {e}")
        return None

def get_user_orders(telegram_id):
    try:
        result = supabase.table("orders").select("*").eq("user_id", telegram_id).order("id", desc=True).execute()
        return result.data
    except Exception as e:
        return []

def get_pending_orders():
    try:
        result = supabase.table("orders").select("*").eq("status", "pending").execute()
        return result.data
    except Exception as e:
        return []

def update_order_status(order_id, status, config=""):
    try:
        data = {"status": status}
        if config:
            data["config"] = config
        result = supabase.table("orders").update(data).eq("id", order_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ update_order_status: {e}")
        return None

def add_payment(user_id, amount, photo_url):
    try:
        data = {
            "user_id": user_id,
            "amount": amount,
            "photo_url": photo_url,
            "status": "pending",
            "date": datetime.now().isoformat()
        }
        result = supabase.table("payments").insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ add_payment: {e}")
        return None

def get_pending_payments():
    try:
        result = supabase.table("payments").select("*").eq("status", "pending").execute()
        return result.data
    except Exception as e:
        return []

def confirm_payment(payment_id):
    try:
        result = supabase.table("payments").update({"status": "confirmed"}).eq("id", payment_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        return None

def reject_payment(payment_id):
    try:
        result = supabase.table("payments").update({"status": "rejected"}).eq("id", payment_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        return None

def add_support_message(user_id, message, is_from_admin=False):
    try:
        data = {
            "user_id": user_id,
            "message": message,
            "is_from_admin": is_from_admin,
            "date": datetime.now().isoformat()
        }
        result = supabase.table("support_messages").insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ add_support_message: {e}")
        return None

def get_user_support_messages(user_id):
    try:
        result = supabase.table("support_messages").select("*").eq("user_id", user_id).order("id").execute()
        return result.data
    except Exception as e:
        return []

def get_all_unread_messages():
    try:
        result = supabase.table("support_messages").select("*").eq("is_read", False).eq("is_from_admin", False).execute()
        return result.data
    except Exception as e:
        return []

def mark_support_read(message_id):
    try:
        supabase.table("support_messages").update({"is_read": True}).eq("id", message_id).execute()
        return True
    except Exception as e:
        return False

# ==================== تخفیف ====================

def get_discount(code):
    try:
        result = supabase.table("discounts").select("*").eq("code", code).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        return None

def use_discount(code, user_id):
    try:
        discount = get_discount(code)
        if not discount:
            return False, "کد تخفیف نامعتبر است!"
        if not discount["is_active"]:
            return False, "این کد تخفیف غیرفعال شده است!"
        if discount["used_count"] >= discount["max_uses"]:
            return False, "این کد تخفیف قبلاً استفاده شده است!"
        if user_id in discount["used_by"]:
            return False, "شما قبلاً از این کد استفاده کرده‌اید!"
        used_by = discount["used_by"] + [user_id]
        supabase.table("discounts").update({
            "used_count": discount["used_count"] + 1,
            "used_by": used_by
        }).eq("code", code).execute()
        return True, discount
    except Exception as e:
        return False, str(e)

def calculate_discounted_price(price, code):
    discount = get_discount(code)
    if not discount or not discount["is_active"]:
        return price, 0
    if discount["type"] == "percent":
        discount_amount = int(price * discount["value"] / 100)
    else:
        discount_amount = min(discount["value"], price)
    return price - discount_amount, discount_amount

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
        [InlineKeyboardButton("💳 تایید شارژ", callback_data='admin_payments')],
        [InlineKeyboardButton("💬 پیام‌های پشتیبانی", callback_data='admin_support_messages')],
        [InlineKeyboardButton("📊 آمار فروش", callback_data='admin_stats')],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data='back_to_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_plans_keyboard(discount_code=None):
    plans = get_plans()
    keyboard = []
    for plan in plans:
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
        await update.message.reply_text("👋 سلام ادمین عزیز!", reply_markup=get_admin_keyboard())
        return
    if not get_user(user.id):
        create_user(user.id, user.username, user.first_name)
    balance = get_balance(user.id)
    await update.message.reply_text(
        f"🔥 به فروشگاه پنل خوش آمدید!\n\n👋 سلام {user.first_name} عزیز\n💰 موجودی شما: {balance:,} تومان",
        reply_markup=get_main_keyboard()
    )

async def back_to_menu(update: Update, context):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    if user.id == ADMIN_ID:
        await query.message.edit_text("👋 سلام ادمین عزیز!", reply_markup=get_admin_keyboard())
        return
    balance = get_balance(user.id)
    await query.message.edit_text(
        f"🔥 به فروشگاه پنل خوش آمدید!\n\n👋 سلام {user.first_name} عزیز\n💰 موجودی شما: {balance:,} تومان",
        reply_markup=get_main_keyboard()
    )

async def show_balance(update: Update, context):
    query = update.callback_query
    await query.answer()
    balance = get_balance(query.from_user.id)
    await query.message.edit_text(
        f"💰 موجودی شما: {balance:,} تومان",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_menu')]])
    )

# ==================== شارژ حساب ====================

async def show_charge_options(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text(
        "💰 **شارژ حساب**\n\nلطفاً مبلغ مورد نظر را انتخاب کنید:",
        reply_markup=get_charge_amounts(),
        parse_mode='Markdown'
    )

CHARGE_AMOUNT, CHARGE_PHOTO = range(2)

async def charge_selected(update: Update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == 'charge_other':
        await query.message.edit_text("💰 لطفاً مبلغ مورد نظر را به تومان وارد کنید:\nمثال: 150000")
        return CHARGE_AMOUNT
    amount = int(data.split('_')[1])
    context.user_data['charge_amount'] = amount
    await query.message.edit_text(
        f"💰 **مبلغ انتخاب شده:** {amount:,} تومان\n\n📌 شماره کارت: `6219861958949868`\nبه نام **کوروش وجاهت**\n\n✅ پس از واریز، روی دکمه زیر کلیک کنید.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ واریز کردم، عکس رو بفرستم", callback_data='send_photo')],
            [InlineKeyboardButton("🔙 انصراف", callback_data='back_to_menu')]
        ]),
        parse_mode='Markdown'
    )
    return ConversationHandler.END

async def charge_send_photo(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text("📸 لطفاً عکس رسید واریزی خود را ارسال کنید:")
    return CHARGE_PHOTO

async def handle_charge_photo(update: Update, context):
    try:
        user = update.effective_user
        amount = context.user_data.get('charge_amount', 0)
        photo = update.message.photo[-1]
        file_id = photo.file_id
        payment = add_payment(user.id, amount, file_id)
        if not payment:
            await update.message.reply_text("❌ خطا در ثبت درخواست!")
            return ConversationHandler.END
        await update.message.reply_text(
            f"✅ عکس رسید شما با موفقیت ارسال شد!\n💰 مبلغ: {amount:,} تومان\n\n⏳ درخواست شما در انتظار تایید است.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منو", callback_data='back_to_menu')]])
        )
        admin_text = f"🆕 **درخواست شارژ جدید!**\n\n👤 کاربر: {user.first_name}\n🆔 آیدی: `{user.id}`\n💰 مبلغ: {amount:,} تومان"
        keyboard_admin = [
            [InlineKeyboardButton("✅ تایید", callback_data=f"admin_confirm_payment_{payment['id']}")],
            [InlineKeyboardButton("❌ رد", callback_data=f"admin_reject_payment_{payment['id']}")]
        ]
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=file_id,
            caption=admin_text,
            reply_markup=InlineKeyboardMarkup(keyboard_admin),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    except Exception as e:
        print(f"❌ handle_charge_photo: {e}")
        await update.message.reply_text("❌ خطا!")
        return ConversationHandler.END

async def handle_charge_amount(update: Update, context):
    try:
        amount = int(update.message.text.replace(',', ''))
        if amount < 1000:
            await update.message.reply_text("❌ حداقل مبلغ ۱,۰۰۰ تومان است.")
            return CHARGE_AMOUNT
        context.user_data['charge_amount'] = amount
        await update.message.reply_text(
            f"💰 **مبلغ:** {amount:,} تومان\n\n📌 شماره کارت: `6219861958949868`\nبه نام **کوروش وجاهت**\n\n✅ پس از واریز، روی دکمه زیر کلیک کنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ واریز کردم، عکس رو بفرستم", callback_data='send_photo')],
                [InlineKeyboardButton("🔙 انصراف", callback_data='back_to_menu')]
            ]),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return CHARGE_AMOUNT

# ==================== خرید پنل ====================

async def show_buy_plans(update: Update, context):
    query = update.callback_query
    await query.answer()
    discount_code = context.user_data.get('discount_code')
    text = "🛍️ **خرید پنل**\n\nلطفاً یکی از پنل‌های زیر را انتخاب کنید:"
    if discount_code and get_discount(discount_code):
        text += f"\n🎫 کد تخفیف فعال: `{discount_code}`"
    await query.message.edit_text(text, reply_markup=get_plans_keyboard(discount_code), parse_mode='Markdown')

async def buy_plan_selected(update: Update, context):
    query = update.callback_query
    await query.answer()
    try:
        plan_id = int(query.data.split('_')[2])
    except:
        await query.message.edit_text("❌ خطا!")
        return
    user_id = query.from_user.id
    plan = get_plan_by_id(plan_id)
    if not plan:
        await query.message.edit_text("❌ پنل یافت نشد!")
        return
    discount_code = context.user_data.get('discount_code')
    final_price, discount_amount = calculate_discounted_price(plan["price"], discount_code)
    balance = get_balance(user_id)
    if balance >= final_price:
        new_balance = update_balance(user_id, -final_price)
        if new_balance is None:
            await query.message.edit_text("❌ خطا!")
            return
        order = add_order(user_id, plan_id, plan["name"], final_price)
        if not order:
            await query.message.edit_text("❌ خطا در ثبت سفارش!")
            return
        if discount_code:
            context.user_data['discount_code'] = None
        await query.message.edit_text(
            f"✅ **خرید موفق!**\n\n📦 {plan['name']}\n💰 قیمت: {final_price:,} تومان\n💳 موجودی: {new_balance:,} تومان\n🆔 سفارش: {order['id']}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 سفارشات من", callback_data='my_plans')],
                [InlineKeyboardButton("🔙 منو", callback_data='back_to_menu')]
            ])
        )
        admin_text = f"🆕 **سفارش جدید!**\n\n👤 {query.from_user.first_name}\n📦 {plan['name']}\n💰 {final_price:,} تومان"
        await context.bot.send_message(
            ADMIN_ID,
            text=admin_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📨 ارسال کانفیگ", callback_data=f"send_config_{order['id']}")]
            ])
        )
    else:
        await query.message.edit_text(
            f"❌ **موجودی کافی نیست!**\n\n📦 {plan['name']}\n💰 قیمت: {final_price:,} تومان\n💳 موجودی: {balance:,} تومان",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 شارژ حساب", callback_data='charge')],
                [InlineKeyboardButton("🔙 لیست", callback_data='buy_plan')],
                [InlineKeyboardButton("🏠 منو", callback_data='back_to_menu')]
            ])
        )

# ==================== پنل‌های من ====================

async def show_my_plans(update: Update, context):
    query = update.callback_query
    await query.answer()
    orders = get_user_orders(query.from_user.id)
    if not orders:
        await query.message.edit_text("📋 شما هیچ سفارشی ندارید.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍️ خرید", callback_data='buy_plan')],
            [InlineKeyboardButton("🔙 منو", callback_data='back_to_menu')]
        ]))
        return
    text = "📋 **سفارشات شما:**\n\n"
    for o in orders[:10]:
        status_emoji = {"pending": "⏳", "completed": "✅", "delivered": "📨"}
        text += f"{status_emoji.get(o['status'], '❓')} #{o['id']} - {o['plan_name']}\n💰 {o['price']:,} تومان\n\n"
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ خرید جدید", callback_data='buy_plan')],
        [InlineKeyboardButton("🔙 منو", callback_data='back_to_menu')]
    ]), parse_mode='Markdown')

# ==================== پشتیبانی ====================

async def show_support_menu(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text(
        "📞 **پشتیبانی**\n\nبرای ارسال پیام به پشتیبانی، روی دکمه زیر کلیک کنید.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✉️ ارسال پیام", callback_data='support_send')],
            [InlineKeyboardButton("📋 تاریخچه", callback_data='support_history')],
            [InlineKeyboardButton("🔙 منو", callback_data='back_to_menu')]
        ])
    )

SUPPORT_SEND = 1

async def support_send_start(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text("✉️ لطفاً پیام خود را بنویسید و ارسال کنید:\n\n🔹 برای لغو /cancel")
    return SUPPORT_SEND

async def support_send_message(update: Update, context):
    user = update.effective_user
    msg = update.message.text or "📎 پیام شامل فایل است"
    add_support_message(user.id, msg, is_from_admin=False)
    await update.message.reply_text("✅ پیام شما ارسال شد!", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 پشتیبانی", callback_data='support')],
        [InlineKeyboardButton("🔙 منو", callback_data='back_to_menu')]
    ]))
    await context.bot.send_message(
        ADMIN_ID,
        text=f"💬 **پیام جدید از پشتیبانی!**\n\n👤 {user.first_name}\n🆔 {user.id}\n📝 {msg}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✉️ پاسخ", callback_data=f"support_reply_{user.id}")]
        ])
    )
    return ConversationHandler.END

async def support_history(update: Update, context):
    query = update.callback_query
    await query.answer()
    messages = get_user_support_messages(query.from_user.id)
    if not messages:
        await query.message.edit_text("📋 شما هیچ پیامی نداشته‌اید.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 پشتیبانی", callback_data='support')]
        ]))
        return
    text = "📋 **تاریخچه مکالمات:**\n\n"
    for m in messages[-10:]:
        sender = "👤 شما" if not m["is_from_admin"] else "🛡️ پشتیبان"
        text += f"{sender}: {m['message'][:100]}...\n"
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 پشتیبانی", callback_data='support')]
    ]))

SUPPORT_REPLY = 2

async def support_reply_start(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split('_')[2])
    context.user_data['support_reply_user_id'] = user_id
    await query.message.edit_text("✉️ پاسخ خود را تایپ کنید:\n\n🔹 برای لغو /cancel")
    return SUPPORT_REPLY

async def support_reply_message(update: Update, context):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ شما دسترسی ندارید!")
        return ConversationHandler.END
    user_id = context.user_data.get('support_reply_user_id')
    if not user_id:
        await update.message.reply_text("❌ کاربری انتخاب نشده!")
        return ConversationHandler.END
    msg = update.message.text or "📎 پاسخ شامل فایل است"
    add_support_message(user_id, msg, is_from_admin=True)
    await context.bot.send_message(user_id, f"🛡️ **پاسخ پشتیبانی:**\n\n{msg}")
    await update.message.reply_text("✅ پاسخ ارسال شد!")
    context.user_data['support_reply_user_id'] = None
    return ConversationHandler.END

# ==================== ادمین ====================

async def admin_payments(update: Update, context):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.message.edit_text("❌ دسترسی ندارید!")
        return
    payments = get_pending_payments()
    if not payments:
        await query.message.edit_text("✅ هیچ درخواست شارژی در انتظار تایید نیست.")
        return
    text = "💳 **درخواست‌های شارژ:**\n\n"
    for p in payments:
        user = get_user(p["user_id"])
        name = user["first_name"] if user else "کاربر"
        text += f"🆔 {p['id']} - {name}\n💰 {p['amount']:,} تومان\n"
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 پنل ادمین", callback_data='admin_panel')]
    ]))

async def admin_pending_orders(update: Update, context):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.message.edit_text("❌ دسترسی ندارید!")
        return
    orders = get_pending_orders()
    if not orders:
        await query.message.edit_text("✅ هیچ سفارش در انتظاری وجود ندارد.")
        return
    text = "📋 **سفارشات در انتظار:**\n\n"
    for o in orders:
        user = get_user(o["user_id"])
        name = user["first_name"] if user else "کاربر"
        text += f"🆔 {o['id']} - {name}\n📦 {o['plan_name']}\n💰 {o['price']:,} تومان\n\n"
    keyboard = []
    for o in orders:
        keyboard.append([InlineKeyboardButton(f"📨 ارسال کانفیگ #{o['id']}", callback_data=f"send_config_{o['id']}")])
    keyboard.append([InlineKeyboardButton("🔙 پنل ادمین", callback_data='admin_panel')])
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

SENDING_CONFIG = 1

async def send_config_start(update: Update, context):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.message.edit_text("❌ دسترسی ندارید!")
        return
    order_id = int(query.data.split('_')[2])
    context.user_data['sending_order_id'] = order_id
    await query.message.edit_text("📨 کانفیگ را تایپ کنید:\n\n🔹 برای لغو /cancel")
    return SENDING_CONFIG

async def send_config_message(update: Update, context):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ دسترسی ندارید!")
        return ConversationHandler.END
    order_id = context.user_data.get('sending_order_id')
    if not order_id:
        await update.message.reply_text("❌ سفارشی انتخاب نشده!")
        return ConversationHandler.END
    config = update.message.text
    order = update_order_status(order_id, "delivered", config)
    if order:
        await context.bot.send_message(order["user_id"], f"✅ **کانفیگ سفارش #{order_id} ارسال شد!**\n\n{config}")
        await update.message.reply_text("✅ کانفیگ ارسال شد!")
    else:
        await update.message.reply_text("❌ خطا!")
    context.user_data['sending_order_id'] = None
    return ConversationHandler.END

# ==================== تخفیف ====================

async def show_discount_menu(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text(
        "🎫 **کد تخفیف**\n\nاگر کد تخفیف دارید، روی دکمه زیر کلیک کنید.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ اعمال کد", callback_data='apply_discount')],
            [InlineKeyboardButton("🔙 منو", callback_data='back_to_menu')]
        ])
    )

DISCOUNT_APPLY = 1

async def apply_discount_start(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text("🎫 کد تخفیف را وارد کنید:\n\n🔹 برای لغو /cancel")
    return DISCOUNT_APPLY

async def apply_discount_code(update: Update, context):
    code = update.message.text.upper().strip()
    user_id = update.effective_user.id
    success, result = use_discount(code, user_id)
    if not success:
        await update.message.reply_text(f"❌ {result}")
        return ConversationHandler.END
    context.user_data['discount_code'] = code
    await update.message.reply_text(
        f"✅ کد تخفیف اعمال شد!\n🎫 {code}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍️ خرید با تخفیف", callback_data='buy_plan')],
            [InlineKeyboardButton("🔙 منو", callback_data='back_to_menu')]
        ])
    )
    return ConversationHandler.END

# ==================== ادمین پنل ====================

async def admin_panel(update: Update, context):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.message.edit_text("❌ دسترسی ندارید!")
        return
    await query.message.edit_text("👋 پنل مدیریت", reply_markup=get_admin_keyboard())

async def admin_stats(update: Update, context):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.message.edit_text("❌ دسترسی ندارید!")
        return
    users = supabase.table("users").select("*").execute()
    orders = supabase.table("orders").select("*").execute()
    text = f"📊 **آمار:**\n\n👥 کاربران: {len(users.data)}\n📦 سفارشات: {len(orders.data)}"
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 پنل ادمین", callback_data='admin_panel')]
    ]))

# ==================== مدیریت کلیک‌ها ====================

async def handle_callback(update: Update, context):
    query = update.callback_query
    data = query.data
    if data == 'back_to_menu':
        await back_to_menu(update, context)
    elif data == 'charge':
        await show_charge_options(update, context)
    elif data == 'buy_plan':
        await show_buy_plans(update, context)
    elif data == 'discount':
        await show_discount_menu(update, context)
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
    elif data == 'admin_payments':
        await admin_payments(update, context)
    elif data == 'admin_stats':
        await admin_stats(update, context)
    elif data == 'apply_discount':
        await apply_discount_start(update, context)
    elif data.startswith('buy_plan_'):
        await buy_plan_selected(update, context)
    elif data.startswith('charge_'):
        await charge_selected(update, context)
    elif data == 'send_photo':
        await charge_send_photo(update, context)
    elif data.startswith('admin_confirm_payment_'):
        payment_id = int(data.split('_')[3])
        confirm_payment(payment_id)
        await query.message.edit_text("✅ شارژ تایید شد!")
    elif data.startswith('admin_reject_payment_'):
        payment_id = int(data.split('_')[3])
        reject_payment(payment_id)
        await query.message.edit_text("❌ شارژ رد شد!")
    elif data.startswith('send_config_'):
        await send_config_start(update, context)
    elif data.startswith('support_reply_'):
        await support_reply_start(update, context)
    else:
        await query.answer("دستور نامعتبر!")

async def cancel(update: Update, context):
    await update.message.reply_text("❌ عملیات لغو شد.", reply_markup=get_main_keyboard())
    return ConversationHandler.END

# ==================== اجرا ====================

async def run_bot():
    app = Application.builder().token(TOKEN).connect_timeout(60).read_timeout(60).build()
    await app.bot.set_my_commands([BotCommand("start", "شروع 🚀"), BotCommand("cancel", "لغو ❌")])
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(charge_selected, pattern='^charge_'), CallbackQueryHandler(charge_send_photo, pattern='^send_photo$')],
        states={
            CHARGE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_charge_amount)],
            CHARGE_PHOTO: [MessageHandler(filters.PHOTO, handle_charge_photo)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    ))
    
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(apply_discount_start, pattern='^apply_discount$')],
        states={DISCOUNT_APPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_discount_code)]},
        fallbacks=[CommandHandler('cancel', cancel)]
    ))
    
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(support_send_start, pattern='^support_send$')],
        states={SUPPORT_SEND: [MessageHandler(filters.TEXT & ~filters.COMMAND, support_send_message)]},
        fallbacks=[CommandHandler('cancel', cancel)]
    ))
    
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(support_reply_start, pattern='^support_reply_')],
        states={SUPPORT_REPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, support_reply_message)]},
        fallbacks=[CommandHandler('cancel', cancel)]
    ))
    
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(send_config_start, pattern='^send_config_')],
        states={SENDING_CONFIG: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_config_message)]},
        fallbacks=[CommandHandler('cancel', cancel)]
    ))
    
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("🤖 بات روشن شد!")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == '__main__':
    asyncio.run(run_bot())