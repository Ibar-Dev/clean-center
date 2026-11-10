import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import {
  AdminProductPayload,
  Category,
  Page,
  Product,
  Reservation,
  ReservationStatus,
  ReservationStatusUpdate,
  ReservationSummary,
} from '../models';

export interface AdminReservationQuery {
  status?: ReservationStatus | '';
  search?: string;
  page?: number;
  pageSize?: number;
}

export interface AdminProductQuery {
  search?: string;
  categoryId?: number | null;
  includeInactive?: boolean;
  page?: number;
  pageSize?: number;
}

@Injectable({ providedIn: 'root' })
export class AdminService {
  private readonly http = inject(HttpClient);

  listReservations(query: AdminReservationQuery = {}): Promise<Page<ReservationSummary>> {
    let params = new HttpParams()
      .set('page', query.page ?? 1)
      .set('page_size', query.pageSize ?? 20);

    if (query.status) {
      params = params.set('status', query.status);
    }
    if (query.search?.trim()) {
      params = params.set('search', query.search.trim());
    }

    return firstValueFrom(
      this.http.get<Page<ReservationSummary>>('/api/admin/reservations', { params }),
    );
  }

  getReservation(id: number): Promise<Reservation> {
    return firstValueFrom(this.http.get<Reservation>(`/api/admin/reservations/${id}`));
  }

  updateReservationStatus(
    id: number,
    payload: ReservationStatusUpdate,
  ): Promise<Reservation> {
    return firstValueFrom(
      this.http.patch<Reservation>(`/api/admin/reservations/${id}/status`, payload),
    );
  }

  listProducts(query: AdminProductQuery = {}): Promise<Page<Product>> {
    let params = new HttpParams()
      .set('page', query.page ?? 1)
      .set('page_size', query.pageSize ?? 20)
      .set('include_inactive', query.includeInactive ?? true);

    if (query.search?.trim()) {
      params = params.set('search', query.search.trim());
    }
    if (query.categoryId) {
      params = params.set('category_id', query.categoryId);
    }

    return firstValueFrom(this.http.get<Page<Product>>('/api/admin/products', { params }));
  }

  listCategories(): Promise<Category[]> {
    return firstValueFrom(this.http.get<Category[]>('/api/admin/categories'));
  }

  createProduct(payload: AdminProductPayload): Promise<Product> {
    return firstValueFrom(this.http.post<Product>('/api/admin/products', payload));
  }

  updateProduct(id: number, payload: Partial<AdminProductPayload>): Promise<Product> {
    return firstValueFrom(this.http.patch<Product>(`/api/admin/products/${id}`, payload));
  }

  setProductStatus(id: number, isActive: boolean): Promise<Product> {
    return firstValueFrom(
      this.http.patch<Product>(`/api/admin/products/${id}/status`, { is_active: isActive }),
    );
  }
}
