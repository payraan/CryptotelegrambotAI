import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime
from utils.media_handler import media_handler
from config.constants import (
    MAIN_MENU, SELECTING_MARKET, SELECTING_TIMEFRAME,
    SELECTING_STRATEGY, WAITING_IMAGES, PROCESSING_ANALYSIS,
    MARKETS, TIMEFRAMES, EXPECTED_TIMEFRAMES, STRATEGIES, STRATEGY_CATEGORIES
)
from config.settings import NARMOON_DEX_LINK, NARMOON_COIN_LINK, TUTORIAL_VIDEO_LINK, SOLANA_WALLETS
from database.operations import check_subscription, register_user, activate_subscription
from services.ai_service import analyze_chart_images
from utils.helpers import load_static_texts
# بارگزاری متن‌های ثابت
STATIC_TEXTS = load_static_texts()
async def send_long_message(update, context, message, max_length=3500):
    """تقسیم پیام‌های طولانی به چند بخش"""
    if len(message) <= max_length:
        # پیام کوتاه است، ارسال معمولی
        await update.message.reply_text(message, parse_mode='Markdown')
        return
    
    # تقسیم پیام به چند بخش
    chunks = []
    current_chunk = ""
    lines = message.split('\n')
    
    for line in lines:
        if len(current_chunk) + len(line) + 1 > max_length:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = line + '\n'
            else:
                # خط خیلی طولانی است، تقسیم اجباری
                chunks.append(line[:max_length])
                current_chunk = line[max_length:] + '\n'
        else:
            current_chunk += line + '\n'
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # ارسال قسمت‌ها
    for i, chunk in enumerate(chunks):
        if i == 0:
            header = f"📊 تحلیل مولتی تایم فریم نارموون (بخش {i+1}/{len(chunks)})\n\n"
            await update.message.reply_text(header + chunk, parse_mode='Markdown')
        else:
            await asyncio.sleep(1.5)  # تاخیر 1.5 ثانیه
            header = f"📊 ادامه تحلیل (بخش {i+1}/{len(chunks)})\n\n"
            await update.message.reply_text(header + chunk, parse_mode='Markdown')

# هندلرهای اصلی
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ربات و نمایش منوی اصلی"""
    # ریست وضعیت کاربر
    context.user_data.clear()
    
    # ثبت کاربر در دیتابیس
    user_id = update.effective_user.id
    username = update.effective_user.username
    register_user(user_id, username)
    
    # پردازش کد رفرال اگر وجود داشته باشد
    if context.args and len(context.args) > 0:
        referral_param = context.args[0]
        if referral_param.startswith("REF"):
            # پردازش رفرال
            from database.operations import create_referral_relationship
            result = create_referral_relationship(referral_param, user_id)
            
            if result.get("success"):
                # نمایش پیام موفقیت به کاربر جدید
                referrer_id = result.get("referrer_id")
                await update.message.reply_text(
                    f"🎉 شما از طریق کد دعوت وارد شده‌اید!\n"
                    f"با خرید اشتراک، دعوت‌کننده شما کمیسیون دریافت می‌کند."
                )
            elif "قبلاً ثبت شده" in result.get("error", ""):
                # کاربر قبلاً از این کد استفاده کرده
                await update.message.reply_text(
                    "شما قبلاً از این کد دعوت استفاده کرده‌اید."
                )
    
   # ایجاد منوی اصلی
    main_menu_buttons = [
    [InlineKeyboardButton("📊 تحلیل نمودارها با هوش مصنوعی TNT", callback_data="analyze_charts")],
    [InlineKeyboardButton("🪙 رمزارز", callback_data="crypto")],
    [InlineKeyboardButton("💰 سیستم رفرال", callback_data="referral_panel")],
    [
        InlineKeyboardButton("💳 خرید اشتراک", callback_data="subscription"),
        InlineKeyboardButton("📚 دفترچه راهنما", callback_data="guide")
    ],
    [InlineKeyboardButton("🧠 قابلیت‌های دستیار هوش مصنوعی", callback_data="ai_features")],
    [
        InlineKeyboardButton("❓ سوالات متداول", callback_data="faq"),
        InlineKeyboardButton("📜 قوانین و مقررات", callback_data="terms")
    ],
    [InlineKeyboardButton("👨‍💻 ارتباط با پشتیبانی", callback_data="support")]
    ]

    main_menu_markup = InlineKeyboardMarkup(main_menu_buttons)
    
    # تلاش برای ارسال با رسانه
    print(f"🔍 DEBUG: About to call media_handler...")
    media_sent = await media_handler.send_welcome_media(update, context, main_menu_markup)
    print(f"🔍 DEBUG: media_sent result: {media_sent}")

    # اگر رسانه ارسال نشد، متن ساده ارسال کن
    if not media_sent:
        user_name = update.effective_user.first_name if update.effective_user.first_name else "کاربر"
        welcome_text = f"""
سلام {user_name} عزیز! 👋✨ به دستیار هوش مصنوعی معامله‌گری نارموون خوش اومدی!

🚀 اینجا می‌تونی:
- بازارهای مالی رو با قدرت هوش مصنوعی تحلیل کنی
- آمار لحظه‌ای رمزارزها رو ببینی
- سیگنال بگیری و همیشه یک قدم جلوتر از بازار باشی

