import { Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { formatDateTime, formatMoney } from '../../core/format';
import { ConfigService } from '../../core/services/config.service';
import { ReservationService } from '../../core/services/reservation.service';

@Component({
  selector: 'app-confirmation-page',
  imports: [RouterLink],
  template: `
    <section class="container page">
      @if (reservation(); as data) {
        <div class="confirmation-hero">
          <div class="success-mark" aria-hidden="true">✓</div>
          <span class="eyebrow">Reserva confirmada</span>
          <h1>¡Listo, {{ data.customer_name }}!</h1>
          <p>
            Guardá tu código. Lo vas a necesitar para retirar los productos en
            {{ config.config().store_address }}.
          </p>
          <div class="code-box">
            <span>Código de reserva</span>
            <strong>{{ data.code }}</strong>
          </div>
        </div>

        <div class="confirmation-layout">
          <div class="card detail-card">
            <div class="card-heading">
              <h2>Detalle de la reserva</h2>
              <span class="status-badge" [class]="'status-' + data.status.toLowerCase()">
                {{ statusLabel(data.status) }}
              </span>
            </div>

            <dl class="detail-grid">
              <div>
                <dt>Retiro</dt>
                <dd>{{ dateTime(data.pickup_date) }}</dd>
              </div>
              <div>
                <dt>Vence</dt>
                <dd>{{ dateTime(data.expires_at) }}</dd>
              </div>
              <div>
                <dt>Precio garantizado hasta</dt>
                <dd>{{ dateTime(data.price_guaranteed_until) }}</dd>
              </div>
              <div>
                <dt>Cliente</dt>
                <dd>{{ data.customer_name }} {{ data.customer_last_name }}</dd>
              </div>
              <div>
                <dt>Correo</dt>
                <dd>{{ data.customer_email }}</dd>
              </div>
              <div>
                <dt>Teléfono</dt>
                <dd>{{ data.customer_phone }}</dd>
              </div>
            </dl>

            <h3>Productos reservados</h3>
            <ul class="item-list">
              @for (item of data.items; track item.id) {
                <li>
                  <span>
                    <strong>{{ item.quantity }}×</strong> {{ item.product_name }}
                    <small>{{ item.product_unit }}</small>
                  </span>
                  <span>{{ money(item.line_total) }}</span>
                </li>
              }
            </ul>

            <div class="total-row">
              <span>Total a pagar en el local</span>
              <strong>{{ money(data.total_amount) }}</strong>
            </div>

            <div class="notice">
              <strong>Recordá</strong>
              <p>
                El pago se realiza únicamente en el local al retirar. Presentá el código
                {{ data.code }} y tu documento de identidad dentro del horario de atención:
                {{ config.config().store_hours }}.
              </p>
            </div>
          </div>

          <aside class="card actions-card">
            <h2>Próximos pasos</h2>
            <ol class="steps">
              <li>Guardá o imprimí este código.</li>
              <li>Acercate al local en el horario elegido.</li>
              <li>Presentá el código y pagá en el local.</li>
            </ol>

            @if (data.whatsapp_url) {
              <a
                class="btn btn-whatsapp btn-block"
                [href]="data.whatsapp_url"
                target="_blank"
                rel="noopener"
              >
                Enviar pedido por WhatsApp
              </a>
              <p class="actions-note">
                Se abrirá WhatsApp con el mensaje de tu reserva. El envío es manual: revisá y
                enviá el mensaje desde tu teléfono.
              </p>
            }

            <a class="btn btn-primary btn-block" [routerLink]="['/consulta']">
              Consultar o cancelar reserva
            </a>
            <a class="btn btn-ghost btn-block" routerLink="/">Volver al catálogo</a>
            <button type="button" class="btn btn-ghost btn-block" (click)="print()">
              Imprimir comprobante
            </button>
          </aside>
        </div>
      } @else {
        <div class="empty-state">
          <h2>No encontramos esta reserva en esta sesión</h2>
          <p>
            Por seguridad, el comprobante se guarda solo en el navegador donde se creó la reserva.
            Podés consultarla con tu código y correo electrónico.
          </p>
          <a class="btn btn-primary" routerLink="/consulta">Consultar reserva</a>
        </div>
      }
    </section>
  `,
  styles: [
    `
      .page {
        padding-top: 2.5rem;
      }
      .confirmation-hero {
        text-align: center;
        max-width: 44rem;
        margin: 0 auto 2rem;
        display: grid;
        justify-items: center;
      }
      .success-mark {
        display: grid;
        place-items: center;
        width: 4rem;
        height: 4rem;
        border-radius: 50%;
        background: #eaf7cf;
        color: #3f6212;
        font-size: 2rem;
        font-weight: 800;
        margin-bottom: 1rem;
      }
      .confirmation-hero h1 {
        margin: 0.3rem 0 0.5rem;
      }
      .confirmation-hero p {
        color: var(--muted);
        line-height: 1.7;
        margin: 0 0 1.25rem;
      }
      .code-box {
        display: grid;
        gap: 0.2rem;
        background: var(--teal-950);
        color: #fff;
        border-radius: 0.9rem;
        padding: 0.8rem 1.5rem;
      }
      .code-box span {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: #9fc2bc;
      }
      .code-box strong {
        font-size: 1.6rem;
        letter-spacing: 0.12em;
      }
      .confirmation-layout {
        display: grid;
        grid-template-columns: minmax(0, 1.6fr) minmax(16rem, 0.7fr);
        gap: 1.25rem;
        align-items: start;
      }
      .detail-card {
        padding: 1.4rem;
      }
      .card-heading {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
      }
      .card-heading h2 {
        margin: 0;
        font-size: 1.2rem;
      }
      .detail-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
        margin: 1.25rem 0;
      }
      .detail-grid dt {
        color: var(--muted);
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.2rem;
      }
      .detail-grid dd {
        margin: 0;
        font-size: 0.9rem;
        font-weight: 600;
        overflow-wrap: anywhere;
      }
      .detail-card h3 {
        font-size: 0.95rem;
        margin: 1.25rem 0 0.6rem;
      }
      .item-list {
        list-style: none;
        margin: 0;
        padding: 0;
        display: grid;
        gap: 0.6rem;
      }
      .item-list li {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        border-bottom: 1px solid var(--border);
        padding-bottom: 0.6rem;
        font-size: 0.9rem;
        color: var(--muted);
      }
      .item-list li:last-child {
        border-bottom: none;
        padding-bottom: 0;
      }
      .item-list strong {
        color: var(--ink);
      }
      .item-list small {
        display: block;
        font-size: 0.75rem;
      }
      .total-row {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 1rem;
        border-top: 1px solid var(--border);
        padding-top: 1rem;
        margin-top: 1rem;
      }
      .total-row span {
        font-weight: 700;
      }
      .total-row strong {
        font-size: 1.35rem;
        color: var(--teal-900);
      }
      .notice {
        margin-top: 1.25rem;
        background: var(--teal-50);
        border-radius: 0.8rem;
        padding: 0.9rem 1rem;
      }
      .notice strong {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--teal-800);
      }
      .notice p {
        margin: 0.35rem 0 0;
        color: var(--teal-900);
        font-size: 0.86rem;
        line-height: 1.6;
      }
      .actions-card {
        padding: 1.3rem;
        display: grid;
        gap: 0.75rem;
      }
      .actions-card h2 {
        margin: 0;
        font-size: 1.15rem;
      }
      .steps {
        margin: 0 0 0.5rem;
        padding-left: 1.1rem;
        color: var(--muted);
        font-size: 0.86rem;
        line-height: 1.7;
      }
      .actions-note {
        margin: 0;
        color: var(--muted);
        font-size: 0.78rem;
        line-height: 1.5;
      }
      @media (max-width: 900px) {
        .confirmation-layout {
          grid-template-columns: 1fr;
        }
        .detail-grid {
          grid-template-columns: 1fr;
        }
      }
    `,
  ],
})
export class ConfirmationPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly reservations = inject(ReservationService);

  readonly config = inject(ConfigService);
  readonly money = formatMoney;
  readonly dateTime = formatDateTime;

  private readonly code = signal(this.route.snapshot.paramMap.get('code') ?? '');
  readonly reservation = computed(() => {
    const reservation = this.reservations.lastReservation();
    return reservation && reservation.code === this.code() ? reservation : null;
  });

  statusLabel(status: string): string {
    const labels: Record<string, string> = {
      PENDIENTE: 'Pendiente',
      CONFIRMADO: 'Confirmada',
      RETIRADO: 'Retirada',
      CANCELADO: 'Cancelada',
    };
    return labels[status] ?? status;
  }

  print(): void {
    window.print();
  }
}
