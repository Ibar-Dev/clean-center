import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { Reservation, ReservationCreatePayload } from '../models';

const SESSION_KEY = 'clean_center_last_reservation';

@Injectable({ providedIn: 'root' })
export class ReservationService {
  private readonly http = inject(HttpClient);

  readonly lastReservation = signal<Reservation | null>(this.restore());

  async create(payload: ReservationCreatePayload): Promise<Reservation> {
    const reservation = await firstValueFrom(
      this.http.post<Reservation>('/api/reservations', payload),
    );
    this.lastReservation.set(reservation);
    this.persist(reservation);
    return reservation;
  }

  lookup(code: string, email: string): Promise<Reservation> {
    return firstValueFrom(
      this.http.post<Reservation>('/api/reservations/lookup', { code, email }),
    );
  }

  cancel(code: string, email: string, reason?: string): Promise<Reservation> {
    return firstValueFrom(
      this.http.post<Reservation>(`/api/reservations/${encodeURIComponent(code)}/cancel`, {
        email,
        reason: reason ?? null,
      }),
    );
  }

  forget(): void {
    this.lastReservation.set(null);
    try {
      sessionStorage.removeItem(SESSION_KEY);
    } catch {
      // Sin sessionStorage la confirmación sigue disponible en memoria.
    }
  }

  private restore(): Reservation | null {
    try {
      const raw = sessionStorage.getItem(SESSION_KEY);
      return raw ? (JSON.parse(raw) as Reservation) : null;
    } catch {
      return null;
    }
  }

  private persist(reservation: Reservation): void {
    try {
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(reservation));
    } catch {
      // Sin sessionStorage la confirmación sigue disponible en memoria.
    }
  }
}
