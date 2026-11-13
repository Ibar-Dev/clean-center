import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { ConfigService } from '../core/services/config.service';
import { LegalService } from '../core/services/legal.service';

@Component({
  selector: 'app-footer',
  imports: [RouterLink],
  template: `
    <footer class="site-footer">
      <div class="container footer-grid">
        <div class="footer-brand">
          <div class="brand brand-inverse">
            <span class="brand-mark" aria-hidden="true">CC</span>
            <span class="brand-text">
              <strong>{{ config.config().store_name }}</strong>
              <small>Click &amp; Collect</small>
            </span>
          </div>
          <p>
            Reservá tus productos de limpieza online y retiralos en el local. El pago se realiza
            en el momento del retiro.
          </p>
          <a class="btn btn-lime btn-sm" routerLink="/arrepentimiento">
            Botón de Arrepentimiento
          </a>
        </div>

        <div>
          <h3>Contacto</h3>
          <ul class="footer-list">
            <li>{{ config.config().store_address }}</li>
            <li>
              <a [href]="'tel:' + config.config().store_phone">
                {{ config.config().store_phone }}
              </a>
            </li>
            <li>
              <a [href]="'mailto:' + config.config().store_email">
                {{ config.config().store_email }}
              </a>
            </li>
            <li>{{ config.config().store_hours }}</li>
          </ul>
        </div>

        <div>
          <h3>Ayuda</h3>
          <ul class="footer-list">
            <li><a routerLink="/consulta">Consultar o cancelar reserva</a></li>
            <li><a routerLink="/carrito">Ver mi carrito</a></li>
            <li><a routerLink="/admin/login">Acceso administración</a></li>
            @if (config.config().whatsapp_available) {
              <li>Envío por WhatsApp disponible al confirmar tu reserva.</li>
            }
          </ul>
        </div>
      </div>

      <div class="container footer-legal">
        <div class="legal-links">
          <button type="button" class="link-button" (click)="legal.open('terms')">
            Términos y Condiciones
          </button>
          <span aria-hidden="true">·</span>
          <button type="button" class="link-button" (click)="legal.open('privacy')">
            Política de Privacidad
          </button>
          <span aria-hidden="true">·</span>
          <a [href]="config.config().aaip_url" target="_blank" rel="noopener">
            AAIP (Ley 25.326)
          </a>
        </div>
        <p>
          {{ config.config().store_legal_name }} · {{ config.config().store_address }}
        </p>
        <p class="tiny">
          Precios en pesos argentinos. El pago se realiza exclusivamente en el local al retirar.
          Garantía de precio por {{ config.config().reservation_expiration_hours }} horas desde
          la reserva. Las reservas vencen
          {{ config.config().reservation_expiration_hours }} horas después de su creación si no
          se retiran.
        </p>
      </div>
    </footer>
  `,
  styles: [
    `
      .site-footer {
        margin-top: 4rem;
        background: var(--teal-950);
        color: #dbe9e6;
      }
      .footer-grid {
        display: grid;
        grid-template-columns: 1.4fr 1fr 1fr;
        gap: 2.5rem;
        padding-top: 3rem;
        padding-bottom: 2rem;
      }
      .brand {
        display: inline-flex;
        align-items: center;
        gap: 0.7rem;
        color: #fff;
      }
      .brand-mark {
        display: grid;
        place-items: center;
        width: 2.6rem;
        height: 2.6rem;
        border-radius: 0.9rem;
        background: linear-gradient(135deg, var(--teal-500), var(--teal-300));
        color: var(--teal-950);
        font-weight: 800;
      }
      .brand-text {
        display: flex;
        flex-direction: column;
        line-height: 1.1;
      }
      .brand-text small {
        color: #9fc2bc;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
      }
      .footer-brand p {
        color: #b6d1cc;
        max-width: 32rem;
        margin: 1rem 0 1.25rem;
        line-height: 1.65;
      }
      h3 {
        color: #fff;
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        margin: 0 0 1rem;
      }
      .footer-list {
        list-style: none;
        padding: 0;
        margin: 0;
        display: grid;
        gap: 0.7rem;
        color: #b6d1cc;
        font-size: 0.92rem;
      }
      .footer-list a,
      .footer-list a:link,
      .footer-list a:visited,
      .footer-legal a,
      .footer-legal a:link,
      .footer-legal a:visited {
        color: #dbe9e6;
        text-decoration: none;
      }
      .footer-list a:hover,
      .footer-legal a:hover {
        color: var(--lime-400);
      }
      .footer-brand a.btn-lime:link,
      .footer-brand a.btn-lime:visited {
        color: var(--teal-950);
        text-decoration: none;
      }
      .footer-brand a.btn-lime:hover,
      .footer-brand a.btn-lime:focus-visible {
        background: #d9f99d;
        border-color: #d9f99d;
        color: var(--teal-950);
      }
      .footer-legal {
        border-top: 1px solid rgba(255, 255, 255, 0.12);
        padding-top: 1.5rem;
        padding-bottom: 2.25rem;
        display: grid;
        gap: 0.45rem;
        color: #9fc2bc;
        font-size: 0.85rem;
      }
      .legal-links {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.55rem;
      }
      .link-button {
        background: none;
        border: none;
        padding: 0;
        color: #dbe9e6;
        font: inherit;
        cursor: pointer;
        text-decoration: underline;
        text-underline-offset: 3px;
      }
      .link-button:hover {
        color: var(--lime-400);
      }
      .tiny {
        font-size: 0.78rem;
        color: #86aca6;
        max-width: 70rem;
      }
      @media (max-width: 860px) {
        .footer-grid {
          grid-template-columns: 1fr;
          gap: 2rem;
        }
      }
    `,
  ],
})
export class FooterComponent {
  readonly config = inject(ConfigService);
  readonly legal = inject(LegalService);
}
