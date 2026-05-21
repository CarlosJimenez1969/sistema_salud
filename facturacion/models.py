from django.db import models, transaction


class SecuencialFactura(models.Model):
    """Contador de secuenciales por establecimiento/punto de emisión."""
    establecimiento = models.CharField(max_length=3, default='001')
    punto_emision = models.CharField(max_length=3, default='001')
    ultimo_secuencial = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ['establecimiento', 'punto_emision']
        verbose_name = 'Secuencial de Factura'

    @classmethod
    def siguiente(cls, establecimiento='001', punto_emision='001') -> int:
        """Retorna el siguiente número secuencial de forma atómica (thread-safe)."""
        with transaction.atomic():
            obj, _ = cls.objects.select_for_update().get_or_create(
                establecimiento=establecimiento,
                punto_emision=punto_emision,
                defaults={'ultimo_secuencial': 0},
            )
            obj.ultimo_secuencial += 1
            obj.save(update_fields=['ultimo_secuencial'])
            return obj.ultimo_secuencial

    def __str__(self):
        return f"{self.establecimiento}-{self.punto_emision}: {self.ultimo_secuencial}"


class FacturaElectronica(models.Model):

    ESTADOS = [
        ('PENDIENTE', 'Pendiente de envío'),
        ('ENVIADA', 'Enviada al SRI'),
        ('AUTORIZADA', 'Autorizada por SRI'),
        ('RECHAZADA', 'Rechazada por SRI'),
        ('ERROR', 'Error en el proceso'),
        ('ANULADA', 'Anulada'),
    ]

    TIPO_ID = [
        ('04', 'RUC'),
        ('05', 'Cédula'),
        ('06', 'Pasaporte'),
        ('07', 'Consumidor Final'),
    ]

    # Relación con el médico que pagó
    medico = models.ForeignKey(
        'medico.Medico',
        on_delete=models.PROTECT,
        related_name='facturas',
        null=True, blank=True,
    )

    # Identificación de la factura
    clave_acceso = models.CharField(max_length=49, unique=True)
    numero_secuencial = models.CharField(max_length=20)  # 001-001-000000001
    secuencial_numero = models.PositiveIntegerField()

    # Datos del receptor (quien paga)
    receptor_tipo_id = models.CharField(max_length=2, choices=TIPO_ID, default='05')
    receptor_identificacion = models.CharField(max_length=20)
    receptor_nombre = models.CharField(max_length=300)
    receptor_email = models.EmailField(blank=True)
    receptor_direccion = models.CharField(max_length=300, blank=True, default='N/A')

    # Montos
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    iva_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    iva_valor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)

    # Descripción del servicio
    descripcion = models.CharField(
        max_length=300,
        default='Registro de suscripción - VertexSalud'
    )

    # XML generado
    xml_sin_firma = models.TextField(blank=True)
    xml_firmado = models.TextField(blank=True)

    # Estado y respuesta del SRI
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    numero_autorizacion = models.CharField(max_length=100, blank=True)
    fecha_autorizacion = models.DateTimeField(null=True, blank=True)
    respuesta_sri = models.JSONField(null=True, blank=True)
    mensajes_sri = models.TextField(blank=True)

    # Auditoría
    fecha_emision = models.DateTimeField(auto_now_add=True)
    fecha_envio = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha_emision']
        verbose_name = 'Factura Electrónica'
        verbose_name_plural = 'Facturas Electrónicas'

    def __str__(self):
        return f"{self.numero_secuencial} | {self.receptor_nombre} | {self.get_estado_display()}"

    @property
    def estado_badge(self):
        colores = {
            'PENDIENTE': 'warning',
            'ENVIADA': 'info',
            'AUTORIZADA': 'success',
            'RECHAZADA': 'danger',
            'ERROR': 'danger',
            'ANULADA': 'secondary',
        }
        return colores.get(self.estado, 'secondary')
