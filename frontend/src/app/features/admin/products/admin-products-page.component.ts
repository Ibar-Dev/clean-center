import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { formatMoney, parseApiError } from '../../../core/format';
import { Category, Page, Product } from '../../../core/models';
import { AdminService } from '../../../core/services/admin.service';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-admin-products-page',
  imports: [ReactiveFormsModule],
  template: `
    <section class="container admin-page">
      <header class="admin-page-header">
        <div>
          <span class="eyebrow">Catálogo</span>
          <h1>Productos</h1>
          <p>Creá, editá y archivá productos. Los cambios se reflejan en la tienda.</p>
        </div>
        <button type="button" class="btn btn-primary" (click)="openCreate()">
          + Nuevo producto
        </button>
      </header>

      @if (formOpen()) {
        <form class="card product-form" [formGroup]="form" (ngSubmit)="save()" novalidate>
          <div class="form-heading">
            <h2>{{ editingId() ? 'Editar producto' : 'Nuevo producto' }}</h2>
            <button type="button" class="btn btn-ghost btn-sm" (click)="closeForm()">
              Cancelar
            </button>
          </div>

          <div class="form-grid">
            <label class="field">
              <span>Nombre *</span>
              <input type="text" formControlName="name" maxlength="160" />
              @if (showError('name')) {
                <small class="field-error">Ingresá un nombre de al menos 2 caracteres.</small>
              }
            </label>
            <label class="field">
              <span>Categoría *</span>
              <select formControlName="category_id">
                @for (category of categories(); track category.id) {
                  <option [value]="category.id">{{ category.name }}</option>
                }
              </select>
            </label>
            <label class="field">
              <span>Precio (ARS) *</span>
              <input type="number" formControlName="price" min="0.01" step="0.01" />
              @if (showError('price')) {
                <small class="field-error">Ingresá un precio mayor a cero.</small>
              }
            </label>
            <label class="field">
              <span>Unidad *</span>
              <input type="text" formControlName="unit" placeholder="500 ml, 1 Litro, Unidad" />
              @if (showError('unit')) {
                <small class="field-error">Ingresá la unidad de venta.</small>
              }
            </label>
            <label class="field">
              <span>Stock *</span>
              <input type="number" formControlName="stock" min="0" step="1" />
              @if (showError('stock')) {
                <small class="field-error">El stock no puede ser negativo.</small>
              }
            </label>
            <label class="check-field">
              <input type="checkbox" formControlName="is_active" />
              <span>Producto visible en el catálogo</span>
            </label>
          </div>

          <label class="field">
            <span>Descripción</span>
            <textarea formControlName="description" rows="3" maxlength="2000"></textarea>
          </label>

          @if (formError(); as message) {
            <div class="alert alert-error">{{ message }}</div>
          }

          <div class="form-actions">
            <button type="submit" class="btn btn-primary" [disabled]="saving()">
              {{ saving() ? 'Guardando…' : editingId() ? 'Guardar cambios' : 'Crear producto' }}
            </button>
          </div>
        </form>
      }

      <div class="filters card">
        <label class="field">
          <span>Buscar</span>
          <input
            type="search"
            placeholder="Nombre del producto"
            [value]="search()"
            (input)="onSearch($any($event.target).value)"
          />
        </label>
        <label class="check-field filter-check">
          <input
            type="checkbox"
            [checked]="includeInactive()"
            (change)="onIncludeInactive($any($event.target).checked)"
          />
          <span>Incluir productos archivados</span>
        </label>
        @if (result(); as pageResult) {
          <span class="filters-count">{{ pageResult.total }} productos</span>
        }
      </div>

      @if (error(); as message) {
        <div class="alert alert-error">{{ message }}</div>
      }

      <div class="card table-card">
        @if (loading()) {
          <p class="loading-note">Cargando productos…</p>
        } @else if (result(); as pageResult) {
          @if (pageResult.items.length === 0) {
            <div class="empty-state compact">
              <h2>No hay productos</h2>
              <p>Creá el primero o ajustá la búsqueda.</p>
            </div>
          } @else {
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Producto</th>
                    <th>Categoría</th>
                    <th>Precio</th>
                    <th>Stock</th>
                    <th>Estado</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  @for (product of pageResult.items; track product.id) {
                    <tr>
                      <td>
                        <span class="cell-main">{{ product.name }}</span>
                        <span class="cell-sub">{{ product.unit }}</span>
                      </td>
                      <td>{{ product.category?.name ?? '—' }}</td>
                      <td>{{ money(product.price) }}</td>
                      <td>{{ product.stock }}</td>
                      <td>
                        <span
                          class="status-badge"
                          [class.status-confirmado]="product.is_active"
                          [class.status-cancelado]="!product.is_active"
                        >
                          {{ product.is_active ? 'Activo' : 'Archivado' }}
                        </span>
                      </td>
                      <td class="cell-action">
                        <div class="row-actions">
                          <button
                            type="button"
                            class="btn btn-ghost btn-sm"
                            (click)="openEdit(product)"
                          >
                            Editar
                          </button>
                          <button
                            type="button"
                            class="btn btn-ghost btn-sm"
                            [disabled]="togglingId() === product.id"
                            (click)="toggleActive(product)"
                          >
                            {{ product.is_active ? 'Archivar' : 'Activar' }}
                          </button>
                        </div>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
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
      </div>
    </section>
  `,
  styles: [
    `
      .admin-page {
        padding-top: 2.25rem;
      }
      .admin-page-header {
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 1rem;
        flex-wrap: wrap;
        margin-bottom: 1.5rem;
      }
      .admin-page-header h1 {
        margin: 0.2rem 0 0.3rem;
      }
      .admin-page-header p {
        margin: 0;
        color: var(--muted);
      }
      .product-form {
        padding: 1.25rem;
        margin-bottom: 1rem;
        display: grid;
        gap: 1rem;
        border-left: 4px solid var(--teal-500);
      }
      .form-heading {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
      }
      .form-heading h2 {
        margin: 0;
        font-size: 1.1rem;
      }
      .form-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.9rem;
      }
      .filter-check {
        padding-bottom: 0.6rem;
      }
      .form-actions {
        display: flex;
        justify-content: flex-end;
      }
      .filters {
        display: flex;
        align-items: flex-end;
        gap: 1rem;
        flex-wrap: wrap;
        padding: 1rem;
        margin-bottom: 1rem;
      }
      .filters .field {
        min-width: 14rem;
        flex: 1 1 14rem;
      }
      .filters-count {
        color: var(--muted);
        font-size: 0.85rem;
        padding-bottom: 0.65rem;
      }
      .table-card {
        padding: 0.5rem;
      }
      .table-wrap {
        overflow-x: auto;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.88rem;
      }
      th,
      td {
        text-align: left;
        padding: 0.8rem 0.75rem;
        border-bottom: 1px solid var(--border);
        vertical-align: middle;
      }
      th {
        color: var(--muted);
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.09em;
        white-space: nowrap;
      }
      tbody tr:hover {
        background: var(--surface-alt);
      }
      tbody tr:last-child td {
        border-bottom: none;
      }
      .cell-main {
        display: block;
        font-weight: 600;
      }
      .cell-sub {
        display: block;
        color: var(--muted);
        font-size: 0.78rem;
      }
      .cell-action {
        text-align: right;
      }
      .row-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.3rem;
        flex-wrap: wrap;
      }
      .loading-note {
        padding: 2rem;
        text-align: center;
        color: var(--muted);
      }
      .pagination {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 1rem;
        padding: 1rem;
        color: var(--muted);
        font-size: 0.85rem;
      }
      .check-field {
        display: flex;
        gap: 0.55rem;
        align-items: center;
        font-size: 0.85rem;
        color: var(--muted);
      }
      .check-field input {
        accent-color: var(--teal-700);
      }
      @media (max-width: 900px) {
        .form-grid {
          grid-template-columns: 1fr 1fr;
        }
      }
      @media (max-width: 620px) {
        .form-grid {
          grid-template-columns: 1fr;
        }
      }
    `,
  ],
})
export class AdminProductsPageComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly admin = inject(AdminService);
  private readonly toast = inject(ToastService);

  readonly money = formatMoney;
  readonly result = signal<Page<Product> | null>(null);
  readonly categories = signal<Category[]>([]);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly search = signal('');
  readonly includeInactive = signal(true);
  readonly page = signal(1);
  readonly formOpen = signal(false);
  readonly editingId = signal<number | null>(null);
  readonly saving = signal(false);
  readonly formError = signal<string | null>(null);
  readonly togglingId = signal<number | null>(null);

  private searchTimer: ReturnType<typeof setTimeout> | undefined;

  readonly form = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(160)]],
    description: ['', [Validators.maxLength(2000)]],
    price: ['', [Validators.required, Validators.pattern(/^\d+(\.\d{1,2})?$/)]],
    unit: ['', [Validators.required, Validators.maxLength(60)]],
    stock: [0, [Validators.required, Validators.min(0)]],
    category_id: [0, [Validators.required, Validators.min(1)]],
    is_active: [true],
  });

  ngOnInit(): void {
    void this.loadCategories();
    void this.load();
  }

  onSearch(value: string): void {
    this.search.set(value);
    this.page.set(1);
    if (this.searchTimer) {
      clearTimeout(this.searchTimer);
    }
    this.searchTimer = setTimeout(() => void this.load(), 300);
  }

  onIncludeInactive(value: boolean): void {
    this.includeInactive.set(value);
    this.page.set(1);
    void this.load();
  }

  goToPage(page: number): void {
    this.page.set(page);
    void this.load();
  }

  openCreate(): void {
    this.editingId.set(null);
    this.formError.set(null);
    this.form.reset({
      name: '',
      description: '',
      price: '',
      unit: '',
      stock: 0,
      category_id: this.categories()[0]?.id ?? 0,
      is_active: true,
    });
    this.formOpen.set(true);
  }

  openEdit(product: Product): void {
    this.editingId.set(product.id);
    this.formError.set(null);
    this.form.reset({
      name: product.name,
      description: product.description,
      price: product.price,
      unit: product.unit,
      stock: product.stock,
      category_id: product.category_id,
      is_active: product.is_active,
    });
    this.formOpen.set(true);
  }

  closeForm(): void {
    this.formOpen.set(false);
    this.editingId.set(null);
    this.formError.set(null);
  }

  showError(controlName: 'name' | 'price' | 'unit' | 'stock' | 'category_id'): boolean {
    const control = this.form.controls[controlName];
    return control.invalid && (control.dirty || control.touched);
  }

  async save(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const value = this.form.getRawValue();
    if (Number(value.price) <= 0) {
      this.formError.set('El precio debe ser mayor a cero.');
      return;
    }

    this.saving.set(true);
    this.formError.set(null);
    const payload = {
      name: value.name.trim(),
      description: value.description.trim(),
      price: value.price,
      unit: value.unit.trim(),
      stock: Number(value.stock),
      category_id: Number(value.category_id),
      is_active: value.is_active,
    };

    try {
      const editingId = this.editingId();
      if (editingId) {
        await this.admin.updateProduct(editingId, payload);
        this.toast.success('Producto actualizado.');
      } else {
        await this.admin.createProduct(payload);
        this.toast.success('Producto creado.');
      }
      this.closeForm();
      await this.load();
    } catch (error) {
      this.formError.set(parseApiError(error));
    } finally {
      this.saving.set(false);
    }
  }

  async toggleActive(product: Product): Promise<void> {
    const next = !product.is_active;
    if (
      !next &&
      !window.confirm(`¿Archivar "${product.name}"? Dejará de mostrarse en el catálogo público.`)
    ) {
      return;
    }

    this.togglingId.set(product.id);
    try {
      await this.admin.setProductStatus(product.id, next);
      this.toast.success(next ? 'Producto activado.' : 'Producto archivado.');
      await this.load();
    } catch (error) {
      this.toast.error(parseApiError(error));
    } finally {
      this.togglingId.set(null);
    }
  }

  private async loadCategories(): Promise<void> {
    try {
      const categories = await this.admin.listCategories();
      this.categories.set(categories);
      if (this.form.controls.category_id.value === 0 && categories.length) {
        this.form.controls.category_id.setValue(categories[0].id);
      }
    } catch {
      this.categories.set([]);
    }
  }

  private async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      const result = await this.admin.listProducts({
        search: this.search(),
        includeInactive: this.includeInactive(),
        page: this.page(),
        pageSize: 20,
      });
      this.result.set(result);
    } catch (error) {
      this.error.set(parseApiError(error));
    } finally {
      this.loading.set(false);
    }
  }
}
