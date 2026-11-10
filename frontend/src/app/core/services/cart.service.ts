import { Injectable, computed, effect, signal } from '@angular/core';

import { CartItem, Product } from '../models';

const STORAGE_KEY = 'clean_center_cart_v1';
const MAX_QUANTITY = 99;

@Injectable({ providedIn: 'root' })
export class CartService {
  readonly items = signal<CartItem[]>(this.restore());

  readonly count = computed(() =>
    this.items().reduce((total, item) => total + item.quantity, 0),
  );
  readonly subtotal = computed(() =>
    this.items().reduce((total, item) => total + Number(item.product.price) * item.quantity, 0),
  );
  readonly isEmpty = computed(() => this.items().length === 0);

  constructor() {
    effect(() => {
      this.persist(this.items());
    });
  }

  quantityFor(productId: number): number {
    return this.items().find((item) => item.product.id === productId)?.quantity ?? 0;
  }

  add(product: Product, quantity = 1): { ok: boolean; message: string } {
    if (product.stock <= 0) {
      return { ok: false, message: 'Este producto no tiene stock disponible.' };
    }

    const current = this.quantityFor(product.id);
    const nextQuantity = Math.min(current + quantity, MAX_QUANTITY, product.stock);

    if (nextQuantity === current) {
      return {
        ok: false,
        message: `Solo hay ${product.stock} unidades disponibles de ${product.name}.`,
      };
    }

    if (current === 0) {
      this.items.update((items) => [...items, { product, quantity: nextQuantity }]);
    } else {
      this.items.update((items) =>
        items.map((item) =>
          item.product.id === product.id ? { ...item, product, quantity: nextQuantity } : item,
        ),
      );
    }

    return { ok: true, message: `${product.name} agregado al carrito.` };
  }

  updateQuantity(productId: number, quantity: number): void {
    this.items.update((items) =>
      items.map((item) => {
        if (item.product.id !== productId) {
          return item;
        }
        const max = Math.min(item.product.stock, MAX_QUANTITY);
        const safeQuantity = Math.max(1, Math.min(quantity, max));
        return { ...item, quantity: safeQuantity };
      }),
    );
  }

  increment(productId: number): void {
    this.updateQuantity(productId, this.quantityFor(productId) + 1);
  }

  decrement(productId: number): void {
    this.updateQuantity(productId, this.quantityFor(productId) - 1);
  }

  remove(productId: number): void {
    this.items.update((items) => items.filter((item) => item.product.id !== productId));
  }

  clear(): void {
    this.items.set([]);
  }

  private restore(): CartItem[] {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return [];
      }
      const parsed = JSON.parse(raw) as CartItem[];
      if (!Array.isArray(parsed)) {
        return [];
      }
      return parsed.filter(
        (item) =>
          item &&
          item.product &&
          typeof item.product.id === 'number' &&
          typeof item.quantity === 'number' &&
          item.quantity > 0,
      );
    } catch {
      return [];
    }
  }

  private persist(items: CartItem[]): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    } catch {
      // El carrito sigue funcionando en memoria si el navegador bloquea localStorage.
    }
  }
}
