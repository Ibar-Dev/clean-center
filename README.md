# Clean Center · Reservas Click & Collect

Sistema de reservas **Click & Collect** para Clean Center (Argentina). Los clientes
reservan productos de limpieza desde la web, reciben un código `CC-XXXXXX` y pagan
**exclusivamente en el local** al retirar. Incluye panel de administración para gestionar
reservas, stock y catálogo.

---

## Stack

| Capa      | Tecnología                                                                 |
| --------- | -------------------------------------------------------------------------- |
| Backend   | FastAPI · Pydantic v2 · SQLModel · SQLite (WAL) · `uv` · Loguru · SlowAPI  |
| Frontend  | Angular 22 (standalone, signals, zoneless) · TypeScript · CSS             |
| Auth      | JWT + Argon2 (solo administración, sin registro público)                   |
| Deploy    | Docker / Docker Compose · Nginx como reverse proxy · volumen `/app/data`   |
| Calidad   | pytest (59 tests) · Ruff · build de producción de Angular · sanity check E2E |

Compatible con **Python 3.12 y 3.13**. La imagen Docker usa Python 3.13.

---

## Estructura

```
clean-center/
├── backend/
│   ├── app/
│   │   ├── core/          # config, database (WAL), logging, seguridad, rate limit
│   │   ├── models/        # Product, Category, Reservation, ReservationItem, User
│   │   ├── schemas/       # Pydantic v2 (entrada/salida, dinero y fechas UTC)
│   │   ├── services/      # lógica de reservas, catálogo, admin, WhatsApp, seed
│   │   └── routers/       # health, config, auth, catalog, reservations, admin
│   ├── tests/             # pytest
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── uv.lock
├── frontend/
│   ├── src/app/
│   │   ├── core/          # modelos, servicios, guards, interceptor, formato
│   │   ├── features/      # catálogo, carrito, checkout, confirmación, consulta
│   │   ├── shared/        # header, footer, modal legal, toasts
│   │   └── app.*.ts       # rutas y configuración
│   ├── Dockerfile
│   ├── nginx.conf
│   └── proxy.conf.json
├── scripts/
│   └── sanity_check.py    # verificación end-to-end del stack Docker
├── Makefile
├── pyproject.toml         # herramienta de sanity check (httpx)
├── uv.lock
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Puesta en marcha local

### 1. Variables de entorno

```bash
cp .env.example .env
```

Editá `.env` y reemplazá **todos** los datos comerciales y legales por los reales.
Para generar un secreto JWT seguro:

```bash
openssl rand -hex 32
```

> `ENVIRONMENT=production` exige que `JWT_SECRET_KEY` y `ADMIN_PASSWORD` no sean los
> valores por defecto; la aplicación se niega a arrancar si lo son.

### 2. Backend

Requiere [`uv`](https://docs.astral.sh/uv/) y Python 3.12/3.13.

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

- API: <http://localhost:8000/api>
- Docs: <http://localhost:8000/api/docs>
- Health: <http://localhost:8000/api/health>

El arranque crea las tablas, activa WAL y siembra el catálogo inicial desde
`backend/app/data/catalog_seed.json`: 6 categorías ordenadas por `sort_order` y 68 productos
reales. El seed es idempotente y **insert-if-missing por `slug`**: nunca pisa precios, stock,
nombres ni el estado activo/inactivo que se hayan ajustado desde `/admin`. Todos los SKUs se
cargan con `stock: 50` como valor inicial para que Karen los ajuste desde el panel. También
crea el usuario administrador definido en `ADMIN_USERNAME` / `ADMIN_PASSWORD`.

### 3. Frontend

Requiere Node.js 20+ y npm.

```bash
cd frontend
npm ci
npm start
```

- App: <http://localhost:4200>
- El dev server proxya `/api` hacia `http://localhost:8000` (`proxy.conf.json`).

### 4. Panel de administración

- URL: <http://localhost:4200/admin/login>
- Usuario y contraseña: los definidos en `.env`.

