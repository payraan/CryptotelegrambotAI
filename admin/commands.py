from telegram import Update
from telegram.ext import ContextTypes
from config.settings import ADMIN_ID
from database.operations import activate_subscription, get_user_info, get_user_api_stats, get_connection

async def admin_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فعال‌سازی اشتراک کاربر توسط ادمین (فرمت: /activate user_id duration plan_type)"""
    # بررسی دسترسی ادمین
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("شما دسترسی به این دستور را ندارید.")
        return

    try:
        # بررسی پارامترها
        args = context.args
        if len(args) < 3:
            await update.message.reply_text(
                "فرمت صحیح: /activate user_id duration plan_type\n"
                "مثال: /activate 123456789 3 سه_ماهه"
            )
            return

        user_id = int(args[0])
        duration = int(args[1])
        plan_type = args[2]

        # فعال‌سازی اشتراک
        end_date = activate_subscription(user_id, duration, plan_type)

        # ⭐ اضافه: محاسبه کمیسیون رفرال ⭐
        from database.operations import get_connection, calculate_commission
        
        # بررسی اینکه آیا این کاربر از طریق رفرال آمده
        try:
            conn = get_connection()
            cursor = conn.cursor()
            is_postgres = hasattr(conn, 'server_version')
            
            # پیدا کردن referrer برای این کاربر
            if is_postgres:
                cursor.execute("SELECT referrer_id FROM referrals WHERE referred_id = %s", (user_id,))
            else:
                cursor.execute("SELECT referrer_id FROM referrals WHERE referred_id = ?", (user_id,))
            
            referrer = cursor.fetchone()
            conn.close()
            
            if referrer:
                referrer_id = referrer[0]
                print(f"🔍 Found referrer {referrer_id} for user {user_id}")
                
                # حالا کمیسیون را محاسبه کن
                commission_result = calculate_commission(referrer_id, user_id, plan_type, None)
                
                if commission_result.get("success"):
                    commission_amount = commission_result.get("total_amount", 0)
                    successful_referrals = commission_result.get("successful_referrals", 0)
                    
                    # اطلاع به ادمین
                    await update.message.reply_text(
                        f"💰 کمیسیون رفرال محاسبه شد!\n"
                        f"👤 رفرردهنده: {referrer_id}\n"
                        f"💵 مبلغ کمیسیون: ${commission_amount:.2f}\n"
                        f"📊 تعداد رفرال‌های موفق: {successful_referrals}"
                    )
                    
                    print(f"✅ Commission calculated: Referrer {referrer_id} -> User {user_id}: ${commission_amount}")
                else:
                    error_msg = commission_result.get("error", "Unknown error")
                    print(f"❌ Commission calculation failed: {error_msg}")
                    await update.message.reply_text(f"⚠️ خطا در محاسبه کمیسیون: {error_msg}")
            else:
                print(f"ℹ️ No referral relationship found for user {user_id}")
                
        except Exception as commission_error:
            print(f"❌ Commission calculation error: {commission_error}")
            await update.message.reply_text(f"⚠️ خطا در بررسی رفرال: {str(commission_error)}")

        # ارسال پیام به ادمین
        await update.message.reply_text(
            f"✅ اشتراک کاربر {user_id} با موفقیت فعال شد.\n"
            f"📅 تاریخ پایان: {end_date}"
        )

        # ارسال پیام به کاربر
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🎉 اشتراک شما با موفقیت فعال شد!\n\n"
                     f"🔹 نوع اشتراک: {plan_type}\n"
                     f"📅 تاریخ پایان: {end_date}\n\n"
                     f"از خرید شما متشکریم! برای شروع دستور /start را بزنید."
            )
        except Exception as e:
            await update.message.reply_text(
                f"اشتراک فعال شد اما ارسال پیام به کاربر با خطا مواجه شد: {str(e)}"
            )

    except Exception as e:
        await update.message.reply_text(f"خطا در فعال‌سازی اشتراک: {str(e)}")

async def admin_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش اطلاعات کاربر برای ادمین"""
    # بررسی دسترسی ادمین
    if update.effective_user.id != ADMIN_ID:
        return
    
    try:
        # بررسی پارامترها
        args = context.args
        if not args:
            await update.message.reply_text(
                "فرمت صحیح: /userinfo user_id\n"
                "مثال: /userinfo 123456789"
            )
            return
        
        user_id = int(args[0])
        
        # دریافت اطلاعات کاربر
        user_info = get_user_info(user_id)
        
        if not user_info:
            await update.message.reply_text(f"کاربری با شناسه {user_id} یافت نشد.")
            return
        
        user_data = user_info["user_data"]
        transactions = user_info["transactions"]
        
        # دریافت آمار API
        api_stats = get_user_api_stats(user_id)
        
        # نمایش اطلاعات کاربر
        response = f"""
👤 اطلاعات کاربر:
شناسه: {user_data[0]}
نام کاربری: {user_data[1] or 'نامشخص'}
تاریخ پایان اشتراک: {user_data[2] or 'ندارد'}
نوع اشتراک: {user_data[3] or 'ندارد'}
وضعیت اشتراک: {'فعال' if user_data[4] else 'غیرفعال'}

📊 آمار API:
درخواست‌های امروز: {api_stats['today']}
کل درخواست‌ها: {api_stats['total']}
        """
        
        # اضافه کردن اطلاعات تراکنش‌ها
        if transactions:
            response += "\n💰 تراکنش‌های اخیر:\n"
            for tx in transactions:
                response += f"TXID: {tx[2]}\n"
                response += f"کیف پول: {tx[3]}\n"
                response += f"مبلغ: {tx[4]}\n"
                response += f"وضعیت: {tx[6]}\n"
                response += f"تاریخ: {tx[7]}\n\n"
        
        await update.message.reply_text(response)
    
    except Exception as e:
        await update.message.reply_text(f"خطا در دریافت اطلاعات کاربر: {str(e)}")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آمار کلی ربات - PostgreSQL Compatible"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    from datetime import datetime, timedelta
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # تعداد کل کاربران
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        # کاربران فعال (با اشتراک)
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = %s", (True,))
        active_users = cursor.fetchone()[0]
        
        # کاربران جدید امروز
        today = datetime.now().date()
        cursor.execute(
            "SELECT COUNT(*) FROM users WHERE DATE(created_at) = %s",
            (today,)
        )
        new_users_today = cursor.fetchone()[0]
        
        # درآمد ماه جاری
        first_day = today.replace(day=1)
        cursor.execute(
            "SELECT SUM(amount) FROM transactions WHERE status = 'completed' AND DATE(created_at) >= %s",
            (first_day,)
        )
        monthly_revenue = cursor.fetchone()[0] or 0
        
        conn.close()
        
        stats_text = f"""
📊 آمار کلی ربات:

👥 تعداد کل کاربران: {total_users}
✅ کاربران فعال: {active_users}
🆕 کاربران جدید امروز: {new_users_today}
💰 درآمد ماه جاری: ${monthly_revenue:.2f}

🤖 وضعیت ربات: فعال ✅
        """
        
        await update.message.reply_text(stats_text)
        
    except Exception as e:
        await update.message.reply_text(f"خطا در دریافت آمار: {str(e)}")

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال پیام به همه کاربران - PostgreSQL Compatible"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    try:
        # بررسی وجود پیام
        if not context.args:
            await update.message.reply_text(
                "لطفاً پیام خود را بعد از دستور بنویسید.\n"
                "مثال: /broadcast سلام به همه کاربران عزیز!"
            )
            return
        
        message = ' '.join(context.args)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # دریافت لیست کاربران
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        conn.close()
        
        success_count = 0
        fail_count = 0
        
        await update.message.reply_text(f"شروع ارسال پیام به {len(users)} کاربر...")
        
        # اضافه کردن delay برای جلوگیری از rate limiting
        import asyncio
        
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user[0],
                    text=f"📢 اطلاعیه:\n\n{message}"
                )
                success_count += 1
                # delay کوتاه برای جلوگیری از spam detection
                await asyncio.sleep(0.05)  # 20 پیام در ثانیه
            except Exception as e:
                fail_count += 1
                print(f"Failed to send message to {user[0]}: {e}")
        
        await update.message.reply_text(
            f"✅ ارسال پیام کامل شد!\n"
            f"موفق: {success_count}\n"
            f"ناموفق: {fail_count}"
        )
        
    except Exception as e:
        await update.message.reply_text(f"خطا در ارسال پیام: {str(e)}")

