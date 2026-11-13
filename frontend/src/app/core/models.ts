export interface AppConfig {
  store_name: string;
  store_legal_name: string;
  store_cuit: string;
  store_address: string;
  store_phone: string;
  store_email: string;
  store_hours: string;
  reservation_expiration_hours: number;
  min_pickup_lead_minutes: number;
  aaip_url: string;
  terms_version: string;
  privacy_version: string;
  whatsapp_available: boolean;
}

export interface Category {
  id: number;
  name: string;
  slug: string;
}

export interface Product {
  id: number;
  name: string;
  description: string;
  price: string;
  unit: string;
  stock: number;
  category_id: number;
  category: Category | null;
  is_active: boolean;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export type ReservationStatus = 'PENDIENTE' | 'CONFIRMADO' | 'RETIRADO' | 'CANCELADO';

export interface ReservationItem {
  id: number;
  product_id: number;
  product_name: string;
  product_unit: string;
  quantity: number;
  unit_price: string;
  line_total: string;
}

export interface Reservation {
  id: number;
  code: string;
  customer_name: string;
  customer_last_name: string;
  customer_email: string;
  customer_phone: string;
  pickup_date: string;
  status: ReservationStatus;
  total_amount: string;
  created_at: string;
  expires_at: string;
  price_guaranteed_until: string;
  terms_version: string;
  privacy_version: string;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  items: ReservationItem[];
  whatsapp_url: string | null;
}

export interface ReservationSummary {
  id: number;
  code: string;
  customer_name: string;
  customer_last_name: string;
  customer_email: string;
  customer_phone: string;
  pickup_date: string;
  status: ReservationStatus;
  total_amount: string;
  created_at: string;
  expires_at: string;
  item_count: number;
}

export interface User {
  id: number;
  username: string;
  role: 'ADMIN' | 'STAFF';
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface CartItem {
  product: Product;
  quantity: number;
}

export interface ReservationCreatePayload {
  customer_name: string;
  customer_last_name: string;
  customer_email: string;
  customer_phone: string;
  pickup_date: string;
  items: { product_id: number; quantity: number }[];
  terms_accepted: boolean;
  privacy_consent: boolean;
  idempotency_key?: string;
}

export interface ReservationStatusUpdate {
  status: ReservationStatus;
  reason?: string;
}

export interface AdminProductPayload {
  name: string;
  description: string;
  price: string;
  unit: string;
  stock: number;
  category_id: number;
  is_active?: boolean;
}

export const STATUS_LABELS: Record<ReservationStatus, string> = {
  PENDIENTE: 'Pendiente',
  CONFIRMADO: 'Confirmada',
  RETIRADO: 'Retirada',
  CANCELADO: 'Cancelada',
};

export const NEXT_STATUSES: Record<ReservationStatus, ReservationStatus[]> = {
  PENDIENTE: ['CONFIRMADO', 'CANCELADO'],
  CONFIRMADO: ['RETIRADO', 'CANCELADO'],
  RETIRADO: [],
  CANCELADO: [],
};
