import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { formatDateTime, formatMoney, parseApiError } from '../../core/format';
import { Reservation, STATUS_LABELS } from '../../core/models';
import { ConfigService } from '../../core/services/config.service';
import { ReservationService } from '../../core/services/reservation.service';
import { ToastService } from '../../core/services/toast.service';

@Component({
  selector: 'app-lookup-page',
  imports: [ReactiveFormsModule, RouterLink],
  template: `
    <section class="container page">
      <header class="page-header">
        <div>
          <span class="eyebrow">{{ isArrepentimiento() ? 'Derecho del consumidor' : 'Consulta' }}</span>
          <h1>
            {{ isArrepentimiento() ? 'Botón de Arrepentimiento' : 'Consultar tu reserva' }}
          </h1>
          <p>
            @if (isArrepentimiento()) {
              Podés cancelar tu reserva sin costo. No se realizaron cobros online: el pago se
              hace en el local al retirar.
            } @else {
              Ingresá tu código y el correo que usaste al reservar para ver el estado o cancelar.
            }
          </p>
        </div>
        <a class="btn btn-ghost" routerLink="/">Volver al catálogo</a>
      </header>

      @if (isArrepentimiento()) {
        <div class="legal-banner">
          <strong>Resolución 424/2020 · Ley 24.240</strong>
          <p>
            Este botón te permite revocar la reserva de forma directa y sin costo. Si la reserva
            todavía no fue retirada, al confirmar la cancelación se libera el stock reservado. No
            se aplican penalidades porque no existe pago online.
          </p>
        </div>
      }

      <div class="lookup-layout">
        <form class="card lookup-form" [formGroup]="form" (ngSubmit)="search()" novalidate>
          <h2>Buscar reserva</h2>
          <label class="field">
            <span>Código de reserva *</span>
            <input
              type="text"
              formControlName="code"
              placeholder="CC-XXXXXX"
              autocomplete="off"
              maxlength="12"
            />
            @if (form.controls.code.invalid && form.controls.code.touched) {
              <small class="field-error">Ingresá el código de 6 caracteres.</small>
            }
          </label>
          <label class="field">
            <span>Correo electrónico *</span>
            <input type="email" formControlName="email" autocomplete="email" />
            @if (form.controls.email.invalid && form.controls.email.touched) {
              <small class="field-error">Ingresá el correo usado en la reserva.</small>
            }
          </label>

          @if (error(); as message) {
            <div class="alert alert-error">{{ message }}</div>
          }

          <button type="submit" class="btn btn-primary btn-block" [disabled]="loading()">
            {{ loading() ? 'Buscando…' : 'Consultar reserva' }}
          </button>
          <p class="form-note">
            Por seguridad, solo mostramos la reserva si el código y el correo coinciden.
          </p>
        </form>

        @if (reservation(); as data) {
          <article class="card result-card">
            <div class="result-heading">
              <div>
                <span class="eyebrow">Reserva {{ data.code }}</span>
                <h2>{{ data.customer_name }} {{ data.customer_last_name }}</h2>
              </div>
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
                <dt>Total</dt>
                <dd>{{ money(data.total_amount) }}</dd>
              </div>
              <div>
                <dt>Pago</dt>
                <dd>En el local</dd>
              </div>
            </dl>

            <ul class="item-list">
              @for (item of data.items; track item.id) {
                <li>
                  <span>{{ item.quantity }}× {{ item.product_name }}</span>
                  <span>{{ money(item.line_total) }}</span>
                </li>
              }
            </ul>

            @if (data.cancelled_at) {
              <div class="alert alert-info">
                <strong>Reserva cancelada</strong>
                {{ dateTime(data.cancelled_at) }}
                @if (data.cancellation_reason) {
                  · {{ data.cancellation_reason }}
                }
              </div>
            }

            <div class="result-actions">
              @if (data.whatsapp_url) {
                <a
                  class="btn btn-whatsapp"
                  [href]="data.whatsapp_url"
                  target="_blank"
                  rel="noopener"
                >
                  Enviar por WhatsApp
                </a>
              }
              @if (data.status === 'PENDIENTE' || data.status === 'CONFIRMADO') {
                <button
                  type="button"
                  class="btn btn-danger"
                  [disabled]="cancelling()"
                  (click)="cancel(data)"
                >
                  {{ cancelling() ? 'Cancelando…' : 'Cancelar reserva' }}
                </button>
              }
            </div>

            @if (data.status === 'RETIRADO') {
              <p class="form-note">Esta reserva ya fue retirada y no puede cancelarse.</p>
            }
            @if (data.status === 'CANCELADO') {
              <p class="form-note">Esta reserva ya está cancelada. No se realizó ningún cobro.</p>
            }
          </article>
        }
      </div>
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
        max-width: 42rem;
        line-height: 1.65;
      }
      .legal-banner {
        background: #f4fbe4;
        border: 1px solid #d8ecb0;
        border-radius: 0.9rem;
        padding: 1rem 1.15rem;
        margin-bottom: 1.5rem;
      }
      .legal-banner strong {
        color: #365314;
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }
      .legal-banner p {
        margin: 0.35rem 0 0;
        color: #4d6b24;
        font-size: 0.88rem;
        line-height: 1.65;
      }
      .lookup-layout {
        display: grid;
        grid-template-columns: minmax(16rem, 0.7fr) minmax(0, 1.3fr);
        gap: 1.25rem;
        align-items: start;
      }
      .lookup-form {
        padding: 1.3rem;
        display: grid;
        gap: 0.9rem;
      }
      .lookup-form h2 {
        margin: 0 0 0.2rem;
        font-size: 1.1rem;
      }
      .form-note {
        margin: 0;
        color: var(--muted);
        font-size: 0.78rem;
        line-height: 1.55;
      }
      .result-card {
        padding: 1.4rem;
        display: grid;
        gap: 1rem;
      }
      .result-heading {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 1rem;
      }
      .result-heading h2 {
        margin: 0.2rem 0 0;
        font-size: 1.25rem;
      }
      .detail-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.85rem;
        margin: 0;
      }
      .detail-grid dt {
        color: var(--muted);
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.15rem;
      }
      .detail-grid dd {
        margin: 0;
        font-weight: 600;
        font-size: 0.9rem;
      }
      .item-list {
        list-style: none;
        padding: 0;
        margin: 0;
        display: grid;
        gap: 0.5rem;
        border-top: 1px solid var(--border);
        padding-top: 0.9rem;
      }
      .item-list li {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        font-size: 0.88rem;
        color: var(--muted);
      }
      .result-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 0.6rem;
        border-top: 1px solid var(--border);
        padding-top: 1rem;
      }
      @media (max-width: 900px) {
        .lookup-layout {
          grid-template-columns: 1fr;
        }
      }
      @media (max-width: 560px) {
        .detail-grid {
          grid-template-columns: 1fr;
        }
      }
    `,
  ],
})
export class LookupPageComponent {
  private readonly fb = inject(FormBuilder);
  private readonly route = inject(ActivatedRoute);
  private readonly reservations = inject(ReservationService);
  private readonly toast = inject(ToastService);

