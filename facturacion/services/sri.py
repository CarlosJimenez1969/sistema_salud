"""
Servicio de Facturación Electrónica para el SRI Ecuador.

Flujo:
  1. generar_xml()       → XML según esquema SRI v1.1.0
  2. firmar_xml()        → XML con firma XAdES-BES (P12 requerido)
  3. enviar_recepcion()  → SOAP al servicio de recepción del SRI
  4. consultar_autorizacion() → SOAP al servicio de autorización del SRI
  5. procesar_factura()  → ejecuta el flujo completo y actualiza la BD
"""

import base64
import hashlib
import io
import random
from datetime import datetime
from decimal import Decimal

import requests as http_requests
from lxml import etree

# ─── Helper ───────────────────────────────────────────────────────────────────

def _e(parent, tag: str, text: str = '') -> etree._Element:
    """Crea un sub-elemento con texto."""
    elem = etree.SubElement(parent, tag)
    if text:
        elem.text = str(text)
    return elem


# ─── SriService ───────────────────────────────────────────────────────────────

class SriService:

    # URLs de los servicios SOAP del SRI
    RECEPCION_URLS = {
        '1': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline',
        '2': 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline',
    }
    AUTORIZACION_URLS = {
        '1': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline',
        '2': 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline',
    }

    def __init__(self):
        from django.conf import settings as cfg

        self.ruc = cfg.SRI_RUC
        self.razon_social = cfg.SRI_RAZON_SOCIAL
        self.nombre_comercial = getattr(cfg, 'SRI_NOMBRE_COMERCIAL', cfg.SRI_RAZON_SOCIAL)
        self.direccion_matriz = cfg.SRI_DIRECCION_MATRIZ
        self.ambiente = getattr(cfg, 'SRI_AMBIENTE', '1')          # '1'=pruebas  '2'=produccion
        self.establecimiento = getattr(cfg, 'SRI_ESTABLECIMIENTO', '001')
        self.punto_emision = getattr(cfg, 'SRI_PUNTO_EMISION', '001')
        # Certificado: prioriza base64 (producción Render), fallback a ruta de archivo (local)
        self.cert_path = getattr(cfg, 'SRI_CERTIFICADO_P12', '')
        self.cert_base64 = getattr(cfg, 'SRI_CERTIFICADO_P12_BASE64', '')
        self.cert_password = getattr(cfg, 'SRI_CERTIFICADO_PASSWORD', '')
        self.iva_porcentaje = Decimal(str(getattr(cfg, 'SRI_IVA_PORCENTAJE', '12')))
        self.obligado_contabilidad = getattr(cfg, 'SRI_OBLIGADO_CONTABILIDAD', 'NO')

    # ── 1. Clave de Acceso (49 dígitos) ──────────────────────────────────────

    def generar_clave_acceso(self, fecha: datetime, secuencial: int) -> str:
        """
        Estructura (49 dígitos):
          fechaEmision(8) + tipoComprobante(2) + ruc(13) + ambiente(1)
          + estab(3) + ptoEmi(3) + secuencial(9) + codigoNumerico(8)
          + tipoEmision(1) + digitoVerificador(1)
        """
        fecha_str = fecha.strftime('%d%m%Y')                        # 8
        tipo_comp = '01'                                             # 01 = factura
        ruc = self.ruc                                               # 13
        ambiente = self.ambiente                                     # 1
        estab = self.establecimiento                                 # 3
        pto = self.punto_emision                                     # 3
        sec = str(secuencial).zfill(9)                               # 9
        codigo = str(random.randint(10000000, 99999999))             # 8
        tipo_emision = '1'                                           # 1 = normal

        sin_dv = f"{fecha_str}{tipo_comp}{ruc}{ambiente}{estab}{pto}{sec}{codigo}{tipo_emision}"
        assert len(sin_dv) == 48, f"Clave sin dígito verificador: {len(sin_dv)} dígitos (esperado 48)"

        return sin_dv + self._modulo11(sin_dv)

    def _modulo11(self, numero: str) -> str:
        """Calcula el dígito verificador módulo 11 según la especificación del SRI."""
        multiplicadores = [2, 3, 4, 5, 6, 7]
        suma = sum(
            int(d) * multiplicadores[i % 6]
            for i, d in enumerate(reversed(numero))
        )
        residuo = 11 - (suma % 11)
        if residuo == 11:
            return '0'
        if residuo == 10:
            return '1'
        return str(residuo)

    # ── 2. Generación del XML (esquema SRI Factura v1.1.0) ───────────────────

    def generar_xml(self, factura) -> str:
        """Genera el XML de la factura según el esquema oficial del SRI."""
        root = etree.Element('factura', version='1.1.0')
        root.set('id', 'comprobante')  # SRI Ecuador usa lowercase id

        # ── infoTributaria ──────────────────────────────────────────────────
        it = etree.SubElement(root, 'infoTributaria')
        _e(it, 'ambiente',       self.ambiente)
        _e(it, 'tipoEmision',    '1')
        _e(it, 'razonSocial',    self.razon_social)
        _e(it, 'nombreComercial', self.nombre_comercial)
        _e(it, 'ruc',            self.ruc)
        _e(it, 'claveAcceso',    factura.clave_acceso)
        _e(it, 'codDoc',         '01')
        _e(it, 'estab',          self.establecimiento)
        _e(it, 'ptoEmi',         self.punto_emision)
        _e(it, 'secuencial',     str(factura.secuencial_numero).zfill(9))
        _e(it, 'dirMatriz',      self.direccion_matriz)

        # ── infoFactura ─────────────────────────────────────────────────────
        fecha = factura.fecha_emision or datetime.now()
        ifact = etree.SubElement(root, 'infoFactura')
        _e(ifact, 'fechaEmision',               fecha.strftime('%d/%m/%Y'))
        _e(ifact, 'dirEstablecimiento',          self.direccion_matriz)
        _e(ifact, 'obligadoContabilidad',        self.obligado_contabilidad)
        _e(ifact, 'tipoIdentificacionComprador', factura.receptor_tipo_id)
        _e(ifact, 'razonSocialComprador',        factura.receptor_nombre)
        _e(ifact, 'identificacionComprador',     factura.receptor_identificacion)
        _e(ifact, 'totalSinImpuestos',           f"{factura.subtotal:.2f}")
        _e(ifact, 'totalDescuento',              '0.00')

        total_imp_elem = etree.SubElement(ifact, 'totalConImpuestos')
        t_imp = etree.SubElement(total_imp_elem, 'totalImpuesto')
        codigo_porc = self._codigo_porcentaje_iva()
        _e(t_imp, 'codigo',           '2')
        _e(t_imp, 'codigoPorcentaje', codigo_porc)
        _e(t_imp, 'baseImponible',    f"{factura.subtotal:.2f}")
        _e(t_imp, 'valor',            f"{factura.iva_valor:.2f}")

        _e(ifact, 'propina',      '0.00')
        _e(ifact, 'importeTotal', f"{factura.total:.2f}")
        _e(ifact, 'moneda',       'DOLAR')

        # pagos va dentro de infoFactura (schema SRI v1.1.0)
        pagos_if = etree.SubElement(ifact, 'pagos')
        pago_if  = etree.SubElement(pagos_if, 'pago')
        _e(pago_if, 'formaPago', getattr(factura, 'forma_pago', '01') or '01')
        _e(pago_if, 'total', f"{factura.total:.2f}")
        _e(pago_if, 'plazo', '0')
        _e(pago_if, 'unidadTiempo', 'dias')

        # ── detalles ────────────────────────────────────────────────────────
        detalles = etree.SubElement(root, 'detalles')
        det = etree.SubElement(detalles, 'detalle')
        _e(det, 'codigoPrincipal',          '001')
        _e(det, 'descripcion',              factura.descripcion)
        _e(det, 'cantidad',                 '1.000000')
        _e(det, 'precioUnitario',           f"{factura.subtotal:.6f}")
        _e(det, 'descuento',                '0.00')
        _e(det, 'precioTotalSinImpuesto',   f"{factura.subtotal:.2f}")

        impuestos_elem = etree.SubElement(det, 'impuestos')
        imp = etree.SubElement(impuestos_elem, 'impuesto')
        _e(imp, 'codigo',           '2')
        _e(imp, 'codigoPorcentaje', codigo_porc)
        _e(imp, 'tarifa',           f"{self.iva_porcentaje:.2f}")
        _e(imp, 'baseImponible',    f"{factura.subtotal:.2f}")
        _e(imp, 'valor',            f"{factura.iva_valor:.2f}")

        # ── infoAdicional ───────────────────────────────────────────────────
        info_ad = etree.SubElement(root, 'infoAdicional')
        if factura.receptor_email:
            c = etree.SubElement(info_ad, 'campoAdicional', nombre='email')
            c.text = factura.receptor_email
        if factura.receptor_direccion:
            c2 = etree.SubElement(info_ad, 'campoAdicional', nombre='direccion')
            c2.text = factura.receptor_direccion

        return etree.tostring(
            root,
            pretty_print=False,
            xml_declaration=True,
            encoding='UTF-8',
        ).decode('utf-8')

    def _codigo_porcentaje_iva(self) -> str:
        """
        Códigos SRI para porcentaje de IVA (Ecuador 2024+):
          0  → 0%
          2  → 12% (hasta 31/marzo/2024)
          3  → 14% (transitorio 2016)
          4  → 15% (vigente desde 01/abril/2024)
          5  → 5% (medicamentos, etc.)
        """
        mapping = {
            Decimal('0'):  '0',
            Decimal('5'):  '5',
            Decimal('12'): '2',
            Decimal('14'): '3',
            Decimal('15'): '4',
        }
        return mapping.get(self.iva_porcentaje, '4')

    # ── 3. Firma XAdES-BES ───────────────────────────────────────────────────

    def firmar_xml(self, xml_str: str) -> str:
        """
        Firma el XML con XAdES-BES usando el certificado P12 configurado.
        Lanza ValueError si no hay certificado configurado.
        """
        if not self.cert_path and not self.cert_base64:
            raise ValueError(
                "Certificado SRI no configurado. "
                "Define SRI_CERTIFICADO_P12_BASE64 (producción) o SRI_CERTIFICADO_P12 (ruta local)."
            )

        # ── Cargar certificado P12 ──────────────────────────────────────────
        from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding as asym_padding

        if self.cert_base64:
            p12_data = base64.b64decode(self.cert_base64)
        else:
            with open(self.cert_path, 'rb') as f:
                p12_data = f.read()

        pwd = self.cert_password.encode() if self.cert_password else b''
        private_key, certificate, chain_certs = load_key_and_certificates(p12_data, pwd)

        # Datos del certificado
        cert_der = certificate.public_bytes(serialization.Encoding.DER)
        cert_b64 = base64.b64encode(cert_der).decode()
        cert_sha1_b64 = base64.b64encode(hashlib.sha1(cert_der).digest()).decode()
        serial_number = str(certificate.serial_number)
        # Issuer en formato compatible con BouncyCastle Java (mapeo OID → nombre estándar)
        _OID_NAMES = {
            '2.5.4.3': 'CN', '2.5.4.6': 'C', '2.5.4.7': 'L', '2.5.4.8': 'ST',
            '2.5.4.9': 'STREET', '2.5.4.10': 'O', '2.5.4.11': 'OU',
            '2.5.4.5': 'SERIALNUMBER', '2.5.4.4': 'SN', '2.5.4.42': 'GN',
            '1.2.840.113549.1.9.1': 'emailAddress', '2.5.4.12': 'T',
            '2.5.4.13': 'description', '0.9.2342.19200300.100.1.25': 'DC',
        }
        issuer_str = ','.join(
            f"{_OID_NAMES.get(attr.oid.dotted_string, attr.oid.dotted_string)}={attr.value}"
            for rdn in reversed(certificate.issuer.rdns)
            for attr in rdn
        )
        signing_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S-05:00')

        # ── Parsear el XML ──────────────────────────────────────────────────
        xml_bytes = xml_str.encode('utf-8') if isinstance(xml_str, str) else xml_str
        root = etree.fromstring(xml_bytes)

        DS    = 'http://www.w3.org/2000/09/xmldsig#'
        XADES = 'http://uri.etsi.org/01903/v1.3.2#'
        C14N  = 'http://www.w3.org/TR/2001/REC-xml-c14n-20010315'
        ENVELOPED = 'http://www.w3.org/2000/09/xmldsig#enveloped-signature'
        nsmap_ds    = {'ds': DS}
        nsmap_xades = {'xades': XADES, 'ds': DS}

        # ── Paso 1: digest del comprobante (sin firma, se usará con enveloped-signature transform) ──
        comprobante_c14n = etree.tostring(root, method='c14n', exclusive=False, with_comments=False)
        comprobante_digest_b64 = base64.b64encode(hashlib.sha1(comprobante_c14n).digest()).decode()

        # ── Paso 2: construir SignedProperties (XAdES) ───────────────────────
        signed_props_id = 'Signature-SignedProperties'
        xsp = etree.Element(f'{{{XADES}}}SignedProperties', nsmap=nsmap_xades)
        xsp.set('Id', signed_props_id)

        xssp = etree.SubElement(xsp, f'{{{XADES}}}SignedSignatureProperties')
        _e(xssp, f'{{{XADES}}}SigningTime', signing_time)

        signing_cert = etree.SubElement(xssp, f'{{{XADES}}}SigningCertificate')
        cert_elem    = etree.SubElement(signing_cert, f'{{{XADES}}}Cert')
        cert_digest  = etree.SubElement(cert_elem, f'{{{XADES}}}CertDigest')
        dm_cert      = etree.SubElement(cert_digest, f'{{{DS}}}DigestMethod')
        dm_cert.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#sha1')
        _e(cert_digest, f'{{{DS}}}DigestValue', cert_sha1_b64)

        issuer_serial = etree.SubElement(cert_elem, f'{{{XADES}}}IssuerSerial')
        _e(issuer_serial, f'{{{DS}}}X509IssuerName',   issuer_str)
        _e(issuer_serial, f'{{{DS}}}X509SerialNumber', serial_number)

        # Digest de SignedProperties
        sp_c14n = etree.tostring(xsp, method='c14n', exclusive=False, with_comments=False)
        sp_digest_b64 = base64.b64encode(hashlib.sha1(sp_c14n).digest()).decode()

        # ── Paso 3: construir SignedInfo ─────────────────────────────────────
        signed_info = etree.Element(f'{{{DS}}}SignedInfo', nsmap=nsmap_ds)

        c14n_method = etree.SubElement(signed_info, f'{{{DS}}}CanonicalizationMethod')
        c14n_method.set('Algorithm', C14N)

        sig_method = etree.SubElement(signed_info, f'{{{DS}}}SignatureMethod')
        sig_method.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#rsa-sha1')

        # Referencia 1 → comprobante (enveloped-signature + c14n transforms)
        ref1 = etree.SubElement(signed_info, f'{{{DS}}}Reference', Id='comprobante-ref', URI='#comprobante')
        transforms1 = etree.SubElement(ref1, f'{{{DS}}}Transforms')
        t1_env = etree.SubElement(transforms1, f'{{{DS}}}Transform')
        t1_env.set('Algorithm', ENVELOPED)
        t1_c14n = etree.SubElement(transforms1, f'{{{DS}}}Transform')
        t1_c14n.set('Algorithm', C14N)
        dm1 = etree.SubElement(ref1, f'{{{DS}}}DigestMethod')
        dm1.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#sha1')
        _e(ref1, f'{{{DS}}}DigestValue', comprobante_digest_b64)

        # Referencia 2 → SignedProperties
        ref2 = etree.SubElement(
            signed_info, f'{{{DS}}}Reference',
            URI=f'#{signed_props_id}',
            Type='http://uri.etsi.org/01903#SignedProperties',
        )
        transforms2 = etree.SubElement(ref2, f'{{{DS}}}Transforms')
        t2 = etree.SubElement(transforms2, f'{{{DS}}}Transform')
        t2.set('Algorithm', C14N)
        dm2 = etree.SubElement(ref2, f'{{{DS}}}DigestMethod')
        dm2.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#sha1')
        _e(ref2, f'{{{DS}}}DigestValue', sp_digest_b64)

        # ── Paso 4: firmar SignedInfo ────────────────────────────────────────
        si_c14n = etree.tostring(signed_info, method='c14n', exclusive=False, with_comments=False)
        sig_bytes = private_key.sign(si_c14n, asym_padding.PKCS1v15(), hashes.SHA1())
        sig_b64   = base64.b64encode(sig_bytes).decode()

        # ── Paso 5: ensamblar el elemento Signature completo ─────────────────
        sig = etree.Element(f'{{{DS}}}Signature', Id='Signature', nsmap=nsmap_ds)
        sig.append(signed_info)

        sig_value = etree.SubElement(sig, f'{{{DS}}}SignatureValue')
        sig_value.text = sig_b64

        key_info = etree.SubElement(sig, f'{{{DS}}}KeyInfo')
        x509_data = etree.SubElement(key_info, f'{{{DS}}}X509Data')
        _e(x509_data, f'{{{DS}}}X509Certificate', cert_b64)

        obj = etree.SubElement(sig, f'{{{DS}}}Object', Id='QualifyingProperties-Object')
        qp  = etree.SubElement(obj, f'{{{XADES}}}QualifyingProperties', nsmap=nsmap_xades)
        qp.set('Target', '#Signature')
        qp.append(xsp)

        # ── Paso 6: insertar Signature en el XML original ────────────────────
        root.append(sig)

        # IMPORTANTE: pretty_print=False para que no agregue whitespace text nodes
        # que cambiarían el C14N del SignedInfo y romperían la verificación de firma
        return etree.tostring(
            root,
            pretty_print=False,
            xml_declaration=True,
            encoding='UTF-8',
        ).decode('utf-8')

    # ── 4. Envío al servicio de RECEPCIÓN del SRI (SOAP) ─────────────────────

    def enviar_recepcion(self, xml_firmado: str) -> dict:
        """
        Envía el XML firmado (en Base64) al servicio de recepción del SRI.
        Retorna: {'estado': 'RECIBIDA'|'DEVUELTA', 'mensajes': [...]}
        """
        xml_b64 = base64.b64encode(xml_firmado.encode('utf-8')).decode()

        soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope
  xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:ec="http://ec.gob.sri.ws.recepcion">
  <soapenv:Header/>
  <soapenv:Body>
    <ec:validarComprobante>
      <xml>{xml_b64}</xml>
    </ec:validarComprobante>
  </soapenv:Body>
