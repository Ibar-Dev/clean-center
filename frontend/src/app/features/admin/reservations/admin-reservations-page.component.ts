import { Component, OnInit, inject, signal } from '@angular/core';

import { formatDateTime, formatMoney, parseApiError } from '../../../core/format';
import {
  NEXT_STATUSES,
  Page,
  Reservation,
  ReservationStatus,
  ReservationSummary,
  STATUS_LABELS,
} from '../../../core/models';
import { AdminService } from '../../../core/services/admin.service';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-admin-reservations-page',
  template: `
    <section class="container admin-page">
      <header class="admin-page-header">
        <div>
          <span class="eyebrow">Operación diaria</span>
          <h1>Reservas</h1>
          <p>Revisá, confirmá y actualizá el estado de las reservas recibidas.</p>
        </div>
        <button type="button" class="btn btn-ghost" (click)="load()">Actualizar</button>
      </header>

      <div class="filters card">
        <label class="field">
          <span>Buscar</span>
          <input
            type="search"
            placeholder="Código, nombre o correo"
            [value]="search()"
            (input)="onSearch($any($event.target).value)"
          />
        </label>
        <label class="field">
          <span>Estado</span>
          <select [value]="status()" (change)="onStatus($any($event.target).value)">
            <option value="">Todos</option>
            @for (option of statusOptions; track option.value) {
              <option [value]="option.value">{{ option.label }}</option>
            }
          </select>
        </label>
        @if (result(); as pageResult) {
          <span class="filters-count">{{ pageResult.total }} reservas</span>
        }
      </div>

      @if (error(); as message) {
        <div class="alert alert-error">{{ message }}</div>
      }

      <div class="card table-card">
        @if (loading()) {
          <p class="loading-note">Cargando reservas…</p>
        } @else if (result(); as pageResult) {
          @if (pageResult.items.length === 0) {
            <div class="empty-state compact">
              <h2>No hay reservas con esos filtros</h2>
              <p>Probá con otro estado o limpiá la búsqueda.</p>
            </div>
          } @else {
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Código</th>
                    <th>Cliente</th>
                    <th>Retiro</th>
                    <th>Total</th>
                    <th>Estado</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  @for (reservation of pageResult.items; track reservation.id) {
                    <tr>
                      <td><strong>{{ reservation.code }}</strong></td>
                      <td>
                        <span class="cell-main">
                          {{ reservation.customer_name }} {{ reservation.customer_last_name }}
                        </span>
                        <span class="cell-sub">{{ reservation.customer_email }}</span>
                      </td>
                      <td>{{ dateTime(reservation.pickup_date) }}</td>
                      <td>{{ money(reservation.total_amount) }}</td>
                      <td>
                        <span
                          class="status-badge"
                          [class]="'status-' + reservation.status.toLowerCase()"
                        >
                          {{ statusLabel(reservation.status) }}
                        </span>
                      </td>
                      <td class="cell-action">
                        <button
                          type="button"
                          class="btn btn-ghost btn-sm"
                          (click)="openDetail(reservation)"
                        >
                          Gestionar
                        </button>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>

            @if (pageResult.pages > 1) {
              <nav class="pagination" aria-label="Paginación de reservas">
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

    @if (selected(); as detail) {
      <div class="modal-backdrop" (click)="closeDetail()" role="presentation">
        <section
          class="modal-panel"
          role="dialog"
          aria-modal="true"
          aria-label="Detalle de reserva"
          (click)="$event.stopPropagation()"
        >
          <header class="modal-header">
            <div>
              <span class="eyebrow">Reserva {{ detail.code }}</span>
              <h2>{{ detail.customer_name }} {{ detail.customer_last_name }}</h2>
            </div>
            <button type="button" class="icon-button" aria-label="Cerrar" (click)="closeDetail()">
              ✕
            </button>
          </header>

          <div class="modal-body">
            <div class="detail-top">
              <span class="status-badge" [class]="'status-' + detail.status.toLowerCase()">
                {{ statusLabel(detail.status) }}
              </span>
              <span class="cell-sub">Creada {{ dateTime(detail.created_at) }}</span>
            </div>

            <dl class="detail-grid">
              <div>
                <dt>Retiro</dt>
                <dd>{{ dateTime(detail.pickup_date) }}</dd>
              </div>
              <div>
                <dt>Vence</dt>
                <dd>{{ dateTime(detail.expires_at) }}</dd>
              </div>
              <div>
                <dt>Correo</dt>
                <dd>{{ detail.customer_email }}</dd>
              </div>
              <div>
                <dt>Teléfono</dt>
                <dd>{{ detail.customer_phone }}</dd>
              </div>
              <div>
                <dt>Total</dt>
                <dd>{{ money(detail.total_amount) }}</dd>
              </div>
              <div>
                <dt>Documentos aceptados</dt>
                <dd>T&amp;C {{ detail.terms_version }} · Privacidad {{ detail.privacy_version }}</dd>
              </div>
            </dl>

            <h3>Productos</h3>
            <ul class="item-list">
              @for (item of detail.items; track item.id) {
                <li>
                  <span>
                    {{ item.quantity }}× {{ item.product_name }}
                    <small>{{ item.product_unit }}</small>
                  </span>
                  <span>{{ money(item.line_total) }}</span>
                </li>
              }
            </ul>

            @if (detail.cancelled_at) {
              <div class="alert alert-info">
                Cancelada {{ dateTime(detail.cancelled_at) }}
                @if (detail.cancellation_reason) {
                  · {{ detail.cancellation_reason }}
                }
              </div>
            }

            @if (actionError(); as message) {
              <div class="alert alert-error">{{ message }}</div>
            }
          </div>

          <footer class="modal-footer">
            <div class="footer-actions">
              @if (detail.whatsapp_url) {
                <a
                  class="btn btn-whatsapp btn-sm"
                  [href]="detail.whatsapp_url"
                  target="_blank"
                  rel="noopener"
                >
                  WhatsApp
                </a>
              }
              @for (nextStatus of nextStatuses(detail.status); track nextStatus) {
                <button
                  type="button"
                  class="btn btn-sm"
                  [class.btn-primary]="nextStatus !== 'CANCELADO'"
                  [class.btn-danger]="nextStatus === 'CANCELADO'"
                  [disabled]="updating() === detail.id"
                  (click)="changeStatus(detail, nextStatus)"
                >
                  {{ actionLabel(nextStatus) }}
                </button>
              }
              @if (nextStatuses(detail.status).length === 0) {
                <span class="cell-sub">Sin acciones disponibles para este estado.</span>
              }
            </div>
          </footer>
        </section>
      </div>
    }
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
      .filters {
        display: flex;
        align-items: flex-end;
        gap: 1rem;
        flex-wrap: wrap;
        padding: 1rem;
        margin-bottom: 1rem;
      }
      .filters .field {
        min-width: 12rem;
        flex: 1 1 12rem;
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
      .detail-top {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1rem;
      }
      .detail-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.85rem;
        margin: 0 0 1.25rem;
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
        overflow-wrap: anywhere;
      }
      .modal-body h3 {
        font-size: 0.95rem;
        margin: 0 0 0.6rem;
      }
      .item-list {
        list-style: none;
        padding: 0;
        margin: 0 0 1rem;
        display: grid;
        gap: 0.5rem;
      }
      .item-list li {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        font-size: 0.88rem;
        color: var(--muted);
        border-bottom: 1px solid var(--border);
        padding-bottom: 0.5rem;
      }
      .item-list li:last-child {
        border-bottom: none;
      }
      .item-list small {
        display: block;
        font-size: 0.75rem;
      }
      .modal-footer {
        display: flex;
        justify-content: flex-end;
      }
      .footer-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        align-items: center;
      }
      @media (max-width: 620px) {
        .detail-grid {
          grid-template-columns: 1fr;
        }
      }
    `,
  ],
})
export class AdminReservationsPageComponent implements OnInit {
  private readonly admin = inject(AdminService);
  private readonly toast = inject(ToastService);