  readonly config = inject(ConfigService);
  readonly money = formatMoney;
  readonly dateTime = formatDateTime;
  readonly reservation = signal<Reservation | null>(null);
  readonly loading = signal(false);
  readonly cancelling = signal(false);
  readonly error = signal<string | null>(null);
  readonly isArrepentimiento = signal(this.route.snapshot.data['mode'] === 'arrepentimiento');

  readonly form = this.fb.nonNullable.group({
    code: ['', [Validators.required, Validators.minLength(6), Validators.maxLength(12)]],
    email: ['', [Validators.required, Validators.email]],
  });

  async search(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.loading.set(true);
    this.error.set(null);
    const { code, email } = this.form.getRawValue();

    try {
      const reservation = await this.reservations.lookup(code.trim().toUpperCase(), email.trim());
      this.reservation.set(reservation);
    } catch (error) {
      this.reservation.set(null);
      this.error.set(parseApiError(error));
    } finally {
      this.loading.set(false);
    }
  }

  async cancel(reservation: Reservation): Promise<void> {
    const confirmed = window.confirm(
      '¿Confirmás la cancelación de la reserva? Se liberará el stock reservado y no se realizará ningún cobro.',
    );
    if (!confirmed) {
      return;
    }

    this.cancelling.set(true);
    this.error.set(null);
    try {
      const updated = await this.reservations.cancel(
        reservation.code,
        reservation.customer_email,
        this.isArrepentimiento()
          ? 'Cancelación solicitada mediante el Botón de Arrepentimiento'
          : 'Cancelación solicitada por el cliente',
      );
      this.reservation.set(updated);
      this.toast.success('Reserva cancelada. El stock fue liberado.');
    } catch (error) {
      this.error.set(parseApiError(error));
    } finally {
      this.cancelling.set(false);
    }
  }

  statusLabel(status: Reservation['status']): string {
    return STATUS_LABELS[status];
  }
}