Desde el panel podés:

- Filtrar/buscar reservas por estado, código, nombre o correo.
- Confirmar, marcar como retirada o cancelar reservas (la cancelación repone stock).
- Crear, editar, archivar y reactivar productos.

---

## Pruebas y calidad

```bash
cd backend
uv run pytest            # 59 tests
uv run ruff check .
uv run ruff format --check .
```

```bash
cd frontend
npm run build -- --configuration production
```

Los tests cubren: configuración pública sin secretos, autenticación JWT, catálogo, seed del
catálogo (idempotencia y no-sobrescritura de ediciones del admin), creación de reservas con
descuento atómico de stock, idempotencia de reservas ante reintentos, ventana de retiro,
cancelación con reposición de stock, transiciones de estado del admin, CRUD de productos,
snapshots de precio, formato de WhatsApp y modo WAL de SQLite.

---

## Docker / producción

```bash
cp .env.example .env   # editar con datos reales
docker compose up --build -d
```

- Frontend: <http://localhost:8080>
- Nginx sirve la SPA y proxya `/api/` al backend (`backend:8000`).
- La base SQLite vive en el volumen nombrado `clean_center_data` (`/app/data`).
- El backend corre como usuario sin privilegios (UID 10001), con 1 worker de Uvicorn.

Ver logs:

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

Detener sin borrar datos:

```bash
docker compose down
```

> `docker compose down -v` **elimina el volumen** y con él la base de datos.

### Persistencia y WAL

SQLite se configura por conexión con:

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
```

WAL permite lecturas concurrentes durante escrituras. Para verificar el modo:

```bash
docker compose exec backend python -c "
import sqlite3
conn = sqlite3.connect('/app/data/clean_center.db')
print(conn.execute('PRAGMA journal_mode;').fetchone())
"
```

---

## Sanity check del despliegue

Verifica de punta a punta el stack Docker **a través de Nginx** (`http://localhost:8080`)
usando `httpx`. Está pensado para ejecutarse después de `docker compose up` o como
paso de una rutina de despliegue.

### Requisitos

- Stack Docker levantado y saludable.
- `.env` en la raíz con las mismas variables que consume `docker compose`.
- `uv` y `docker` disponibles en el host.

### Ejecución

```bash
# Recomendado: levanta/recompila el stack, espera los healthchecks y verifica
make sanity-check-up

# Solo verifica un stack ya levantado
make sanity-check

# Igual, con detalle adicional de las peticiones
make sanity-check-verbose

# Equivalente directo
uv run python scripts/sanity_check.py
```

> El `pyproject.toml` de la raíz declara `httpx` como dependencia de la herramienta.
> `uv run` crea/sincroniza el entorno del proyecto automáticamente; no hace falta
> instalar nada aparte.

### Opciones

| Opción | Default | Descripción |
| ------ | ------- | ----------- |
| `--base-url URL` | `http://localhost:8080` o `SANITY_BASE_URL` | URL base del frontend. |
| `--env-file PATH` | `.env` | Variables contra las que se compara `/api/config`. |
| `--product-id ID` | primer producto activo con stock | Fuerza el producto a usar. |
| `--quantity N` | `1` | Cantidad reservada (1-99). |
| `--timeout SEGUNDOS` | `10` | Timeout por request HTTP. |
| `--compose-file PATH` | `docker-compose.yml` | Compose usado para la verificación WAL. |
| `--backend-container SERVICIO` | `backend` | Servicio/contenedor del backend para WAL. |
| `--verbose` | desactivado | Muestra detalle adicional de las peticiones. |

Ejemplos:

```bash
uv run python scripts/sanity_check.py --product-id 3 --quantity 2
uv run python scripts/sanity_check.py \
  --base-url http://127.0.0.1:8080 --verbose
make sanity-check SANITY_ARGS='--product-id 3 --quantity 2'
```

### Cobertura