🔹 برای شروع می‌تونی از منوی پایین یکی از گزینه‌ها رو انتخاب کنی!
    """
    
    # اگر callback_query داریم (برگشت به منوی اصلی)
    if update.callback_query:
        await update.callback_query.edit_message_text(
            welcome_text,
            reply_markup=main_menu_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            welcome_text,
            reply_markup=main_menu_markup,
            parse_mode='Markdown'
        )

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش دکمه‌های فشرده شده در منوی اصلی"""
    query = update.callback_query
    await query.answer()
    
    # بررسی کدام دکمه فشرده شده است
    if query.data == "main_menu":
        return await start(update, context)
    elif query.data == "guide":
        return await usage_guide(update, context)
    elif query.data == "terms":
        return await terms_and_conditions(update, context)
    elif query.data == "subscription":
        return await subscription_plans(update, context)
    elif query.data == "support":
        return await support_contact(update, context)
    elif query.data == "narmoon_products":
        return await show_narmoon_products(update, context)
    elif query.data == "ai_features":
        return await show_ai_features(update, context)
    elif query.data == "faq":
        return await show_faq(update, context)
    elif query.data == "crypto":
        from handlers.crypto_handlers import crypto_menu
        return await crypto_menu(update, context)
    elif query.data == "referral_panel":
        return await show_referral_panel(update, context)
    elif query.data == "analyze_charts":
        user_id = update.effective_user.id
        from database.operations import check_tnt_analysis_limit
        
        limit_check = check_tnt_analysis_limit(user_id)
        
        if limit_check["allowed"]:
            return await show_market_selection(update, context)
        else:
            subscription_buttons = [
                [InlineKeyboardButton("💳 خرید اشتراک TNT", callback_data="subscription")],
                [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
            ]
            
            await query.edit_message_text(
                "⚠️ برای استفاده از تحلیل TNT نیاز به اشتراک دارید",
                reply_markup=InlineKeyboardMarkup(subscription_buttons)
            )
            return MAIN_MENU
    
    return MAIN_MENU

async def show_market_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست بازارها برای انتخاب"""
   
    market_buttons = [
        [InlineKeyboardButton("🪙 رمزارزها", callback_data="market_crypto")],
        [
            InlineKeyboardButton("💱 فارکس", callback_data="market_forex"),
            InlineKeyboardButton("🥇 طلا", callback_data="market_gold")
        ],
        [
            InlineKeyboardButton("📈 سهام خارجی", callback_data="market_international_stocks"),
            InlineKeyboardButton("📊 سهام ایران", callback_data="market_iranian_stocks")
        ],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
 
    market_markup = InlineKeyboardMarkup(market_buttons)
    
    await update.callback_query.edit_message_text(
        "🎯 لطفاً بازار مورد نظر خود را انتخاب کنید:",
        reply_markup=market_markup
    )
    
    return SELECTING_MARKET

async def handle_market_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت انتخاب بازار"""
    query = update.callback_query
    await query.answer()
    
    # استخراج کلید بازار انتخابی
    market_key = query.data.replace("market_", "")
    context.user_data['selected_market'] = market_key
    
    # انتقال به انتخاب تایم فریم
    return await show_timeframes(update, context)

async def show_timeframes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست تایم‌فریم‌ها برای انتخاب"""

    timeframe_buttons = [
        [
            InlineKeyboardButton("۱ دقیقه", callback_data="tf_۱ دقیقه"),
            InlineKeyboardButton("۵ دقیقه", callback_data="tf_۵ دقیقه"),
            InlineKeyboardButton("۱۵ دقیقه", callback_data="tf_۱۵ دقیقه")
        ],
        [
            InlineKeyboardButton("۱ ساعته", callback_data="tf_۱ ساعته"),
            InlineKeyboardButton("۴ ساعته", callback_data="tf_۴ ساعته"),
            InlineKeyboardButton("روزانه", callback_data="tf_روزانه")
        ],
        [InlineKeyboardButton("هفتگی", callback_data="tf_هفتگی")]
    ]
    
    # Fix: بهبود navigation buttons
    timeframe_buttons.append([
        InlineKeyboardButton("🔙 بازگشت به انتخاب بازار", callback_data="analyze_charts"),
        InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")
    ])
    timeframe_markup = InlineKeyboardMarkup(timeframe_buttons)
    
    # نمایش بازار انتخابی
    selected_market = context.user_data.get('selected_market', 'نامشخص')
    market_name = MARKETS.get(selected_market, 'نامشخص')
    
    await update.callback_query.edit_message_text(
        f"📊 بازار انتخابی: {market_name}\n\n⏰ لطفاً تایم‌فریم مورد نظر خود را انتخاب کنید:",
        reply_markup=timeframe_markup
    )
    
    return SELECTING_TIMEFRAME

async def handle_timeframe_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت انتخاب تایم‌فریم"""
    query = update.callback_query
    await query.answer()
    
    selected_tf = query.data.replace("tf_", "")
    context.user_data['selected_timeframe'] = selected_tf
    context.user_data['expected_frames'] = EXPECTED_TIMEFRAMES[selected_tf]
    context.user_data['received_images'] = []
    
    # انتقال به انتخاب استراتژی
    return await show_strategy_selection(update, context)

async def show_strategy_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتخاب خودکار استراتژی نارموون (تنها گزینه موجود)"""
    
    # مستقیم انتخاب استراتژی نارموون بدون نمایش منو
    context.user_data['selected_strategy'] = 'narmoon_ai'
    
    # بارگیری پرامپت استراتژی از فایل استراتژی‌ها
    from resources.prompts.strategies import STRATEGY_PROMPTS
    context.user_data['strategy_prompt'] = STRATEGY_PROMPTS['narmoon_ai']
    
    # نمایش اطلاعات انتخاب‌ها
    selected_market = context.user_data.get('selected_market', 'نامشخص')
    selected_timeframe = context.user_data.get('selected_timeframe', 'نامشخص')
    market_name = MARKETS.get(selected_market, 'نامشخص')
    expected_frames = context.user_data['expected_frames']
    tf_list = " - ".join(expected_frames)
    
    await update.callback_query.edit_message_text(
        f"✅ انتخاب‌های شما:\n" +
        f"📊 بازار: {market_name}\n" +
        f"⏰ تایم‌فریم: {selected_timeframe}\n" +
        f"🎯 استراتژی: 🤖 استراتژی شخصی هوش مصنوعی نارموون\n\n" +
        f"📸 مرحله نهایی: لطفاً ۳ اسکرین‌شات از نمودار در تایم‌فریم‌های زیر ارسال کنید:\n\n" +
        f"🔹 {tf_list}\n\n" +
        f"💡 برای لغو تحلیل، دستور /cancel را بفرست.",
        parse_mode='Markdown'
    )
    
    return WAITING_IMAGES

async def handle_strategy_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت انتخاب استراتژی (فقط نارموون موجود است)"""
    query = update.callback_query
    await query.answer()
    
    # چون فقط یک استراتژی داریم، مستقیم نارموون رو انتخاب می‌کنیم
    context.user_data['selected_strategy'] = 'narmoon_ai'
    
    # بارگیری پرامپت استراتژی از فایل استراتژی‌ها
    from resources.prompts.strategies import STRATEGY_PROMPTS
    context.user_data['strategy_prompt'] = STRATEGY_PROMPTS['narmoon_ai']
    
    # نمایش پیام برای ارسال تصاویر
    selected_market = context.user_data.get('selected_market', 'نامشخص')
    selected_timeframe = context.user_data.get('selected_timeframe', 'نامشخص')
    market_name = MARKETS.get(selected_market, 'نامشخص')
    expected_frames = context.user_data['expected_frames']
    tf_list = " - ".join(expected_frames)

    await query.edit_message_text(
        f"✅ انتخاب‌های شما:\n" +
        f"📊 بازار: {market_name}\n" +
        f"⏰ تایم‌فریم: {selected_timeframe}\n" +
        f"🎯 استراتژی: 🤖 استراتژی شخصی هوش مصنوعی نارموون\n\n" +
        f"📸 مرحله نهایی: لطفاً ۳ اسکرین‌شات از نمودار در تایم‌فریم‌های زیر ارسال کنید:\n\n" +
        f"🔹 {tf_list}\n\n" +
        f"💡 برای لغو تحلیل، دستور /cancel را بفرست.",
        parse_mode='Markdown'
    )

    return WAITING_IMAGES

async def receive_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت تصاویر چارت از کاربر"""
    # بررسی محدودیت TNT کاربر
    user_id = update.effective_user.id
    
    # Import توابع جدید TNT
    from database.operations import check_tnt_analysis_limit, record_tnt_analysis_usage
    
    # بررسی محدودیت
    limit_check = check_tnt_analysis_limit(user_id)
    
    if not limit_check["allowed"]:
        # تعیین نوع پیام خطا
        reason = limit_check.get("reason", "unknown")
        message = limit_check.get("message", "خطا در بررسی محدودیت")
        
        if reason == "plan_required":
            # نیاز به اشتراک
            subscription_buttons = [
                [InlineKeyboardButton("💳 خرید اشتراک TNT", callback_data="subscription")],
                [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
            ]
            
            await update.message.reply_text(
                "⚠️ دسترسی محدود\n\n"
                "برای استفاده از تحلیل هوش مصنوعی TNT نیاز به اشتراک دارید.\n\n"
                "🔸 پلن‌های موجود:\n"
                "• TNT MINI: $10/ماه (60 تحلیل)\n"
                "• TNT PLUS+: $18/ماه (150 تحلیل)\n"
                "• TNT MAX: $39/ماه (400 تحلیل + گروه VIP)",
                reply_markup=InlineKeyboardMarkup(subscription_buttons),
                parse_mode='Markdown'
            )
            return MAIN_MENU
            
        elif reason == "plan_expired":
            # اشتراک منقضی
            subscription_buttons = [
                [InlineKeyboardButton("🔄 تمدید اشتراک", callback_data="subscription")],
                [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
            ]
            
            await update.message.reply_text(
                "⏰ اشتراک منقضی شده\n\n"
                f"{message}\n\n"
                "برای ادامه استفاده از تحلیل TNT، اشتراک خود را تمدید کنید.",
                reply_markup=InlineKeyboardMarkup(subscription_buttons),
                parse_mode='Markdown'
            )
            return MAIN_MENU
            
        elif reason == "monthly_limit":
            # سقف ماهانه
            usage = limit_check.get("usage", 0)
            limit = limit_check.get("limit", 0)
            
            subscription_buttons = [
                [InlineKeyboardButton("⬆️ ارتقا پلن", callback_data="subscription")],
                [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
            ]
            
            await update.message.reply_text(
                "📊 سقف ماهانه به پایان رسید\n\n"
                f"استفاده شده: {usage}/{limit} تحلیل\n\n"
                "💡 برای تحلیل بیشتر می‌توانید:\n"
                "• پلن خود را ارتقا دهید\n"
                "• تا ماه آینده صبر کنید",
                reply_markup=InlineKeyboardMarkup(subscription_buttons),
                parse_mode='Markdown'
            )
            return MAIN_MENU
            
        elif reason == "hourly_limit":
            # سقف ساعتی
            usage = limit_check.get("usage", 0)
            limit = limit_check.get("limit", 0)
            
            back_button = [
                [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
            ]
            
            await update.message.reply_text(
                "⏱️ سقف ساعتی به پایان رسید\n\n"
                f"استفاده شده: {usage}/{limit} تحلیل در این ساعت\n\n"
                "⏰ لطفاً یک ساعت دیگر دوباره تلاش کنید.\n\n"
                "💡 برای حد ساعتی بیشتر، پلن خود را ارتقا دهید.",
                reply_markup=InlineKeyboardMarkup(back_button),
                parse_mode='Markdown'
            )
            return MAIN_MENU
        
        else:
            # خطای عمومی
            back_button = [
                [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
            ]
            
            await update.message.reply_text(
                f"❌ {message}",
                reply_markup=InlineKeyboardMarkup(back_button)
            )
            return MAIN_MENU
    
    # اگر همه چیز OK بود، ادامه پردازش تصویر
    file = None
    ext = "jpeg"
    
    # پشتیبانی از عکس یا داکیومنت عکس
    if update.message.photo:
        file = await update.message.photo[-1].get_file()
    elif update.message.document and update.message.document.mime_type.startswith('image/'):
        file = await update.message.document.get_file()
        ext = update.message.document.mime_type.split('/')[-1]
    else:
        await update.message.reply_text("فقط عکس ارسال کن رفیق! 😅")
        return WAITING_IMAGES
    
    photo_bytes = await file.download_as_bytearray()
    context.user_data['received_images'].append((photo_bytes, ext))
    
    received = len(context.user_data['received_images'])
    expected = 3
    
    if received < expected:
        # نمایش پیشرفت به همراه آمار باقی‌مانده
        remaining_monthly = limit_check.get("remaining_monthly", "نامشخص")
        remaining_hourly = limit_check.get("remaining_hourly", "نامشخص")
        
        progress_message = f"عالی! {expected-received} عکس دیگه از تایم‌فریم‌های بعدی رو بفرست 🤩\n\n"
        progress_message += f"📊 باقی‌مانده ماهانه: {remaining_monthly} تحلیل\n"
        progress_message += f"⏰ باقی‌مانده ساعتی: {remaining_hourly} تحلیل"
        
        await update.message.reply_text(progress_message)
        return WAITING_IMAGES
    
    # وقتی هر سه عکس رسید...
    await update.message.reply_text("🔥 در حال تحلیل نمودارها با استراتژی انتخابی شما... ⏳")
    
    try:
        # ثبت استفاده قبل از تحلیل
        record_success = record_tnt_analysis_usage(user_id)
        if not record_success:
            print(f"⚠️ Warning: Failed to record usage for user {user_id}")
        
        # استفاده از پرامپت اختصاصی استراتژی انتخابی
        strategy_prompt = context.user_data.get('strategy_prompt')
        result = analyze_chart_images(context.user_data['received_images'], strategy_prompt)
        
        # دکمه بازگشت به منوی اصلی
        menu_button = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]])
        
        # نمایش خلاصه انتخاب‌ها و نتیجه
        selected_market = context.user_data.get('selected_market', 'نامشخص')
        selected_timeframe = context.user_data.get('selected_timeframe', 'نامشخص')
        selected_strategy = context.user_data.get('selected_strategy', 'نامشخص')
        market_name = MARKETS.get(selected_market, 'نامشخص')
        strategy_name = STRATEGIES.get(selected_strategy, 'نامشخص')
        
        summary = f"📊 تحلیل شخصی‌سازی شده نارموون\n\n"
        summary += f"🎯 بازار: {market_name}\n"
        summary += f"⏰ تایم‌فریم: {selected_timeframe}\n"
        summary += f"🔧 استراتژی: {strategy_name}\n"
        
        # اضافه کردن آمار استفاده
        updated_limit_check = check_tnt_analysis_limit(user_id)
        if updated_limit_check["allowed"]:
            summary += f"📈 باقی‌مانده ماهانه: {updated_limit_check.get('remaining_monthly', 'نامشخص')} تحلیل\n"
            summary += f"⏱️ باقی‌مانده ساعتی: {updated_limit_check.get('remaining_hourly', 'نامشخص')} تحلیل\n"
        
        summary += f"{'═' * 30}\n\n"
        
        # استفاده از تابع تقسیم پیام
        full_message = summary + result
        await send_long_message(update, context, full_message)

        # ارسال دکمه منو در پیام جداگانه
        await update.message.reply_text(
            "✅ تحلیل کامل شد!",
            reply_markup=menu_button
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در تحلیل! دوباره تلاش کن یا /start رو بزن.\n{str(e)}")
    
    context.user_data.clear()
    return MAIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو عملیات جاری و بازگشت به منوی اصلی"""
    context.user_data.clear()
    
    # دکمه بازگشت به منوی اصلی
    menu_button = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]])
    
    await update.message.reply_text(
        "عملیات لغو شد. می‌توانید به منوی اصلی بازگردید.",
        reply_markup=menu_button
    )
    
    return MAIN_MENU

