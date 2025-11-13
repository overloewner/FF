"""Telegram bot handlers and logic."""

import json
import logging
from datetime import datetime
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from config import Config
from kinguin_client import KinguinClient, KinguinAPIError, Product
from database import Database, Purchase

logger = logging.getLogger(__name__)


class KinguinBot:
    """Kinguin Telegram bot."""

    def __init__(self, config: Config):
        self.config = config
        self.kinguin = KinguinClient(
            api_key=config.kinguin_api_key,
            api_secret=config.kinguin_api_secret,
            base_url=config.kinguin_base_url
        )
        self.db = Database(config.database_path)
        self.pending_purchases = {}  # {user_id: Product}

    def _check_authorization(self, update: Update) -> bool:
        """Check if user is authorized."""
        user_id = update.effective_user.id
        if not self.config.is_user_allowed(user_id):
            logger.warning(f"Unauthorized access attempt from user {user_id}")
            return False
        return True

    async def start_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /start command."""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ У вас нет доступа к этому боту.")
            return

        welcome_message = (
            "🎮 *Kinguin Purchase Bot*\n\n"
            "Доступные команды:\n"
            "/buy `<kinguin_id>` `<quantity>` - Купить товар\n"
            "/balance - Проверить баланс\n"
            "/history - История покупок\n"
            "/help - Справка"
        )
        await update.message.reply_text(
            welcome_message,
            parse_mode="Markdown"
        )

    async def help_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /help command."""
        if not self._check_authorization(update):
            return

        help_text = (
            "📖 *Справка*\n\n"
            "*Покупка товара:*\n"
            "`/buy 123456 1` - купить 1 шт товара с ID 123456\n\n"
            "*Проверка баланса:*\n"
            "`/balance` - показать текущий баланс\n\n"
            "*История:*\n"
            "`/history` - показать последние 10 покупок\n\n"
            "После команды /buy вы получите карточку товара "
            "с кнопкой подтверждения."
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def balance_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /balance command."""
        if not self._check_authorization(update):
            return

        try:
            balance_data = self.kinguin.get_balance()
            balance = balance_data.get("balance", 0)
            currency = balance_data.get("currency", "EUR")

            await update.message.reply_text(
                f"💰 *Баланс:* {balance:.2f} {currency}",
                parse_mode="Markdown"
            )

        except KinguinAPIError as e:
            logger.error(f"Failed to get balance: {e}")
            await update.message.reply_text(
                f"❌ Ошибка при получении баланса: {str(e)}"
            )

    async def buy_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /buy command."""
        if not self._check_authorization(update):
            return

        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Использование: `/buy <kinguin_id> <quantity>`",
                parse_mode="Markdown"
            )
            return

        try:
            kinguin_id = int(context.args[0])
            quantity = int(context.args[1])

            if quantity <= 0:
                await update.message.reply_text("❌ Количество должно быть > 0")
                return

        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат. Используйте числа."
            )
            return

        # Get product info
        try:
            await update.message.reply_text("🔍 Поиск товара...")
            product = self.kinguin.get_product(kinguin_id)

            if product.qty < quantity:
                await update.message.reply_text(
                    f"❌ Недостаточно товара на складе. Доступно: {product.qty}"
                )
                return

            if product.qty == 0:
                await update.message.reply_text(
                    "❌ Товар отсутствует на складе"
                )
                return

            # Store pending purchase
            user_id = update.effective_user.id
            self.pending_purchases[user_id] = (product, quantity)

            # Create product card with confirmation button
            total_price = product.price * quantity

            card_text = (
                f"🎮 *{product.name}*\n\n"
                f"💰 Цена: €{product.price:.2f}\n"
                f"📦 Количество: {quantity}\n"
                f"💵 Итого: €{total_price:.2f}\n\n"
                f"🖥 Платформа: {product.platform}\n"
                f"🌍 Регион: {product.region}\n"
                f"📊 Доступно: {product.qty} шт."
            )

            keyboard = [
                [InlineKeyboardButton("✅ Подтвердить покупку", callback_data="confirm_purchase")],
                [InlineKeyboardButton("❌ Отменить", callback_data="cancel_purchase")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                card_text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )

        except KinguinAPIError as e:
            logger.error(f"Failed to get product {kinguin_id}: {e}")
            await update.message.reply_text(
                f"❌ Ошибка при получении информации о товаре: {str(e)}"
            )

    async def history_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /history command."""
        if not self._check_authorization(update):
            return

        user_id = update.effective_user.id
        purchases = self.db.get_user_purchases(user_id, limit=10)

        if not purchases:
            await update.message.reply_text("📋 История покупок пуста")
            return

        history_text = "📋 *История покупок:*\n\n"

        for i, purchase in enumerate(purchases, 1):
            created_at = datetime.fromisoformat(purchase.created_at)
            date_str = created_at.strftime("%d.%m.%Y %H:%M")

            status_emoji = {
                "completed": "✅",
                "processing": "⏳",
                "new": "🆕",
                "cancelled": "❌",
                "refunded": "↩️"
            }.get(purchase.status, "❓")

            history_text += (
                f"{i}. {status_emoji} *{purchase.product_name}*\n"
                f"   💰 €{purchase.total_price:.2f} | "
                f"📦 {purchase.quantity} шт\n"
                f"   📅 {date_str}\n"
                f"   🆔 `{purchase.order_id}`\n\n"
            )

        await update.message.reply_text(history_text, parse_mode="Markdown")

    async def button_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle button callbacks."""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id

        if query.data == "confirm_purchase":
            await self._process_purchase(query, user_id)

        elif query.data == "cancel_purchase":
            if user_id in self.pending_purchases:
                del self.pending_purchases[user_id]
            await query.edit_message_text("❌ Покупка отменена")

    async def _process_purchase(self, query, user_id: int):
        """Process confirmed purchase."""
        if user_id not in self.pending_purchases:
            await query.edit_message_text(
                "❌ Сессия покупки истекла. Повторите команду /buy"
            )
            return

        product, quantity = self.pending_purchases[user_id]
        del self.pending_purchases[user_id]

        try:
            # Create order
            await query.edit_message_text("⏳ Обрабатываю заказ...")

            order = self.kinguin.create_order(
                kinguin_id=product.kinguin_id,
                quantity=quantity,
                price=product.price,
                name=product.name
            )

            order_id = order["orderId"]
            status = order["status"]
            total_price = order["totalPrice"]

            # Save to database
            purchase = Purchase(
                id=None,
                user_id=user_id,
                order_id=order_id,
                kinguin_id=product.kinguin_id,
                product_name=product.name,
                quantity=quantity,
                price=product.price,
                total_price=total_price,
                status=status,
                keys=None,
                created_at=datetime.now().isoformat()
            )
            self.db.add_purchase(purchase)

            # Try to get keys if order is completed
            keys_text = ""
            if status == "completed":
                try:
                    keys = self.kinguin.get_order_keys(order_id)
                    if keys:
                        keys_json = json.dumps([
                            {"serial": k.serial, "name": k.name, "type": k.type}
                            for k in keys
                        ])
                        self.db.update_purchase_status(order_id, status, keys_json)

                        keys_text = "\n\n🔑 *Ключи:*\n"
                        for i, key in enumerate(keys, 1):
                            keys_text += f"{i}. `{key.serial}`\n"
                except Exception as e:
                    logger.error(f"Failed to get keys: {e}")

            success_message = (
                f"✅ *Покупка завершена!*\n\n"
                f"🆔 ID заказа: `{order_id}`\n"
                f"💰 Сумма: €{total_price:.2f}\n"
                f"📊 Статус: {status}"
                f"{keys_text}"
            )

            await query.edit_message_text(
                success_message,
                parse_mode="Markdown"
            )

            # Check order status for pending orders
            if status not in ["completed", "cancelled", "refunded"]:
                await query.message.reply_text(
                    "⏳ Заказ обрабатывается. Ключи будут отправлены автоматически."
                )

        except KinguinAPIError as e:
            logger.error(f"Purchase failed: {e}")
            await query.edit_message_text(
                f"❌ Ошибка при покупке: {str(e)}"
            )

    async def error_handler(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle errors."""
        logger.error(f"Update {update} caused error {context.error}")

    def build_application(self) -> Application:
        """Build telegram application."""
        application = Application.builder().token(self.config.telegram_token).build()

        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("balance", self.balance_command))
        application.add_handler(CommandHandler("buy", self.buy_command))
        application.add_handler(CommandHandler("history", self.history_command))
        application.add_handler(CallbackQueryHandler(self.button_callback))

        # Error handler
        application.add_error_handler(self.error_handler)

        return application
