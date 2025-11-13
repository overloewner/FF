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
from database import Database, Purchase, FunPayLink

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
            "/balance - Проверить баланс\n"
            "/search `<название>` - Найти товар\n"
            "/buy `<kinguin_id>` `<quantity>` - Купить товар\n"
            "/history - История покупок\n"
            "/order `<order_id>` - Детали заказа\n\n"
            "*FunPay интеграция:*\n"
            "/link `<kinguin_id>` `<funpay_id>` - Связать товары\n"
            "/funpay `<funpay_id>` - Быстрая покупка\n"
            "/links - Список связей\n"
            "/unlink `<funpay_id>` - Удалить связь\n\n"
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
            "*Баланс:*\n"
            "`/balance` - проверить баланс аккаунта\n\n"
            "*Поиск товара:*\n"
            "`/search Steam` - найти товары по названию\n\n"
            "*Покупка товара:*\n"
            "`/buy 123456 1` - купить 1 шт товара с ID 123456\n\n"
            "*История:*\n"
            "`/history` - показать последние 10 покупок\n\n"
            "*Детали заказа:*\n"
            "`/order G94DBBFFB63F` - посмотреть заказ с ключами\n\n"
            "*FunPay интеграция (для перепродажи):*\n"
            "`/link 123456 32608058` - связать Kinguin и FunPay ID\n"
            "`/funpay 32608058` - быстрая покупка по FunPay ID\n"
            "`/links` - список всех связанных товаров\n"
            "`/unlink 32608058` - удалить связь\n\n"
            "После команды /buy или /funpay вы получите карточку товара "
            "с кнопкой подтверждения."
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def search_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /search command."""
        if not self._check_authorization(update):
            return

        if not context.args:
            await update.message.reply_text(
                "❌ Использование: `/search <название>`",
                parse_mode="Markdown"
            )
            return

        query = " ".join(context.args)

        try:
            await update.message.reply_text(f"🔍 Ищу: {query}...")
            products = self.kinguin.search_products(name=query, limit=10)

            if not products:
                await update.message.reply_text(
                    f"❌ Товары не найдены по запросу: {query}"
                )
                return

            result_text = f"🎮 *Найдено товаров:* {len(products)}\n\n"

            for i, product in enumerate(products, 1):
                result_text += (
                    f"{i}. *{product.name}*\n"
                    f"   🆔 ID: `{product.kinguin_id}`\n"
                    f"   💰 Цена: €{product.price:.2f}\n"
                    f"   📦 Доступно: {product.qty} шт\n"
                    f"   🖥 Платформа: {product.platform}\n"
                    f"   🌍 Регион: {product.region}\n\n"
                )

            result_text += "\nДля покупки используйте:\n`/buy <ID> <количество>`"

            await update.message.reply_text(result_text, parse_mode="Markdown")

        except KinguinAPIError as e:
            logger.error(f"Failed to search products: {e}")
            await update.message.reply_text(
                f"❌ Ошибка поиска: {str(e)}"
            )

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

        history_text += "\n💡 Для просмотра деталей: `/order <order_id>`"

        await update.message.reply_text(history_text, parse_mode="Markdown")

    async def order_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /order command - view order details by ID."""
        if not self._check_authorization(update):
            return

        if not context.args:
            await update.message.reply_text(
                "❌ Использование: `/order <order_id>`\n\n"
                "Пример: `/order G94DBBFFB63F`",
                parse_mode="Markdown"
            )
            return

        order_id = context.args[0].strip()

        try:
            # Get order from API
            await update.message.reply_text(f"🔍 Загружаю данные заказа {order_id}...")
            order = self.kinguin.get_order(order_id)

            # Try to get keys
            keys_text = ""
            try:
                keys = self.kinguin.get_order_keys(order_id)
                if keys:
                    keys_text = "\n\n🔑 *Ключи:*\n"
                    for i, key in enumerate(keys, 1):
                        keys_text += f"{i}. `{key.serial}`\n"
                        if key.name != "N/A":
                            keys_text += f"   📝 {key.name}\n"
            except Exception as e:
                logger.warning(f"Could not fetch keys for order {order_id}: {e}")
                if order.get("status") == "completed":
                    keys_text = "\n\n⚠️ Не удалось получить ключи"

            # Format order details
            status = order.get("status", "unknown")
            status_emoji = {
                "completed": "✅",
                "processing": "⏳",
                "new": "🆕",
                "cancelled": "❌",
                "refunded": "↩️"
            }.get(status, "❓")

            order_text = (
                f"📦 *Детали заказа*\n\n"
                f"🆔 ID: `{order_id}`\n"
                f"📊 Статус: {status_emoji} {status}\n"
                f"💰 Сумма: €{order.get('totalPrice', 0):.2f}\n"
            )

            # Add products info
            products = order.get("products", [])
            if products:
                order_text += f"\n🎮 *Товары ({len(products)}):*\n"
                for product in products:
                    order_text += (
                        f"• {product.get('name', 'N/A')}\n"
                        f"  📦 {product.get('qty', 0)} шт × €{product.get('price', 0):.2f}\n"
                    )

            order_text += keys_text

            await update.message.reply_text(order_text, parse_mode="Markdown")

        except KinguinAPIError as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            await update.message.reply_text(
                f"❌ Ошибка при получении заказа: {str(e)}"
            )

    async def link_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /link command - link FunPay ID to Kinguin ID."""
        if not self._check_authorization(update):
            return

        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Использование: `/link <kinguin_id> <funpay_id>`\n\n"
                "Пример: `/link 123456 32608058`\n"
                "Это привяжет FunPay ID 32608058 к Kinguin ID 123456",
                parse_mode="Markdown"
            )
            return

        try:
            kinguin_id = int(context.args[0])
            funpay_id = context.args[1].strip()
        except ValueError:
            await update.message.reply_text("❌ Kinguin ID должен быть числом")
            return

        user_id = update.effective_user.id

        # Verify Kinguin product exists
        try:
            await update.message.reply_text(f"🔍 Проверяю товар Kinguin {kinguin_id}...")
            product = self.kinguin.get_product(kinguin_id)

            # Save link with current price
            self.db.add_funpay_link(funpay_id, kinguin_id, user_id, product.price)

            await update.message.reply_text(
                f"✅ *Связь создана!*\n\n"
                f"🔗 FunPay ID: `{funpay_id}`\n"
                f"🎮 Kinguin ID: `{kinguin_id}`\n"
                f"📦 Товар: {product.name}\n"
                f"💰 Цена на момент связи: €{product.price:.2f}\n\n"
                f"Теперь используйте `/funpay {funpay_id}` для быстрой покупки",
                parse_mode="Markdown"
            )

        except KinguinAPIError as e:
            logger.error(f"Failed to verify product {kinguin_id}: {e}")
            await update.message.reply_text(
                f"❌ Ошибка: товар Kinguin {kinguin_id} не найден"
            )

    async def unlink_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /unlink command - remove FunPay link."""
        if not self._check_authorization(update):
            return

        if not context.args:
            await update.message.reply_text(
                "❌ Использование: `/unlink <funpay_id>`\n\n"
                "Пример: `/unlink 32608058`",
                parse_mode="Markdown"
            )
            return

        funpay_id = context.args[0].strip()
        user_id = update.effective_user.id

        if self.db.remove_funpay_link(funpay_id, user_id):
            await update.message.reply_text(
                f"✅ Связь для FunPay ID `{funpay_id}` удалена",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"❌ Связь для FunPay ID `{funpay_id}` не найдена",
                parse_mode="Markdown"
            )

    async def links_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /links command - show all FunPay links."""
        if not self._check_authorization(update):
            return

        user_id = update.effective_user.id
        links = self.db.get_all_funpay_links(user_id)

        if not links:
            await update.message.reply_text(
                "📋 Список связей пуст\n\n"
                "Используйте `/link <kinguin_id> <funpay_id>` для создания связи",
                parse_mode="Markdown"
            )
            return

        links_text = "🔗 *Связи FunPay → Kinguin:*\n\n"

        for i, link in enumerate(links, 1):
            created = datetime.fromisoformat(link.created_at)
            date_str = created.strftime("%d.%m.%Y")

            links_text += (
                f"{i}. FunPay: `{link.funpay_id}` → Kinguin: `{link.kinguin_id}`\n"
                f"   💰 Цена при создании: €{link.price:.2f}\n"
                f"   📅 {date_str}\n\n"
            )

        links_text += "\n💡 Используйте `/funpay <funpay_id>` для покупки"

        await update.message.reply_text(links_text, parse_mode="Markdown")

    async def funpay_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /funpay command - quick buy by FunPay ID."""
        if not self._check_authorization(update):
            return

        if not context.args:
            await update.message.reply_text(
                "❌ Использование: `/funpay <funpay_id>`\n\n"
                "Пример: `/funpay 32608058`",
                parse_mode="Markdown"
            )
            return

        funpay_id = context.args[0].strip()
        user_id = update.effective_user.id

        # Get link
        link = self.db.get_funpay_link(funpay_id, user_id)
        if not link:
            await update.message.reply_text(
                f"❌ Связь для FunPay ID `{funpay_id}` не найдена\n\n"
                f"Используйте `/link <kinguin_id> <funpay_id>` для создания связи",
                parse_mode="Markdown"
            )
            return

        kinguin_id = link.kinguin_id
        old_price = link.price
        quantity = 1  # Default quantity

        # Get product info
        try:
            await update.message.reply_text("🔍 Загружаю информацию о товаре...")
            product = self.kinguin.get_product(kinguin_id)

            if product.qty == 0:
                await update.message.reply_text(
                    "❌ Товар отсутствует на складе"
                )
                return

            # Store pending purchase
            self.pending_purchases[user_id] = (product, quantity)

            # Create product card with confirmation button
            total_price = product.price * quantity
            current_price = product.price

            # Price comparison
            price_diff = current_price - old_price
            price_emoji = "📈" if price_diff > 0 else "📉" if price_diff < 0 else "➡️"
            price_text = f"💰 Цена сейчас: €{current_price:.2f}\n"

            if price_diff != 0:
                price_text += f"{price_emoji} Изменение: €{price_diff:+.2f} (было €{old_price:.2f})\n"

            card_text = (
                f"🎮 *{product.name}*\n\n"
                f"🔗 FunPay ID: `{funpay_id}`\n"
                f"🆔 Kinguin ID: `{kinguin_id}`\n\n"
                f"{price_text}"
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
        application.add_handler(CommandHandler("search", self.search_command))
        application.add_handler(CommandHandler("buy", self.buy_command))
        application.add_handler(CommandHandler("history", self.history_command))
        application.add_handler(CommandHandler("order", self.order_command))

        # FunPay integration
        application.add_handler(CommandHandler("link", self.link_command))
        application.add_handler(CommandHandler("unlink", self.unlink_command))
        application.add_handler(CommandHandler("links", self.links_command))
        application.add_handler(CommandHandler("funpay", self.funpay_command))

        application.add_handler(CallbackQueryHandler(self.button_callback))

        # Error handler
        application.add_error_handler(self.error_handler)

        return application
