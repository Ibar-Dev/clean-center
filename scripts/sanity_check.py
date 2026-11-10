#!/usr/bin/env python3
"""Sanity check end-to-end del despliegue Docker de Clean Center.

Ejecuta el flujo completo a través de Nginx (por defecto http://localhost:8080):
healthcheck, configuración pública, headers de seguridad, catálogo, ciclo de vida
de una reserva, autenticación de administración, persistencia de productos y
modo WAL de SQLite dentro del contenedor del backend.

Códigos de salida:
    0  Todas las verificaciones y la limpieza terminaron correctamente.
    1  Falló una verificación o la limpieza de los datos de prueba.
    2  Error de configuración o de entorno (por ejemplo, falta .env o el stack
       no está disponible).
"""

from __future__ import annotations

import argparse
import contextlib
import os
import re
import subprocess
import sys
import traceback
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILE = REPO_ROOT / ".env"
DEFAULT_COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"
DEFAULT_BASE_URL = "http://localhost:8080"

EXIT_OK = 0
EXIT_CHECK = 1
EXIT_CONFIG = 2

RESERVATION_CODE_RE = re.compile(r"^CC-[A-HJ-NP-Z2-9]{6}$")
ASSET_RE = re.compile(
    r'(?:src|href)="([^"]+\.(?:js|css|woff2?|ttf|eot|ico|png|jpg|jpeg|gif|svg|webp))"'
)
ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

EXPECTED_CONFIG_KEYS = {
    "store_name",
    "store_legal_name",
    "store_cuit",
    "store_address",
    "store_phone",
    "store_email",
    "store_hours",
    "reservation_expiration_hours",
    "min_pickup_lead_minutes",
    "aaip_url",
    "terms_version",
    "privacy_version",
    "whatsapp_available",
}
SENSITIVE_KEY_PARTS = ("password", "secret", "token", "database", "jwt")
SECURITY_HEADERS = {
    "x-frame-options": "SAMEORIGIN",
    "x-content-type-options": "nosniff",
}

# (variable .env, campo de /api/config, tipo de comparación)
CONFIG_COMPARISONS: tuple[tuple[str, str, str], ...] = (
    ("STORE_NAME", "store_name", "text"),
    ("STORE_LEGAL_NAME", "store_legal_name", "text"),
    ("STORE_CUIT", "store_cuit", "text"),
    ("STORE_ADDRESS", "store_address", "text"),
    ("STORE_PHONE", "store_phone", "text"),
    ("STORE_EMAIL", "store_email", "email"),
    ("STORE_HOURS", "store_hours", "text"),
    ("RESERVATION_EXPIRATION_HOURS", "reservation_expiration_hours", "int"),
    ("MIN_PICKUP_LEAD_MINUTES", "min_pickup_lead_minutes", "int"),
    ("AAIP_URL", "aaip_url", "url"),
    ("TERMS_VERSION", "terms_version", "text"),
    ("PRIVACY_VERSION", "privacy_version", "text"),
)
REQUIRED_ENV_KEYS = ("ADMIN_USERNAME", "ADMIN_PASSWORD")
CONFIG_ENV_KEYS = (*tuple(item[0] for item in CONFIG_COMPARISONS), "WHATSAPP_PHONE")


class ConfigError(Exception):
    """Error de configuración o de entorno (código de salida 2)."""


class CheckFailure(Exception):
    """Fallo de una verificación o de la limpieza (código de salida 1)."""


class Reporter:
    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose

    def info(self, message: str) -> None:
        print(f"[INFO] {message}", flush=True)

    def ok(self, message: str) -> None:
        print(f"[ OK ] {message}", flush=True)

    def fail(self, message: str) -> None:
        print(f"[FAIL] {message}", file=sys.stderr, flush=True)

    def cleanup(self, message: str) -> None:
        print(f"[CLEAN] {message}", flush=True)

    def debug(self, message: str) -> None:
        if self.verbose:
            print(f"[DEBUG] {message}", flush=True)


@dataclass
class ProductState:
    id: int
    name: str
    price: str
    stock: int


@dataclass
class ReservationState:
    id: int
    code: str
    email: str
    cancelled: bool = False


