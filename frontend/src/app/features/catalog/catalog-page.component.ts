import { Component, OnInit, inject, signal } from '@angular/core';

import { formatMoney } from '../../core/format';
import { Category, Page, Product } from '../../core/models';
import { CartService } from '../../core/services/cart.service';
import { CatalogService } from '../../core/services/catalog.service';
import { ConfigService } from '../../core/services/config.service';
import { ToastService } from '../../core/services/toast.service';

@Component({
  selector: 'app-catalog-page',
  template: `
    <section class="hero">
      <div class="container hero-inner">
        <div class="hero-copy">
          <span class="eyebrow">Reservá online · Retirá en el local</span>
          <h1>Productos de limpieza, listos para retirar.</h1>
          <p>
            Elegí lo que necesitás, reservá en minutos y pasá a buscarlo por
            {{ config.config().store_address }}. El pago se realiza en el local.
          </p>
          <div class="hero-chips">
            <span>Sin pago online</span>
            <span>Precio garantizado {{ config.config().reservation_expiration_hours }} h</span>
            <span>Retiro desde {{ config.config().min_pickup_lead_minutes }} min</span>
          </div>
        </div>
        <div class="hero-card">
          <h2>¿Cómo funciona?</h2>
          <ol>
            <li><span>1</span> Agregá productos al carrito.</li>
            <li><span>2</span> Elegí día y horario de retiro.</li>
            <li><span>3</span> Recibí tu código CC-XXXXXX.</li>
            <li><span>4</span> Pagá y retirá en el local.</li>
          </ol>
        </div>
      </div>
    </section>

    <section class="container catalog">
      <div class="catalog-toolbar">
        <div class="search-field">
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="1.8" />
            <path d="m20 20-3.5-3.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
          </svg>
          <input
            type="search"
            placeholder="Buscar por nombre o descripción"
            [value]="search()"
            (input)="onSearch($any($event.target).value)"
            aria-label="Buscar productos"
          />
        </div>
        <div class="toolbar-meta">
          @if (result(); as pageResult) {
            <span>{{ pageResult.total }} productos</span>
          }
        </div>
      </div>

      <div class="chip-row" role="group" aria-label="Filtrar por categoría">
        <button
          type="button"
          class="chip"
          [class.active]="category() === ''"
          (click)="selectCategory('')"
        >
          Todos
        </button>
        @for (item of categories(); track item.id) {
          <button
            type="button"
            class="chip"
            [class.active]="category() === item.slug"
            (click)="selectCategory(item.slug)"
          >
            {{ item.name }}
          </button>
        }
      </div>

      @if (error(); as message) {
        <div class="alert alert-error">{{ message }}</div>
      }

      @if (loading()) {
        <div class="product-grid" aria-busy="true">
          @for (placeholder of [1, 2, 3, 4, 5, 6]; track placeholder) {
            <div class="product-card skeleton-card"></div>
          }
        </div>
      } @else if (result(); as pageResult) {
        @if (pageResult.items.length === 0) {
          <div class="empty-state">
            <h2>No encontramos productos</h2>
            <p>Probá con otra búsqueda o quitá el filtro de categoría.</p>
            <button type="button" class="btn btn-primary" (click)="clearFilters()">
              Ver todos los productos
            </button>
          </div>
        } @else {
          <div class="product-grid">
            @for (product of pageResult.items; track product.id) {
              <article class="product-card">
                <div class="product-top">
                  <span class="pill">{{ product.category?.name ?? 'General' }}</span>
                  <span class="stock-pill" [class.low]="product.stock > 0 && product.stock <= 5">
                    {{ product.stock > 0 ? product.stock + ' disponibles' : 'Sin stock' }}
                  </span>
                </div>
                <h2>{{ product.name }}</h2>
                <p class="product-description">{{ product.description }}</p>
                <div class="product-price-row">
                  <strong>{{ money(product.price) }}</strong>
                  <span>por {{ product.unit }}</span>
                </div>
                <div class="product-footer">
                  @if (cart.quantityFor(product.id) > 0) {
                    <span class="in-cart">En carrito: {{ cart.quantityFor(product.id) }}</span>
                  } @else {
                    <span class="muted-note">Retiro en el local</span>
                  }
                  <button
                    type="button"
                    class="btn btn-primary btn-sm"
                    [disabled]="product.stock === 0"
                    (click)="addToCart(product)"
                  >
                    {{ product.stock === 0 ? 'Sin stock' : 'Agregar' }}
                  </button>
                </div>
              </article>
            }
          </div>

          @if (pageResult.pages > 1) {
            <nav class="pagination" aria-label="Paginación de productos">
              <button
                type="button"
                class="btn btn-ghost btn-sm"
                [disabled]="page() <= 1"
                (click)="goToPage(page() - 1)"
              >
                Anterior
              </button>
              <span>Página {{ pageResult.page }} de {{ pageResult.pages }}</span>
              <button
                type="button"
                class="btn btn-ghost btn-sm"
                [disabled]="page() >= pageResult.pages"
                (click)="goToPage(page() + 1)"
              >
                Siguiente
              </button>
            </nav>
          }
        }
      }
    </section>
  `,
  styles: [
    `
      .hero {
        background:
          radial-gradient(circle at 12% 10%, rgba(56, 189, 166, 0.18), transparent 45%),
          radial-gradient(circle at 88% 0%, rgba(190, 242, 100, 0.18), transparent 40%),
          linear-gradient(160deg, #f3fbf9 0%, #eef7f4 55%, #f8fbf3 100%);
        border-bottom: 1px solid var(--border);
      }
      .hero-inner {
        display: grid;
        grid-template-columns: 1.35fr 1fr;
        gap: 3rem;
        align-items: center;
        padding-top: 3.5rem;
        padding-bottom: 3.5rem;
      }
      .hero h1 {
        font-size: clamp(2.1rem, 4.2vw, 3.4rem);
        line-height: 1.05;
        margin: 0.6rem 0 1rem;
        max-width: 15ch;
      }
      .hero-copy p {
        color: var(--muted);
        font-size: 1.05rem;
        line-height: 1.7;
        max-width: 34rem;
      }
      .hero-chips {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-top: 1.4rem;
      }
      .hero-chips span {
        background: #fff;
        border: 1px solid var(--border);
        color: var(--teal-800);
        border-radius: 999px;
        padding: 0.4rem 0.75rem;
        font-size: 0.8rem;
        font-weight: 600;
      }
      .hero-card {
        background: #fff;
        border: 1px solid var(--border);
        border-radius: 1.25rem;
        padding: 1.5rem;
        box-shadow: var(--shadow-md);
      }
      .hero-card h2 {
        font-size: 1rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: var(--teal-700);
        margin: 0 0 1rem;
      }
      .hero-card ol {
        list-style: none;
        margin: 0;
        padding: 0;
        display: grid;
        gap: 0.8rem;
      }
      .hero-card li {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        color: var(--muted);
        font-size: 0.92rem;
      }
      .hero-card li span {
        display: grid;
        place-items: center;
        width: 1.7rem;
        height: 1.7rem;
        border-radius: 50%;
        background: var(--teal-50);
        color: var(--teal-700);
        font-weight: 800;
        font-size: 0.8rem;
      }
      .catalog {
        padding-top: 2.5rem;
      }
      .catalog-toolbar {
        display: flex;
        gap: 1rem;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
      }
      .search-field {
        flex: 1 1 22rem;
        display: flex;
        align-items: center;
        gap: 0.6rem;
        background: #fff;
        border: 1px solid var(--border);
        border-radius: 0.85rem;
        padding: 0.7rem 0.9rem;
        color: var(--muted);
        box-shadow: var(--shadow-sm);
      }
      .search-field input {
        border: none;
        outline: none;
        width: 100%;
        font: inherit;
        color: var(--ink);
        background: transparent;
      }
      .toolbar-meta {
        color: var(--muted);
        font-size: 0.85rem;
      }
      .chip-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin: 1.1rem 0 2rem;
      }
      .chip {
        border: 1px solid var(--border);
        background: #fff;
        color: var(--muted);
        border-radius: 999px;
        padding: 0.45rem 0.9rem;
        font: inherit;
        font-size: 0.85rem;
        font-weight: 600;
        cursor: pointer;
      }
      .chip:hover {
        border-color: var(--teal-300);
        color: var(--teal-700);
      }
      .chip.active {
        background: var(--teal-700);
        border-color: var(--teal-700);
        color: #fff;
      }
      .product-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(15.5rem, 1fr));
        gap: 1.1rem;
      }
      .product-card {
        display: flex;
        flex-direction: column;
        background: #fff;
        border: 1px solid var(--border);
        border-radius: 1rem;
        padding: 1.1rem;
        box-shadow: var(--shadow-sm);
        transition: transform 0.16s ease, box-shadow 0.16s ease;
      }
      .product-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
      }
      .product-top {
        display: flex;
        justify-content: space-between;
        gap: 0.5rem;
        align-items: center;
      }
      .product-card h2 {
        font-size: 1.02rem;
        margin: 0.8rem 0 0.35rem;
        letter-spacing: -0.01em;
      }
      .product-description {
        color: var(--muted);
        font-size: 0.85rem;
        line-height: 1.55;
        margin: 0 0 1rem;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        min-height: 2.6rem;
      }
      .product-price-row {
        display: flex;
        align-items: baseline;
        gap: 0.4rem;
        margin-top: auto;
      }
      .product-price-row strong {
        font-size: 1.2rem;
        color: var(--teal-900);
        letter-spacing: -0.02em;
      }
      .product-price-row span {
        color: var(--muted);
        font-size: 0.8rem;
      }
      .product-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.5rem;
        margin-top: 1rem;
        padding-top: 0.85rem;
        border-top: 1px solid var(--border);
      }
      .in-cart {
        color: var(--teal-700);
        font-size: 0.8rem;
        font-weight: 700;
      }
      .muted-note {
        color: var(--muted);
        font-size: 0.78rem;
      }
      .stock-pill.low {
        background: #fff4e5;
        color: #9a5b00;
      }
      .skeleton-card {
        min-height: 17rem;
        background: linear-gradient(90deg, #f2f6f5 25%, #e8efed 50%, #f2f6f5 75%);
        background-size: 200% 100%;
        animation: shimmer 1.2s infinite;
      }
      @keyframes shimmer {
        from {
          background-position: 200% 0;
        }
        to {
          background-position: -200% 0;
        }
      }
      .pagination {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 1rem;
        margin-top: 2rem;
        color: var(--muted);
        font-size: 0.85rem;
      }
      @media (max-width: 860px) {
        .hero-inner {
          grid-template-columns: 1fr;
          gap: 1.75rem;
          padding-top: 2.5rem;
          padding-bottom: 2.5rem;
        }
      }
    `,
  ],
})
export class CatalogPageComponent implements OnInit {
  private readonly catalog = inject(CatalogService);
  private readonly cartService = inject(CartService);
  private readonly toast = inject(ToastService);
  private searchTimer: ReturnType<typeof setTimeout> | undefined;

