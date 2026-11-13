import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { formatMoney, parseApiError } from '../../core/format';
import { CartService } from '../../core/services/cart.service';
import { ConfigService } from '../../core/services/config.service';
import { LegalService } from '../../core/services/legal.service';
import { ReservationService } from '../../core/services/reservation.service';
import { ToastService } from '../../core/services/toast.service';

type CheckoutControl =
  | 'customer_name'
  | 'customer_last_name'
  | 'customer_email'
  | 'customer_phone'
  | 'pickup_date'
  | 'terms_accepted'
  | 'privacy_consent';

const IDEMPOTENCY_STORAGE_KEY = 'clean_center_checkout_idempotency';

function createIdempotencyKey(): string {
  const cryptoObj = globalThis.crypto;
  if (cryptoObj && typeof cryptoObj.randomUUID === 'function') {
    return cryptoObj.randomUUID();
  }
  // Fallback UUID v4 para contextos sin crypto.randomUUID (HTTP no seguro).
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (char) => {
    const random = Math.floor(Math.random() * 16);
    const value = char === 'x' ? random : (random & 0x3) | 0x8;
    return value.toString(16);
  });
}

@Component({
  selector: 'app-checkout-page',
  imports: [ReactiveFormsModule, RouterLink],
  template: `
    <section class="container page">
      <header class="page-header">
        <div>
          <span class="eyebrow">Paso final</span>
          <h1>Datos de la reserva</h1>
          <p>Completá tus datos y elegí cuándo vas a retirar. El pago se realiza en el local.</p>
        </div>
        <a class="btn btn-ghost" routerLink="/carrito">Volver al carrito</a>
      </header>

      @if (cart.isEmpty()) {
        <div class="empty-state">
          <h2>No hay productos en el carrito</h2>
          <p>Agregá productos antes de completar la reserva.</p>
          <a class="btn btn-primary" routerLink="/">Ver catálogo</a>
        </div>
      } @else {
        <div class="checkout-layout">
          <form class="card checkout-form" [formGroup]="form" (ngSubmit)="submit()" novalidate>
            <fieldset>
              <legend>Datos del cliente</legend>
              <div class="form-grid">
                <label class="field">
                  <span>Nombre *</span>
                  <input type="text" formControlName="customer_name" autocomplete="given-name" />
                  @if (showError('customer_name')) {
                    <small class="field-error">Ingresá tu nombre (mínimo 2 caracteres).</small>
                  }
                </label>
                <label class="field">
                  <span>Apellido *</span>
                  <input
                    type="text"
                    formControlName="customer_last_name"
                    autocomplete="family-name"
                  />
                  @if (showError('customer_last_name')) {
                    <small class="field-error">Ingresá tu apellido (mínimo 2 caracteres).</small>
                  }
                </label>
                <label class="field">
                  <span>Correo electrónico *</span>
                  <input type="email" formControlName="customer_email" autocomplete="email" />
                  @if (showError('customer_email')) {
                    <small class="field-error">Ingresá un correo electrónico válido.</small>
                  }
                </label>
                <label class="field">
                  <span>Teléfono *</span>
                  <input type="tel" formControlName="customer_phone" autocomplete="tel" />
                  @if (showError('customer_phone')) {
                    <small class="field-error">Ingresá un teléfono de contacto válido.</small>
                  }
                </label>
              </div>
            </fieldset>

            <fieldset>
              <legend>Retiro</legend>
              <label class="field">
                <span>Fecha y hora de retiro *</span>
                <input
                  type="datetime-local"
                  formControlName="pickup_date"
                  [min]="minPickup()"
                  [max]="maxPickup()"
                />
                @if (showError('pickup_date')) {
                  <small class="field-error">Elegí una fecha y hora de retiro.</small>
                }
                <small class="field-hint">
                  Podés retirar desde {{ config.config().min_pickup_lead_minutes }} minutos
                  después de reservar y hasta
                  {{ config.config().reservation_expiration_hours }} horas.
                </small>
              </label>
              <div class="info-box">
                <strong>Horario de atención</strong>
                <span>{{ config.config().store_hours }}</span>
                <span>Dirección de retiro: {{ config.config().store_address }}</span>
              </div>
            </fieldset>

            <fieldset>
              <legend>Pago y condiciones</legend>
              <div class="info-box info-box-strong">
                <strong>Pago en el local</strong>
                <span>
                  No se realiza ningún cobro online. Abonás el total al retirar los productos.
                </span>
              </div>

              <label class="check-field">
                <input type="checkbox" formControlName="terms_accepted" />
                <span>
                  Acepto los
                  <button type="button" class="link-button" (click)="legal.open('terms')">
                    Términos y Condiciones
                  </button>
                  (versión {{ config.config().terms_version }}), incluida la modalidad de pago en
                  el local y la garantía de precio por
                  {{ config.config().reservation_expiration_hours }} horas.
                </span>
              </label>
              @if (showError('terms_accepted')) {
                <small class="field-error">Debés aceptar los Términos y Condiciones.</small>
              }

              <label class="check-field">
                <input type="checkbox" formControlName="privacy_consent" />
                <span>
                  Presto mi consentimiento para el tratamiento de mis datos personales conforme a
                  la
                  <button type="button" class="link-button" (click)="legal.open('privacy')">
                    Política de Privacidad
                  </button>
                  (Ley 25.326). Podés consultar la autoridad de control en
                  <a [href]="config.config().aaip_url" target="_blank" rel="noopener">AAIP</a>.
                </span>
              </label>
              @if (showError('privacy_consent')) {
                <small class="field-error">
                  Debés aceptar la Política de Privacidad para continuar.
                </small>
              }
            </fieldset>

            @if (serverError(); as message) {
              <div class="alert alert-error">{{ message }}</div>
            }

            <button type="submit" class="btn btn-primary btn-block btn-lg" [disabled]="submitting()">
              {{ submitting() ? 'Creando reserva…' : 'Confirmar reserva' }}
            </button>
            <p class="submit-note">
              Al confirmar, se descuenta el stock y se genera un código único de reserva.
            </p>
          </form>

          <aside class="card summary-card">
            <h2>Tu reserva</h2>
            <ul class="summary-items">
              @for (item of cart.items(); track item.product.id) {
                <li>
                  <span>
                    <strong>{{ item.quantity }}×</strong> {{ item.product.name }}
                    <small>{{ item.product.unit }}</small>
                  </span>
                  <span>{{ lineTotal(item.product.price, item.quantity) }}</span>
                </li>
              }
            </ul>
            <dl class="summary-lines">
              <div>
                <dt>Productos</dt>
                <dd>{{ cart.count() }}</dd>
              </div>
              <div class="total-line">
                <dt>Total estimado</dt>
                <dd>{{ money(cart.subtotal()) }}</dd>
              </div>
            </dl>
            <p class="summary-note">
              El precio queda garantizado por {{ config.config().reservation_expiration_hours }}
              horas desde la confirmación. El total se abona en el local.
            </p>
            <div class="summary-help">
              <strong>¿Necesitás ayuda?</strong>
              <span>{{ config.config().store_phone }}</span>
              <span>{{ config.config().store_email }}</span>
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
      .checkout-layout {
        display: grid;
        grid-template-columns: minmax(0, 1.6fr) minmax(17rem, 0.8fr);
        gap: 1.25rem;
        align-items: start;
      }
      .checkout-form {
        padding: 1.4rem;
        display: grid;
        gap: 1.4rem;
      }
      fieldset {
        border: none;
        padding: 0;
        margin: 0;
        display: grid;
        gap: 1rem;
      }
      legend {
        font-weight: 800;
        color: var(--teal-900);
        padding: 0;
        margin-bottom: 0.2rem;
        font-size: 1.02rem;
      }
      .form-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
      }
      .check-field {
        display: flex;
        gap: 0.65rem;
        align-items: flex-start;
        font-size: 0.85rem;
        color: var(--muted);
        line-height: 1.6;
      }
      .check-field input {
        margin-top: 0.2rem;
        width: 1.05rem;
        height: 1.05rem;
        accent-color: var(--teal-700);
        flex: none;
      }
      .check-field a {
        color: var(--teal-700);
      }
      .info-box {
        display: grid;
        gap: 0.2rem;
        background: var(--teal-50);
        color: var(--teal-900);
        border-radius: 0.75rem;
        padding: 0.8rem 0.9rem;
        font-size: 0.84rem;
      }
      .info-box strong {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }
      .info-box-strong {
        background: #f4fbe4;
        color: #365314;
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
      .summary-items {
        list-style: none;
        padding: 0;
        margin: 0;
        display: grid;
        gap: 0.7rem;
      }
      .summary-items li {
        display: flex;
        justify-content: space-between;
        gap: 0.75rem;
        font-size: 0.86rem;
        color: var(--muted);
        border-bottom: 1px solid var(--border);
        padding-bottom: 0.7rem;
      }
      .summary-items li:last-child {
        border-bottom: none;
        padding-bottom: 0;
      }
      .summary-items strong {
        color: var(--ink);
      }
      .summary-items small {
        display: block;
        color: var(--muted);
        font-size: 0.75rem;
      }
      .summary-lines {
        margin: 0;
        display: grid;
        gap: 0.55rem;
      }
      .summary-lines div {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        font-size: 0.9rem;
      }
      .summary-lines dt {
        color: var(--muted);
      }
      .summary-lines dd {
        margin: 0;
        font-weight: 700;
      }
      .total-line {
        border-top: 1px solid var(--border);
        padding-top: 0.6rem;
        font-size: 1rem !important;
      }
      .total-line dd {
        font-size: 1.15rem;
        color: var(--teal-900);
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
      .submit-note {
        margin: 0;
        text-align: center;
        color: var(--muted);
        font-size: 0.78rem;
      }
      .link-button {
        background: none;
        border: none;
        padding: 0;
        color: var(--teal-700);
        font: inherit;
        text-decoration: underline;
        text-underline-offset: 2px;
        cursor: pointer;
      }
      @media (max-width: 900px) {
        .checkout-layout {
          grid-template-columns: 1fr;
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
export class CheckoutPageComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly reservations = inject(ReservationService);
  private readonly toast = inject(ToastService);

  readonly cart = inject(CartService);
  readonly config = inject(ConfigService);
  readonly legal = inject(LegalService);
  readonly money = formatMoney;

  readonly submitting = signal(false);
  readonly serverError = signal<string | null>(null);
  readonly minPickup = signal('');
  readonly maxPickup = signal('');

  readonly form = this.fb.nonNullable.group({
    customer_name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(80)]],
    customer_last_name: [
      '',
      [Validators.required, Validators.minLength(2), Validators.maxLength(80)],
    ],
    customer_email: ['', [Validators.required, Validators.email]],
    customer_phone: ['', [Validators.required, Validators.minLength(8), Validators.maxLength(30)]],
    pickup_date: ['', [Validators.required]],
    terms_accepted: [false, [Validators.requiredTrue]],
    privacy_consent: [false, [Validators.requiredTrue]],
  });

  ngOnInit(): void {
    this.refreshPickupWindow();
  }

  refreshPickupWindow(): void {
    const min = this.config.minPickupInput();
    const max = this.config.maxPickupInput();
    this.minPickup.set(min);
    this.maxPickup.set(max);
    if (!this.form.controls.pickup_date.value) {
      this.form.controls.pickup_date.setValue(min);
    }
  }

  showError(controlName: CheckoutControl): boolean {
    const control = this.form.controls[controlName];
    return control.invalid && (control.dirty || control.touched);
  }

  lineTotal(price: string, quantity: number): string {
    return formatMoney(Number(price) * quantity);
  }

  private checkoutIdempotencyKey(): string {
    try {
      const stored = sessionStorage.getItem(IDEMPOTENCY_STORAGE_KEY);
      if (stored) {
        return stored;
      }
      const key = createIdempotencyKey();
      sessionStorage.setItem(IDEMPOTENCY_STORAGE_KEY, key);
      return key;
    } catch {
      // Si el navegador bloquea sessionStorage, se genera una clave por intento.
      return createIdempotencyKey();
    }
  }

  private clearIdempotencyKey(): void {
    try {
      sessionStorage.removeItem(IDEMPOTENCY_STORAGE_KEY);
    } catch {
      // Sin sessionStorage no hay nada que limpiar.
    }
  }

  async submit(): Promise<void> {
    if (this.cart.isEmpty()) {
      await this.router.navigate(['/carrito']);
      return;
    }

    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.submitting.set(true);
    this.serverError.set(null);
    const value = this.form.getRawValue();

    try {
      const reservation = await this.reservations.create({
        customer_name: value.customer_name.trim(),
        customer_last_name: value.customer_last_name.trim(),
        customer_email: value.customer_email.trim(),
        customer_phone: value.customer_phone.trim(),
        pickup_date: new Date(value.pickup_date).toISOString(),
        items: this.cart.items().map((item) => ({
          product_id: item.product.id,
          quantity: item.quantity,
        })),
        terms_accepted: value.terms_accepted,
        privacy_consent: value.privacy_consent,
        idempotency_key: this.checkoutIdempotencyKey(),
      });

      this.clearIdempotencyKey();
      this.cart.clear();
      this.toast.success('Reserva creada con éxito.');
      await this.router.navigate(['/confirmacion', reservation.code]);
    } catch (error) {
      this.serverError.set(parseApiError(error));
      this.refreshPickupWindow();
    } finally {
      this.submitting.set(false);
    }
  }
}
