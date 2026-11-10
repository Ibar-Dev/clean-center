import { Component, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AuthService } from '../../core/services/auth.service';
import { ConfigService } from '../../core/services/config.service';

@Component({
  selector: 'app-admin-layout',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <section class="admin-shell">
      <header class="admin-bar">
        <div class="container admin-bar-inner">
          <div class="admin-title">
            <span class="brand-mark" aria-hidden="true">CC</span>
            <div>
              <strong>{{ config.config().store_name }} · Panel</strong>
              <small>{{ auth.user()?.username }}</small>
            </div>
          </div>
          <nav class="admin-nav" aria-label="Secciones de administración">
            <a routerLink="/admin/reservas" routerLinkActive="active">Reservas</a>
            <a routerLink="/admin/productos" routerLinkActive="active">Productos</a>
          </nav>
          <div class="admin-actions">
            <a class="btn btn-ghost btn-sm" routerLink="/">Ver tienda</a>
            <button type="button" class="btn btn-ghost btn-sm" (click)="logout()">
              Salir
            </button>
          </div>
        </div>
      </header>

      <router-outlet />
    </section>
  `,
  styles: [
    `
      .admin-shell {
        min-height: 60vh;
      }
      .admin-bar {
        background: var(--teal-950);
        color: #fff;
      }
      .admin-bar-inner {
        display: flex;
        align-items: center;
        gap: 1.25rem;
        min-height: 4.25rem;
        flex-wrap: wrap;
      }
      .admin-title {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        margin-right: auto;
      }
      .brand-mark {
        display: grid;
        place-items: center;
        width: 2.3rem;
        height: 2.3rem;
        border-radius: 0.75rem;
        background: linear-gradient(135deg, var(--teal-500), var(--teal-300));
        color: var(--teal-950);
        font-weight: 800;
      }
      .admin-title div {
        display: grid;
        line-height: 1.2;
      }
      .admin-title strong {
        font-size: 0.92rem;
      }
      .admin-title small {
        color: #9fc2bc;
        font-size: 0.75rem;
      }
      .admin-nav {
        display: flex;
        gap: 0.3rem;
      }
      .admin-nav a {
        color: #b6d1cc;
        text-decoration: none;
        font-weight: 600;
        font-size: 0.88rem;
        padding: 0.5rem 0.8rem;
        border-radius: 999px;
      }
      .admin-nav a:hover,
      .admin-nav a.active {
        background: rgba(255, 255, 255, 0.1);
        color: #fff;
      }
      .admin-actions {
        display: flex;
        gap: 0.4rem;
      }
      .admin-actions .btn {
        color: #dbe9e6;
        border-color: rgba(255, 255, 255, 0.22);
      }
      .admin-actions .btn:hover {
        background: rgba(255, 255, 255, 0.1);
      }
      @media (max-width: 720px) {
        .admin-bar-inner {
          padding-top: 0.7rem;
          padding-bottom: 0.7rem;
        }
        .admin-actions {
          width: 100%;
        }
      }
    `,
  ],
})
export class AdminLayoutComponent {
  readonly auth = inject(AuthService);
  readonly config = inject(ConfigService);
  private readonly router = inject(Router);

  async logout(): Promise<void> {
    this.auth.logout();
    await this.router.navigate(['/admin/login']);
  }
}
