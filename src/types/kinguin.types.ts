export interface KinguinConfig {
  apiKey: string;
  apiSecret?: string;
  environment?: 'sandbox' | 'production';
  baseUrl?: string;
}

export interface Product {
  kinguinId: number;
  productId: string;
  name: string;
  price: number;
  qty: number;
  textQty?: string;
  isPreorder: boolean;
  releaseDate?: string;
  platform: string;
  region: string;
  merchantName?: string;
  offerId?: string;
}

export interface SearchProductsParams {
  name?: string;
  kinguinId?: number;
  page?: number;
  limit?: number;
  sortBy?: 'name' | 'price' | 'qty';
  sortType?: 'asc' | 'desc';
  priceFrom?: number;
  priceTo?: number;
  platform?: string;
  region?: string;
}

export interface SearchProductsResponse {
  results: Product[];
  item_count: number;
}

export interface OrderProduct {
  kinguinId: number;
  qty: number;
  price: number;
  name: string;
  offerId?: string;
}

export interface CreateOrderRequest {
  products: OrderProduct[];
  orderExternalId?: string;
  couponCode?: string;
}

export interface OrderKey {
  serial: string;
  name: string;
  type: string;
  kinguinId: number;
}

export interface Order {
  orderId: string;
  totalPrice: number;
  status: string;
  keys?: OrderKey[];
  products?: OrderProduct[];
  createdAt?: string;
  dispatchedAt?: string;
}

export interface CreateOrderResponse {
  orderId: string;
  totalPrice: number;
  status: string;
}

export interface GetOrderResponse {
  orderId: string;
  totalPrice: number;
  status: string;
  products: Array<{
    kinguinId: number;
    name: string;
    qty: number;
    price: number;
    keys?: Array<{
      serial: string;
      type: string;
      name: string;
    }>;
  }>;
}

export interface BalanceResponse {
  balance: number;
  currency: string;
}

export interface KinguinApiError {
  error: string;
  message: string;
  statusCode: number;
}