async def admin_activate_tnt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فعال‌سازی اشتراک TNT توسط ادمین"""
    # بررسی دسترسی ادمین
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("شما دسترسی به این دستور را ندارید.")
        return

    try:
        # بررسی پارامترها
        args = context.args
        if len(args) < 3:
            await update.message.reply_text(
                "فرمت صحیح: /activatetnt user_id plan_name duration\n\n"
                "پلن‌های موجود:\n"
                "• TNT_MINI: $6 (60 تحلیل/ماه، 2 تحلیل/ساعت)\n"
                "• TNT_PLUS: $10 (150 تحلیل/ماه، 4 تحلیل/ساعت)\n"
                "• TNT_MAX: $22 (400 تحلیل/ماه، 8 تحلیل/ساعت + VIP)\n\n"
                "مثال: /activatetnt 123456789 TNT_MINI 1"
            )
            return

        user_id = int(args[0])
        plan_name = args[1].upper()
        duration = int(args[2])

        # اطمینان از وجود کاربر
        from database.operations import register_user, activate_tnt_subscription
        register_user(user_id, f"admin_user_{user_id}")

        # فعال‌سازی اشتراک TNT
        result = activate_tnt_subscription(user_id, plan_name, duration)

        if result["success"]:
            # محاسبه کمیسیون رفرال (همان کد قبلی)
            from database.operations import get_connection, calculate_commission
            
            try:
                conn = get_connection()
                cursor = conn.cursor()
                is_postgres = hasattr(conn, 'server_version')
                
                # پیدا کردن referrer برای این کاربر
                if is_postgres:
                    cursor.execute("SELECT referrer_id FROM referrals WHERE referred_id = %s", (user_id,))
                else:
                    cursor.execute("SELECT referrer_id FROM referrals WHERE referred_id = ?", (user_id,))
                
                referrer = cursor.fetchone()
                conn.close()
                
                if referrer:
                    referrer_id = referrer[0]
                    print(f"🔍 Found referrer {referrer_id} for user {user_id}")
                    
                    # محاسبه کمیسیون
                    commission_result = calculate_commission(referrer_id, user_id, plan_name, None)
                    
                    if commission_result.get("success"):
                        commission_amount = commission_result.get("total_amount", 0)
                        successful_referrals = commission_result.get("successful_referrals", 0)
                        
                        # اطلاع به ادمین
                        await update.message.reply_text(
                            f"💰 کمیسیون رفرال محاسبه شد!\n"
                            f"👤 رفرردهنده: {referrer_id}\n"
                            f"💵 مبلغ کمیسیون: ${commission_amount:.2f}\n"
                            f"📊 تعداد رفرال‌های موفق: {successful_referrals}"
                        )
                        
                        print(f"✅ Commission calculated: Referrer {referrer_id} -> User {user_id}: ${commission_amount}")
                    else:
                        error_msg = commission_result.get("error", "Unknown error")
                        print(f"❌ Commission calculation failed: {error_msg}")
                        await update.message.reply_text(f"⚠️ خطا در محاسبه کمیسیون: {error_msg}")
                else:
                    print(f"ℹ️ No referral relationship found for user {user_id}")
                    
            except Exception as commission_error:
                print(f"❌ Commission calculation error: {commission_error}")
                await update.message.reply_text(f"⚠️ خطا در بررسی رفرال: {str(commission_error)}")

            # پیام موفقیت ادمین
            await update.message.reply_text(
                f"✅ اشتراک TNT کاربر {user_id} فعال شد\n\n"
                f"📋 جزئیات:\n"
                f"• پلن: {result['plan_display']}\n"
                f"• سقف ماهانه: {result['monthly_limit']} تحلیل\n"
                f"• سقف ساعتی: {result['hourly_limit']} تحلیل\n"
                f"• شروع: {result['start_date']}\n"
                f"• پایان: {result['end_date']}\n"
                f"• VIP Access: {'✅' if result['vip_access'] else '❌'}"
            )

            # ارسال پیام به کاربر
            try:
                vip_text = ""
                if result['vip_access']:
                    vip_text = "\n🎖️ **VIP Access:** دسترسی به گروه ویژه TNT MAX"

                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🎉 **اشتراک TNT شما فعال شد!**\n\n"
                         f"🔹 **پلن:** {result['plan_display']}\n"
                         f"📊 **سقف ماهانه:** {result['monthly_limit']} تحلیل\n"
                         f"⏰ **سقف ساعتی:** {result['hourly_limit']} تحلیل\n"
                         f"📅 **تاریخ پایان:** {result['end_date']}\n"
                         f"{vip_text}\n\n"
                         f"✨ حالا می‌توانید از تحلیل هوش مصنوعی TNT استفاده کنید!\n"
                         f"برای شروع دستور /start را بزنید.",
                )
            except Exception as e:
                await update.message.reply_text(
                    f"اشتراک فعال شد اما ارسال پیام به کاربر با خطا مواجه شد: {str(e)}"
                )
        else:
            await update.message.reply_text(f"❌ خطا در فعال‌سازی: {result['error']}")

    except ValueError:
        await update.message.reply_text("❌ فرمت user_id یا duration نامعتبر است.")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در فعال‌سازی اشتراک TNT: {str(e)}")

async def admin_tnt_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آمار TNT برای ادمین"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    from database.operations import get_connection
    from datetime import datetime, date
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        is_postgres = hasattr(conn, 'server_version')
        
        # آمار کلی پلن‌ها
        if is_postgres:
            cursor.execute("""
                SELECT tnt_plan_type, COUNT(*) as count
                FROM users 
                WHERE tnt_plan_type IS NOT NULL
                GROUP BY tnt_plan_type
                ORDER BY count DESC
            """)
        else:
            cursor.execute("""
                SELECT tnt_plan_type, COUNT(*) as count
                FROM users 
                WHERE tnt_plan_type IS NOT NULL
                GROUP BY tnt_plan_type
                ORDER BY count DESC
            """)
        
        plan_stats = cursor.fetchall()
        
        # آمار استفاده امروز
        today = date.today()
        if is_postgres:
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) as active_users,
                       SUM(analysis_count) as total_analyses
                FROM tnt_usage_tracking 
                WHERE usage_date = %s
            """, (today,))
        else:
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) as active_users,
                       SUM(analysis_count) as total_analyses
                FROM tnt_usage_tracking 
                WHERE usage_date = ?
            """, (today.isoformat(),))
        
        usage_today = cursor.fetchone()
        active_users_today = usage_today[0] or 0
        total_analyses_today = usage_today[1] or 0
        
        # آمار استفاده ماه جاری
        start_of_month = date(today.year, today.month, 1)
        if is_postgres:
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) as monthly_users,
                       SUM(analysis_count) as monthly_analyses
                FROM tnt_usage_tracking 
                WHERE usage_date >= %s
            """, (start_of_month,))
        else:
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) as monthly_users,
                       SUM(analysis_count) as monthly_analyses
                FROM tnt_usage_tracking 
                WHERE usage_date >= ?
            """, (start_of_month.isoformat(),))
        
        usage_monthly = cursor.fetchone()
        monthly_users = usage_monthly[0] or 0
        monthly_analyses = usage_monthly[1] or 0
        
        # پربازدیدترین کاربران
        if is_postgres:
            cursor.execute("""
                SELECT u.user_id, u.username, u.tnt_plan_type, 
                       SUM(t.analysis_count) as total_usage
                FROM users u
                JOIN tnt_usage_tracking t ON u.user_id = t.user_id
                WHERE t.usage_date >= %s
                GROUP BY u.user_id, u.username, u.tnt_plan_type
                ORDER BY total_usage DESC
                LIMIT 10
            """, (start_of_month,))
        else:
            cursor.execute("""
                SELECT u.user_id, u.username, u.tnt_plan_type, 
                       SUM(t.analysis_count) as total_usage
                FROM users u
                JOIN tnt_usage_tracking t ON u.user_id = t.user_id
                WHERE t.usage_date >= ?
                GROUP BY u.user_id, u.username, u.tnt_plan_type
                ORDER BY total_usage DESC
                LIMIT 10
            """, (start_of_month.isoformat(),))
        
        top_users = cursor.fetchall()
        
        conn.close()
        
        # ساخت پیام آمار
        stats_message = f"""📊 **آمار TNT سیستم**

