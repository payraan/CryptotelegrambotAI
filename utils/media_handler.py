# utils/media_handler.py
import os
from telegram import Update, InlineKeyboardMarkup, InputMediaPhoto, InputMediaAnimation
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

class MediaHandler:
    def __init__(self):
        self.media_path = "resources/media/"
        self.gifs_path = os.path.join(self.media_path, "gifs/")
        self.images_path = os.path.join(self.media_path, "images/")
        self.ensure_media_directories()
        
        # تعریف نام فایل‌های گیف برای هر بخش
        self.gif_files = {
            'welcome': 'welcome.gif',
            'crypto_menu': 'crypto_menu.gif',
            'dex_menu': 'dex_menu.gif',
            'coin_menu': 'coin_menu.gif',
            'tnt_analysis': 'tnt_analysis.gif',
            'subscription': 'subscription.gif',
            'referral': 'referral.gif',
            'guide': 'guide.gif',
            'faq': 'faq.gif',
            'support': 'support.gif'
        }

    def ensure_media_directories(self):
        """اطمینان از وجود پوشه‌های رسانه"""
        directories = [self.media_path, self.gifs_path, self.images_path]
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"📁 Created directory: {directory}")

    def file_exists(self, file_path):
        """بررسی وجود فایل"""
        return os.path.exists(file_path) and os.path.getsize(file_path) > 0

    def get_gif_path(self, gif_name):
        """دریافت مسیر کامل گیف"""
        if gif_name in self.gif_files:
            return os.path.join(self.gifs_path, self.gif_files[gif_name])
        return None

    async def send_gif_with_text(self, update, context, gif_name, text, reply_markup=None, edit_message=False):
        """ارسال گیف همراه با متن"""
        return False  # موقتاً غیرفعال برای تست
        
        gif_path = self.get_gif_path(gif_name)
        
        if gif_path and self.file_exists(gif_path):
            try:
                print(f"🎬 Sending {gif_name} GIF...")
                
                with open(gif_path, 'rb') as gif:
                    if edit_message and update.callback_query:
                        # بجای delete، فقط send جدید
                        await context.bot.send_animation(
                            chat_id=update.effective_chat.id,
                            animation=gif, 
                            caption=text,
                            reply_markup=reply_markup,
                            parse_mode='Markdown'
                        )
                        # حذف پیام قبلی بعد از ارسال موفق
                        try:
                            await update.callback_query.delete_message()
                        except:
                            pass  # اگر پیام قبلی حذف نشد، مهم نیست
                    else:
                        # ارسال جدید
                        await context.bot.send_animation(
                            chat_id=update.effective_chat.id,
                            animation=gif,
                            caption=text,
                            reply_markup=reply_markup,
                            parse_mode='Markdown'
                        )
                
                print(f"✅ {gif_name} GIF sent successfully!")
                return True
                
            except Exception as e:
                print(f"❌ Error sending {gif_name} GIF: {e}")
        
        # اگر گیف موجود نباشد، فقط متن ارسال کن   
        if edit_message and update.callback_query:
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        return False

    async def send_welcome_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                               reply_markup: InlineKeyboardMarkup = None):
        """ارسال رسانه خوشامدگویی"""
        print(f"🔍 DEBUG: Looking for GIF at: {self.gifs_path}welcome.gif")
        welcome_gif = os.path.join(self.gifs_path, "welcome.gif")
        print(f"🔍 DEBUG: File exists: {self.file_exists(welcome_gif)}")

        if self.file_exists(welcome_gif):
            try:
                print(f"🔍 DEBUG: Attempting to send GIF...")
                with open(welcome_gif, 'rb') as gif:
                    user_name = update.effective_user.first_name or "کاربر"
                    caption = (
                        f"سلام {user_name} عزیز! 👋✨\n\n"
                        "🚀 به دستیار هوش مصنوعی نارموون خوش اومدی!\n\n"
                        "اینجا می‌تونی بازارها رو تحلیل کنی و سیگنال بگیری 📈"
                    )

                    await context.bot.send_animation(
                        chat_id=update.effective_chat.id,
                        animation=gif,
                        caption=caption,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    print(f"✅ DEBUG: GIF sent successfully!")
                    return True
            except Exception as e:
                print(f"❌ Error sending welcome GIF: {e}")
        else:
            print(f"❌ DEBUG: GIF file not found or empty")

        return False

    async def send_crypto_menu_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   message_text: str, reply_markup: InlineKeyboardMarkup = None):
        """ارسال رسانه برای منوی کریپتو"""
        return await self.send_gif_with_text(
            update, context, 'crypto_menu', message_text, reply_markup, edit_message=True
        )

# نمونه global
media_handler = MediaHandler()
