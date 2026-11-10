import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { formatMoney } from '../../core/format';
import { CartService } from '../../core/services/cart.service';
import { ConfigService } from '../../core/services/config.service';

@Component({
  selector: 'app-cart-page',
  imports: [RouterLink],
  template: `
    <section class="container page">
      <header class="page-header">
        <div>
          <span class="eyebrow">Tu selección</span>
          <h1>Carrito de reserva</h1>
          <p>Revisá los productos antes de completar los datos de retiro.</p>
        </div>
        <a class="btn btn-ghost" routerLink="/">Seguir comprando</a>
      </header>

      @if (cart.isEmpty()) {
        <div class="empty-state">
          <h2>Tu carrito está vacío</h2>
          <p>Agregá productos del catálogo para iniciar una reserva.</p>
          <a class="btn btn-primary" routerLink="/">Ver catálogo</a>
        </div>
      } @else {
        <div class="cart-layout">
          <div class="card cart-list">
            @for (item of cart.items(); track item.product.id) {
              <article class="cart-row">
                <div class="cart-info">
                  <span class="pill">{{ item.product.category?.name ?? 'General' }}</span>
                  <h2>{{ item.product.name }}</h2>
                  <p>{{ money(item.product.price) }} · {{ item.product.unit }}</p>
                </div>

                <div class="quantity-control" aria-label="Cantidad">
                  <button
                    type="button"
                    (click)="cart.decrement(item.product.id)"
                    [disabled]="item.quantity <= 1"
                    aria-label="Quitar una unidad"
                  >
                    −
                  </button>
                  <span>{{ item.quantity }}</span>
                  <button
                    type="button"
                    (click)="cart.increment(item.product.id)"
                    [disabled]="item.quantity >= item.product.stock"
                    aria-label="Agregar una unidad"
                  >
                    +
                  </button>
                </div>

                <strong class="line-total">
                  {{ lineTotal(item.product.price, item.quantity) }}
                </strong>

                <button
                  type="button"
                  class="remove-button"
                  (click)="cart.remove(item.product.id)"
                  aria-label="Eliminar producto"
                >
                  Eliminar
                </button>
              </article>
            }
          </div>

          <aside class="card summary-card">
            <h2>Resumen</h2>
            <dl class="summary-lines">
              <div>
                <dt>Productos</dt>
                <dd>{{ cart.count() }}</dd>
              </div>
              <div>
                <dt>Subtotal estimado</dt>
                <dd>{{ money(cart.subtotal()) }}</dd>
              </div>
              <div>
                <dt>Pago</dt>
                <dd>En el local</dd>
              </div>
            </dl>
            <p class="summary-note">
              El total final se confirma con el stock y los precios vigentes al crear la reserva.
              No se cobra nada online.
            </p>
            <a class="btn btn-primary btn-block" routerLink="/checkout">
              Continuar con la reserva
            </a>
            <div class="summary-help">
              <strong>Horario de atención</strong>
              <span>{{ config.config().store_hours }}</span>
            </div>
            <div class="summary-help">
              <strong>Retiro</strong>
              <span>
                Desde {{ config.config().min_pickup_lead_minutes }} minutos y hasta
                {{ config.config().reservation_expiration_hours }} horas.
              </span>
            </div>
          </aside>
        </div>
      }
    </section>
  `,
  styles: [
    `
      .page {
        padding-top: 2.75rem;
      }
      .page-header {
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 1rem;
        flex-wrap: wrap;
        margin-bottom: 1.75rem;
      }
      .page-header h1 {
        margin: 0.25rem 0 0.35rem;
      }
      .page-header p {
        margin: 0;
        color: var(--muted);
      }
      .cart-layout {
        display: grid;
        grid-template-columns: minmax(0, 1.6fr) minmax(17rem, 0.8fr);
        gap: 1.25rem;
        align-items: start;
      }
      .cart-list {
        padding: 0.5rem 1.1rem;
      }
      .cart-row {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto auto auto;
        align-items: center;
        gap: 1rem;
        padding: 1.1rem 0;
        border-bottom: 1px solid var(--border);
      }
      .cart-row:last-child {
        border-bottom: none;
      }
      .cart-info h2 {
        font-size: 1rem;
        margin: 0.4rem 0 0.15rem;
      }
      .cart-info p {
        margin: 0;
        color: var(--muted);
        font-size: 0.85rem;
      }
      .quantity-control {
        display: inline-flex;
        align-items: center;
        border: 1px solid var(--border);
        border-radius: 999px;
        overflow: hidden;
      }
      .quantity-control button {
        width: 2rem;
        height: 2rem;
        border: none;
        background: #fff;
        color: var(--teal-800);
        font-size: 1.1rem;
        cursor: pointer;
      }
      .quantity-control button:hover:not(:disabled) {
        background: var(--teal-50);
      }
      .quantity-control button:disabled {
        opacity: 0.35;
        cursor: not-allowed;
      }
      .quantity-control span {
        min-width: 2rem;
        text-align: center;
        font-weight: 700;
        font-size: 0.9rem;
      }
      .line-total {
        white-space: nowrap;
        color: var(--teal-900);
      }
      .remove-button {
        background: none;
        border: none;
        color: var(--muted);
        font: inherit;
        font-size: 0.8rem;
        text-decoration: underline;
        cursor: pointer;
        padding: 0.25rem;
      }
      .remove-button:hover {
        color: #b42318;
      }
      .summary-card {
        padding: 1.3rem;
        display: grid;
        gap: 1rem;
      }
      .summary-card h2 {
        margin: 0;
        font-size: 1.15rem;
      }
      .summary-lines {
        margin: 0;
        display: grid;
        gap: 0.6rem;
      }
      .summary-lines div {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        font-size: 0.92rem;
      }
      .summary-lines dt {
        color: var(--muted);
      }
      .summary-lines dd {
        margin: 0;
        font-weight: 700;
      }
      .summary-note {
        margin: 0;
        color: var(--muted);
        font-size: 0.82rem;
        line-height: 1.55;
      }
      .summary-help {
        display: grid;
        gap: 0.15rem;
        border-top: 1px solid var(--border);
        padding-top: 0.8rem;
        font-size: 0.84rem;
        color: var(--muted);
      }
      .summary-help strong {
        color: var(--ink);
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }
      @media (max-width: 900px) {
        .cart-layout {
          grid-template-columns: 1fr;
        }
        .cart-row {
          grid-template-columns: 1fr auto;
          row-gap: 0.6rem;
        }
        .line-total {
          grid-column: 1;
        }
        .remove-button {
          grid-column: 2;
          justify-self: end;
        }
      }
    `,
  ],
})
export class CartPageComponent {
  readonly cart = inject(CartService);
  readonly config = inject(ConfigService);
  readonly money = formatMoney;

  lineTotal(price: string, quantity: number): string {
    return formatMoney(Number(price) * quantity);
  }
}