# سایر هندلرها (منوها و بخش‌ها)
async def show_narmoon_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش محصولات نارموون"""
    products_text = STATIC_TEXTS["narmoon_products"]
    
    products_buttons = [
        [
            InlineKeyboardButton("🔄 نارموون دکس (رایگان)", url=NARMOON_DEX_LINK),
            InlineKeyboardButton("💰 نارموون کوین (رایگان)", url=NARMOON_COIN_LINK)
        ],
        [InlineKeyboardButton("🤖 نارموون TNT (ویژه Pro)", callback_data="subscription")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    
    products_markup = InlineKeyboardMarkup(products_buttons)
    
    await update.callback_query.edit_message_text(
        products_text,
        reply_markup=products_markup,
        parse_mode='Markdown'
    )
    
    return MAIN_MENU

async def show_ai_features(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش قابلیت‌های دستیار هوش مصنوعی"""
    features_text = STATIC_TEXTS["ai_assistant_features"]
    
    features_buttons = [
        [InlineKeyboardButton("💳 خرید اشتراک", callback_data="subscription")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    
    features_markup = InlineKeyboardMarkup(features_buttons)
    
    await update.callback_query.edit_message_text(
        features_text,
        reply_markup=features_markup,
        parse_mode='Markdown'
    )
    
    return MAIN_MENU

async def show_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش صفحه اول سوالات متداول"""
    faq_text_page1 = """❓ **سوالات متداول نارموون** ❓

**۱. نارموون چیست و چه کاربردی دارد؟**
نارموون یک دستیار هوش مصنوعی مبتنی بر GPT-4o است که تحلیل تخصصی بازارهای مالی (رمزارز، فارکس، سهام و طلا) و ارائه سیگنال‌های معاملاتی هوشمند را انجام می‌دهد.

**۲. آیا می‌توانم مستقیماً از طریق نارموون معامله کنم؟**
خیر، نارموون صرفاً ابزار تحلیل و سیگنال‌دهی است و هیچ عملیات خرید، فروش یا مدیریت دارایی را انجام نمی‌دهد. امنیت شما اولویت ماست.

**۳. امنیت اطلاعات من چگونه تضمین می‌شود؟**
نارموون هیچ‌گاه اطلاعات شخصی، کلید خصوصی یا دسترسی به صرافی‌ها را دریافت نمی‌کند. تنها تصاویر چارت ارسالی شما برای تحلیل استفاده می‌شود.

**۴. تفاوت نارموون دکس و نارموون کوین چیست؟**
- **نارموون دکس:** تحلیل توکن‌های DEX سولانا، میم‌کوین‌ها و شناسایی فرصت‌های جدید
- **نارموون کوین:** تحلیل کوین‌های اصلی، داده‌های بازار جهانی و آمار DeFi

**۵. آیا سیگنال‌ها و تحلیل‌های نارموون تضمینی هستند؟**
خیر. تمام تحلیل‌ها صرفاً جنبه آموزشی دارند و هیچ تضمینی برای سود وجود ندارد. مدیریت ریسک همیشه ضروری است."""
    
    faq_buttons_page1 = [
        [InlineKeyboardButton("📖 ادامه سوالات", callback_data="faq_page2")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    faq_markup_page1 = InlineKeyboardMarkup(faq_buttons_page1)
    
    await update.callback_query.edit_message_text(
        faq_text_page1,
        reply_markup=faq_markup_page1,
        parse_mode='Markdown'
    )
    
    return MAIN_MENU

async def show_faq_page2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش صفحه دوم سوالات متداول"""
    faq_text_page2 = """❓ **سوالات متداول (ادامه)** ❓

**۶. پلن‌های اشتراک TNT چه تفاوت‌هایی دارند؟**
- **TNT MINI ($10/ماه):** ۶۰ تحلیل ماهانه، ۲ تحلیل ساعتی
- **TNT PLUS+ ($18/ماه):** ۱۵۰ تحلیل ماهانه، ۴ تحلیل ساعتی
- **TNT MAX ($39/ماه):** ۴۰۰ تحلیل ماهانه، ۸ تحلیل ساعتی + دسترسی VIP

**۷. چگونه از کلاهبرداری توکن‌ها محافظت کنم؟**
نارموون پارامترهای امنیتی مانند Mint/Freeze Authority، سن توکن، حجم معاملات، حرکت نهنگ‌ها و GT Score را بررسی می‌کند. همیشه تحقیق شخصی (DYOR) انجام دهید.

**۸. نحوه پرداخت و فعال‌سازی اشتراک چگونه است؟**
پرداخت با USDT روی شبکه سولانا. پس از واریز، TXID را به @Narmoon_support ارسال کنید. فعال‌سازی حداکثر ۳۰ دقیقه زمان می‌برد.

💡 **سوال دیگری دارید؟** با پشتیبانی @Narmoon_support در تماس باشید."""
    
    faq_buttons_page2 = [
        [InlineKeyboardButton("🔙 بازگشت به صفحه قبل", callback_data="faq")],
        [InlineKeyboardButton("💬 تماس با پشتیبانی", callback_data="support")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]
    ]
    faq_markup_page2 = InlineKeyboardMarkup(faq_buttons_page2)
    
    await update.callback_query.edit_message_text(
        faq_text_page2,
        reply_markup=faq_markup_page2,
        parse_mode='Markdown'
    )
    
    return MAIN_MENU

async def usage_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش راهنمای استفاده از ربات"""
    guide_text = f"""
📚 راهنمای استفاده از ربات تحلیل چارت

برای آشنایی کامل با نحوه استفاده از ربات، لطفاً ویدیوی آموزشی زیر را مشاهده کنید:

🎬 [مشاهده ویدیوی آموزشی]({TUTORIAL_VIDEO_LINK})

"""
    
    guide_buttons = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]]
    guide_markup = InlineKeyboardMarkup(guide_buttons)
    
    await update.callback_query.edit_message_text(
        guide_text,
        reply_markup=guide_markup,
        parse_mode='Markdown',
        disable_web_page_preview=False
    )
    
    return MAIN_MENU

async def terms_and_conditions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش صفحه اول قوانین و مقررات"""
    terms_text_page1 = """📜 قوانین و مقررات استفاده از دستیار معاملاتی هوش مصنوعی نارموون

شما کاربر گرامی، پیش از استفاده از خدمات هوش مصنوعی نارموون، ملزم به مطالعه دقیق و پذیرش کامل شرایط زیر هستید:

**بخش ۱: ماهیت خدمات و تعریف سرویس**
- نارموون TNT یک سیستم تحلیل هوشمند و ابزار کمک تصمیم‌گیری است، نه مشاور مالی، صرافی یا کارگزار
- تحلیل‌ها بر پایه الگوریتم‌های هوش مصنوعی، داده‌های تاریخی و الگوهای تکنیکال ارائه می‌شود
- این سیستم هیچ‌گونه خدمات خرید، فروش یا مدیریت مستقیم سرمایه ارائه نمی‌دهد

**بخش ۲: سلب مسئولیت کامل (بحرانی)**
- تمامی تحلیل‌ها و سیگنال‌ها صرفاً جنبه آموزشی و اطلاع‌رسانی دارند
- هیچ تضمینی برای دقت پیش‌بینی‌ها، کسب سود یا جلوگیری از ضرر وجود ندارد
- تمامی تصمیمات سرمایه‌گذاری، ریسک‌ها و نتایج مالی مسئولیت شخصی کاربر است
- نارموون هیچ مسئولیتی در قبال ضررهای مالی، از دست رفتن سرمایه یا آسیب اقتصادی ندارد

**بخش ۳: حریم خصوصی و امنیت اطلاعات**
- نارموون به هیچ‌وجه اطلاعات ورود، کلیدهای خصوصی یا دسترسی به حساب‌های صرافی درخواست نمی‌کند
- تنها داده‌های ارسالی کاربر (تصاویر چارت، متن) برای ارائه تحلیل استفاده و محفوظ نگهداری می‌شود
- هیچ اتصال مستقیمی به صرافی‌ها، کیف پول‌ها یا حساب‌های مالی وجود ندارد"""
    
    terms_buttons_page1 = [
        [InlineKeyboardButton("📖 ادامه مطالعه", callback_data="terms_page2")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    terms_markup_page1 = InlineKeyboardMarkup(terms_buttons_page1)
    
    await update.callback_query.edit_message_text(
        terms_text_page1,
        reply_markup=terms_markup_page1
    )
    
    return MAIN_MENU

async def terms_and_conditions_page2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش صفحه دوم قوانین و مقررات"""
    terms_text_page2 = """📜 قوانین و مقررات (ادامه - صفحه ۲)

**بخش ۴: مسئولیت‌های قانونی کاربر**
- کاربر تأیید می‌کند در کشور محل سکونت حق معامله در بازارهای مالی را دارد
- رعایت قوانین محلی، مقررات مالیاتی و ضوابط ارزی بر عهده کاربر است
- استفاده از سرویس برای فعالیت‌های غیرقانونی یا پولشویی ممنوع و پیگرد قانونی دارد

**بخش ۵: شرایط مالی و اشتراک**
- مبالغ پرداختی بابت اشتراک غیرقابل بازگشت است مگر در شرایط خاص با تأیید پشتیبانی
- کاربر موظف است پیش از خرید، راهنمای پرداخت و محدودیت‌های پلن را مطالعه کند
- نارموون این حق را دارد که قیمت‌ها، پلن‌ها و محدودیت‌های خدمات را با اطلاع‌رسانی قبلی تغییر دهد

**بخش ۶: مالکیت معنوی و محدودیت‌های استفاده**
- تمامی محتوا، تحلیل‌ها، الگوریتم‌ها و سیگنال‌ها متعلق به نارموون است
- کپی‌برداری، انتشار مجدد، فروش یا استفاده تجاری بدون مجوز کتبی ممنوع است

**بخش ۷: تغییرات سرویس و قطع خدمات**
- نارموون حق تغییر، تعلیق یا قطع خدمات را بدون اطلاع قبلی محفوظ می‌دارد
- هیچ تعهدی برای ارائه دائمی، پیوسته یا بدون اختلال خدمات وجود ندارد
- در صورت تغییر قوانین، ادامه استفاده به منزله پذیرش شرایط جدید است"""
    
    terms_buttons_page2 = [
        [InlineKeyboardButton("📖 ادامه مطالعه", callback_data="terms_page3")],
        [InlineKeyboardButton("🔙 بازگشت به صفحه قبل", callback_data="terms")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]
    ]
    terms_markup_page2 = InlineKeyboardMarkup(terms_buttons_page2)
    
    await update.callback_query.edit_message_text(
        terms_text_page2,
        reply_markup=terms_markup_page2
    )
    
    return MAIN_MENU

async def terms_and_conditions_page3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش صفحه سوم قوانین و مقررات"""
    terms_text_page3 = """📜 قوانین و مقررات (پایان - صفحه ۳)

**بخش ۸: محدودیت مسئولیت و خسارات**

تحت هیچ شرایطی، نارموون مسئول جبران خسارات مستقیم، غیرمستقیم، تبعی یا اتفاقی ناشی از استفاده یا عدم امکان استفاده از سرویس نخواهد بود.

حداکثر میزان مسئولیت نارموون در هر شرایط، معادل مجموع مبالغ پرداختی کاربر طی سه ماه گذشته خواهد بود.

کاربر با استفاده از سرویس، حق هرگونه طرح دعوای قضایی علیه نارموون را از خود سلب می‌نماید.

⚠️ **تأیید نهایی و الزام‌آور:**

**با ادامه استفاده از ربات نارموون، شما:**
✅ پذیرش کامل تمامی بندهای فوق را تأیید می‌کنید
✅ مسئولیت کامل تصمیمات مالی خود را می‌پذیرید
✅ از نارموون در قبال هرگونه ضرر مالی سلب مسئولیت می‌کنید
✅ متعهد به رعایت قوانین و عدم سوءاستفاده هستید

**پشتیبانی نارموون:** @Narmoon_support"""
    
    terms_buttons_page3 = [
        [InlineKeyboardButton("🔙 بازگشت به صفحه قبل", callback_data="terms_page2")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]
    ]
    terms_markup_page3 = InlineKeyboardMarkup(terms_buttons_page3)
    
    await update.callback_query.edit_message_text(
        terms_text_page3,
        reply_markup=terms_markup_page3
    )
    
    return MAIN_MENU

async def subscription_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش پلن‌های TNT جدید - بهبود یافته"""
    subscription_text = """💳 **پلن‌های اشتراک TNT نارموون**

🤖 سیستم تحلیل پیشرفته با هوش مصنوعی TNT

━━━━━━━━━━━━━━━

🔸 **TNT MINI** — $10/ماه
   • ۶۰ تحلیل در ماه
   • ۲ تحلیل در ساعت
   • دسترسی کامل به استراتژی هوش مصنوعی TNT

━━━━━━━━━━━━━━━

🔸 **TNT PLUS+** — $18/ماه
   • ۱۵۰ تحلیل در ماه
   • ۴ تحلیل در ساعت
   • دسترسی کامل به استراتژی هوش مصنوعی TNT

━━━━━━━━━━━━━━━

🔸 **TNT MAX** — $39/ماه
   • ۴۰۰ تحلیل در ماه
   • ۸ تحلیل در ساعت
   • دسترسی کامل به استراتژی هوش مصنوعی TNT
   • دسترسی VIP به کانال ویژه
   • دسترسی به پشتیبانی و اولویت آپدیت های آینده ی ربات نارموون

━━━━━━━━━━━━━━━

🌟 شروع کن و سطح تحلیل و ترید خودت رو ارتقا بده!"""
    
    # دکمه‌های تک ردیفه
    subscription_buttons = [
        [InlineKeyboardButton("🔸 TNT MINI ($10)", callback_data="tnt_mini")],
        [InlineKeyboardButton("🔸 TNT PLUS+ ($18)", callback_data="tnt_plus")],
        [InlineKeyboardButton("🔸 TNT MAX ($39)", callback_data="tnt_max")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    
    subscription_markup = InlineKeyboardMarkup(subscription_buttons)
    
    # اگر callback_query داریم
    if update.callback_query:
        await update.callback_query.edit_message_text(
            subscription_text,
            reply_markup=subscription_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            subscription_text,
            reply_markup=subscription_markup,
            parse_mode='Markdown'
        )
    
    return MAIN_MENU

async def show_payment_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش اطلاعات پرداخت و کیف پول"""
    try:
        # انتخاب تصادفی یک آدرس کیف پول
        wallet_address = random.choice(SOLANA_WALLETS)
        
        # ذخیره آدرس انتخاب شده در دیتای کاربر
        context.user_data['selected_wallet'] = wallet_address
        
        plan = context.user_data['selected_plan']
        amount = context.user_data['plan_amount']
        
        payment_text = f"""
💎 اطلاعات پرداخت اشتراک {plan}
مبلغ: {amount} دلار
آدرس کیف پول سولانا:

<code>{wallet_address}</code>

لطفا پس از پرداخت، با پشتیبان تماس بگیرید و شناسه تراکنش (TXID) را برای فعال‌سازی اشتراک ارسال کنید.
@Narmoon_support
"""
        
        payment_buttons = [[InlineKeyboardButton("🔙 بازگشت", callback_data="subscription")]]
        payment_markup = InlineKeyboardMarkup(payment_buttons)
        
        await update.callback_query.edit_message_text(
            payment_text,
            reply_markup=payment_markup,
            parse_mode='HTML'
        )
    except Exception as e:
        print(f"Error in show_payment_info: {str(e)}")
        try:
            # روش جایگزین در صورت بروز خطا
            await update.callback_query.message.reply_text(
                payment_text,
                reply_markup=payment_markup,
                parse_mode='HTML'
            )
        except Exception as e2:
            print(f"Second attempt also failed: {str(e2)}")
    
    return MAIN_MENU

async def support_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش اطلاعات تماس با پشتیبان"""
    support_text = """
👨‍💻 پشتیبانی ربات تحلیل چارت
برای ارتباط با پشتیبان و ارسال TXID پرداخت، لطفاً با آیدی زیر در تلگرام تماس بگیرید:

@Narmoon_support

می‌توانید روی لینک زیر کلیک کنید:
https://t.me/Narmoon_support

📝 راهنمای ارسال TXID به پشتیبان:
1. پس از پرداخت، شناسه تراکنش (TXID) را کپی کنید
2. به پشتیبان پیام بدهید و TXID را ارسال کنید
3. آیدی تلگرام خود را هم ذکر کنید
4. پس از تأیید تراکنش، اشتراک شما فعال خواهد شد
"""
    
    # دکمه بازگشت به منوی اصلی
    back_button = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]]
    back_markup = InlineKeyboardMarkup(back_button)
    
    await update.callback_query.edit_message_text(
        support_text,
        reply_markup=back_markup,
        parse_mode='Markdown',
        disable_web_page_preview=True
    )
    
    return MAIN_MENU

# Fix: اضافه کردن handler برای back_to_timeframes
async def handle_back_to_timeframes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بازگشت به انتخاب تایم‌فریم"""
    return await show_timeframes(update, context)

async def show_referral_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش پنل رفرال کاربر"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Import referral functions
    from database.operations import get_referral_stats
    
    try:
        # دریافت آمار رفرال کاربر
        stats = get_referral_stats(user_id)
        
        if not stats.get('success'):
            await query.edit_message_text(
                "❌ خطا در دریافت اطلاعات رفرال.\n"
                "لطفاً دوباره تلاش کنید.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")
                ]])
            )
            return MAIN_MENU
        
        # ساخت پیام پنل رفرال
        referral_code = stats['referral_code']
        referral_link = f"https://t.me/NarmoonAI_BOT?start={referral_code}"
        
        message = f"""💰 پنل رفرال شما

🔗 لینک دعوت:
{referral_link}

📊 آمار خریداران:
✅ خریداران موفق: {stats['successful_referrals']} نفر

💵 وضعیت مالی:
💰 کل درآمد: ${stats['total_earned']:.2f}
💳 قابل برداشت: ${stats['pending_amount']:.2f}
🏦 پرداخت شده: ${stats['total_paid']:.2f}

"""
        
        # اضافه کردن لیست خریداران
        if stats['buyers']:
            message += "👥 جزئیات خریداران:\n"
            for i, buyer in enumerate(stats['buyers'][:5], 1):  # فقط 5 تای اول
                plan_emoji = "📅" if buyer['plan_type'] == "ماهانه" else "📆"
                status_emoji = "💰" if buyer['status'] == 'pending' else "✅"
                message += f"{i}. {status_emoji} {buyer['username']}\n"
                message += f"   {plan_emoji} {buyer['plan_type']} - ${buyer['amount']:.2f}\n"
            
            if len(stats['buyers']) > 5:
                message += f"... و {len(stats['buyers']) - 5} نفر دیگر\n"
        
        message += f"""
📞 برای دریافت پول:
حداقل مبلغ برداشت: $20
پیام خصوصی به @Narmoon_support
+ شماره کیف پول خود را ارسال کنید

🔄 آپدیت: همین الان"""
        
        # دکمه‌های پنل
        keyboard = [
            [InlineKeyboardButton("📋 کپی لینک", callback_data=f"copy_link_{referral_code}")],
            [InlineKeyboardButton("📊 جزئیات کامل", callback_data="referral_details")],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
            # حذف parse_mode='Markdown' برای جلوگیری از خطا
        )
        
        return MAIN_MENU
        
    except Exception as e:
        print(f"Error in show_referral_panel: {e}")
        await query.edit_message_text(
            "❌ خطا در نمایش پنل رفرال.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")
            ]])
        )
        return MAIN_MENU