📈 **آمار پلن‌ها:**
"""
        
        for plan_type, count in plan_stats:
            stats_message += f"• {plan_type}: {count} کاربر\n"
        
        stats_message += f"""
🔥 **فعالیت امروز:**
• کاربران فعال: {active_users_today}
• تحلیل‌های انجام شده: {total_analyses_today}

📅 **فعالیت ماه جاری:**
• کاربران فعال: {monthly_users}
• کل تحلیل‌ها: {monthly_analyses}

👑 **فعال‌ترین کاربران (ماه جاری):**
"""
        
        for i, (user_id, username, plan_type, usage) in enumerate(top_users[:5], 1):
            username_display = username or f"User_{user_id}"
            stats_message += f"{i}. {username_display} ({plan_type}): {usage} تحلیل\n"
        
        await update.message.reply_text(stats_message)
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در دریافت آمار TNT: {str(e)}")

async def admin_user_tnt_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش اطلاعات TNT کاربر خاص"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    try:
        args = context.args
        if not args:
            await update.message.reply_text(
                "فرمت صحیح: /usertnt user_id\n"
                "مثال: /usertnt 123456789"
            )
            return
        
        user_id = int(args[0])
        
        from database.operations import get_user_tnt_usage_stats
        
        # دریافت آمار کامل
        stats = get_user_tnt_usage_stats(user_id)
        
        if not stats:
            await update.message.reply_text(f"کاربر {user_id} یافت نشد یا خطا در دریافت اطلاعات.")
            return
        
        plan_info = stats["plan_info"]
        
        info_message = f"""👤 **اطلاعات TNT کاربر {user_id}**