  readonly config = inject(ConfigService);
  readonly cart = this.cartService;
  readonly money = formatMoney;

  readonly categories = signal<Category[]>([]);
  readonly result = signal<Page<Product> | null>(null);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly search = signal('');
  readonly category = signal('');
  readonly page = signal(1);

  ngOnInit(): void {
    void this.loadCategories();
    void this.loadProducts();
  }

  onSearch(value: string): void {
    this.search.set(value);
    this.page.set(1);
    if (this.searchTimer) {
      clearTimeout(this.searchTimer);
    }
    this.searchTimer = setTimeout(() => void this.loadProducts(), 300);
  }

  selectCategory(slug: string): void {
    this.category.set(slug);
    this.page.set(1);
    void this.loadProducts();
  }

  clearFilters(): void {
    this.search.set('');
    this.category.set('');
    this.page.set(1);
    void this.loadProducts();
  }

  goToPage(page: number): void {
    this.page.set(page);
    void this.loadProducts();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  addToCart(product: Product): void {
    const result = this.cart.add(product);
    if (result.ok) {
      this.toast.success(result.message);
    } else {
      this.toast.error(result.message);
    }
  }

  private async loadCategories(): Promise<void> {
    try {
      this.categories.set(await this.catalog.loadCategories());
    } catch {
      this.categories.set([]);
    }
  }

  private async loadProducts(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      const result = await this.catalog.listProducts({
        search: this.search(),
        category: this.category(),
        page: this.page(),
        pageSize: 12,
      });
      this.result.set(result);
    } catch {
      this.error.set('No pudimos cargar el catálogo. Revisá tu conexión e intentá nuevamente.');
      this.result.set(null);
    } finally {
      this.loading.set(false);
    }
  }
}