async def handle_referral_copy_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کپی لینک رفرال"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    referral_code = callback_data.replace("copy_link_", "")
    referral_link = f"https://t.me/NarmoonAI_BOT?start={referral_code}"
    
    await query.edit_message_text(
        f"🔗 لینک رفرال شما:\n\n"
        f"`{referral_link}`\n\n"
        f"💡 این لینک را کپی کرده و با دوستان خود به اشتراک بگذارید.\n"
        f"برای هر خرید موفق، کمیسیون دریافت خواهید کرد!",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="referral_panel")
        ]]),
        parse_mode='Markdown'
    )
    return MAIN_MENU

async def handle_referral_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش جزئیات کامل رفرال"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    from database.operations import get_referral_stats
    stats = get_referral_stats(user_id)
    
    if not stats.get('success'):
        await query.edit_message_text(
            "❌ خطا در دریافت جزئیات رفرال.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 بازگشت", callback_data="referral_panel")
            ]])
        )
        return MAIN_MENU
    
    message = f"""📊 جزئیات کامل رفرال

🔗 کد رفرال: `{stats['referral_code']}`

💰 آمار مالی:
- کل درآمد: ${stats['total_earned']:.2f}
- پرداخت شده: ${stats['total_paid']:.2f}
- در انتظار: ${stats['pending_amount']:.2f}

👥 آمار دعوت:
- کل دعوت‌های موفق: {stats['successful_referrals']} نفر

"""
    
    if stats['buyers']:
        message += "🛒 لیست خریداران:\n"
        for i, buyer in enumerate(stats['buyers'], 1):
            status_emoji = "✅" if buyer['status'] == 'paid' else "⏳"
            message += f"{i}. {status_emoji} {buyer['username']}\n"
            message += f"   📅 {buyer['plan_type']} - ${buyer['amount']:.2f}\n"
            message += f"   📆 {buyer['date'][:10]}\n\n"
    
    message += """💡 نکات مهم:
- حداقل مبلغ برداشت: $20
- برای برداشت با @Narmoon_support تماس بگیرید
- کمیسیون پس از تایید پرداخت محاسبه می‌شود"""
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="referral_panel")
        ]]),
        parse_mode='Markdown'
    )
    return MAIN_MENU

