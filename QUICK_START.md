# Быстрый старт - Покупка через Kinguin API

## Шаг 1: Установка и настройка

```bash
npm install
cp .env.example .env
```

Отредактируйте `.env`:
```env
KINGUIN_API_KEY=ваш_ключ
KINGUIN_API_SECRET=ваш_секрет
KINGUIN_ENV=sandbox
```

## Шаг 2: Простой скрипт покупки

Создайте файл `buy.ts`:

```typescript
import * as dotenv from 'dotenv';
import { KinguinService } from './src/services/KinguinService';

dotenv.config();

async function buyProduct() {
  const kinguin = new KinguinService({
    apiKey: process.env.KINGUIN_API_KEY!,
    apiSecret: process.env.KINGUIN_API_SECRET,
    environment: 'sandbox',
  });

  try {
    // 1. Проверяем баланс
    const balance = await kinguin.getBalance();
    console.log(`💰 Баланс: €${balance.balance}`);

    // 2. Ищем товар
    const results = await kinguin.searchProducts({
      name: 'название игры',
      limit: 5,
    });

    if (results.results.length === 0) {
      console.log('❌ Товары не найдены');
      return;
    }

    // 3. Выбираем первый товар
    const product = results.results[0];
    console.log(`\n📦 Найден товар:`);
    console.log(`   ${product.name}`);
    console.log(`   Цена: €${product.price}`);
    console.log(`   Доступно: ${product.qty} шт.`);

    // 4. Проверяем достаточно ли средств
    if (balance.balance < product.price) {
      console.log('❌ Недостаточно средств');
      return;
    }

    // 5. Создаем заказ
    console.log('\n🛒 Создаем заказ...');
    const order = await kinguin.createOrder({
      products: [{
        kinguinId: product.kinguinId,
        qty: 1,
        price: product.price,
        name: product.name,
      }],
      orderExternalId: `order-${Date.now()}`,
    });

    console.log(`✅ Заказ создан!`);
    console.log(`   ID: ${order.orderId}`);
    console.log(`   Статус: ${order.status}`);

    // 6. Ждем обработки и получаем ключи
    console.log('\n⏳ Ожидаем обработки заказа...');

    let attempts = 0;
    const maxAttempts = 10;

    while (attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 2000)); // Ждем 2 секунды

      const orderInfo = await kinguin.getOrder(order.orderId);
      console.log(`   Статус: ${orderInfo.status}`);

      if (orderInfo.status === 'completed') {
        console.log('\n🎉 Заказ завершен!');

        // Получаем ключи
        const keys = await kinguin.getOrderKeys(order.orderId);
        console.log('\n🔑 Ваши ключи:');

        if (Array.isArray(keys)) {
          keys.forEach((key: any, index: number) => {
            console.log(`\n${index + 1}. ${key.name}`);
            console.log(`   Ключ: ${key.serial}`);
            console.log(`   Тип: ${key.type}`);
          });
        }
        break;
      }

      attempts++;
    }

    if (attempts === maxAttempts) {
      console.log('\n⚠️  Заказ все еще обрабатывается');
      console.log('   Проверьте позже через getOrder()');
    }

  } catch (error: any) {
    console.error('❌ Ошибка:', error.message);
    if (error.response) {
      console.error('Детали:', error.response.data);
    }
  }
}

buyProduct();
```

## Шаг 3: Запуск

```bash
npx ts-node buy.ts
```

## Основные команды API

### Поиск товара
```typescript
const results = await kinguin.searchProducts({
  name: 'GTA V',
  platform: 'Steam',
  region: 'EU',
  limit: 10,
});
```

### Покупка
```typescript
const order = await kinguin.createOrder({
  products: [{
    kinguinId: 12345,
    qty: 1,
    price: 29.99,
    name: 'Product Name',
  }],
});
```

### Получение ключей
```typescript
const keys = await kinguin.getOrderKeys(orderId);
```

## Частые вопросы

**Q: Когда я получу ключи?**
A: Обычно мгновенно, но может занять до нескольких минут. Проверяйте статус заказа.

**Q: Что делать если заказ висит в processing?**
A: Подождите несколько минут и проверьте статус через `getOrder(orderId)`.

**Q: Можно ли отменить заказ?**
A: Нет, заказы через API нельзя отменить автоматически. Обратитесь в поддержку Kinguin.

**Q: Разница между sandbox и production?**
A: Sandbox - тестовая среда без реальных денег. Production - реальные покупки.

**Q: Нужен ли API Secret?**
A: Не обязательно, но рекомендуется для безопасности. С ним генерируется подпись запросов.

## Проверка статуса заказа

```typescript
const orderInfo = await kinguin.getOrder('order-id');
console.log(orderInfo.status);

// Статусы:
// - new: создан
// - processing: обрабатывается
// - completed: готов, ключи доступны
// - cancelled: отменен
```

## Советы

1. **Всегда проверяйте баланс** перед покупкой
2. **Используйте sandbox** для тестирования
3. **Сохраняйте orderId** для отслеживания заказов
4. **Проверяйте availability (qty)** товара перед покупкой
5. **Обрабатывайте ошибки** - API может вернуть ошибку

## Безопасность

❌ НЕ делайте:
- Не коммитьте `.env` файл
- Не публикуйте API ключи
- Не делайте много запросов подряд (rate limiting)

✅ Делайте:
- Используйте переменные окружения
- Храните ключи в безопасном месте
- Добавьте задержки между запросами
- Логируйте все покупки

## Поддержка

Если что-то не работает:
1. Проверьте API ключи в `.env`
2. Убедитесь что используете правильное окружение
3. Проверьте баланс аккаунта
4. Посмотрите логи ошибок
5. Проверьте документацию Kinguin API
