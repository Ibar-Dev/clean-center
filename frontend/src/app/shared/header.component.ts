import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

import { AuthService } from '../core/services/auth.service';
import { CartService } from '../core/services/cart.service';
import { ConfigService } from '../core/services/config.service';

@Component({
  selector: 'app-header',
  imports: [RouterLink, RouterLinkActive],
  template: `
    <header class="site-header">
      <div class="container header-inner">
        <a class="brand" routerLink="/" aria-label="Ir al catálogo">
          <span class="brand-mark" aria-hidden="true">CC</span>
          <span class="brand-text">
            <strong>{{ config.config().store_name }}</strong>
            <small>Click &amp; Collect</small>
          </span>
        </a>

        <nav class="main-nav" aria-label="Navegación principal">
          <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }">
            Catálogo
          </a>
          <a routerLink="/consulta" routerLinkActive="active">Consultar reserva</a>
        </nav>

        <div class="header-actions">
          <a class="cart-link" routerLink="/carrito" aria-label="Ver carrito">
            <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
              <path
                d="M3 4h2l2.4 11.2a2 2 0 0 0 2 1.6h8.8a2 2 0 0 0 2-1.6L22 8H6"
                fill="none"
                stroke="currentColor"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
              <circle cx="10" cy="20" r="1.4" fill="currentColor" />
              <circle cx="18" cy="20" r="1.4" fill="currentColor" />
            </svg>
            <span class="cart-link-label">Carrito</span>
            @if (cart.count() > 0) {
              <span class="cart-badge">{{ cart.count() }}</span>
            }
          </a>

          @if (auth.isAuthenticated()) {
            <a class="btn btn-ghost btn-sm" routerLink="/admin/reservas">Panel</a>
          } @else {
            <a class="btn btn-ghost btn-sm" routerLink="/admin/login">Admin</a>
          }
        </div>
      </div>
    </header>
  `,
  styles: [
    `
      .site-header {
        position: sticky;
        top: 0;
        z-index: 30;
        background: rgba(255, 255, 255, 0.94);
        backdrop-filter: blur(12px);
        border-bottom: 1px solid var(--border);
      }
      .header-inner {
        display: flex;
        align-items: center;
        gap: 1.25rem;
        min-height: 4.5rem;
      }
      .brand {
        display: inline-flex;
        align-items: center;
        gap: 0.7rem;
        text-decoration: none;
        color: var(--ink);
        margin-right: auto;
      }
      .brand-mark {
        display: grid;
        place-items: center;
        width: 2.6rem;
        height: 2.6rem;
        border-radius: 0.9rem;
        background: linear-gradient(135deg, var(--teal-600), var(--teal-400));
        color: #fff;
        font-weight: 800;
        letter-spacing: -0.04em;
      }
      .brand-text {
        display: flex;
        flex-direction: column;
        line-height: 1.1;
      }
      .brand-text strong {
        font-size: 1.05rem;
        letter-spacing: -0.02em;
      }
      .brand-text small {
        color: var(--muted);
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
      }
      .main-nav {
        display: flex;
        gap: 0.35rem;
      }
      .main-nav a {
        padding: 0.55rem 0.85rem;
        border-radius: 999px;
        color: var(--muted);
        text-decoration: none;
        font-weight: 600;
        font-size: 0.9rem;
      }
      .main-nav a:hover,
      .main-nav a.active {
        color: var(--teal-700);
        background: var(--teal-50);
      }
      .header-actions {
        display: flex;
        align-items: center;
        gap: 0.6rem;
      }
      .cart-link {
        position: relative;
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        color: var(--ink);
        text-decoration: none;
        padding: 0.5rem 0.7rem;
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.9rem;
      }
      .cart-link:hover {
        background: var(--surface-alt);
      }
      .cart-badge {
        display: grid;
        place-items: center;
        min-width: 1.35rem;
        height: 1.35rem;
        padding: 0 0.3rem;
        border-radius: 999px;
        background: var(--lime-400);
        color: var(--teal-900);
        font-size: 0.72rem;
        font-weight: 800;
      }
      @media (max-width: 760px) {
        .header-inner {
          flex-wrap: wrap;
          gap: 0.5rem;
          padding-top: 0.6rem;
          padding-bottom: 0.6rem;
        }
        .main-nav {
          order: 3;
          width: 100%;
          overflow-x: auto;
        }
        .cart-link-label {
          display: none;
        }
        .brand-text small {
          display: none;
        }
      }
    `,
  ],
})
export class HeaderComponent {
  readonly config = inject(ConfigService);
  readonly cart = inject(CartService);
  readonly auth = inject(AuthService);
}
