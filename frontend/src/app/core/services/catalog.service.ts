import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { Category, Page, Product } from '../models';

export interface CatalogQuery {
  search?: string;
  category?: string;
  page?: number;
  pageSize?: number;
}

@Injectable({ providedIn: 'root' })
export class CatalogService {
  private readonly http = inject(HttpClient);

  readonly categories = signal<Category[]>([]);
  readonly categoriesLoaded = signal(false);

  async loadCategories(force = false): Promise<Category[]> {
    if (this.categoriesLoaded() && !force) {
      return this.categories();
    }
    const categories = await firstValueFrom(this.http.get<Category[]>('/api/categories'));
    this.categories.set(categories);
    this.categoriesLoaded.set(true);
    return categories;
  }

  listProducts(query: CatalogQuery = {}): Promise<Page<Product>> {
    let params = new HttpParams()
      .set('page', query.page ?? 1)
      .set('page_size', query.pageSize ?? 12);

    if (query.search?.trim()) {
      params = params.set('search', query.search.trim());
    }
    if (query.category?.trim()) {
      params = params.set('category', query.category.trim());
    }

    return firstValueFrom(this.http.get<Page<Product>>('/api/products', { params }));
  }

  getProduct(id: number): Promise<Product> {
    return firstValueFrom(this.http.get<Product>(`/api/products/${id}`));
  }
}
