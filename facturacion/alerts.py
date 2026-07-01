"""Alertas por email al administrador cuando falla la emisión de facturas SRI.

Esto evita que un fallo de SRI (cert vencido, servicio caído, datos inválidos)
quede invisible — Carlos se entera por correo inmediatamente.
"""
from __future__ import annotations

import traceback

import requests
from django.conf import settings


ADMIN_EMAIL = 'cijj1969@gmail.com'


def alertar_factura_fallida(
    contexto: str,
    error: Exception,
    medico=None,
    monto=None,
    payphone_transaction_id: str = '',
) -> None:
    """Envía email al admin cuando falla la emisión de una factura SRI.

    Diseñada para llamarse desde un `except` — nunca debe lanzar excepción
    propia (silencia errores internos para no romper el thread llamador).
    """
    if not settings.RESEND_API_KEY:
        print(f"[ALERT] RESEND_API_KEY no configurado — no se envió alerta a {ADMIN_EMAIL}")
        return

    filas = [f"<strong>Contexto:</strong> {contexto}"]
    if medico is not None:
        nombre = medico.usuario.get_full_name() or medico.usuario.email
        filas.append(f"<strong>Médico:</strong> {nombre} ({medico.usuario.email})")
    if monto is not None:
        filas.append(f"<strong>Monto:</strong> ${monto}")
    if payphone_transaction_id:
        filas.append(f"<strong>PayPhone txId:</strong> {payphone_transaction_id}")
    filas.append(f"<strong>Error:</strong> {type(error).__name__}: {error}")

    tb = traceback.format_exc()

    html = (
        "<h3 style='color:#dc3545;'>⚠️ Falla en emisión de factura SRI</h3>"
        f"<ul>{''.join(f'<li>{f}</li>' for f in filas)}</ul>"
        "<h4>Traceback:</h4>"
        f"<pre style='background:#f8f9fa;padding:12px;border-radius:4px;font-size:11px;overflow:auto;'>"
        f"{tb}</pre>"
        "<p style='color:#666;font-size:13px;'>Para investigar en producción:</p>"
        "<pre style='background:#f8f9fa;padding:8px;font-size:11px;'>"
        ".\\logs.ps1\n"
        "# o\n"
        "ssh ... \"docker compose -f /opt/vertexjd/docker-compose.yml logs --tail 100 vertexsalud\""
        "</pre>"
    )

    _enviar_email_admin("⚠️ VertexSalud — Falla emisión factura SRI", html)


def alertar_confirmacion_pago_fallida(
    contexto: str,
    error: Exception,
    transaction_id: str = '',
    client_transaction_id: str = '',
    username: str = '',
) -> None:
    """Envía email al admin cuando el callback de PayPhone falla.

    Este es el escenario más crítico: el médico pagó con tarjeta pero el
    sistema no pudo extender su suscripción. Sin esta alerta, el médico
    queda pagando sin servicio y el admin no se entera.
    """
    if not settings.RESEND_API_KEY:
        print(f"[ALERT] RESEND_API_KEY no configurado — no se envió alerta a {ADMIN_EMAIL}")
        return

    filas = [f"<strong>Contexto:</strong> {contexto}"]
    if username:
        filas.append(f"<strong>Username:</strong> {username}")
    if transaction_id:
        filas.append(f"<strong>PayPhone txId:</strong> {transaction_id}")
    if client_transaction_id:
        filas.append(f"<strong>clientTransactionId:</strong> {client_transaction_id}")
    filas.append(f"<strong>Error:</strong> {type(error).__name__}: {error}")

    tb = traceback.format_exc()

    html = (
        "<h3 style='color:#dc3545;'>🚨 CRÍTICO: Confirmación de pago PayPhone falló</h3>"
        "<p><strong>El médico probablemente pagó pero su suscripción NO se extendió.</strong></p>"
        f"<ul>{''.join(f'<li>{f}</li>' for f in filas)}</ul>"
        "<h4>Traceback:</h4>"
        f"<pre style='background:#f8f9fa;padding:12px;border-radius:4px;font-size:11px;overflow:auto;'>"
        f"{tb}</pre>"
        "<h4>Acción sugerida:</h4>"
        "<ol>"
        "<li>Verificar en <a href='https://commerce.payphone.app'>commerce.payphone.app</a> si el pago fue efectivamente cobrado</li>"
        "<li>Si cobró: reintentar la confirmación manualmente en Django shell</li>"
        "<li>Si NO cobró: no hay acción, el médico verá pantalla de pago de nuevo</li>"
        "</ol>"
    )

    _enviar_email_admin("🚨 VertexSalud — Confirmación PayPhone falló (CRÍTICO)", html)


def _enviar_email_admin(subject: str, html: str) -> None:
    """Helper interno para enviar emails al admin vía Resend."""
    try:
        requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.RESEND_FROM,
                "to": [ADMIN_EMAIL],
                "subject": subject,
                "html": html,
            },
            timeout=10,
        )
    except Exception as e:
        # Nunca propagar — esto se llama desde un except y no debe romper más
        print(f"[ALERT ERROR] No se pudo enviar alerta al admin: {e}")