@dataclass
class Context:
    env: dict[str, str]
    base_url: str
    client: httpx.Client
    reporter: Reporter
    quantity: int
    product_id: int | None
    compose_file: Path
    backend_container: str
    token: str | None = None
    product: ProductState | None = None
    product_modified: bool = False
    reservation: ReservationState | None = None
    config: dict[str, Any] = field(default_factory=dict)
    checks_ok: int = 0
    checks_total: int = 0
    current_step: str = "Verificación"

    def auth_headers(self) -> dict[str, str]:
        if self.token is None:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    def request(
        self,
        method: str,
        path: str,
        *,
        expected: int = 200,
        params: dict[str, Any] | None = None,
        json: Any = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        self.reporter.debug(f"{method} {path}")
        try:
            response = self.client.request(
                method,
                path,
                params=params,
                json=json,
                headers=headers,
            )
        except httpx.HTTPError as exc:
            raise ConfigError(f"No se pudo conectar con {self.base_url}{path}: {exc}") from exc

        if response.status_code in {502, 504}:
            raise ConfigError(
                f"{method} {path} devolvió HTTP {response.status_code}; "
                "el stack no está disponible en este momento."
            )
        if response.status_code != expected:
            raise CheckFailure(
                f"{method} {path} devolvió HTTP {response.status_code} "
                f"(esperado {expected}): {response_detail(response)}"
            )
        self.reporter.debug(f"{method} {path} -> HTTP {response.status_code}")
        return response


def response_detail(response: httpx.Response) -> str:
    """Devuelve un detalle seguro de la respuesta, sin cuerpos completos."""
    try:
        payload = response.json()
    except ValueError:
        return response.reason_phrase
    if isinstance(payload, dict) and "detail" in payload:
        return str(payload["detail"])[:500]
    return response.reason_phrase


def get_any(client: httpx.Client, path: str) -> httpx.Response:
    try:
        return client.get(path)
    except httpx.HTTPError as exc:
        raise ConfigError(f"No se pudo conectar con {path}: {exc}") from exc


def load_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise ConfigError(
            f"No se encontró el archivo .env en {path}. "
            "Copiá .env.example a .env y configurá los valores."
        )
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise ConfigError(f"No se pudo leer {path}: {exc}") from exc

    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not ENV_KEY_RE.fullmatch(key):
            raise ConfigError(f"Línea {line_number} de {path}: clave de entorno inválida {key!r}.")
        values[key] = _parse_env_value(value.strip())
    return values


def _parse_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    comment_index = value.find(" #")
    if comment_index != -1:
        return value[:comment_index].rstrip()
    return value


def require_env(env: dict[str, str]) -> None:
    missing_required = [key for key in REQUIRED_ENV_KEYS if not env.get(key)]
    if missing_required:
        raise ConfigError("Faltan variables obligatorias en .env: " + ", ".join(missing_required))
    missing_public = [key for key in CONFIG_ENV_KEYS if key not in env]
    if missing_public:
        raise ConfigError("Faltan variables públicas en .env: " + ", ".join(missing_public))


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("debe ser un entero positivo") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("debe ser un entero positivo")
    return number


def _quantity(value: str) -> int:
    number = _positive_int(value)
    if number > 99:
        raise argparse.ArgumentTypeError("la cantidad máxima es 99")
    return number


def _positive_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("debe ser un número positivo") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("debe ser un número positivo")
    return number


def _base_url(value: str) -> str:
    cleaned = value.strip().rstrip("/")
    parsed = urlsplit(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise argparse.ArgumentTypeError(
            "debe ser una URL http(s) válida, por ejemplo http://localhost:8080"
        )
    if parsed.path not in {"", "/"}:
        raise argparse.ArgumentTypeError("la URL no debe incluir un path")
    return cleaned


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verifica de punta a punta el stack Docker de Clean Center.",
        epilog=(
            "Códigos de salida: 0 = OK; 1 = fallo de verificación o limpieza; "
            "2 = error de configuración o entorno."
        ),
    )
    parser.add_argument(
        "--base-url",
        type=_base_url,
        default=DEFAULT_BASE_URL,
        help=f"URL base del frontend (default: SANITY_BASE_URL o {DEFAULT_BASE_URL}).",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_FILE,
        metavar="PATH",
        help=f"Archivo de variables de entorno (default: {DEFAULT_ENV_FILE}).",
    )
    parser.add_argument(
        "--product-id",
        type=_positive_int,
        default=None,
        metavar="ID",
        help="Producto a usar; por defecto, el primero activo con stock suficiente.",
    )
    parser.add_argument(
        "--quantity",
        type=_quantity,
        default=1,
        metavar="N",
        help="Cantidad a reservar por producto (default: 1).",
    )
    parser.add_argument(
        "--timeout",
        type=_positive_float,
        default=10.0,
        metavar="SEGUNDOS",
        help="Timeout por request HTTP (default: 10).",
    )
    parser.add_argument(
        "--compose-file",
        type=Path,
        default=DEFAULT_COMPOSE_FILE,
        metavar="PATH",
        help=f"Archivo Compose para la verificación WAL (default: {DEFAULT_COMPOSE_FILE}).",
    )
    parser.add_argument(
        "--backend-container",
        default="backend",
        metavar="SERVICIO",
        help="Servicio/contenedor del backend para la verificación WAL (default: backend).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Muestra detalle adicional de las peticiones.",
    )
    try:
        parser.set_defaults(base_url=_base_url(os.environ.get("SANITY_BASE_URL", DEFAULT_BASE_URL)))
    except argparse.ArgumentTypeError as exc:
        parser.error(f"valor de SANITY_BASE_URL inválido: {exc}")
    return parser.parse_args(argv)


def run_step(
    ctx: Context,
    reporter: Reporter,
    name: str,
    check: Callable[[Context, Reporter], None],
) -> None:
    ctx.checks_total += 1
    ctx.current_step = name
    check(ctx, reporter)
    ctx.checks_ok += 1
    reporter.ok(f"{ctx.checks_total:02d}. {name}")


def run_all(ctx: Context, reporter: Reporter) -> None:
    steps: tuple[tuple[str, Callable[[Context, Reporter], None]], ...] = (
        ("Healthcheck del stack", check_health),
        ("Configuración pública coincide con .env", check_public_config),
        ("Headers de seguridad de Nginx", check_nginx_headers),
        ("Catálogo: producto de prueba", check_catalog_product),
        ("Creación de reserva", check_create_reservation),
        ("Descuento exacto de stock", check_stock_decrement),
        ("Consulta pública de la reserva", check_lookup_reservation),
        ("Cancelación de la reserva", check_cancel_reservation),
        ("Reposición exacta de stock", check_stock_restored),
        ("Login de administrador (JWT)", check_admin_login),
        ("Listado admin de la reserva cancelada", check_admin_reservations),
        ("Persistencia de precio y stock desde admin", check_admin_product),
        ("SQLite en modo WAL dentro del contenedor", check_wal),
    )
    for name, check in steps:
        run_step(ctx, reporter, name, check)


def check_health(ctx: Context, reporter: Reporter) -> None:
    response = get_any(ctx.client, "/api/health")
    if response.status_code in {502, 503, 504}:
        raise ConfigError(
            f"/api/health devolvió HTTP {response.status_code}; "
            "el stack todavía no está listo o el backend no responde."
        )
    if response.status_code != 200:
        raise CheckFailure(
            f"/api/health devolvió HTTP {response.status_code}: {response_detail(response)}"
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise CheckFailure("/api/health no devolvió JSON válido.") from exc
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        raise CheckFailure(f"Respuesta inesperada de /api/health: {payload!r}")
    reporter.debug("Backend saludable.")


def check_public_config(ctx: Context, reporter: Reporter) -> None:
    response = ctx.request("GET", "/api/config")
    try:
        payload = response.json()
    except ValueError as exc:
        raise CheckFailure("/api/config no devolvió JSON válido.") from exc
    if not isinstance(payload, dict):
        raise CheckFailure("/api/config no devolvió un objeto JSON.")

    missing = sorted(EXPECTED_CONFIG_KEYS - set(payload))
    if missing:
        raise CheckFailure(
            "La configuración pública no incluye los campos esperados: " + ", ".join(missing)
        )
    leaked = sorted(
        key for key in payload if any(part in key.lower() for part in SENSITIVE_KEY_PARTS)
    )
    if leaked:
        raise CheckFailure("La configuración pública expone campos sensibles: " + ", ".join(leaked))

    for env_key, config_key, kind in CONFIG_COMPARISONS:
        raw_value = ctx.env[env_key].strip()
        actual = payload.get(config_key)
        if kind == "int":
            try:
                expected: Any = int(raw_value)
            except ValueError as exc:
                raise ConfigError(
                    f"{env_key} debe ser un entero; valor recibido: {raw_value!r}"
                ) from exc
            if actual != expected:
                raise CheckFailure(
                    f"/api/config.{config_key}={actual!r} no coincide con "
                    f"{env_key}={expected!r} en .env."
                )
        elif kind == "url":
            if str(actual).rstrip("/") != raw_value.rstrip("/"):
                raise CheckFailure(
                    f"/api/config.{config_key}={actual!r} no coincide con "
                    f"{env_key}={raw_value!r} en .env."
                )
        elif kind == "email":
            if str(actual).lower() != raw_value.lower():
                raise CheckFailure(
                    f"/api/config.{config_key}={actual!r} no coincide con "
                    f"{env_key}={raw_value!r} en .env."
                )
        elif str(actual) != raw_value:
            raise CheckFailure(
                f"/api/config.{config_key}={actual!r} no coincide con "
                f"{env_key}={raw_value!r} en .env."
            )

    raw_phone = ctx.env.get("WHATSAPP_PHONE", "")
    digits = "".join(character for character in raw_phone if character.isdigit())
    expected_whatsapp = 8 <= len(digits) <= 15
    if bool(payload.get("whatsapp_available")) != expected_whatsapp:
        raise CheckFailure("/api/config.whatsapp_available no coincide con WHATSAPP_PHONE en .env.")

    ctx.config = payload
    reporter.debug("Configuración pública validada contra .env.")


def check_nginx_headers(ctx: Context, reporter: Reporter) -> None:
    root = get_any(ctx.client, "/")
    if root.status_code != 200:
        raise CheckFailure(f"La raíz del frontend devolvió HTTP {root.status_code}.")

    asset_path = _first_asset_path(root.text)
    asset = get_any(ctx.client, asset_path)
    if asset.status_code >= 500:
        raise CheckFailure(f"El asset {asset_path} devolvió HTTP {asset.status_code}.")

    health = get_any(ctx.client, "/api/health")
    if health.status_code in {502, 503, 504}:
        raise ConfigError(f"/api/health devolvió HTTP {health.status_code} al verificar headers.")
    if health.status_code != 200:
        raise CheckFailure(f"/api/health devolvió HTTP {health.status_code} al verificar headers.")

    for label, response in (
        ("/", root),
        (asset_path, asset),
        ("/api/health", health),
    ):
        for header, expected_value in SECURITY_HEADERS.items():
            actual_value = response.headers.get(header)
            if actual_value != expected_value:
                raise CheckFailure(
                    f"{label} no devolvió {header}: {expected_value!r} "
                    f"(recibido: {actual_value!r})."
                )
    reporter.debug(f"Headers verificados en /, {asset_path} y /api/health.")


def _first_asset_path(html: str) -> str:
    match = ASSET_RE.search(html)
    if match is None:
        return "/favicon.ico"
    candidate = match.group(1).split("?", 1)[0]
    if candidate.startswith(("http://", "https://")):
        candidate = urlsplit(candidate).path or "/"
    return candidate if candidate.startswith("/") else f"/{candidate}"


def check_catalog_product(ctx: Context, reporter: Reporter) -> None:
    if ctx.product_id is not None:
        try:
            payload = ctx.request("GET", f"/api/products/{ctx.product_id}").json()
        except CheckFailure as exc:
            raise CheckFailure(f"No se pudo usar --product-id {ctx.product_id}: {exc}") from exc
        if not isinstance(payload, dict):
            raise CheckFailure("El detalle del producto no devolvió un objeto JSON.")
    else:
        payload = _find_product_with_stock(ctx)

    try:
        product_id = int(payload["id"])
        name = str(payload["name"])
        price = str(payload["price"])
        stock = int(payload["stock"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CheckFailure(
            f"El producto del catálogo tiene un formato inesperado: {payload!r}"
        ) from exc

    if payload.get("is_active") is not True:
        raise CheckFailure(f"El producto #{product_id} no está activo.")
    if stock < ctx.quantity:
        raise CheckFailure(
            f"El producto #{product_id} tiene stock {stock}, "
            f"insuficiente para la cantidad {ctx.quantity}."
        )
    try:
        Decimal(price)
    except InvalidOperation as exc:
        raise CheckFailure(
            f"El producto #{product_id} tiene un precio inválido: {price!r}"
        ) from exc

    ctx.product = ProductState(id=product_id, name=name, price=price, stock=stock)
    reporter.info(f"Producto de prueba: #{product_id} {name} | stock={stock} | precio={price}")


def _find_product_with_stock(ctx: Context) -> dict[str, Any]:
    page = 1
    while True:
        response = ctx.request(
            "GET",
            "/api/products",
            params={"page": page, "page_size": 50},
        )
        try:
            body = response.json()
        except ValueError as exc:
            raise CheckFailure("El catálogo no devolvió JSON válido.") from exc
        if not isinstance(body, dict):
            raise CheckFailure("El catálogo no devolvió un objeto JSON.")
        items = body.get("items") or []
        if not isinstance(items, list):
            raise CheckFailure("El catálogo devolvió una lista de productos inválida.")
        for item in items:
            if (
                isinstance(item, dict)
                and item.get("is_active") is True
                and int(item.get("stock", 0)) >= ctx.quantity
            ):
                return item
        pages = int(body.get("pages") or 0)
        if page >= pages:
            break
        page += 1
    raise CheckFailure(
        "No hay productos activos con stock suficiente. "
        "Reponé stock o usá --product-id para elegir otro producto."
    )


def check_create_reservation(ctx: Context, reporter: Reporter) -> None:
    product = require_product(ctx)
    lead_seconds = int(ctx.config["min_pickup_lead_minutes"]) * 60
    expiration_seconds = int(ctx.config["reservation_expiration_hours"]) * 3600
    offset_seconds = lead_seconds + 30
    if offset_seconds >= expiration_seconds:
        offset_seconds = (lead_seconds + expiration_seconds) // 2
    if offset_seconds <= lead_seconds:
        raise ConfigError("La ventana de retiro configurada no permite elegir una fecha válida.")
    pickup_date = (datetime.now(UTC) + timedelta(seconds=offset_seconds)).replace(microsecond=0)

    run_id = uuid.uuid4().hex[:8]
    email = f"sanity-check+{run_id}@example.com"
    payload = {
        "customer_name": "Sanity",
        "customer_last_name": "Check",
        "customer_email": email,
        "customer_phone": "+54 11 5555-0000",
        "pickup_date": pickup_date.isoformat(),
        "items": [{"product_id": product.id, "quantity": ctx.quantity}],
        "terms_accepted": True,
        "privacy_consent": True,
    }
    response = ctx.request("POST", "/api/reservations", json=payload, expected=201)
    try:
        body = response.json()
    except ValueError as exc:
        raise CheckFailure("La creación de la reserva no devolvió JSON válido.") from exc
    if not isinstance(body, dict):
        raise CheckFailure("La creación de la reserva no devolvió un objeto JSON.")

    reservation_id = int(body.get("id") or 0)
    code = body.get("code")
    if isinstance(code, str) and code:
        ctx.reservation = ReservationState(
            id=reservation_id,
            code=code,
            email=email,
        )
    if not isinstance(code, str) or RESERVATION_CODE_RE.fullmatch(code) is None:
        raise CheckFailure(f"La reserva devolvió un código inválido: {code!r}")
    if body.get("status") != "PENDIENTE":
        raise CheckFailure(
            f"La reserva {code} quedó en estado {body.get('status')!r}; se esperaba 'PENDIENTE'."
        )
    if str(body.get("customer_email", "")).lower() != email:
        raise CheckFailure(f"La reserva {code} devolvió otro correo electrónico.")
    if not body.get("pickup_date"):
        raise CheckFailure(f"La reserva {code} no devolvió la fecha de retiro.")

    items = body.get("items")
    if not isinstance(items, list) or len(items) != 1:
        raise CheckFailure(f"La reserva {code} devolvió ítems inválidos.")
    item = items[0]
    try:
        item_product_id = int(item["product_id"])
        item_quantity = int(item["quantity"])
        unit_price = Decimal(str(item["unit_price"]))
        total_amount = Decimal(str(body["total_amount"]))
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise CheckFailure(f"La reserva {code} devolvió importes o ítems inválidos.") from exc
    if item_product_id != product.id:
        raise CheckFailure(f"La reserva {code} devolvió otro producto.")
    if item_quantity != ctx.quantity:
        raise CheckFailure(f"La reserva {code} devolvió otra cantidad.")
    expected_unit_price = Decimal(product.price)
    if unit_price != expected_unit_price:
        raise CheckFailure(
            f"La reserva {code} guardó un precio unitario {unit_price} "
            f"distinto de {expected_unit_price}."
        )
    expected_total = (expected_unit_price * ctx.quantity).quantize(Decimal("0.01"))
    if total_amount != expected_total:
        raise CheckFailure(
            f"La reserva {code} guardó un total {total_amount} distinto de {expected_total}."
        )

    raw_whatsapp = ctx.env.get("WHATSAPP_PHONE", "")
    whatsapp_digits = "".join(character for character in raw_whatsapp if character.isdigit())
    whatsapp_url = body.get("whatsapp_url")
    if 8 <= len(whatsapp_digits) <= 15:
        expected_whatsapp = f"https://wa.me/{whatsapp_digits}?text="
        if not isinstance(whatsapp_url, str) or not whatsapp_url.startswith(expected_whatsapp):
            raise CheckFailure(
                f"La reserva {code} devolvió una URL de WhatsApp inválida: {whatsapp_url!r}; "
                f"se esperaba que empiece con {expected_whatsapp!r}."
            )
    elif whatsapp_url is not None:
        raise CheckFailure(
            f"La reserva {code} devolvió una URL de WhatsApp sin un WHATSAPP_PHONE válido."
        )

    reporter.info(f"Reserva creada: {code} (id={reservation_id}).")


def check_stock_decrement(ctx: Context, reporter: Reporter) -> None:
    product = require_product(ctx)
    require_reservation(ctx)
    response = ctx.request("GET", f"/api/products/{product.id}")
    try:
        body = response.json()
    except ValueError as exc:
        raise CheckFailure("El detalle del producto no devolvió JSON válido.") from exc
    if not isinstance(body, dict):
        raise CheckFailure("El detalle del producto no devolvió un objeto JSON.")
    expected_stock = product.stock - ctx.quantity
    actual_stock = int(body.get("stock", -1))
    if actual_stock != expected_stock:
        raise CheckFailure(
            f"El stock del producto #{product.id} es {actual_stock}; "
            f"se esperaba {expected_stock} tras reservar."
        )
    reporter.debug(f"Stock descontado: {product.stock} -> {actual_stock}.")


def check_lookup_reservation(ctx: Context, reporter: Reporter) -> None:
    reservation = require_reservation(ctx)
    response = ctx.request(
        "POST",
        "/api/reservations/lookup",
        json={"code": reservation.code, "email": reservation.email},
    )
    try:
        body = response.json()
    except ValueError as exc:
        raise CheckFailure("La consulta de la reserva no devolvió JSON válido.") from exc
    if not isinstance(body, dict):
        raise CheckFailure("La consulta no devolvió un objeto JSON.")
    if body.get("code") != reservation.code:
        raise CheckFailure("La consulta devolvió otra reserva.")
    if body.get("status") != "PENDIENTE":
        raise CheckFailure(
            f"La consulta devolvió estado {body.get('status')!r}; se esperaba 'PENDIENTE'."
        )
    reporter.debug(f"Reserva {reservation.code} consultada correctamente.")


def check_cancel_reservation(ctx: Context, reporter: Reporter) -> None:
    reservation = require_reservation(ctx)
    response = ctx.request(
        "POST",
        f"/api/reservations/{quote(reservation.code, safe='')}/cancel",
        json={
            "email": reservation.email,
            "reason": "Sanity check automático: cancelación de prueba",
        },
    )
    try:
        body = response.json()
    except ValueError as exc:
        raise CheckFailure("La cancelación no devolvió JSON válido.") from exc
    if not isinstance(body, dict):
        raise CheckFailure("La cancelación no devolvió un objeto JSON.")
    if body.get("status") != "CANCELADO":
        raise CheckFailure(
            f"La reserva {reservation.code} quedó en estado {body.get('status')!r}; "
            "se esperaba 'CANCELADO'."
        )
    if not body.get("cancelled_at"):
        raise CheckFailure(f"La reserva {reservation.code} no registró la fecha de cancelación.")
    reservation.cancelled = True
    reporter.debug(f"Reserva {reservation.code} cancelada.")


def check_stock_restored(ctx: Context, reporter: Reporter) -> None:
    product = require_product(ctx)
    require_reservation(ctx)
    response = ctx.request("GET", f"/api/products/{product.id}")
    try:
        body = response.json()
    except ValueError as exc:
        raise CheckFailure("El detalle del producto no devolvió JSON válido.") from exc
    if not isinstance(body, dict):
        raise CheckFailure("El detalle del producto no devolvió un objeto JSON.")
    actual_stock = int(body.get("stock", -1))
    if actual_stock != product.stock:
        raise CheckFailure(
            f"El stock del producto #{product.id} es {actual_stock}; "
            f"se esperaba {product.stock} tras cancelar la reserva."
        )
    reporter.debug(f"Stock repuesto: {product.stock}.")


def check_admin_login(ctx: Context, reporter: Reporter) -> None:
    username = ctx.env["ADMIN_USERNAME"]
    password = ctx.env["ADMIN_PASSWORD"]
    response = ctx.request(
        "POST",
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    try:
        body = response.json()
    except ValueError as exc:
        raise CheckFailure("El login no devolvió JSON válido.") from exc
    if not isinstance(body, dict):
        raise CheckFailure("El login no devolvió un objeto JSON.")
    token = body.get("access_token")
    if not isinstance(token, str) or not token:
        raise CheckFailure("El login no devolvió un access_token.")
    if body.get("token_type") != "bearer":
        raise CheckFailure(
            f"El login devolvió token_type={body.get('token_type')!r}; se esperaba 'bearer'."
        )
    user = body.get("user")
    if not isinstance(user, dict) or user.get("username") != username:
        raise CheckFailure("El login devolvió un usuario distinto del configurado.")
    if user.get("role") != "ADMIN":
        raise CheckFailure(
            f"El usuario {username} tiene rol {user.get('role')!r}; se esperaba 'ADMIN'."
        )
    ctx.token = token
    reporter.debug("Token JWT de administrador obtenido.")


def check_admin_reservations(ctx: Context, reporter: Reporter) -> None:
    reservation = require_reservation(ctx)
    require_token(ctx)
    response = ctx.request(
        "GET",
        "/api/admin/reservations",
        params={
            "search": reservation.code,
            "page": 1,
            "page_size": 50,
        },
        headers=ctx.auth_headers(),
    )
    try:
        body = response.json()
    except ValueError as exc:
        raise CheckFailure("El listado admin no devolvió JSON válido.") from exc
    if not isinstance(body, dict):
        raise CheckFailure("El listado admin no devolvió un objeto JSON.")
    items = body.get("items")
    if not isinstance(items, list):
        raise CheckFailure("El listado admin devolvió ítems inválidos.")
    match = next(
        (item for item in items if isinstance(item, dict) and item.get("code") == reservation.code),
        None,
    )
    if match is None:
        raise CheckFailure(
            f"La reserva cancelada {reservation.code} no aparece en el panel admin. "
            "La reserva debe conservarse como registro de auditoría."
        )
    if match.get("status") != "CANCELADO":
        raise CheckFailure(
            f"La reserva {reservation.code} figura como {match.get('status')!r} "
            "en el panel admin; se esperaba 'CANCELADO'."
        )
    if str(match.get("customer_email", "")).lower() != reservation.email:
        raise CheckFailure(
            f"La reserva {reservation.code} figura con otro correo en el panel admin."
        )
    if int(match.get("item_count", 0)) < 1:
        raise CheckFailure(
            f"La reserva {reservation.code} no conserva sus ítems en el panel admin."
        )
    reporter.info(f"Reserva {reservation.code} visible como CANCELADO en el panel admin.")


def check_admin_product(ctx: Context, reporter: Reporter) -> None:
    product = require_product(ctx)
    require_token(ctx)

    original_price = Decimal(product.price)
    candidate_price = original_price + Decimal("0.01")
    if candidate_price > Decimal("9999999999.99"):
        candidate_price = original_price - Decimal("0.01")
    if candidate_price <= 0:
        raise CheckFailure("No se pudo generar un precio alternativo para la prueba.")
    new_price = candidate_price.quantize(Decimal("0.01"))
    expected_price = f"{new_price:.2f}"

    new_stock = product.stock + 7 if product.stock <= 999993 else product.stock - 7
    if new_stock < 0 or new_stock == product.stock:
        raise CheckFailure("No se pudo generar un stock alternativo para la prueba.")

    # Se marca antes del PATCH: si la respuesta falla, la limpieza igual restaura
    # los valores originales de forma idempotente.
    ctx.product_modified = True
    response = ctx.request(
        "PATCH",
        f"/api/admin/products/{product.id}",
        json={"price": expected_price, "stock": new_stock},
        headers=ctx.auth_headers(),
    )
    try:
        body = response.json()
    except ValueError as exc:
        raise CheckFailure("La edición admin no devolvió JSON válido.") from exc
    if not isinstance(body, dict):
        raise CheckFailure("La edición admin no devolvió un objeto JSON.")
    if body.get("price") != expected_price:
        raise CheckFailure(
            f"La edición admin devolvió precio {body.get('price')!r}; "
            f"se esperaba {expected_price!r}."
        )
    if int(body.get("stock", -1)) != new_stock:
        raise CheckFailure(
            f"La edición admin devolvió stock {body.get('stock')!r}; se esperaba {new_stock}."
        )

    persisted = ctx.request("GET", f"/api/products/{product.id}")
    try:
        persisted_body = persisted.json()
    except ValueError as exc:
        raise CheckFailure("La relectura del producto no devolvió JSON válido.") from exc
    if not isinstance(persisted_body, dict):
        raise CheckFailure("La relectura del producto no devolvió un objeto JSON.")
    if persisted_body.get("price") != expected_price:
        raise CheckFailure(
            f"El precio no persistió: se leyó {persisted_body.get('price')!r}; "
            f"se esperaba {expected_price!r}."
        )
    if int(persisted_body.get("stock", -1)) != new_stock:
        raise CheckFailure(
            f"El stock no persistió: se leyó {persisted_body.get('stock')!r}; "
            f"se esperaba {new_stock}."
        )

    reporter.info(
        f"Producto #{product.id}: precio {product.price} -> {expected_price}, "
        f"stock {product.stock} -> {new_stock} (se restaura al finalizar)."
    )


def check_wal(ctx: Context, reporter: Reporter) -> None:
    if not ctx.compose_file.is_file():
        raise ConfigError(f"No se encontró el archivo Compose: {ctx.compose_file}")

    code = (
        "import sqlite3; "
        "c=sqlite3.connect('/app/data/clean_center.db'); "
        "print(c.execute('PRAGMA journal_mode;').fetchone()[0])"
    )
    command = [
        "docker",
        "compose",
        "-f",
        str(ctx.compose_file),
        "exec",
        "-T",
        ctx.backend_container,
        "python",
        "-c",
        code,
    ]
    try:
        process = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ConfigError(
            "No se encontró el comando 'docker'. La verificación WAL requiere Docker."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise ConfigError(
            "La verificación WAL agotó el tiempo de espera al ejecutar docker compose."
        ) from exc

    if process.returncode != 0:
        stderr = (process.stderr or "").strip()
        lowered = stderr.lower()
        if any(
            marker in lowered
            for marker in (
                "no such service",
                "is not running",
                "no such container",
                "cannot connect to the docker daemon",
                "error during connect",
            )
        ):
            raise ConfigError(
                f"No se pudo acceder al contenedor '{ctx.backend_container}': {stderr[-500:]}"
            )
        raise CheckFailure(
            f"La verificación WAL falló con código {process.returncode}: {stderr[-500:]}"
        )

    output = [line.strip() for line in (process.stdout or "").splitlines() if line.strip()]
    if not output:
        raise CheckFailure("La verificación WAL no devolvió el modo de journal de SQLite.")
    journal_mode = output[-1].lower()
    if journal_mode != "wal":
        raise CheckFailure(f"SQLite está en journal_mode={journal_mode!r}; se esperaba 'wal'.")
    reporter.debug(f"journal_mode=wal confirmado en el contenedor '{ctx.backend_container}'.")


def require_product(ctx: Context) -> ProductState:
    if ctx.product is None:
        raise CheckFailure("No hay un producto de prueba seleccionado.")
    return ctx.product


def require_reservation(ctx: Context) -> ReservationState:
    if ctx.reservation is None:
        raise CheckFailure("No hay una reserva de prueba creada.")
    return ctx.reservation


def require_token(ctx: Context) -> str:
    if ctx.token is None:
        raise CheckFailure("No hay un token de administrador disponible.")
    return ctx.token


def cleanup(ctx: Context, reporter: Reporter) -> bool:
    """Restaura los datos tocados por la prueba. Devuelve True si todo quedó bien."""
    ok = True

    if ctx.reservation is not None and not ctx.reservation.cancelled:
        code = ctx.reservation.code
        try:
            response = ctx.client.post(
                f"/api/reservations/{quote(code, safe='')}/cancel",
                json={
                    "email": ctx.reservation.email,
                    "reason": "Sanity check: limpieza automática",
                },
            )
        except httpx.HTTPError as exc:
            reporter.cleanup(f"No se pudo cancelar la reserva {code}: {exc}")
            ok = False
        else:
            payload: Any = {}
            with contextlib.suppress(ValueError):
                payload = response.json()
            if response.status_code == 200 and isinstance(payload, dict):
                if payload.get("status") == "CANCELADO":
                    ctx.reservation.cancelled = True
                    reporter.cleanup(f"Reserva {code} cancelada; stock repuesto.")
                else:
                    reporter.cleanup(
                        f"La reserva {code} no quedó CANCELADO: {response_detail(response)}"
                    )
                    ok = False
            else:
                reporter.cleanup(
                    f"No se pudo cancelar la reserva {code}: "
                    f"HTTP {response.status_code}: {response_detail(response)}"
                )
                ok = False

    if ctx.product_modified:
        product = ctx.product
        if product is None or ctx.token is None:
            reporter.cleanup("No se pudo restaurar el producto de prueba: faltan datos o token.")
            ok = False
        else:
            try:
                response = ctx.client.patch(
                    f"/api/admin/products/{product.id}",
                    json={"price": product.price, "stock": product.stock},
                    headers=ctx.auth_headers(),
                )
            except httpx.HTTPError as exc:
                reporter.cleanup(f"No se pudo restaurar el producto #{product.id}: {exc}")
                ok = False
            else:
                if response.status_code != 200:
                    reporter.cleanup(
                        f"No se pudo restaurar el producto #{product.id}: "
                        f"HTTP {response.status_code}: {response_detail(response)}"
                    )
                    ok = False
                elif _verify_product_state(ctx, product):
                    ctx.product_modified = False
                    reporter.cleanup(
                        f"Producto #{product.id} restaurado "
                        f"(precio {product.price}, stock {product.stock})."
                    )
                else:
                    reporter.cleanup(
                        f"El producto #{product.id} no quedó restaurado "
                        f"(precio {product.price}, stock {product.stock})."
                    )
                    ok = False

    return ok


def _verify_product_state(ctx: Context, product: ProductState) -> bool:
    try:
        response = ctx.client.get(f"/api/products/{product.id}")
    except httpx.HTTPError:
        return False
    if response.status_code != 200:
        return False
    try:
        payload = response.json()
    except ValueError:
        return False
    if not isinstance(payload, dict):
        return False
    return payload.get("price") == product.price and payload.get("stock") == product.stock


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    reporter = Reporter(verbose=args.verbose)
    env_file = args.env_file.expanduser().resolve()
    compose_file = args.compose_file.expanduser().resolve()

    ctx: Context | None = None
    exit_code = EXIT_OK
    cleanup_failed = False

    try:
        env = load_env_file(env_file)
        require_env(env)
        client = httpx.Client(
            base_url=args.base_url,
            timeout=args.timeout,
            trust_env=False,
            follow_redirects=True,
        )
        ctx = Context(
            env=env,
            base_url=args.base_url,
            client=client,
            reporter=reporter,
            quantity=args.quantity,
            product_id=args.product_id,
            compose_file=compose_file,
            backend_container=args.backend_container,
        )
        try:
            reporter.info(f"Verificando {args.base_url} con {env_file}.")
            reporter.info(
                "Se creará una reserva y se cancelará; "
                "el registro CANCELADO quedará como auditoría."
            )
            run_all(ctx, reporter)
        finally:
            cleanup_failed = not cleanup(ctx, reporter)
    except ConfigError as exc:
        reporter.fail(f"Configuración/entorno: {exc}")
        exit_code = EXIT_CONFIG
    except CheckFailure as exc:
        step = ctx.current_step if ctx is not None else "Verificación"
        reporter.fail(f"{step}: {exc}")
        exit_code = EXIT_CHECK
    except KeyboardInterrupt:
        reporter.fail("Verificación interrumpida por el usuario.")
        exit_code = EXIT_CHECK
    except Exception as exc:
        reporter.fail(f"Error inesperado: {exc}")
        if args.verbose:
            traceback.print_exc()
        exit_code = EXIT_CHECK
    finally:
        if ctx is not None:
            ctx.client.close()

    if cleanup_failed:
        reporter.fail("La limpieza de los datos de prueba no pudo completarse.")
        exit_code = EXIT_CHECK

    if ctx is not None:
        reporter.info(f"Verificaciones OK: {ctx.checks_ok}/{ctx.checks_total}.")
    if exit_code == EXIT_OK:
        reporter.info("Sanity check completado correctamente.")
    else:
        reporter.fail(f"Sanity check finalizado con código de salida {exit_code}.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
