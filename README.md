# Kinguin API - Клиент для покупки товаров

Клиент для работы с API Kinguin, позволяющий осуществлять ручные покупки игровых ключей и других цифровых товаров через API.

## Возможности

- ✅ Поиск товаров в каталоге Kinguin
- ✅ Получение детальной информации о товаре
- ✅ Создание заказов (покупка товаров)
- ✅ Получение информации о заказах
- ✅ Получение ключей из заказа
- ✅ Проверка баланса аккаунта
- ✅ Полная типизация TypeScript
- ✅ Поддержка Sandbox и Production окружений
- ✅ Автоматическая генерация подписей для API

## Установка

```bash
# Клонируйте репозиторий
git clone <your-repo-url>
cd FF

# Установите зависимости
npm install

# Скопируйте файл с примером переменных окружения
cp .env.example .env
```

## Настройка

Отредактируйте файл `.env` и добавьте свои учетные данные Kinguin:

```env
KINGUIN_API_KEY=ваш_api_ключ
KINGUIN_API_SECRET=ваш_api_секрет
KINGUIN_ENV=sandbox  # или production
```

### Получение API ключей

1. Зарегистрируйтесь на [Kinguin](https://www.kinguin.net/)
2. Перейдите в раздел API настроек аккаунта
3. Создайте новый API ключ
4. Скопируйте API Key и API Secret

### Окружения

- **Sandbox** (`sandbox`): Тестовое окружение для разработки
  - URL: `https://gateway.kinguin.net/esa/api/v1`
  - Используйте для тестирования без реальных транзакций

- **Production** (`production`): Боевое окружение
  - URL: `https://gateway.kinguin.net/esa/api/v2`
  - Реальные транзакции и списание средств

## Использование

### Базовая инициализация

```typescript
import { KinguinService } from './services/KinguinService';

const kinguin = new KinguinService({
  apiKey: 'ваш_api_ключ',
  apiSecret: 'ваш_api_секрет',  // опционально, но рекомендуется
  environment: 'sandbox',         // или 'production'
});
```

### Поиск товаров

```typescript
// Простой поиск
const results = await kinguin.searchProducts({
  name: 'GTA V',
  limit: 10,
});

console.log(`Найдено товаров: ${results.item_count}`);
results.results.forEach(product => {
  console.log(`${product.name} - €${product.price}`);
});

// Расширенный поиск с фильтрами
const filteredResults = await kinguin.searchProducts({
  name: 'Steam',
  platform: 'Steam',
  region: 'EU',
  priceFrom: 5,
  priceTo: 50,
  sortBy: 'price',
  sortType: 'asc',
  limit: 20,
  page: 1,
});
```

### Получение информации о товаре

```typescript
const productInfo = await kinguin.getProduct(12345); // kinguinId товара
console.log(productInfo);
```

### Создание заказа (покупка)

```typescript
import { CreateOrderRequest } from './types/kinguin.types';

const orderData: CreateOrderRequest = {
  products: [
    {
      kinguinId: 12345,
      qty: 1,
      price: 29.99,
      name: 'Game Name',
    },
  ],
  orderExternalId: `order-${Date.now()}`, // Ваш уникальный ID заказа
  couponCode: 'DISCOUNT10',                // Опционально
};

const order = await kinguin.createOrder(orderData);
console.log(`Заказ создан: ${order.orderId}`);
console.log(`Статус: ${order.status}`);
console.log(`Сумма: €${order.totalPrice}`);
```

### Получение информации о заказе

```typescript
const orderInfo = await kinguin.getOrder('order-id-here');
console.log(orderInfo);
```

### Получение ключей из заказа

```typescript
const keys = await kinguin.getOrderKeys('order-id-here');
keys.forEach(key => {
  console.log(`Ключ: ${key.serial}`);
  console.log(`Название: ${key.name}`);
  console.log(`Тип: ${key.type}`);
});
```

### Получение списка заказов

```typescript
const orders = await kinguin.getOrders({
  page: 1,
  limit: 50,
  dateFrom: '2024-01-01',
  dateTo: '2024-12-31',
});
```

### Проверка баланса

```typescript
const balance = await kinguin.getBalance();
console.log(`Баланс: ${balance.balance} ${balance.currency}`);
```

## Запуск примера

В проекте есть готовый пример использования:

```bash
# Запуск в режиме разработки (с ts-node)
npm run dev

# Или скомпилируйте и запустите
npm run build
npm start
```

## Структура проекта

```
FF/
├── src/
│   ├── services/
│   │   └── KinguinService.ts    # Основной сервис для работы с API
│   ├── types/
│   │   └── kinguin.types.ts     # TypeScript типы
│   ├── example.ts               # Пример использования
│   └── index.ts                 # Экспорты
├── .env.example                 # Пример файла с переменными окружения
├── .gitignore
├── package.json
├── tsconfig.json
└── README.md
```

## API методы

### KinguinService

| Метод | Описание | Параметры |
|-------|----------|-----------|
| `searchProducts(params)` | Поиск товаров | `SearchProductsParams` |
| `getProduct(kinguinId)` | Информация о товаре | `number` |
| `createOrder(orderData)` | Создание заказа | `CreateOrderRequest` |
| `getOrder(orderId)` | Информация о заказе | `string` |
| `getOrders(params)` | Список заказов | `{ page?, limit?, dateFrom?, dateTo? }` |
| `getOrderKeys(orderId)` | Ключи из заказа | `string` |
| `getBalance()` | Баланс аккаунта | - |

## Типы данных

Все типы данных доступны в `src/types/kinguin.types.ts`:

- `KinguinConfig` - Конфигурация сервиса
- `Product` - Информация о товаре
- `SearchProductsParams` - Параметры поиска
- `CreateOrderRequest` - Данные для создания заказа
- `Order` - Информация о заказе
- `OrderKey` - Ключ из заказа
- `BalanceResponse` - Информация о балансе

## Обработка ошибок

```typescript
try {
  const order = await kinguin.createOrder(orderData);
  console.log('Заказ успешно создан:', order.orderId);
} catch (error) {
  if (axios.isAxiosError(error)) {
    console.error('Ошибка API:', error.response?.data);
    console.error('Статус:', error.response?.status);
  } else {
    console.error('Неизвестная ошибка:', error);
  }
}
```

## Безопасность

⚠️ **Важно:**
- Никогда не коммитьте файл `.env` с реальными ключами
- Используйте переменные окружения для хранения API ключей
- Для production используйте безопасное хранилище секретов
- API Secret не обязателен, но значительно повышает безопасность

## Статусы заказов

- `new` - Новый заказ
- `processing` - Обрабатывается
- `completed` - Завершен (ключи доступны)
- `cancelled` - Отменен
- `refunded` - Возвращен

## Полезные ссылки

- [Официальная документация Kinguin API](https://docs.kinguin.net/)
- [Kinguin Developer Portal](https://www.kinguin.net/integration)
- [Список поддерживаемых платформ](https://docs.kinguin.net/v1/platforms)
- [Список регионов](https://docs.kinguin.net/v1/regions)

## Лицензия

MIT

## Поддержка

При возникновении проблем:
1. Проверьте правильность API ключей
2. Убедитесь, что используете правильное окружение (sandbox/production)
3. Проверьте баланс аккаунта перед покупкой
4. Изучите документацию Kinguin API

## Разработка

```bash
# Установка зависимостей
npm install

# Компиляция TypeScript
npm run build

# Запуск примера
npm run dev
```