1. `GET /api/health` responde `{"status": "ok"}`.
2. `GET /api/config` coincide con `.env` y no expone campos sensibles.
3. Nginx envía `X-Frame-Options: SAMEORIGIN` y `X-Content-Type-Options: nosniff`
   en la raíz, en un asset estático y en `/api/health`.
4. Selección del primer producto activo con `stock >= cantidad` (o `--product-id`)
   y captura de su stock/precio.
5. Creación de una reserva con precio y total esperados.
6. Descuento exacto de stock en el catálogo.
7. Consulta pública por código + email.
8. Cancelación de la reserva.
9. Reposición exacta del stock original.
10. Login de administración con JWT y rol `ADMIN`.
11. La reserva cancelada aparece en el listado admin (auditoría).
12. Edición admin de precio/stock y relectura de la persistencia.
13. `PRAGMA journal_mode` devuelve `wal` dentro del contenedor del backend.

### Datos creados y limpieza

- Cada ejecución crea **una reserva** y la cancela. Como las reservas son inmutables
  y no existe endpoint de borrado, el registro queda en estado `CANCELADO` como
  registro de auditoría. Es el comportamiento esperado.
- La verificación admin modifica temporalmente precio y stock de un producto y los
  restaura al finalizar, incluso si una verificación falla.
- Si la limpieza no puede completarse, el script informa el recurso afectado y sale
  con código `1`.

### Códigos de salida

| Código | Significado |
| ------ | ----------- |
| `0` | Todas las verificaciones y la limpieza terminaron correctamente. |
| `1` | Falló una verificación o la limpieza de los datos de prueba. |
| `2` | Error de configuración/entorno: falta `.env`, faltan variables, argumentos inválidos, stack o Docker no disponible. |

### Rate limiting

Cada ejecución consume aproximadamente:

- `1` creación de reserva (`RESERVATION_RATE_LIMIT`, por defecto `5/minute`).
- `1` consulta + `1` cancelación (`LOOKUP_RATE_LIMIT`, por defecto `10/minute`).
- `1` login admin (`LOGIN_RATE_LIMIT`, por defecto `5/minute`).

No ejecutes el sanity check más de **5 veces por minuto**: el backend respondería
`429 Too Many Requests`. En ese caso el script falla con código `1` y muestra el
detalle devuelto por la API; esperá un minuto y volvé a intentar.

---

## Backups

La base es un único archivo SQLite (más `-wal` y `-shm`). Opciones:

```bash
# Backup consistente con la API detenida
docker compose stop backend
docker run --rm -v clean_center_data:/data -v "$PWD/backups:/backup" alpine \
  tar czf /backup/clean-center-$(date +%F).tar.gz -C /data .
docker compose start backend
```

También podés usar `sqlite3 /app/data/clean_center.db ".backup '/app/data/backup.db'"`
con el contenedor en ejecución. Guardá los backups fuera del host del contenedor y
probá periódicamente la restauración.

---

## API principal

| Método | Ruta                                | Descripción                                   |
| ------ | ----------------------------------- | --------------------------------------------- |
| GET    | `/api/health`                       | Healthcheck                                   |
| GET    | `/api/config`                       | Configuración comercial pública (sin secretos)|
| GET    | `/api/categories`                   | Categorías                                    |
| GET    | `/api/products`                     | Catálogo paginado, búsqueda y categoría       |
| GET    | `/api/products/{id}`                | Detalle de producto                           |
| POST   | `/api/reservations`                 | Crear reserva (descuenta stock; `idempotency_key` opcional) |
| POST   | `/api/reservations/lookup`          | Consultar por código + email                  |
| POST   | `/api/reservations/{code}/cancel`   | Cancelar y reponer stock                      |
| POST   | `/api/auth/login`                   | Login admin (JWT)                             |
| GET    | `/api/auth/me`                      | Usuario actual                                |
| GET    | `/api/admin/reservations`           | Listado admin con filtros                     |
| GET    | `/api/admin/reservations/{id}`      | Detalle admin                                 |
| PATCH  | `/api/admin/reservations/{id}/status`| Cambiar estado                                |
| GET    | `/api/admin/products`               | Listado admin (incluye archivados)            |
| GET    | `/api/admin/categories`             | Categorías para el formulario                 |
| POST   | `/api/admin/products`               | Crear producto                                |
| PATCH  | `/api/admin/products/{id}`          | Editar producto                               |
| PATCH  | `/api/admin/products/{id}/status`   | Activar / archivar                            |