async def handle_tnt_plan_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش انتخاب پلن TNT"""
    query = update.callback_query
    await query.answer()
    
    plan_mapping = {
        "tnt_mini": ("TNT_MINI", "$10", "TNT MINI"),
        "tnt_plus": ("TNT_PLUS", "$18", "TNT PLUS+"), 
        "tnt_max": ("TNT_MAX", "$39", "TNT MAX")
    }
    
    if query.data in plan_mapping:
        plan_code, price, plan_name = plan_mapping[query.data]
        context.user_data['selected_tnt_plan'] = plan_code
        context.user_data['plan_amount'] = price
        context.user_data['plan_display'] = plan_name
        
        return await show_tnt_payment_info(update, context)
    
    return MAIN_MENU

async def show_tnt_payment_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش اطلاعات پرداخت TNT"""
    try:
        from config.settings import SOLANA_WALLETS
        import random
        
        # انتخاب تصادفی کیف پول
        wallet_address = random.choice(SOLANA_WALLETS)
        context.user_data['selected_wallet'] = wallet_address
        
        plan_display = context.user_data['plan_display']
        amount = context.user_data['plan_amount']
        
        payment_text = f"""💎 اطلاعات پرداخت {plan_display}

💰 مبلغ: {amount} دلار
🌐 شبکه: Solana

📍 آدرس کیف پول:
<code>{wallet_address}</code>

📞 مراحل بعد:
1️⃣ مبلغ را به آدرس بالا ارسال کنید
2️⃣ TXID تراکنش را کپی کنید
3️⃣ سپس رسید تراکنش را برای پشتیبانی به این آدرس تلگرامی ارسال کنید: @Narmoon_support

⚡ فعال‌سازی: حداکثر 30 دقیقه پس از تأیید

⚠️ **نکات مهم پرداخت اشتراک**
1. **فقط تتر (USDT) را روی شبکه سولانا (Solana) ارسال کنید.**
2. **در صورت ارسال تتر روی سایر شبکه‌ها یا ارسال هر رمزارز دیگری، مسئولیت پیگیری و ضرر احتمالی با شماست.**
3. **پس از واریز، رسید تراکنش را برای پشتیبانی ارسال نمایید.**
4. **پشتیبانی در سریع‌ترین زمان ممکن به درخواست شما رسیدگی خواهد کرد. لطفاً تا دریافت تأییدیه صبور باشید.**

🔗 **در صورت هرگونه سوال یا مشکل، با پشتیبانی در ارتباط باشید.**
"""
        
        payment_buttons = [[InlineKeyboardButton("🔙 بازگشت", callback_data="subscription")]]
        payment_markup = InlineKeyboardMarkup(payment_buttons)
        
        await update.callback_query.edit_message_text(
            payment_text,
            reply_markup=payment_markup,
            parse_mode='HTML'
        )
    except Exception as e:
        print(f"Error in show_tnt_payment_info: {str(e)}")
    
    return MAIN_MENU