📋 **پلن فعلی:**
• نوع: {plan_info['plan_type']}
• سقف ماهانه: {plan_info['monthly_limit']} تحلیل
• سقف ساعتی: {plan_info['hourly_limit']} تحلیل
• وضعیت: {'✅ فعال' if plan_info['plan_active'] else '❌ غیرفعال'}
• تاریخ پایان: {plan_info.get('plan_end', 'نامشخص')}

📊 **استفاده فعلی:**
• مصرف ماهانه: {stats['monthly_usage']}/{plan_info['monthly_limit']} ({stats['monthly_percentage']:.1f}%)
• مصرف ساعتی: {stats['hourly_usage']}/{plan_info['hourly_limit']} ({stats['hourly_percentage']:.1f}%)

⏰ **باقی‌مانده:**
• ماهانه: {stats['monthly_remaining']} تحلیل
• ساعتی: {stats['hourly_remaining']} تحلیل
"""
        
        await update.message.reply_text(info_message)
        
    except ValueError:
        await update.message.reply_text("❌ فرمت user_id نامعتبر است.")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در دریافت اطلاعات: {str(e)}")

async def admin_clean_database(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاک کردن کامل دیتابیس توسط ادمین"""
    # بررسی دسترسی ادمین
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("شما دسترسی به این دستور را ندارید.")
        return

    try:
        # بررسی تایید
        args = context.args
        if not args or args[0] != "CONFIRM":
            await update.message.reply_text(
                "⚠️ **هشدار: این دستور تمام داده‌های دیتابیس را پاک می‌کند!**\n\n"
                "برای تایید، دستور زیر را ارسال کنید:\n"
                "`/cleandb CONFIRM`\n\n"
                "**این عمل قابل بازگشت نیست!**",
            )
            return

        await update.message.reply_text("🧹 شروع پاک‌سازی دیتابیس...")

        from database.operations import get_connection
        
        conn = get_connection()
        cursor = conn.cursor()
        is_postgres = hasattr(conn, 'server_version')
        
        # شمارش کاربران قبل از پاک کردن
        cursor.execute("SELECT COUNT(*) FROM users")
        users_before = cursor.fetchone()[0]
        
        # پاک کردن جداول به ترتیب صحیح (به دلیل foreign keys)
        tables_to_clean = [
            "tnt_usage_tracking",
            "api_requests", 
            "transactions",
            "commissions",
            "referrals",
            "users"
        ]
        
        cleaned_tables = []
        for table in tables_to_clean:
            try:
                cursor.execute(f"DELETE FROM {table}")
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                remaining = cursor.fetchone()[0]
                cleaned_tables.append(f"✅ {table}: پاک شد (باقی‌مانده: {remaining})")
            except Exception as e:
                cleaned_tables.append(f"⚠️ {table}: {str(e)[:50]}")
        
        # Reset auto increment sequences (PostgreSQL)
        if is_postgres:
            try:
                reset_sequences = [
                    "ALTER SEQUENCE users_user_id_seq RESTART WITH 1",
                    "ALTER SEQUENCE transactions_id_seq RESTART WITH 1", 
                    "ALTER SEQUENCE api_requests_id_seq RESTART WITH 1",
                    "ALTER SEQUENCE tnt_usage_tracking_id_seq RESTART WITH 1",
                    "ALTER SEQUENCE referrals_id_seq RESTART WITH 1",
                    "ALTER SEQUENCE commissions_id_seq RESTART WITH 1"
                ]
                
                for seq_sql in reset_sequences:
                    try:
                        cursor.execute(seq_sql)
                        print(f"✅ Reset sequence: {seq_sql}")
                    except Exception as e:
                        print(f"⚠️ Sequence reset: {str(e)[:50]}")
            except Exception as e:
                print(f"⚠️ Sequence reset error: {e}")
        
        # Reset SQLite sequences
        else:
            try:
                cursor.execute("DELETE FROM sqlite_sequence")
                cleaned_tables.append("✅ sqlite_sequence: Reset auto-increment")
            except Exception as e:
                cleaned_tables.append(f"⚠️ sqlite_sequence: {str(e)[:50]}")
        
        conn.commit()
        
        # بررسی نهایی
        cursor.execute("SELECT COUNT(*) FROM users")
        users_after = cursor.fetchone()[0]
        
        conn.close()
        
        # گزارش نتایج
        result_message = f"🧹 **پاک‌سازی دیتابیس کامل شد**\n\n"
        result_message += f"📊 **آمار:**\n"
        result_message += f"• کاربران قبل: {users_before}\n"
        result_message += f"• کاربران بعد: {users_after}\n\n"
        result_message += f"📋 **جزئیات:**\n"
        
        for table_result in cleaned_tables:
            result_message += f"{table_result}\n"
        
        result_message += f"\n✨ **دیتابیس آماده تست‌های جدید است!**"
        
        await update.message.reply_text(result_message)
        
        # اطلاع‌رسانی عمومی
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🔄 دیتابیس بازنشانی شد. همه کاربران حالا می‌توانند با حساب تمیز شروع کنند."
            )
        except:
            pass
            
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در پاک‌سازی دیتابیس: {str(e)}")

