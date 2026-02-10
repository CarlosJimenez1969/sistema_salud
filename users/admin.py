from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

# Configuramos cómo se verá el usuario en el panel
class CustomUserAdmin(UserAdmin):
    model = User
    # Le decimos a Django qué columnas mostrar en la lista
    list_display = ['email', 'username', 'cedula', 'role', 'is_staff']
    
    # Agregamos nuestros campos personalizados al formulario de edición
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('cedula', 'role', 'pago_realizado')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('email', 'cedula', 'role', 'pago_realizado')}),
    )

admin.site.register(User, CustomUserAdmin)