async def debug_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
   """Debug handler برای تمام callback ها"""
   query = update.callback_query
   await query.answer()
   
   callback_data = query.data
   user_id = update.effective_user.id
   user_name = update.effective_user.username or "Anonymous"
   
   print(f"🔍 DEBUG: Received callback: '{callback_data}'")
   print(f"👤 DEBUG: User ID: {user_id}, Username: @{user_name}")
   print(f"⏰ DEBUG: Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
   
   try:
       if callback_data.startswith("copy_link_"):
           print("🎯 DEBUG: Copy link detected - calling handler")
           return await handle_referral_copy_link(update, context)
       elif callback_data == "referral_details":
           print("🎯 DEBUG: Details detected - calling handler") 
           return await handle_referral_details(update, context)
       elif callback_data == "referral_panel":
           print("🎯 DEBUG: Referral panel detected - calling handler")
           return await show_referral_panel(update, context)
       else:
           print(f"❌ DEBUG: Unhandled callback: {callback_data}")
           
           # ارسال پیام debug به کاربر
           await query.edit_message_text(
               f"🔍 Debug Info:\n"
               f"Callback: `{callback_data}`\n"
               f"Status: Unhandled\n\n"
               f"Please report this to support.",
               reply_markup=InlineKeyboardMarkup([[
                   InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")
               ]]),
               parse_mode='Markdown'
           )
           
   except Exception as e:
       error_msg = str(e)
       print(f"💥 DEBUG: Exception in callback handler: {error_msg}")
       print(f"📍 DEBUG: Callback data was: {callback_data}")
       
       try:
           await query.edit_message_text(
               f"❌ خطا در پردازش درخواست:\n"
               f"`{error_msg}`\n\n"
               f"Callback: `{callback_data}`",
               reply_markup=InlineKeyboardMarkup([[
                   InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")
               ]]),
               parse_mode='Markdown'
           )
       except Exception as send_error:
           print(f"💥 DEBUG: Failed to send error message: {send_error}")
   
   return MAIN_MENU
