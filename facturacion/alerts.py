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
                "subject": "⚠️ VertexSalud — Falla emisión factura SRI",
                "html": html,
            },
            timeout=10,
        )
    except Exception as e:
        # Nunca propagar — esto se llama desde un except y no debe romper más
        print(f"[ALERT ERROR] No se pudo enviar alerta de factura fallida: {e}")
