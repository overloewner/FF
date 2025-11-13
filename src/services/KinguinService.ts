import axios, { AxiosInstance, AxiosError } from 'axios';
import * as crypto from 'crypto';
import {
  KinguinConfig,
  SearchProductsParams,
  SearchProductsResponse,
  CreateOrderRequest,
  CreateOrderResponse,
  GetOrderResponse,
  BalanceResponse,
  KinguinApiError
} from '../types/kinguin.types';

export class KinguinService {
  private api: AxiosInstance;
  private apiKey: string;
  private apiSecret?: string;
  private environment: 'sandbox' | 'production';

  constructor(config: KinguinConfig) {
    this.apiKey = config.apiKey;
    this.apiSecret = config.apiSecret;
    this.environment = config.environment || 'sandbox';

    const baseUrl = config.baseUrl || this.getBaseUrl();

    this.api = axios.create({
      baseURL: baseUrl,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Добавляем interceptor для авторизации
    this.api.interceptors.request.use((config) => {
      const timestamp = Date.now().toString();

      // API Key всегда добавляем в заголовок
      config.headers['X-Api-Key'] = this.apiKey;

      // Если есть API Secret, создаем подпись
      if (this.apiSecret) {
        const path = config.url || '';
        const method = config.method?.toUpperCase() || 'GET';
        const body = config.data ? JSON.stringify(config.data) : '';

        const signature = this.generateSignature(
          path,
          method,
          body,
          timestamp
        );

        config.headers['X-Api-Signature'] = signature;
        config.headers['X-Api-Timestamp'] = timestamp;
      }

      return config;
    });
  }

  private getBaseUrl(): string {
    if (this.environment === 'production') {
      return 'https://gateway.kinguin.net/esa/api/v2';
    }
    return 'https://gateway.kinguin.net/esa/api/v1';
  }

  private generateSignature(
    path: string,
    method: string,
    body: string,
    timestamp: string
  ): string {
    if (!this.apiSecret) {
      throw new Error('API Secret is required for signature generation');
    }

    const message = `${path}${method}${body}${timestamp}`;
    const signature = crypto
      .createHmac('sha256', this.apiSecret)
      .update(message)
      .digest('hex');

    return signature;
  }

  /**
   * Поиск товаров в каталоге Kinguin
   */
  async searchProducts(params: SearchProductsParams = {}): Promise<SearchProductsResponse> {
    try {
      const queryParams = new URLSearchParams();

      if (params.name) queryParams.append('name', params.name);
      if (params.kinguinId) queryParams.append('kinguinId', params.kinguinId.toString());
      if (params.page) queryParams.append('page', params.page.toString());
      if (params.limit) queryParams.append('limit', params.limit.toString());
      if (params.sortBy) queryParams.append('sortBy', params.sortBy);
      if (params.sortType) queryParams.append('sortType', params.sortType);
      if (params.priceFrom) queryParams.append('priceFrom', params.priceFrom.toString());
      if (params.priceTo) queryParams.append('priceTo', params.priceTo.toString());
      if (params.platform) queryParams.append('platform', params.platform);
      if (params.region) queryParams.append('region', params.region);

      const response = await this.api.get<SearchProductsResponse>(
        `/products?${queryParams.toString()}`
      );

      return response.data;
    } catch (error) {
      this.handleError(error, 'Failed to search products');
      throw error;
    }
  }

  /**
   * Получение информации о конкретном товаре по kinguinId
   */
  async getProduct(kinguinId: number): Promise<any> {
    try {
      const response = await this.api.get(`/products/${kinguinId}`);
      return response.data;
    } catch (error) {
      this.handleError(error, `Failed to get product ${kinguinId}`);
      throw error;
    }
  }

  /**
   * Создание заказа (покупка)
   */
  async createOrder(orderData: CreateOrderRequest): Promise<CreateOrderResponse> {
    try {
      const response = await this.api.post<CreateOrderResponse>('/order', orderData);
      return response.data;
    } catch (error) {
      this.handleError(error, 'Failed to create order');
      throw error;
    }
  }

  /**
   * Получение информации о заказе
   */
  async getOrder(orderId: string): Promise<GetOrderResponse> {
    try {
      const response = await this.api.get<GetOrderResponse>(`/order/${orderId}`);
      return response.data;
    } catch (error) {
      this.handleError(error, `Failed to get order ${orderId}`);
      throw error;
    }
  }

  /**
   * Получение списка всех заказов
   */
  async getOrders(params?: {
    page?: number;
    limit?: number;
    dateFrom?: string;
    dateTo?: string;
  }): Promise<any> {
    try {
      const queryParams = new URLSearchParams();

      if (params?.page) queryParams.append('page', params.page.toString());
      if (params?.limit) queryParams.append('limit', params.limit.toString());
      if (params?.dateFrom) queryParams.append('dateFrom', params.dateFrom);
      if (params?.dateTo) queryParams.append('dateTo', params.dateTo);

      const response = await this.api.get(`/order?${queryParams.toString()}`);
      return response.data;
    } catch (error) {
      this.handleError(error, 'Failed to get orders');
      throw error;
    }
  }

  /**
   * Получение ключей для заказа
   */
  async getOrderKeys(orderId: string): Promise<any> {
    try {
      const response = await this.api.get(`/order/${orderId}/keys`);
      return response.data;
    } catch (error) {
      this.handleError(error, `Failed to get keys for order ${orderId}`);
      throw error;
    }
  }

  /**
   * Проверка баланса аккаунта
   */
  async getBalance(): Promise<BalanceResponse> {
    try {
      const response = await this.api.get<BalanceResponse>('/user/balance');
      return response.data;
    } catch (error) {
      this.handleError(error, 'Failed to get balance');
      throw error;
    }
  }

  /**
   * Обработка ошибок API
   */
  private handleError(error: unknown, message: string): void {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<KinguinApiError>;
      console.error(`${message}:`, {
        status: axiosError.response?.status,
        statusText: axiosError.response?.statusText,
        data: axiosError.response?.data,
      });
    } else {
      console.error(`${message}:`, error);
    }
  }
}