### Formato de dinero y fechas

- Dinero serializado como string decimal con dos decimales (`"1500.50"`).
- Fechas ISO 8601 en UTC; el frontend las muestra en
  `America/Argentina/Buenos_Aires`.
- `GET /api/config` envía `Cache-Control: public, max-age=60`.

---

## Configuración dinámica

El frontend carga `GET /api/config` al iniciar y usa esos valores para:

- Nombre, razón social, dirección, teléfono, email y horarios del footer.
- Textos legales (T&C y privacidad) y versiones de los documentos.
- Ventana de retiro (mínimo de anticipación y vencimiento).
- Disponibilidad del envío por WhatsApp.

Variables disponibles:

| Variable                       | Uso                                              |
| ------------------------------ | ------------------------------------------------ |
| `STORE_NAME`                   | Nombre comercial                                 |
| `STORE_LEGAL_NAME`             | Razón social                                     |
| `STORE_CUIT`                   | CUIT (se conserva en la API; no se muestra en la UI) |
| `STORE_ADDRESS`                | Dirección de retiro                              |
| `STORE_PHONE` / `STORE_EMAIL`  | Contacto                                         |
| `STORE_HOURS`                  | Horario de atención                              |
| `RESERVATION_EXPIRATION_HOURS` | Garantía de precio / vencimiento de la reserva   |
| `MIN_PICKUP_LEAD_MINUTES`      | Anticipación mínima para el retiro               |
| `AAIP_URL`                     | Enlace a la AAIP                                 |
| `TERMS_VERSION` / `PRIVACY_VERSION` | Versión de los documentos aceptados         |

`GET /api/config` usa un esquema público explícito: **nunca** serializa el objeto de
settings completo ni expone JWT, contraseñas o `DATABASE_URL`.

---

## WhatsApp

`WHATSAPP_PHONE` debe ir con código de país, sin `+`, espacios ni guiones
(ej.: `5491123456789`). Con un número válido, el backend genera un enlace
`https://wa.me/<número>?text=<mensaje>` que incluye:

- Nombre del comercio (`STORE_NAME`) y dirección (`STORE_ADDRESS`).
- Código de reserva, fecha de retiro, productos, cantidades y total.
- Aclaración de pago en el local.

No se usa la API de Meta: el cliente abre WhatsApp y **envía el mensaje manualmente**.

---

## Notificaciones al crear una reserva

Al confirmar una reserva, el backend encola dos tareas en `BackgroundTasks` (después de
responder y de commitear en SQLite):

1. **Email al cliente** con el código de reserva, productos, total, dirección y horarios.
2. **Email de aviso a `ADMIN_EMAIL`** (o a `STORE_EMAIL` si queda vacío) con los datos del
   cliente y la lista de productos a preparar.
3. **Mensaje de Telegram** al chat configurado, si `TELEGRAM_BOT_TOKEN` y
   `TELEGRAM_CHAT_ID` están presentes.

Ninguna notificación puede hacer fallar ni revertir la reserva: si falta configuración o
el proveedor falla/timeout (10 s), se registra un warning en Loguru y se continúa.

### Email (SMTP)

| Variable        | Default | Uso                                              |
| --------------- | ------- | ------------------------------------------------ |
| `SMTP_HOST`     | vacío   | Servidor SMTP. Vacío deshabilita el envío.       |
| `SMTP_PORT`     | `587`   | Puerto SMTP.                                     |
| `SMTP_USER`     | vacío   | Usuario para autenticación (opcional).           |
| `SMTP_PASSWORD` | vacío   | Contraseña o App Password.                       |
| `SMTP_FROM`     | vacío   | Remitente. Debe coincidir con `SMTP_USER`.       |
| `SMTP_TLS`      | `true`  | Usa STARTTLS (puerto 587).                       |
| `ADMIN_EMAIL`   | vacío   | Recibe el aviso de nuevos pedidos.               |

