const currencyFormatter = new Intl.NumberFormat('es-AR', {
  style: 'currency',
  currency: 'ARS',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const dateFormatter = new Intl.DateTimeFormat('es-AR', {
  dateStyle: 'medium',
  timeStyle: 'short',
  timeZone: 'America/Argentina/Buenos_Aires',
});

const dateOnlyFormatter = new Intl.DateTimeFormat('es-AR', {
  dateStyle: 'long',
  timeZone: 'America/Argentina/Buenos_Aires',
});

export function formatMoney(value: string | number): string {
  const numeric = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(numeric) ? currencyFormatter.format(numeric) : String(value);
}

export function formatDateTime(value: string | Date | null | undefined): string {
  if (!value) {
    return '—';
  }
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : dateFormatter.format(date);
}

export function formatDate(value: string | Date | null | undefined): string {
  if (!value) {
    return '—';
  }
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : dateOnlyFormatter.format(date);
}

export function toDateTimeLocal(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`;
}

export function parseApiError(error: unknown): string {
  const fallback = 'Ocurrió un error inesperado. Intentá nuevamente.';
  if (!error || typeof error !== 'object') {
    return fallback;
  }

  const maybeHttpError = error as {
    error?: { detail?: unknown; message?: string };
    message?: string;
  };
  const detail = maybeHttpError.error?.detail;

  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (item && typeof item === 'object' && 'msg' in item) {
          const msg = (item as { msg: unknown }).msg;
          return typeof msg === 'string' ? msg : null;
        }
        return null;
      })
      .filter((msg): msg is string => Boolean(msg));
    if (messages.length) {
      return messages.join(' ');
    }
  }
  if (maybeHttpError.error?.message) {
    return maybeHttpError.error.message;
  }
  if (maybeHttpError.message) {
    return maybeHttpError.message;
  }
  return fallback;
}
