import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { AppConfig } from '../models';

const FALLBACK_CONFIG: AppConfig = {
  store_name: 'Clean Center',
  store_legal_name: 'Clean Center S.R.L.',
  store_cuit: '30-00000000-0',
  store_address: 'Dirección a configurar',
  store_phone: '+54 11 0000-0000',
  store_email: 'contacto@cleancenter.com.ar',
  store_hours: 'Lun a Vie de 09:00 a 18:00, Sáb de 09:00 a 13:00',
  reservation_expiration_hours: 48,
  min_pickup_lead_minutes: 60,
  aaip_url: 'https://www.argentina.gob.ar/aaip',
  terms_version: '2026-11',
  privacy_version: '2026-11',
  whatsapp_available: false,
};

@Injectable({ providedIn: 'root' })
export class ConfigService {
  private readonly http = inject(HttpClient);
  private readonly state = signal<AppConfig | null>(null);

  readonly config = computed<AppConfig>(() => this.state() ?? FALLBACK_CONFIG);
  readonly loaded = signal(false);
  readonly error = signal<string | null>(null);

  async load(): Promise<void> {
    try {
      const config = await firstValueFrom(this.http.get<AppConfig>('/api/config'));
      this.state.set(config);
      this.error.set(null);
    } catch {
      this.error.set(
        'No se pudo cargar la configuración del comercio. Estamos mostrando datos de ejemplo.',
      );
    } finally {
      this.loaded.set(true);
    }
  }

  /** Fecha mínima de retiro en formato datetime-local. */
  minPickupInput(): string {
    const now = new Date();
    now.setMinutes(now.getMinutes() + this.config().min_pickup_lead_minutes);
    now.setSeconds(0, 0);
    return this.toInputValue(now);
  }

  /** Fecha máxima de retiro en formato datetime-local. */
  maxPickupInput(): string {
    const now = new Date();
    now.setHours(now.getHours() + this.config().reservation_expiration_hours);
    now.setSeconds(0, 0);
    return this.toInputValue(now);
  }

  private toInputValue(date: Date): string {
    const pad = (value: number) => String(value).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
      date.getHours(),
    )}:${pad(date.getMinutes())}`;
  }
}
