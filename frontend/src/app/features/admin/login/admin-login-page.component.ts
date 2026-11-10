import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { parseApiError } from '../../../core/format';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-admin-login-page',
  imports: [ReactiveFormsModule, RouterLink],
  template: `
    <section class="container login-page">
      <div class="card login-card">
        <span class="eyebrow">Administración</span>
        <h1>Panel de Clean Center</h1>
        <p>Ingresá con tu usuario administrador para gestionar reservas y productos.</p>

        <form [formGroup]="form" (ngSubmit)="submit()" novalidate>
          <label class="field">
            <span>Usuario</span>
            <input type="text" formControlName="username" autocomplete="username" />
          </label>
          <label class="field">
            <span>Contraseña</span>
            <input
              type="password"
              formControlName="password"
              autocomplete="current-password"
            />
          </label>

          @if (error(); as message) {
            <div class="alert alert-error">{{ message }}</div>
          }

          <button type="submit" class="btn btn-primary btn-block" [disabled]="loading()">
            {{ loading() ? 'Ingresando…' : 'Ingresar' }}
          </button>
        </form>

        <a class="back-link" routerLink="/">← Volver al catálogo</a>
      </div>
    </section>
  `,
  styles: [
    `
      .login-page {
        display: grid;
        place-items: center;
        padding-top: 4rem;
        padding-bottom: 2rem;
      }
      .login-card {
        width: min(26rem, 100%);
        padding: 2rem;
        display: grid;
        gap: 1.1rem;
      }
      .login-card h1 {
        margin: 0.15rem 0 0;
        font-size: 1.6rem;
      }
      .login-card p {
        margin: 0;
        color: var(--muted);
        font-size: 0.9rem;
        line-height: 1.6;
      }
      form {
        display: grid;
        gap: 0.9rem;
      }
      .back-link {
        color: var(--muted);
        font-size: 0.85rem;
        text-decoration: none;
      }
      .back-link:hover {
        color: var(--teal-700);
      }
    `,
  ],
})
export class AdminLoginPageComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  readonly form = this.fb.nonNullable.group({
    username: ['', [Validators.required]],
    password: ['', [Validators.required]],
  });

  ngOnInit(): void {
    if (this.auth.isAuthenticated()) {
      void this.router.navigate(['/admin/reservas']);
    }
  }

  async submit(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.loading.set(true);
    this.error.set(null);
    const { username, password } = this.form.getRawValue();

    try {
      await this.auth.login(username.trim(), password);
      const returnUrl = this.route.snapshot.queryParamMap.get('returnUrl') || '/admin/reservas';
      await this.router.navigateByUrl(returnUrl);
    } catch (error) {
      this.error.set(parseApiError(error));
    } finally {
      this.loading.set(false);
    }
  }
}