</soapenv:Envelope>"""

        url = self.RECEPCION_URLS[self.ambiente]
        try:
            resp = http_requests.post(
                url,
                data=soap_body.encode('utf-8'),
                headers={
                    'Content-Type': 'text/xml; charset=utf-8',
                    'SOAPAction': '',
                },
                timeout=30,
            )
            resp.raise_for_status()
            return self._parsear_respuesta_recepcion(resp.text)
        except http_requests.exceptions.Timeout:
            return {'estado': 'ERROR', 'mensajes': [{'mensaje': 'Timeout al conectar con el SRI.'}]}
        except Exception as e:
            return {'estado': 'ERROR', 'mensajes': [{'mensaje': str(e)}]}

    def _parsear_respuesta_recepcion(self, soap_xml: str) -> dict:
        """Extrae estado y mensajes de la respuesta SOAP de recepción."""
        try:
            ns = {
                's': 'http://schemas.xmlsoap.org/soap/envelope/',
                'r': 'http://ec.gob.sri.ws.recepcion',
            }
            root = etree.fromstring(soap_xml.encode())
            resp = root.find('.//RespuestaRecepcionComprobante') or root.find('.//{*}RespuestaRecepcionComprobante')

            estado = resp.findtext('estado') or 'ERROR'
            mensajes = []
            for m in resp.findall('.//mensaje') or []:
                mensajes.append({
                    'identificador': m.findtext('identificador', ''),
                    'mensaje':       m.findtext('mensaje', ''),
                    'tipo':          m.findtext('tipo', ''),
                    'informacionAdicional': m.findtext('informacionAdicional', ''),
                })
            return {'estado': estado, 'mensajes': mensajes}
        except Exception as e:
            return {'estado': 'ERROR', 'mensajes': [{'mensaje': f'Error parseando respuesta SRI: {e}'}]}

    # ── 5. Consulta al servicio de AUTORIZACIÓN del SRI (SOAP) ───────────────

    def consultar_autorizacion(self, clave_acceso: str) -> dict:
        """
        Consulta el estado de autorización de un comprobante.
        Retorna: {'estado': 'AUTORIZADO'|'NO AUTORIZADO'|'EN PROCESO',
                  'numeroAutorizacion': ..., 'fechaAutorizacion': ..., 'mensajes': [...]}
        """
        soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope
  xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:ec="http://ec.gob.sri.ws.autorizacion">
  <soapenv:Header/>
  <soapenv:Body>
    <ec:autorizacionComprobante>
      <claveAccesoComprobante>{clave_acceso}</claveAccesoComprobante>
    </ec:autorizacionComprobante>
  </soapenv:Body>
</soapenv:Envelope>"""

        url = self.AUTORIZACION_URLS[self.ambiente]
        try:
            resp = http_requests.post(
                url,
                data=soap_body.encode('utf-8'),
                headers={
                    'Content-Type': 'text/xml; charset=utf-8',
                    'SOAPAction': '',
                },
                timeout=30,
            )
            resp.raise_for_status()
            return self._parsear_respuesta_autorizacion(resp.text)
        except http_requests.exceptions.Timeout:
            return {'estado': 'EN PROCESO', 'mensajes': [{'mensaje': 'Timeout al consultar autorización.'}]}
        except Exception as e:
            return {'estado': 'ERROR', 'mensajes': [{'mensaje': str(e)}]}

    def _parsear_respuesta_autorizacion(self, soap_xml: str) -> dict:
        """Extrae datos de la respuesta SOAP de autorización."""
        try:
            root = etree.fromstring(soap_xml.encode())
            aut = root.find('.//{*}autorizacion')
            if aut is None:
                return {'estado': 'ERROR', 'mensajes': [{'mensaje': 'Respuesta de autorización inesperada.'}]}

            estado          = aut.findtext('{*}estado') or aut.findtext('estado') or 'ERROR'
            num_aut         = aut.findtext('{*}numeroAutorizacion') or aut.findtext('numeroAutorizacion') or ''
            fecha_aut_str   = aut.findtext('{*}fechaAutorizacion') or aut.findtext('fechaAutorizacion') or ''

            mensajes = []
            for m in aut.findall('.//{*}mensaje') or aut.findall('.//mensaje') or []:
                mensajes.append({
                    'identificador': m.findtext('{*}identificador') or m.findtext('identificador') or '',
                    'mensaje':       m.findtext('{*}mensaje') or m.findtext('mensaje') or '',
                    'tipo':          m.findtext('{*}tipo') or m.findtext('tipo') or '',
                })

            return {
                'estado':              estado,
                'numeroAutorizacion':  num_aut,
                'fechaAutorizacion':   fecha_aut_str,
                'mensajes':            mensajes,
            }
        except Exception as e:
            return {'estado': 'ERROR', 'mensajes': [{'mensaje': f'Error parseando autorización: {e}'}]}

    # ── 6. Flujo completo ────────────────────────────────────────────────────

    def procesar_factura(self, factura) -> None:
        """
        Ejecuta el flujo completo de facturación electrónica:
          generar XML → firmar → enviar SRI → consultar autorización → actualizar BD
        """
        from django.utils import timezone
        import time

        try:
            # Generar XML
            xml = self.generar_xml(factura)
            factura.xml_sin_firma = xml

            # Intentar firmar (puede no tener certificado configurado)
            try:
                xml_firmado = self.firmar_xml(xml)
                factura.xml_firmado = xml_firmado
            except ValueError:
                # Sin certificado configurado: guardamos sin firma y marcamos error
                factura.estado = 'ERROR'
                factura.mensajes_sri = 'Certificado P12 no configurado. Configure SRI_CERTIFICADO_P12_BASE64 (producción) o SRI_CERTIFICADO_P12 (ruta local).'
                factura.save()
                return
            except Exception as e:
                factura.estado = 'ERROR'
                factura.mensajes_sri = f'Error al firmar el XML: {e}'
                factura.save()
                return

            # Enviar al SRI
            factura.fecha_envio = timezone.now()
            resp_recepcion = self.enviar_recepcion(xml_firmado)
            factura.respuesta_sri = {'recepcion': resp_recepcion}

            if resp_recepcion.get('estado') in ('RECIBIDA',):
                factura.estado = 'ENVIADA'
                factura.save()

                # Esperar brevemente y consultar autorización
                time.sleep(3)
                resp_aut = self.consultar_autorizacion(factura.clave_acceso)
                factura.respuesta_sri['autorizacion'] = resp_aut

                estado_aut = resp_aut.get('estado', '').upper()
                if estado_aut == 'AUTORIZADO':
                    factura.estado = 'AUTORIZADA'
                    factura.numero_autorizacion = resp_aut.get('numeroAutorizacion', '')
                    fecha_str = resp_aut.get('fechaAutorizacion', '')
                    if fecha_str:
                        try:
                            factura.fecha_autorizacion = datetime.strptime(
                                fecha_str, '%Y-%m-%dT%H:%M:%S'
                            ).replace(tzinfo=timezone.utc)
                        except ValueError:
                            factura.fecha_autorizacion = timezone.now()
                    factura.mensajes_sri = 'Comprobante autorizado correctamente.'
                    self._enviar_correo_factura(factura)
                elif estado_aut in ('NO AUTORIZADO',):
                    factura.estado = 'RECHAZADA'
                    mensajes = resp_aut.get('mensajes', [])
                    factura.mensajes_sri = '; '.join(m.get('mensaje', '') for m in mensajes)
                else:
                    # EN PROCESO: el SRI todavía lo está procesando
                    factura.estado = 'ENVIADA'
                    factura.mensajes_sri = 'Comprobante en proceso de autorización en el SRI.'
            else:
                # DEVUELTA (rechazada en recepción) o ERROR
                factura.estado = 'RECHAZADA' if resp_recepcion.get('estado') == 'DEVUELTA' else 'ERROR'
                mensajes = resp_recepcion.get('mensajes', [])
                factura.mensajes_sri = '; '.join(m.get('mensaje', '') for m in mensajes)

        except Exception as e:
            factura.estado = 'ERROR'
            factura.mensajes_sri = f'Error inesperado: {e}'

        finally:
            factura.save()

    # ── 7. Envío de factura autorizada por correo ────────────────────────────

    def _enviar_correo_factura(self, factura) -> None:
        """Envía la factura autorizada al correo del receptor con XML + RIDE PDF adjuntos."""
        if not factura.receptor_email:
            return
        try:
            from django.core.mail import EmailMessage
            from django.conf import settings as djconf
            from django.template.loader import render_to_string

            emisor = getattr(djconf, 'SRI_RAZON_SOCIAL', 'VertexSalud')
            asunto = f'Factura Electrónica {factura.numero_secuencial} — Autorizada por el SRI'

            cuerpo = (
                f"Estimado/a {factura.receptor_nombre},\n\n"
                f"Adjunto encontrará su factura electrónica autorizada por el SRI.\n\n"
                f"  N° Factura      : {factura.numero_secuencial}\n"
                f"  N° Autorización : {factura.numero_autorizacion}\n"
                f"  Fecha           : {factura.fecha_emision.strftime('%d/%m/%Y %H:%M')}\n"
                f"  Descripción     : {factura.descripcion}\n"
                f"  Subtotal        : ${factura.subtotal:.2f}\n"
                f"  IVA ({factura.iva_porcentaje}%)       : ${factura.iva_valor:.2f}\n"
                f"  TOTAL           : ${factura.total:.2f}\n\n"
                f"Este comprobante es válido como documento tributario.\n\n"
                f"Atentamente,\n{emisor}"
            )

            email = EmailMessage(
                subject=asunto,
                body=cuerpo,
                to=[factura.receptor_email],
            )

            # Adjuntar XML firmado (formateado para legibilidad)
            if factura.xml_firmado:
                try:
                    from lxml import etree as _etree
                    _root = _etree.fromstring(factura.xml_firmado.encode('utf-8'))
                    xml_legible = _etree.tostring(
                        _root, pretty_print=True, xml_declaration=True, encoding='UTF-8'
                    )
                except Exception:
                    xml_legible = factura.xml_firmado.encode('utf-8')
                nombre_xml = f"factura_{factura.numero_secuencial.replace('-', '')}.xml"
                email.attach(nombre_xml, xml_legible, 'application/xml')

            # Generar y adjuntar RIDE (PDF)
            try:
                from io import BytesIO
                from xhtml2pdf import pisa

                contexto_ride = {
                    'factura': factura,
                    'emisor_ruc': getattr(djconf, 'SRI_RUC', ''),
                    'emisor_razon_social': getattr(djconf, 'SRI_RAZON_SOCIAL', ''),
                    'emisor_nombre_comercial': getattr(djconf, 'SRI_NOMBRE_COMERCIAL', ''),
                    'emisor_direccion': getattr(djconf, 'SRI_DIRECCION_MATRIZ', ''),
                    'emisor_obligado': getattr(djconf, 'SRI_OBLIGADO_CONTABILIDAD', 'NO'),
                    'ambiente': getattr(djconf, 'SRI_AMBIENTE', '1'),
                }
                html_ride = render_to_string('facturacion/ride_pdf.html', contexto_ride)
                buffer = BytesIO()
                pisa.CreatePDF(html_ride, dest=buffer)
                nombre_pdf = f"RIDE_{factura.numero_secuencial.replace('-', '')}.pdf"
                email.attach(nombre_pdf, buffer.getvalue(), 'application/pdf')
            except Exception:
                pass

            email.send(fail_silently=True)
        except Exception:
            pass

    # ── 8. Crear factura desde un pago ───────────────────────────────────────

    def crear_factura_pago(self, medico, monto_total: Decimal) -> 'FacturaElectronica':
        """
        Crea, persiste y procesa una FacturaElectronica para un pago de registro médico.
        """
        from facturacion.models import FacturaElectronica, SecuencialFactura
        from django.conf import settings as cfg

        # Calcular montos
        if self.iva_porcentaje > 0:
            # El monto incluye IVA: subtotal = total / (1 + iva/100)
            subtotal  = (monto_total / (1 + self.iva_porcentaje / 100)).quantize(Decimal('0.01'))
            iva_valor = (monto_total - subtotal).quantize(Decimal('0.01'))
        else:
            subtotal  = monto_total
            iva_valor = Decimal('0.00')

        # Número secuencial y clave de acceso
        secuencial_num = SecuencialFactura.siguiente(self.establecimiento, self.punto_emision)
        clave = self.generar_clave_acceso(datetime.now(), secuencial_num)

        numero_formateado = (
            f"{self.establecimiento}-{self.punto_emision}-{str(secuencial_num).zfill(9)}"
        )

        # Datos del receptor desde el modelo User del médico
        usuario = medico.usuario
        cedula = usuario.cedula or '9999999999999'
        tipo_id = '04' if len(cedula) == 13 else '05'  # 13 dígitos = RUC; 10 = cédula

        factura = FacturaElectronica.objects.create(
            medico=medico,
            clave_acceso=clave,
            numero_secuencial=numero_formateado,
            secuencial_numero=secuencial_num,
            receptor_tipo_id=tipo_id,
            receptor_identificacion=cedula,
            receptor_nombre=usuario.get_full_name() or usuario.email,
            receptor_email=usuario.email,
            receptor_direccion=getattr(medico, 'direccion_consultorio', '') or 'N/A',
            subtotal=subtotal,
            iva_porcentaje=self.iva_porcentaje,
            iva_valor=iva_valor,
            total=monto_total,
            descripcion='Registro de suscripción - VertexSalud',
            estado='PENDIENTE',
        )

        # Procesar la factura (genera XML, firma, envía al SRI)
        self.procesar_factura(factura)

        # Enviar email al receptor con el resumen de la factura
        try:
            self._enviar_email_factura(factura)
        except Exception as e:
            print(f"[FACTURACIÓN EMAIL] No se pudo enviar email de factura: {e}")

        return factura

    def _enviar_email_factura(self, factura) -> None:
        """Envía un email al receptor con el resumen de la factura electrónica."""
        from django.core.mail import send_mail
        from django.conf import settings as cfg

        if not factura.receptor_email:
            return

        estado_texto = factura.get_estado_display()
        num_aut = factura.numero_autorizacion or 'Pendiente de autorización SRI'

        asunto = f"Factura Electrónica {factura.numero_secuencial} - VertexSalud"
        cuerpo = f"""Estimado(a) {factura.receptor_nombre},

Le informamos que se ha emitido su factura electrónica con los siguientes datos:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  FACTURA ELECTRÓNICA - VertexSalud
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  N° Factura:          {factura.numero_secuencial}
  Clave de Acceso:     {factura.clave_acceso}
  Fecha de Emisión:    {factura.fecha_emision.strftime('%d/%m/%Y %H:%M')}
  Estado SRI:          {estado_texto}
  N° Autorización:     {num_aut}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DETALLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Descripción:   {factura.descripcion}
  Subtotal:      ${factura.subtotal:.2f}
  IVA ({factura.iva_porcentaje}%):    ${factura.iva_valor:.2f}
  TOTAL:         ${factura.total:.2f}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Puede verificar su comprobante en el portal del SRI:
https://srienlinea.sri.gob.ec/comprobantes-electronicos-ws/

Gracias por su confianza.
VertexSalud - Sistema de Gestión Médica
"""
        # Generar adjuntos (XML firmado + RIDE PDF)
        adjuntos = []

        if factura.xml_firmado:
            try:
                from lxml import etree as _etree
                _root = _etree.fromstring(factura.xml_firmado.encode('utf-8'))
                xml_legible = _etree.tostring(_root, pretty_print=True, xml_declaration=True, encoding='UTF-8')
            except Exception:
                xml_legible = factura.xml_firmado.encode('utf-8')
            adjuntos.append({
                'filename': f"factura_{factura.numero_secuencial.replace('-', '')}.xml",
                'content': xml_legible,
            })

        try:
            from io import BytesIO
            from xhtml2pdf import pisa
            from django.template.loader import render_to_string
            contexto_ride = {
                'factura': factura,
                'emisor_ruc': getattr(cfg, 'SRI_RUC', ''),
                'emisor_razon_social': getattr(cfg, 'SRI_RAZON_SOCIAL', ''),
                'emisor_nombre_comercial': getattr(cfg, 'SRI_NOMBRE_COMERCIAL', ''),
                'emisor_direccion': getattr(cfg, 'SRI_DIRECCION_MATRIZ', ''),
                'emisor_obligado': getattr(cfg, 'SRI_OBLIGADO_CONTABILIDAD', 'NO'),
                'ambiente': getattr(cfg, 'SRI_AMBIENTE', '1'),
            }
            html_ride = render_to_string('facturacion/ride_pdf.html', contexto_ride)
            buffer = BytesIO()
            pisa.CreatePDF(html_ride, dest=buffer)
            adjuntos.append({
                'filename': f"RIDE_{factura.numero_secuencial.replace('-', '')}.pdf",
                'content': buffer.getvalue(),
            })
        except Exception as e:
            print(f"[FACTURACIÓN PDF] No se pudo generar RIDE: {e}")

        # Resend HTTP API (Render bloquea SMTP)
        if cfg.RESEND_API_KEY:
            import requests as http_requests
            import base64
            html = cuerpo.replace('\n', '<br>')
            payload = {
                "from": cfg.RESEND_FROM,
                "to": [factura.receptor_email],
                "subject": asunto,
                "html": html,
            }
            if adjuntos:
                payload["attachments"] = [
                    {
                        "filename": a['filename'],
                        "content": base64.b64encode(a['content']).decode('ascii'),
                    } for a in adjuntos
                ]
            resp = http_requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {cfg.RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=20,
            )
            print(f"[FACTURACIÓN EMAIL] Resend status={resp.status_code} body={resp.text[:200]}")
            resp.raise_for_status()
        else:
            from django.core.mail import EmailMessage
            email = EmailMessage(
                subject=asunto,
                body=cuerpo,
                from_email=cfg.DEFAULT_FROM_EMAIL,
                to=[factura.receptor_email],
            )
            for a in adjuntos:
                email.attach(a['filename'], a['content'])
            email.send(fail_silently=False)
