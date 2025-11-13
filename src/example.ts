import * as dotenv from 'dotenv';
import { KinguinService } from './services/KinguinService';
import { CreateOrderRequest } from './types/kinguin.types';

// Загружаем переменные окружения
dotenv.config();

async function main() {
  // Инициализация сервиса Kinguin
  const kinguin = new KinguinService({
    apiKey: process.env.KINGUIN_API_KEY || '',
    apiSecret: process.env.KINGUIN_API_SECRET,
    environment: (process.env.KINGUIN_ENV as 'sandbox' | 'production') || 'sandbox',
  });

  try {
    console.log('=== Проверка баланса ===');
    const balance = await kinguin.getBalance();
    console.log(`Баланс: ${balance.balance} ${balance.currency}`);
    console.log('');

    // Пример 1: Поиск товаров
    console.log('=== Поиск товаров ===');
    const searchResults = await kinguin.searchProducts({
      name: 'Steam',
      limit: 5,
      sortBy: 'price',
      sortType: 'asc',
    });

    console.log(`Найдено товаров: ${searchResults.item_count}`);
    searchResults.results.forEach((product, index) => {
      console.log(`\n${index + 1}. ${product.name}`);
      console.log(`   ID: ${product.kinguinId}`);
      console.log(`   Цена: €${product.price}`);
      console.log(`   Платформа: ${product.platform}`);
      console.log(`   Регион: ${product.region}`);
      console.log(`   Доступно: ${product.qty} шт.`);
    });
    console.log('');

    // Пример 2: Получение информации о конкретном товаре
    if (searchResults.results.length > 0) {
      const firstProduct = searchResults.results[0];
      console.log('=== Информация о товаре ===');
      const productInfo = await kinguin.getProduct(firstProduct.kinguinId);
      console.log(JSON.stringify(productInfo, null, 2));
      console.log('');
    }

    // Пример 3: Создание заказа (раскомментируйте для реальной покупки)
    /*
    console.log('=== Создание заказа ===');

    // Убедитесь, что у вас есть товар для покупки
    const productToBuy = searchResults.results[0];

    if (!productToBuy) {
      console.log('Нет доступных товаров для покупки');
      return;
    }

    const orderData: CreateOrderRequest = {
      products: [
        {
          kinguinId: productToBuy.kinguinId,
          qty: 1,
          price: productToBuy.price,
          name: productToBuy.name,
        },
      ],
      orderExternalId: `order-${Date.now()}`, // Ваш внутренний ID заказа
    };

    const order = await kinguin.createOrder(orderData);
    console.log('Заказ создан:', order);
    console.log(`ID заказа: ${order.orderId}`);
    console.log(`Статус: ${order.status}`);
    console.log(`Сумма: €${order.totalPrice}`);
    console.log('');

    // Пример 4: Получение информации о заказе
    console.log('=== Получение информации о заказе ===');
    const orderInfo = await kinguin.getOrder(order.orderId);
    console.log(JSON.stringify(orderInfo, null, 2));
    console.log('');

    // Пример 5: Получение ключей из заказа
    if (orderInfo.status === 'completed') {
      console.log('=== Получение ключей ===');
      const keys = await kinguin.getOrderKeys(order.orderId);
      console.log('Ключи получены:');
      console.log(JSON.stringify(keys, null, 2));
    } else {
      console.log(`Заказ еще не завершен. Статус: ${orderInfo.status}`);
    }
    */

    // Пример 6: Получение списка заказов
    console.log('=== Получение списка заказов ===');
    const orders = await kinguin.getOrders({
      limit: 10,
      page: 1,
    });
    console.log(`Всего заказов: ${orders.item_count || 0}`);
    if (orders.results && orders.results.length > 0) {
      orders.results.forEach((order: any, index: number) => {
        console.log(`\n${index + 1}. Заказ ${order.orderId}`);
        console.log(`   Статус: ${order.status}`);
        console.log(`   Сумма: €${order.totalPrice}`);
        console.log(`   Дата: ${order.createdAt}`);
      });
    } else {
      console.log('Заказов пока нет');
    }

  } catch (error: any) {
    console.error('Ошибка:', error.message);
    if (error.response) {
      console.error('Детали:', error.response.data);
    }
  }
}

// Запуск примера
main();
