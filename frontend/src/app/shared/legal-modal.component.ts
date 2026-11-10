import { Component, HostListener, inject } from '@angular/core';

import { ConfigService } from '../core/services/config.service';
import { LegalService } from '../core/services/legal.service';

@Component({
  selector: 'app-legal-modal',
  template: `
    @if (legal.current(); as document) {
      <div class="modal-backdrop" (click)="legal.close()" role="presentation">
        <section
          class="modal-panel"
          role="dialog"
          aria-modal="true"
          [attr.aria-label]="
            document === 'terms' ? 'Términos y Condiciones' : 'Política de Privacidad'
          "
          (click)="$event.stopPropagation()"
        >
          <header class="modal-header">
            <div>
              <span class="eyebrow">Información legal</span>
              <h2>
                {{ document === 'terms' ? 'Términos y Condiciones' : 'Política de Privacidad' }}
              </h2>
            </div>
            <button
              type="button"
              class="icon-button"
              aria-label="Cerrar"
              (click)="legal.close()"
            >
              ✕
            </button>
          </header>

          <div class="modal-body legal-copy">
            @if (document === 'terms') {
              <p class="legal-meta">
                Versión {{ config.config().terms_version }} · Vigente desde la publicación.
              </p>
              <h3>1. Identificación del comercio</h3>
              <p>
                {{ config.config().store_legal_name }}, CUIT {{ config.config().store_cuit }},
                con domicilio en {{ config.config().store_address }}. Correo electrónico:
                {{ config.config().store_email }}. Teléfono:
                {{ config.config().store_phone }}.
              </p>

              <h3>2. Modalidad Click &amp; Collect</h3>
              <p>
                El sitio permite reservar productos de limpieza para retirarlos en el local.
                No se procesan pagos online: el pago se realiza exclusivamente en el local, en
                el momento del retiro, por los medios habilitados en la sucursal.
              </p>

              <h3>
                3. Precio y garantía de
                {{ config.config().reservation_expiration_hours }} horas
              </h3>
              <p>
                El precio informado al confirmar la reserva se garantiza por
                {{ config.config().reservation_expiration_hours }} horas desde la creación de la
                reserva, dentro de ese plazo y sujeto a la disponibilidad de stock reservada.
                Luego de ese plazo la reserva vence y los productos vuelven al stock disponible.
              </p>

              <h3>4. Retiro</h3>
              <p>
                La fecha de retiro debe ser al menos
                {{ config.config().min_pickup_lead_minutes }} minutos posterior a la reserva y no
                puede superar la ventana de
                {{ config.config().reservation_expiration_hours }} horas. Horario de atención:
                {{ config.config().store_hours }}. Para retirar, presentá el código de reserva
                (formato CC-XXXXXX) y tu documento de identidad.
              </p>

              <h3>5. Cancelaciones y Botón de Arrepentimiento</h3>
              <p>
                Podés consultar o cancelar tu reserva desde la sección “Consultar reserva” o
                mediante el Botón de Arrepentimiento disponible en el pie del sitio. La
                cancelación no genera cargo alguno porque no se cobra online. Se respetan los
                derechos previstos en la Ley 24.240 de Defensa del Consumidor y en la Resolución
                424/2020 de la Secretaría de Comercio Interior.
              </p>

              <h3>6. Disponibilidad</h3>
              <p>
                Las imágenes y descripciones son ilustrativas. La reserva queda sujeta a la
                confirmación de stock. Si un producto no estuviera disponible, el comercio podrá
                contactarte para ofrecer una alternativa o cancelar sin costo.
              </p>

              <h3>7. Atención al consumidor</h3>
              <p>
                Ante cualquier consulta o reclamo escribí a
                {{ config.config().store_email }} o llamá al
                {{ config.config().store_phone }}. También podés acudir a los organismos de
                defensa del consumidor de tu jurisdicción.
              </p>
            } @else {
              <p class="legal-meta">
                Versión {{ config.config().privacy_version }} · Ley 25.326 de Protección de los
                Datos Personales.
              </p>
              <h3>1. Responsable del tratamiento</h3>
              <p>
                {{ config.config().store_legal_name }}, CUIT {{ config.config().store_cuit }},
                domicilio {{ config.config().store_address }}. Contacto para datos personales:
                {{ config.config().store_email }}.
              </p>

              <h3>2. Datos que recopilamos</h3>
              <p>
                Nombre y apellido, correo electrónico, teléfono, fecha de retiro, productos
                reservados, código de reserva y versiones de los documentos legales aceptados.
                También registramos datos técnicos mínimos para seguridad y prevención de abuso,
                como dirección IP y fecha de acceso.
              </p>

              <h3>3. Finalidad y base legal</h3>
              <p>
                Usamos tus datos para gestionar la reserva, coordinar el retiro, responder
                consultas, cumplir obligaciones legales y prevenir fraudes. El tratamiento se
                basa en tu consentimiento expreso, que otorgás al marcar la casilla
                correspondiente, y en las obligaciones legales aplicables.
              </p>

              <h3>4. Conservación y destinatarios</h3>
              <p>
                Conservamos los datos mientras sean necesarios para la finalidad y por los plazos
                legales aplicables. No vendemos ni cedemos tus datos a terceros con fines
                publicitarios. Podrán acceder prestadores tecnológicos que alojan el sitio,
                sujetos a deberes de confidencialidad.
              </p>

              <h3>5. Tus derechos</h3>
              <p>
                Podés ejercer los derechos de acceso, rectificación, actualización y supresión
                escribiendo a {{ config.config().store_email }}. La Agencia de Acceso a la
                Información Pública (AAIP) es la autoridad de control:
                <a [href]="config.config().aaip_url" target="_blank" rel="noopener">
                  {{ config.config().aaip_url }}
                </a>.
              </p>

              <h3>6. Cookies y almacenamiento local</h3>
              <p>
                Usamos almacenamiento local del navegador para recordar tu carrito y la sesión
                de administración. No utilizamos cookies publicitarias de terceros. Podés borrar
                estos datos desde la configuración de tu navegador.
              </p>

              <h3>7. Seguridad</h3>
              <p>
                Aplicamos medidas razonables de seguridad para proteger la información. Ningún
                sistema es absolutamente invulnerable, por lo que te pedimos que no compartas tu
                código de reserva con personas no autorizadas.
              </p>
            }
          </div>

          <footer class="modal-footer">
            <button type="button" class="btn btn-primary" (click)="legal.close()">
              Entendido
            </button>
          </footer>
        </section>
      </div>
    }
  `,
  styles: [
    `
      .modal-backdrop {
        position: fixed;
        inset: 0;
        z-index: 100;
        background: rgba(4, 32, 30, 0.6);
        backdrop-filter: blur(4px);
        display: grid;
        place-items: center;
        padding: 1rem;
      }
      .modal-panel {
        width: min(46rem, 100%);
        max-height: min(86vh, 52rem);
        display: flex;
        flex-direction: column;
        background: var(--surface);
        border-radius: 1.25rem;
        box-shadow: var(--shadow-lg);
        overflow: hidden;
      }
      .modal-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 1rem;
        padding: 1.35rem 1.5rem;
        border-bottom: 1px solid var(--border);
      }
      .modal-header h2 {
        margin: 0.15rem 0 0;
        font-size: 1.35rem;
      }
      .modal-body {
        padding: 1.35rem 1.5rem;
        overflow-y: auto;
      }
      .modal-footer {
        padding: 1rem 1.5rem;
        border-top: 1px solid var(--border);
        display: flex;
        justify-content: flex-end;
        background: var(--surface-alt);
      }
      .legal-copy h3 {
        font-size: 1rem;
        margin: 1.35rem 0 0.4rem;
        color: var(--teal-800);
      }
      .legal-copy p {
        margin: 0 0 0.75rem;
        color: var(--muted);
        line-height: 1.7;
        font-size: 0.93rem;
      }
      .legal-meta {
        font-size: 0.82rem;
        color: var(--teal-700);
        background: var(--teal-50);
        border-radius: 0.6rem;
        padding: 0.55rem 0.75rem;
        margin-bottom: 0.5rem;
      }
      .legal-copy a {
        color: var(--teal-700);
        word-break: break-word;
      }
    `,
  ],
})
export class LegalModalComponent {
  readonly config = inject(ConfigService);
  readonly legal = inject(LegalService);

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.legal.close();
  }
}
