"""Main entry point for Kinguin Telegram Bot."""

import logging
import asyncio
from telegram.ext import Application

from config import Config
from telegram_bot import KinguinBot

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def check_pending_orders(bot: KinguinBot, app):
    """Background task to check pending orders and send keys when ready."""
    await asyncio.sleep(10)  # Wait for bot to start

    while True:
        try:
            pending = bot.db.get_pending_purchases()

            for purchase in pending:
                try:
                    # Check order status
                    order = bot.kinguin.get_order(purchase.order_id)
                    new_status = order["status"]

                    # Update status if changed
                    if new_status != purchase.status:
                        if new_status == "completed":
                            # Get keys
                            keys = bot.kinguin.get_order_keys(purchase.order_id)

                            if keys:
                                import json
                                keys_json = json.dumps([
                                    {"serial": k.serial, "name": k.name, "type": k.type}
                                    for k in keys
                                ])
                                bot.db.update_purchase_status(
                                    purchase.order_id,
                                    new_status,
                                    keys_json
                                )

                                # Send keys to user
                                keys_text = (
                                    f"✅ *Заказ завершен!*\n\n"
                                    f"🆔 ID: `{purchase.order_id}`\n"
                                    f"🎮 {purchase.product_name}\n\n"
                                    f"🔑 *Ключи:*\n"
                                )

                                for i, key in enumerate(keys, 1):
                                    keys_text += f"{i}. `{key.serial}`\n"

                                await app.bot.send_message(
                                    chat_id=purchase.user_id,
                                    text=keys_text,
                                    parse_mode="Markdown"
                                )

                                logger.info(
                                    f"Sent keys for order {purchase.order_id} "
                                    f"to user {purchase.user_id}"
                                )
                        else:
                            # Update status without keys
                            bot.db.update_purchase_status(
                                purchase.order_id,
                                new_status
                            )

                except Exception as e:
                    logger.error(
                        f"Failed to check order {purchase.order_id}: {e}"
                    )

        except Exception as e:
            logger.error(f"Error in background task: {e}")

        # Check every 60 seconds
        await asyncio.sleep(60)


async def run_bot():
    """Run the bot."""
    # Load configuration
    config = Config.from_env()
    logger.info("Configuration loaded")

    # Initialize bot
    bot = KinguinBot(config)
    logger.info("Bot initialized")

    # Build application
    application = bot.build_application()

    # Initialize the application
    await application.initialize()
    await application.start()

    logger.info("Bot started successfully")

    # Start background task
    background_task = asyncio.create_task(check_pending_orders(bot, application))

    # Start polling
    await application.updater.start_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True
    )

    logger.info("Polling started")

    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Stopping bot...")
        background_task.cancel()
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


def main():
    """Main entry point."""
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
