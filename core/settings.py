from pathlib import Path
from decouple import config, Csv
import dj_database_url
import os
import certifi

os.environ['SSL_CERT_FILE'] = certifi.where()

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Seguridad ──────────────────────────────────────────────────────────────────
SECRET_KEY = config('SECRET_KEY')
DEBUG      = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*', cast=Csv())

# ── Aplicaciones ───────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'users',
    'medico',
    'paciente',
    'citas',
    'historia',
    'facturacion',

    'rest_framework',
    'rest_framework.authtoken',
    'cloudinary_storage',
    'cloudinary',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.ReferrerPolicyMiddleware',
    'core.middleware.SeguridadSesionMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# ── Base de datos ──────────────────────────────────────────────────────────────
_database_url = config('DATABASE_URL', default='')
if _database_url:
    DATABASES = {
        'default': dj_database_url.config(
            default=_database_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME':     config('DB_NAME',     default='sistema_medico_db'),
            'USER':     config('DB_USER',     default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST':     config('DB_HOST',     default='localhost'),
            'PORT':     config('DB_PORT',     default='5432'),
        }
    }

# ── Validación de contraseñas ──────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internacionalización ───────────────────────────────────────────────────────
LANGUAGE_CODE = 'es-ec'
TIME_ZONE     = 'America/Guayaquil'
USE_I18N      = True
USE_TZ        = True

# ── Archivos estáticos ─────────────────────────────────────────────────────────
STATIC_URL  = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# ── Cloudinary (almacenamiento de imágenes en la nube) ─────────────────────────
CLOUDINARY_CLOUD_NAME = config('CLOUDINARY_CLOUD_NAME', default='')
CLOUDINARY_API_KEY    = config('CLOUDINARY_API_KEY',    default='')
CLOUDINARY_API_SECRET = config('CLOUDINARY_API_SECRET', default='')

if CLOUDINARY_CLOUD_NAME:
    import cloudinary
    cloudinary.config(
        cloud_name = CLOUDINARY_CLOUD_NAME,
        api_key    = CLOUDINARY_API_KEY,
        api_secret = CLOUDINARY_API_SECRET,
        secure     = True,
    )
    STORAGES = {
        "default":     {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
        'API_KEY':    CLOUDINARY_API_KEY,
        'API_SECRET': CLOUDINARY_API_SECRET,
    }
else:
    STORAGES = {
        "default":     {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }

# ── Autenticación ──────────────────────────────────────────────────────────────
AUTH_USER_MODEL      = 'users.User'
AUTHENTICATION_BACKENDS = [
    'users.backends.UsernameOrEmailBackend',
]
MEDIA_URL            = '/media/'
MEDIA_ROOT           = BASE_DIR / 'media'
LOGIN_URL            = 'login'
LOGIN_REDIRECT_URL   = 'login_success'
LOGOUT_REDIRECT_URL  = 'login'
SESSION_SAVE_EVERY_REQUEST = True

# ── Correo electrónico ─────────────────────────────────────────────────────────
import ssl
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = config('EMAIL_HOST_USER',     default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL  = f'VertexSalud <{EMAIL_HOST_USER}>'
EMAIL_SSL_CONTEXT   = ssl._create_unverified_context()

# ── PayPal ─────────────────────────────────────────────────────────────────────
PAYPAL_CLIENT_ID     = config('PAYPAL_CLIENT_ID',     default='')
PAYPAL_CLIENT_SECRET = config('PAYPAL_CLIENT_SECRET', default='')
PAYPAL_MODE          = config('PAYPAL_MODE',          default='sandbox')

# ── PayPhone ────────────────────────────────────────────────────────────────────
PAYPHONE_TOKEN    = config('PAYPHONE_TOKEN',    default='')
PAYPHONE_STORE_ID = config('PAYPHONE_STORE_ID', default='')

# ── Facturación Electrónica SRI Ecuador ───────────────────────────────────────
SRI_RUC                   = config('SRI_RUC',                   default='')
SRI_RAZON_SOCIAL          = config('SRI_RAZON_SOCIAL',          default='')
SRI_NOMBRE_COMERCIAL      = config('SRI_NOMBRE_COMERCIAL',      default='')
SRI_DIRECCION_MATRIZ      = config('SRI_DIRECCION_MATRIZ',      default='')
SRI_OBLIGADO_CONTABILIDAD = config('SRI_OBLIGADO_CONTABILIDAD', default='NO')
SRI_ESTABLECIMIENTO       = config('SRI_ESTABLECIMIENTO',       default='001')
SRI_PUNTO_EMISION         = config('SRI_PUNTO_EMISION',         default='001')
SRI_AMBIENTE              = config('SRI_AMBIENTE',              default='1')
SRI_IVA_PORCENTAJE        = config('SRI_IVA_PORCENTAJE',        default='0')
SRI_CERTIFICADO_P12       = config('SRI_CERTIFICADO_P12',       default='')
SRI_CERTIFICADO_PASSWORD  = config('SRI_CERTIFICADO_PASSWORD',  default='')