  readonly money = formatMoney;
  readonly dateTime = formatDateTime;
  readonly statusOptions: { value: ReservationStatus; label: string }[] = (
    Object.keys(STATUS_LABELS) as ReservationStatus[]
  ).map((value) => ({ value, label: STATUS_LABELS[value] }));

  readonly result = signal<Page<ReservationSummary> | null>(null);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly search = signal('');
  readonly status = signal<ReservationStatus | ''>('');
  readonly page = signal(1);
  readonly selected = signal<Reservation | null>(null);
  readonly updating = signal<number | null>(null);
  readonly actionError = signal<string | null>(null);

  private searchTimer: ReturnType<typeof setTimeout> | undefined;

  ngOnInit(): void {
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

  onStatus(value: string): void {
    this.status.set(value as ReservationStatus | '');
    this.page.set(1);
    void this.load();
  }

  goToPage(page: number): void {
    this.page.set(page);
    void this.load();
  }

  async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      const result = await this.admin.listReservations({
        search: this.search(),
        status: this.status(),
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

  async openDetail(reservation: ReservationSummary): Promise<void> {
    this.actionError.set(null);
    try {
      this.selected.set(await this.admin.getReservation(reservation.id));
    } catch (error) {
      this.toast.error(parseApiError(error));
    }
  }

  closeDetail(): void {
    this.selected.set(null);
    this.actionError.set(null);
  }

  nextStatuses(status: ReservationStatus): ReservationStatus[] {
    return NEXT_STATUSES[status];
  }

  actionLabel(status: ReservationStatus): string {
    switch (status) {
      case 'CONFIRMADO':
        return 'Confirmar reserva';
      case 'RETIRADO':
        return 'Marcar como retirada';
      case 'CANCELADO':
        return 'Cancelar reserva';
      default:
        return status;
    }
  }

  statusLabel(status: ReservationStatus): string {
    return STATUS_LABELS[status];
  }

  async changeStatus(reservation: Reservation, status: ReservationStatus): Promise<void> {
    if (
      status === 'CANCELADO' &&
      !window.confirm(
        '¿Cancelar esta reserva? Se repondrá el stock de los productos reservados.',
      )
    ) {
      return;
    }

    this.updating.set(reservation.id);
    this.actionError.set(null);
    try {
      const updated = await this.admin.updateReservationStatus(reservation.id, {
        status,
        reason:
          status === 'CANCELADO' ? 'Cancelación gestionada desde el panel administrador' : undefined,
      });
      this.selected.set(updated);
      this.toast.success(`Reserva actualizada a ${STATUS_LABELS[status]}.`);
      await this.load();
    } catch (error) {
      this.actionError.set(parseApiError(error));
    } finally {
      this.updating.set(null);
    }
  }
}
