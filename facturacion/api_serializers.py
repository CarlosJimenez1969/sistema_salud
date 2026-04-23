from rest_framework import serializers
from .models import FacturaElectronica


class ReceptorSerializer(serializers.Serializer):
    tipo_identificacion = serializers.ChoiceField(
        choices=['04', '05', '06', '07'],
        default='05',
        help_text='04=RUC, 05=Cédula, 06=Pasaporte, 07=Consumidor Final',
    )
    identificacion = serializers.CharField(max_length=20)
    nombre = serializers.CharField(max_length=300)
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    direccion = serializers.CharField(max_length=300, required=False, default='N/A')


class ItemFacturaSerializer(serializers.Serializer):
    descripcion = serializers.CharField(max_length=300)
    cantidad = serializers.DecimalField(max_digits=12, decimal_places=6, default=1)
    precio_unitario = serializers.DecimalField(max_digits=12, decimal_places=6)
    descuento = serializers.DecimalField(max_digits=12, decimal_places=6, default=0)


class EmitirFacturaSerializer(serializers.Serializer):
    receptor = ReceptorSerializer()
    items = ItemFacturaSerializer(many=True, min_length=1)
    forma_pago = serializers.CharField(
        max_length=2, default='01',
        help_text='01=Efectivo, 19=Tarjeta, 20=Transferencia, etc.',
    )


class FacturaElectronicaSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    tipo_id_display = serializers.CharField(source='get_receptor_tipo_id_display', read_only=True)

    class Meta:
        model = FacturaElectronica
        fields = [
            'id',
            'clave_acceso',
            'numero_secuencial',
            'receptor_tipo_id',
            'tipo_id_display',
            'receptor_identificacion',
            'receptor_nombre',
            'receptor_email',
            'receptor_direccion',
            'subtotal',
            'iva_porcentaje',
            'iva_valor',
            'total',
            'descripcion',
            'estado',
            'estado_display',
            'numero_autorizacion',
            'fecha_autorizacion',
            'mensajes_sri',
            'fecha_emision',
            'fecha_envio',
        ]
        read_only_fields = fields