Para Gmail: `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_TLS=true` y una
**contraseña de aplicación** de 16 caracteres (requiere verificación en 2 pasos). La
contraseña normal de la cuenta es rechazada.

### Telegram

1. Crear un bot con `@BotFather` y copiar el token en `TELEGRAM_BOT_TOKEN`.
2. Iniciar una conversación con el bot y obtener el `chat_id` (por ejemplo con
   `https://api.telegram.org/bot<TOKEN>/getUpdates`) en `TELEGRAM_CHAT_ID`.

Sin token o sin chat, la notificación se omite silenciosamente.

> El `BackgroundTasks` de FastAPI se ejecuta con el `TestClient` en los tests, por lo que
> `conftest.py` deja `SMTP_HOST`, `ADMIN_EMAIL`, `TELEGRAM_BOT_TOKEN` y
> `TELEGRAM_CHAT_ID` vacíos para evitar envíos reales.

---

## Cumplimiento legal (Argentina)

La aplicación incluye:

- **Términos y Condiciones** en modal, con pago en el local y garantía de precio
  configurable (por defecto 48 h).
- **Política de Privacidad** con referencia a la **Ley 25.326** y a la **AAIP**.
- **Consentimiento expreso** obligatorio antes de crear la reserva; se guardan
  `terms_version`, `privacy_version` y las marcas de tiempo.
- **Botón de Arrepentimiento** visible en el footer y flujo de consulta/cancelación
  conforme a la **Resolución 424/2020** y la **Ley 24.240**.
- Cancelación sin costo (no hay cobro online) con reposición de stock.

> **Importante:** los textos legales son un punto de partida técnico, no asesoramiento
> jurídico. Antes de publicar, reemplazá `STORE_*`, `AAIP_URL` y las versiones de los
> documentos por los datos reales del comercio y hacé revisar los textos por un
> profesional. Verificá también las obligaciones de inscripción y conservación de datos
> aplicables a tu operatoria.

---

## Decisiones de implementación

- Stock se descuenta de forma atómica (`UPDATE ... WHERE stock >= cantidad RETURNING`)
  al crear la reserva y se repone al cancelar (cliente o admin).
- Reservas idempotentes: si el cliente reintenta tras un corte de red con la misma
  `idempotency_key` (UUID que el frontend guarda en `sessionStorage`), el backend devuelve la
  reserva existente con `200` sin volver a descontar stock. Una reserva nueva responde `201`.
- Los ítems de reserva guardan **snapshot** de nombre, unidad y precio: cambios
  posteriores de precio no alteran reservas existentes.
- Códigos `CC-XXXXXX` con alfabeto sin caracteres ambiguos (`0/O`, `1/I`).
- Reservas sin vencimiento automático programado en esta versión (MVP); el campo
  `expires_at` se informa y muestra, y puede usarse para una tarea futura.
- Sin registro público de usuarios: el administrador se aprovisiona por variables de
  entorno.
- Rate limiting por IP: reservas `5/minute`, consultas `10/minute`, login `5/minute`.
- Se registran request/SQLite/auth con Loguru (JSON opcional con `LOG_JSON=true`).

---

## Checklist antes de producción

- [ ] `.env` con datos comerciales y legales reales.
- [ ] `JWT_SECRET_KEY` generado con `openssl rand -hex 32`.
- [ ] `ADMIN_PASSWORD` robusta y única.
- [ ] `CORS_ORIGINS` limitado al dominio real (si se usa frontend separado).
- [ ] HTTPS terminado en un proxy inverso delante de Nginx.
- [ ] Backups automáticos del volumen `clean_center_data`.
- [ ] Textos legales revisados y versiones actualizadas.
- [ ] Monitoreo de `/api/health` y de los logs del backend.
