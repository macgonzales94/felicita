"""
MODELOS FACTURACIÓN - PROYECTO FELICITA
Sistema de Facturación Electrónica para Perú

Modelos para el módulo de facturación electrónica según normativa SUNAT:
- SerieComprobante
- Factura
- FacturaItem
- NotaCredito
- NotaDebito
- GuiaRemision
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from aplicaciones.core.models import ModeloBase, Cliente, Producto, Empresa
from aplicaciones.usuarios.models import Usuario
import uuid

# =============================================================================
# MODELO SERIE COMPROBANTE
# =============================================================================
class SerieComprobante(ModeloBase):
    """
    Series para numeración de comprobantes según SUNAT
    """
    
    TIPO_COMPROBANTE_CHOICES = [
        ('01', 'Factura'),
        ('03', 'Boleta de Venta'),
        ('07', 'Nota de Crédito'),
        ('08', 'Nota de Débito'),
        ('09', 'Guía de Remisión'),
        ('20', 'Comprobante de Retención'),
        ('40', 'Comprobante de Percepción'),
    ]
    
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='series_comprobantes',
        verbose_name='Empresa'
    )
    
    tipo_comprobante = models.CharField(
        max_length=2,
        choices=TIPO_COMPROBANTE_CHOICES,
        verbose_name='Tipo de Comprobante'
    )
    
    serie = models.CharField(
        max_length=4,
        verbose_name='Serie',
        help_text='Serie del comprobante (ej: F001, B001)'
    )
    
    numero_actual = models.PositiveIntegerField(
        default=0,
        verbose_name='Número Actual',
        help_text='Último número usado'
    )
    
    numero_maximo = models.PositiveIntegerField(
        default=99999999,
        verbose_name='Número Máximo'
    )
    
    activa = models.BooleanField(
        default=True,
        verbose_name='Serie Activa'
    )
    
    punto_venta = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Punto de Venta',
        help_text='Identificador del punto de venta'
    )
    
    class Meta:
        db_table = 'facturacion_serie_comprobante'
        verbose_name = 'Serie de Comprobante'
        verbose_name_plural = 'Series de Comprobantes'
        unique_together = ['empresa', 'tipo_comprobante', 'serie']
        indexes = [
            models.Index(fields=['tipo_comprobante', 'serie']),
            models.Index(fields=['activa']),
        ]
    
    def __str__(self):
        return f"{self.get_tipo_comprobante_display()} - {self.serie}"
    
    def obtener_siguiente_numero(self):
        """Obtiene el siguiente número de la serie"""
        self.numero_actual += 1
        if self.numero_actual > self.numero_maximo:
            raise ValueError(f"Se agotó la numeración para la serie {self.serie}")
        self.save(update_fields=['numero_actual'])
        return self.numero_actual
    
    def get_numero_completo(self, numero=None):
        """Retorna el número completo del comprobante"""
        if numero is None:
            numero = self.numero_actual + 1
        return f"{self.serie}-{numero:08d}"

# =============================================================================
# MODELO BASE COMPROBANTE
# =============================================================================
class ComprobanteBase(ModeloBase):
    """
    Modelo base abstracto para todos los comprobantes
    """
    
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('validado', 'Validado'),
        ('enviado', 'Enviado a SUNAT'),
        ('aceptado', 'Aceptado por SUNAT'),
        ('rechazado', 'Rechazado por SUNAT'),
        ('anulado', 'Anulado'),
        ('baja', 'Comunicación de Baja'),
    ]
    
    MONEDA_CHOICES = [
        ('PEN', 'Nuevos Soles'),
        ('USD', 'Dólares Americanos'),
        ('EUR', 'Euros'),
    ]
    
    # Identificación del comprobante
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        verbose_name='Empresa Emisora'
    )
    
    serie_comprobante = models.ForeignKey(
        SerieComprobante,
        on_delete=models.PROTECT,
        verbose_name='Serie'
    )
    
    numero = models.PositiveIntegerField(
        verbose_name='Número'
    )
    
    numero_completo = models.CharField(
        max_length=20,
        verbose_name='Número Completo',
        help_text='Serie-Número (ej: F001-00000001)'
    )
    
    # Cliente
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        verbose_name='Cliente'
    )
    
    # Fechas
    fecha_emision = models.DateField(
        default=timezone.now,
        verbose_name='Fecha de Emisión'
    )
    
    fecha_vencimiento = models.DateField(
        blank=True,
        null=True,
        verbose_name='Fecha de Vencimiento'
    )
    
    # Montos
    moneda = models.CharField(
        max_length=3,
        choices=MONEDA_CHOICES,
        default='PEN',
        verbose_name='Moneda'
    )
    
    tipo_cambio = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal('1.0000'),
        verbose_name='Tipo de Cambio'
    )
    
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Subtotal'
    )
    
    descuento_global = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Descuento Global'
    )
    
    total_igv = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Total IGV'
    )
    
    total_otros_impuestos = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Total Otros Impuestos'
    )
    
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Total'
    )
    
    # Observaciones
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones'
    )
    
    # Usuario que registra
    usuario_registro = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='%(class)s_registrados',
        verbose_name='Usuario que Registra'
    )
    
    # Estado y auditoría SUNAT
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='borrador',
        verbose_name='Estado'
    )
    
    fecha_envio_sunat = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha de Envío a SUNAT'
    )
    
    hash_documento = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Hash del Documento'
    )
    
    codigo_qr = models.TextField(
        blank=True,
        verbose_name='Código QR'
    )
    
    respuesta_sunat = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Respuesta SUNAT'
    )
    
    xml_documento = models.TextField(
        blank=True,
        verbose_name='XML del Documento'
    )
    
    pdf_documento = models.FileField(
        upload_to='comprobantes/pdf/',
        blank=True,
        null=True,
        verbose_name='PDF del Documento'
    )
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['numero_completo']),
            models.Index(fields=['fecha_emision']),
            models.Index(fields=['cliente']),
            models.Index(fields=['estado']),
        ]
    
    def save(self, *args, **kwargs):
        """Generar número completo automáticamente"""
        if not self.numero_completo:
            self.numero_completo = f"{self.serie_comprobante.serie}-{self.numero:08d}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.numero_completo} - {self.cliente.razon_social}"
    
    def calcular_totales(self):
        """Calcula los totales del comprobante basado en los items"""
        items = self.items.all()
        
        subtotal = sum(item.valor_venta for item in items)
        total_igv = sum(item.igv for item in items)
        total = subtotal + total_igv - self.descuento_global
        
        self.subtotal = subtotal
        self.total_igv = total_igv
        self.total = total
        
        return {
            'subtotal': self.subtotal,
            'total_igv': self.total_igv,
            'total': self.total
        }
    
    def puede_ser_modificado(self):
        """Verifica si el comprobante puede ser modificado"""
        return self.estado in ['borrador', 'validado']
    
    def puede_ser_anulado(self):
        """Verifica si el comprobante puede ser anulado"""
        return self.estado in ['aceptado']

# =============================================================================
# MODELO FACTURA
# =============================================================================
class Factura(ComprobanteBase):
    """
    Facturas electrónicas según normativa SUNAT
    """
    
    TIPO_OPERACION_CHOICES = [
        ('0101', 'Venta Interna'),
        ('0112', 'Venta Interna - Sujeta a Detracción'),
        ('0113', 'Venta Interna - Sujeta a Detracción - Recursos Hidrobiológicos'),
        ('0121', 'Venta Interna - Sujeta a Detracción - Servicios de Transporte de Carga'),
        ('0200', 'Exportación de Bienes'),
        ('0201', 'Exportación de Servicios'),
        ('0202', 'Exportación de Servicios - Prestados por Sujetos Domiciliados'),
        ('0203', 'Exportación de Servicios - Prestados por Sujetos No Domiciliados'),
        ('0204', 'Venta Interna de Bienes y Prestación de Servicios no Gravados'),
        ('0205', 'Operaciones de Comercio Exterior'),
        ('0206', 'Venta de Bienes usados, obras de arte, metales preciosos y piedras preciosas'),
        ('0207', 'Venta de Bienes en consignación'),
        ('0208', 'Venta de Bienes a plazo'),
    ]
    
    # Configuración específica de factura
    tipo_operacion = models.CharField(
        max_length=4,
        choices=TIPO_OPERACION_CHOICES,
        default='0101',
        verbose_name='Tipo de Operación'
    )
    
    orden_compra = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Orden de Compra'
    )
    
    # Detracción (si aplica)
    sujeta_detraccion = models.BooleanField(
        default=False,
        verbose_name='Sujeta a Detracción'
    )
    
    codigo_detraccion = models.CharField(
        max_length=3,
        blank=True,
        verbose_name='Código de Detracción'
    )
    
    porcentaje_detraccion = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[
            MinValueValidator(Decimal('0.00')),
            MaxValueValidator(Decimal('100.00'))
        ],
        verbose_name='Porcentaje de Detracción'
    )
    
    monto_detraccion = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Monto de Detracción'
    )
    
    # Información adicional
    condicion_pago = models.CharField(
        max_length=20,
        choices=[
            ('contado', 'Al Contado'),
            ('credito', 'Al Crédito'),
        ],
        default='contado',
        verbose_name='Condición de Pago'
    )
    
    class Meta:
        db_table = 'facturacion_factura'
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'
        unique_together = ['serie_comprobante', 'numero']
    
    def calcular_detraccion(self):
        """Calcula el monto de detracción si aplica"""
        if self.sujeta_detraccion and self.porcentaje_detraccion > 0:
            self.monto_detraccion = (self.total * self.porcentaje_detraccion) / 100
        else:
            self.monto_detraccion = Decimal('0.00')
        return self.monto_detraccion

# =============================================================================
# MODELO BOLETA
# =============================================================================
class Boleta(ComprobanteBase):
    """
    Boletas de venta electrónicas
    """
    
    # Las boletas tienen menos campos que las facturas
    # pero heredan toda la funcionalidad base
    
    class Meta:
        db_table = 'facturacion_boleta'
        verbose_name = 'Boleta de Venta'
        verbose_name_plural = 'Boletas de Venta'
        unique_together = ['serie_comprobante', 'numero']

# =============================================================================
# MODELO ITEM COMPROBANTE BASE
# =============================================================================
class ItemComprobanteBase(ModeloBase):
    """
    Modelo base abstracto para items de comprobantes
    """
    
    TIPO_AFECTACION_IGV_CHOICES = [
        ('10', 'Gravado - Operación Onerosa'),
        ('11', 'Gravado - Retiro por premio'),
        ('12', 'Gravado - Retiro por donación'),
        ('13', 'Gravado - Retiro'),
        ('14', 'Gravado - Retiro por publicidad'),
        ('15', 'Gravado - Bonificaciones'),
        ('16', 'Gravado - Retiro por entrega a trabajadores'),
        ('17', 'Gravado - IVAP'),
        ('20', 'Exonerado - Operación Onerosa'),
        ('21', 'Exonerado - Transferencia Gratuita'),
        ('30', 'Inafecto - Operación Onerosa'),
        ('31', 'Inafecto - Retiro por Bonificación'),
        ('32', 'Inafecto - Retiro'),
        ('33', 'Inafecto - Retiro por Muestras Médicas'),
        ('34', 'Inafecto - Retiro por Convenio Colectivo'),
        ('35', 'Inafecto - Retiro por premio'),
        ('36', 'Inafecto - Retiro por publicidad'),
        ('40', 'Exportación de Bienes o Servicios'),
    ]
    
    # Producto
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        verbose_name='Producto'
    )
    
    # Descripción (puede ser diferente al producto)
    descripcion = models.CharField(
        max_length=250,
        verbose_name='Descripción'
    )
    
    # Cantidades
    cantidad = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))],
        verbose_name='Cantidad'
    )
    
    unidad_medida = models.CharField(
        max_length=10,
        default='NIU',
        verbose_name='Unidad de Medida'
    )
    
    # Precios
    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0000'))],
        verbose_name='Precio Unitario'
    )
    
    descuento_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal('0.0000'),
        validators=[MinValueValidator(Decimal('0.0000'))],
        verbose_name='Descuento Unitario'
    )
    
    # Cálculos
    valor_venta = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Valor de Venta'
    )
    
    # Impuestos
    tipo_afectacion_igv = models.CharField(
        max_length=2,
        choices=TIPO_AFECTACION_IGV_CHOICES,
        default='10',
        verbose_name='Tipo de Afectación IGV'
    )
    
    porcentaje_igv = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('18.00'),
        verbose_name='Porcentaje IGV'
    )
    
    igv = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='IGV'
    )
    
    precio_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Precio Total'
    )
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        """Calcular valores automáticamente"""
        # Calcular valor de venta
        self.valor_venta = (self.cantidad * self.precio_unitario) - (self.cantidad * self.descuento_unitario)
        
        # Calcular IGV según tipo de afectación
        if self.tipo_afectacion_igv in ['10', '11', '12', '13', '14', '15', '16', '17']:
            # Gravado con IGV
            self.igv = self.valor_venta * (self.porcentaje_igv / 100)
        else:
            # Exonerado, inafecto o exportación
            self.igv = Decimal('0.00')
        
        # Calcular precio total
        self.precio_total = self.valor_venta + self.igv
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.descripcion} - {self.cantidad} {self.unidad_medida}"

# =============================================================================
# MODELO FACTURA ITEM
# =============================================================================
class FacturaItem(ItemComprobanteBase):
    """
    Items de facturas
    """
    
    factura = models.ForeignKey(
        Factura,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Factura'
    )
    
    numero_item = models.PositiveIntegerField(
        verbose_name='Número de Item'
    )
    
    class Meta:
        db_table = 'facturacion_factura_item'
        verbose_name = 'Item de Factura'
        verbose_name_plural = 'Items de Facturas'
        unique_together = ['factura', 'numero_item']
        ordering = ['numero_item']

# =============================================================================
# MODELO BOLETA ITEM
# =============================================================================
class BoletaItem(ItemComprobanteBase):
    """
    Items de boletas
    """
    
    boleta = models.ForeignKey(
        Boleta,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Boleta'
    )
    
    numero_item = models.PositiveIntegerField(
        verbose_name='Número de Item'
    )
    
    class Meta:
        db_table = 'facturacion_boleta_item'
        verbose_name = 'Item de Boleta'
        verbose_name_plural = 'Items de Boletas'
        unique_together = ['boleta', 'numero_item']
        ordering = ['numero_item']

# =============================================================================
# MODELO NOTA DE CRÉDITO
# =============================================================================
class NotaCredito(ComprobanteBase):
    """
    Notas de crédito electrónicas
    """
    
    TIPO_NOTA_CREDITO_CHOICES = [
        ('01', 'Anulación de la operación'),
        ('02', 'Anulación por error en el RUC'),
        ('03', 'Corrección por error en la descripción'),
        ('04', 'Descuento global'),
        ('05', 'Descuento por ítem'),
        ('06', 'Devolución total'),
        ('07', 'Devolución por ítem'),
        ('08', 'Bonificación'),
        ('09', 'Disminución en el valor'),
        ('10', 'Otros conceptos'),
        ('11', 'Ajustes de operaciones de exportación'),
        ('12', 'Ajustes afectos al IVAP'),
    ]
    
    # Documento que se modifica
    tipo_documento_modificado = models.CharField(
        max_length=2,
        choices=[
            ('01', 'Factura'),
            ('03', 'Boleta'),
        ],
        verbose_name='Tipo de Documento Modificado'
    )
    
    numero_documento_modificado = models.CharField(
        max_length=20,
        verbose_name='Número de Documento Modificado'
    )
    
    # Motivo de la nota de crédito
    codigo_motivo = models.CharField(
        max_length=2,
        choices=TIPO_NOTA_CREDITO_CHOICES,
        verbose_name='Código de Motivo'
    )
    
    descripcion_motivo = models.TextField(
        verbose_name='Descripción del Motivo'
    )
    
    class Meta:
        db_table = 'facturacion_nota_credito'
        verbose_name = 'Nota de Crédito'
        verbose_name_plural = 'Notas de Crédito'
        unique_together = ['serie_comprobante', 'numero']

# =============================================================================
# MODELO NOTA DE DÉBITO
# =============================================================================
class NotaDebito(ComprobanteBase):
    """
    Notas de débito electrónicas
    """
    
    TIPO_NOTA_DEBITO_CHOICES = [
        ('01', 'Intereses por mora'),
        ('02', 'Aumento en el valor'),
        ('03', 'Penalidades/ otros conceptos'),
        ('10', 'Ajustes de operaciones de exportación'),
        ('11', 'Ajustes afectos al IVAP'),
    ]
    
    # Documento que se modifica
    tipo_documento_modificado = models.CharField(
        max_length=2,
        choices=[
            ('01', 'Factura'),
            ('03', 'Boleta'),
        ],
        verbose_name='Tipo de Documento Modificado'
    )
    
    numero_documento_modificado = models.CharField(
        max_length=20,
        verbose_name='Número de Documento Modificado'
    )
    
    # Motivo de la nota de débito
    codigo_motivo = models.CharField(
        max_length=2,
        choices=TIPO_NOTA_DEBITO_CHOICES,
        verbose_name='Código de Motivo'
    )
    
    descripcion_motivo = models.TextField(
        verbose_name='Descripción del Motivo'
    )
    
    class Meta:
        db_table = 'facturacion_nota_debito'
        verbose_name = 'Nota de Débito'
        verbose_name_plural = 'Notas de Débito'
        unique_together = ['serie_comprobante', 'numero']

# =============================================================================
# MODELO GUÍA DE REMISIÓN
# =============================================================================
class GuiaRemision(ModeloBase):
    """
    Guías de remisión electrónicas
    """
    
    TIPO_TRASLADO_CHOICES = [
        ('01', 'Venta'),
        ('02', 'Compra'),
        ('04', 'Traslado entre establecimientos de la misma empresa'),
        ('08', 'Importación'),
        ('09', 'Exportación'),
        ('13', 'Otros'),
        ('14', 'Venta sujeta a confirmación del comprador'),
        ('18', 'Traslado emisor itinerante CP'),
        ('19', 'Traslado a zona primaria'),
    ]
    
    MODALIDAD_TRANSPORTE_CHOICES = [
        ('01', 'Transporte público'),
        ('02', 'Transporte privado'),
    ]
    
    # Identificación
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        verbose_name='Empresa'
    )
    
    serie_numero = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Serie-Número'
    )
    
    fecha_emision = models.DateField(
        default=timezone.now,
        verbose_name='Fecha de Emisión'
    )
    
    # Datos del traslado
    tipo_traslado = models.CharField(
        max_length=2,
        choices=TIPO_TRASLADO_CHOICES,
        verbose_name='Tipo de Traslado'
    )
    
    modalidad_transporte = models.CharField(
        max_length=2,
        choices=MODALIDAD_TRANSPORTE_CHOICES,
        verbose_name='Modalidad de Transporte'
    )
    
    fecha_inicio_traslado = models.DateField(
        verbose_name='Fecha de Inicio de Traslado'
    )
    
    peso_bruto_total = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name='Peso Bruto Total (kg)'
    )
    
    # Direcciones
    direccion_origen = models.TextField(
        verbose_name='Dirección de Origen'
    )
    
    ubigeo_origen = models.CharField(
        max_length=6,
        verbose_name='Ubigeo de Origen'
    )
    
    direccion_destino = models.TextField(
        verbose_name='Dirección de Destino'
    )
    
    ubigeo_destino = models.CharField(
        max_length=6,
        verbose_name='Ubigeo de Destino'
    )
    
    # Transportista (si es transporte público)
    ruc_transportista = models.CharField(
        max_length=11,
        blank=True,
        verbose_name='RUC del Transportista'
    )
    
    razon_social_transportista = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Razón Social del Transportista'
    )
    
    # Conductor
    tipo_documento_conductor = models.CharField(
        max_length=1,
        choices=[
            ('1', 'DNI'),
            ('4', 'Carnet de Extranjería'),
            ('7', 'Pasaporte'),
        ],
        blank=True,
        verbose_name='Tipo de Documento del Conductor'
    )
    
    numero_documento_conductor = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Número de Documento del Conductor'
    )
    
    nombres_conductor = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Nombres del Conductor'
    )
    
    apellidos_conductor = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Apellidos del Conductor'
    )
    
    licencia_conductor = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Licencia del Conductor'
    )
    
    # Vehículo
    placa_vehiculo = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='Placa del Vehículo'
    )
    
    # Observaciones
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones'
    )
    
    # Estado SUNAT
    estado_sunat = models.CharField(
        max_length=20,
        choices=[
            ('borrador', 'Borrador'),
            ('enviado', 'Enviado'),
            ('aceptado', 'Aceptado'),
            ('rechazado', 'Rechazado'),
        ],
        default='borrador',
        verbose_name='Estado SUNAT'
    )
    
    hash_documento = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Hash del Documento'
    )
    
    xml_documento = models.TextField(
        blank=True,
        verbose_name='XML del Documento'
    )
    
    class Meta:
        db_table = 'facturacion_guia_remision'
        verbose_name = 'Guía de Remisión'
        verbose_name_plural = 'Guías de Remisión'
        indexes = [
            models.Index(fields=['serie_numero']),
            models.Index(fields=['fecha_emision']),
            models.Index(fields=['estado_sunat']),
        ]
    
    def __str__(self):
        return f"Guía {self.serie_numero}"