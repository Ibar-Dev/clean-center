import { Component, inject, signal } from '@angular/core';
import { NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';

import { ConfigService } from './core/services/config.service';
import { FooterComponent } from './shared/footer.component';
import { HeaderComponent } from './shared/header.component';
import { LegalModalComponent } from './shared/legal-modal.component';
import { ToastsComponent } from './shared/toasts.component';

@Component({
  selector: 'app-root',
  imports: [
    RouterOutlet,
    HeaderComponent,
    FooterComponent,
    LegalModalComponent,
    ToastsComponent,
  ],
  template: `
    @if (!isAdminRoute()) {
      <app-header />
    }

    @if (config.error(); as message) {
      <div class="container config-warning">
        <div class="alert alert-warning">{{ message }}</div>
      </div>
    }

    <main>
      <router-outlet />
    </main>

    @if (!isAdminRoute()) {
      <app-footer />
    }

    <app-legal-modal />
    <app-toasts />
  `,
  styles: [
    `
      .config-warning {
        padding-top: 1rem;
      }
    `,
  ],
})
export class App {
  readonly config = inject(ConfigService);
  private readonly router = inject(Router);
  readonly isAdminRoute = signal(this.computeAdminRoute(this.router.url));

  constructor() {
    this.router.events
      .pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd))
      .subscribe((event) => {
        this.isAdminRoute.set(this.computeAdminRoute(event.urlAfterRedirects));
      });
  }

  private computeAdminRoute(url: string): boolean {
    return url.startsWith('/admin') && !url.startsWith('/admin/login');
  }
}