async def admin_db_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آمار کلی دیتابیس"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    try:
        from database.operations import get_connection
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # آمار جداول مختلف
        tables_stats = {}
        tables = ["users", "transactions", "api_requests", "tnt_usage_tracking", "referrals", "commissions", "tnt_plans"]
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                tables_stats[table] = count
            except Exception as e:
                tables_stats[table] = f"Error: {str(e)[:30]}"
        
        conn.close()
        
        # ساخت پیام آمار
        stats_message = "📊 **آمار کامل دیتابیس**\n\n"
        
        for table, count in tables_stats.items():
            if isinstance(count, int):
                stats_message += f"• **{table}:** {count:,} رکورد\n"
            else:
                stats_message += f"• **{table}:** {count}\n"
        
        await update.message.reply_text(stats_message)
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در دریافت آمار: {str(e)}")

async def admin_reset_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ریست ساده دیتابیس"""
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        from database.operations import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        # شمارش قبل
        cursor.execute("SELECT COUNT(*) FROM users")
        before = cursor.fetchone()[0]
        
        # پاک کردن
        cursor.execute("DELETE FROM tnt_usage_tracking")
        cursor.execute("DELETE FROM api_requests")
        cursor.execute("DELETE FROM transactions")
        cursor.execute("DELETE FROM commissions") 
        cursor.execute("DELETE FROM referrals")
        cursor.execute("DELETE FROM users")
        
        conn.commit()
        conn.close()
        
        await update.message.reply_text(f"Database reset: {before} -> 0 users")
        
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")
