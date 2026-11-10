import { Component, inject } from '@angular/core';

import { ToastService } from '../core/services/toast.service';

@Component({
  selector: 'app-toasts',
  template: `
    <div class="toast-stack" aria-live="polite" aria-atomic="false">
      @for (toast of toasts.toasts(); track toast.id) {
        <div class="toast" [class]="'toast toast-' + toast.kind">
          <span>{{ toast.message }}</span>
          <button
            type="button"
            class="toast-close"
            aria-label="Cerrar notificación"
            (click)="toasts.dismiss(toast.id)"
          >
            ✕
          </button>
        </div>
      }
    </div>
  `,
  styles: [
    `
      .toast-stack {
        position: fixed;
        right: 1rem;
        bottom: 1rem;
        z-index: 120;
        display: grid;
        gap: 0.6rem;
        width: min(24rem, calc(100vw - 2rem));
      }
      .toast {
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
        padding: 0.85rem 0.95rem;
        border-radius: 0.8rem;
        background: var(--teal-950);
        color: #f2fbf9;
        box-shadow: var(--shadow-lg);
        font-size: 0.9rem;
        line-height: 1.45;
        border-left: 4px solid var(--teal-400);
      }
      .toast-success {
        border-left-color: var(--lime-400);
      }
      .toast-error {
        border-left-color: #ff8a7a;
        background: #461812;
      }
      .toast-close {
        margin-left: auto;
        background: none;
        border: none;
        color: inherit;
        cursor: pointer;
        opacity: 0.7;
        font-size: 0.85rem;
      }
      .toast-close:hover {
        opacity: 1;
      }
    `,
  ],
})
export class ToastsComponent {
  readonly toasts = inject(ToastService);
}
