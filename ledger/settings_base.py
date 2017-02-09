from django.core.exceptions import ImproperlyConfigured
from confy import env, database
from oscar.defaults import *
from oscar import get_core_apps, OSCAR_MAIN_TEMPLATE_DIR

import os

# Project paths
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.join(BASE_DIR, 'ledger')

# Application definitions
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG', False)
CSRF_COOKIE_SECURE = env('CSRF_COOKIE_SECURE', False)
SESSION_COOKIE_SECURE = env('SESSION_COOKIE_SECURE', False)
if DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = env('ALLOWED_HOSTS', [])
WSGI_APPLICATION = 'ledger.wsgi.application'
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.gis',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.flatpages',
    'social_django',
    'django_extensions',
    'reversion',
    'widget_tweaks',
    'django_countries',
    'django_cron',
    ] + get_core_apps([  # django-oscar overrides
        'ledger.basket',
        'ledger.order',
        'ledger.checkout',
        'ledger.address',
        'ledger.catalogue',
        'ledger.dashboard.catalogue',
        'ledger.payment'
    ]) + [
    'ledger.accounts',   #  Defines custom user model, passwordless auth pipeline.
    'ledger.licence',
    'ledger.payments',
    'ledger.payments.bpay',
    'ledger.payments.bpoint',
    'ledger.payments.cash',
    'ledger.payments.invoice',
    'ledger.taxonomy',
]

MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'dpaw_utils.middleware.SSOLoginMiddleware',
    'dpaw_utils.middleware.AuditMiddleware',  # Sets model creator/modifier field values.
    'oscar.apps.basket.middleware.BasketMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
]

# Authentication settings
LOGIN_URL = '/'
AUTHENTICATION_BACKENDS = (
    'social_core.backends.email.EmailAuth',
    'django.contrib.auth.backends.ModelBackend',
)
AUTH_USER_MODEL = 'accounts.EmailUser'
SOCIAL_AUTH_STRATEGY = 'social_django.strategy.DjangoStrategy'
SOCIAL_AUTH_STORAGE = 'social_django.models.DjangoStorage'
SOCIAL_AUTH_EMAIL_FORM_URL = '/ledger/'
SOCIAL_AUTH_EMAIL_VALIDATION_FUNCTION = 'ledger.accounts.mail.send_validation'
SOCIAL_AUTH_EMAIL_VALIDATION_URL = '/ledger/validation-sent/'
SOCIAL_AUTH_PASSWORDLESS = True
SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/'
SOCIAL_AUTH_USERNAME_IS_FULL_EMAIL = True
SOCIAL_AUTH_ADMIN_USER_SEARCH_FIELDS = ['first_name', 'last_name', 'email']
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'ledger.accounts.pipeline.lower_email_address',
    'ledger.accounts.pipeline.logout_previous_session',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    # 'social.pipeline.mail.mail_validation',
    'ledger.accounts.pipeline.mail_validation',
    'ledger.accounts.pipeline.user_by_email',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    #'social_core.pipeline.user.user_details'
)

SESSION_COOKIE_DOMAIN = env('SESSION_COOKIE_DOMAIN', None)
if SESSION_COOKIE_DOMAIN:
    SESSION_COOKIE_NAME = (SESSION_COOKIE_DOMAIN + ".ledger_sessionid").replace(".", "_")


# Email settings
ADMINS = ('asi@dpaw.wa.gov.au',)
EMAIL_HOST = env('EMAIL_HOST', 'email.host')
EMAIL_PORT = env('EMAIL_PORT', 25)
EMAIL_FROM = env('EMAIL_FROM', ADMINS[0])
DEFAULT_FROM_EMAIL = EMAIL_FROM


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(PROJECT_DIR, 'templates'),
            OSCAR_MAIN_TEMPLATE_DIR,
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',

                # django-oscar default templates
                'oscar.apps.search.context_processors.search_form',
                'oscar.apps.promotions.context_processors.promotions',
                'oscar.apps.checkout.context_processors.checkout',
                'oscar.apps.customer.notifications.context_processors.notifications',
                'oscar.core.context_processors.metadata',
            ],
        },
    },
]


BOOTSTRAP3 = {
    'jquery_url': '//static.dpaw.wa.gov.au/static/libs/jquery/2.2.1/jquery.min.js',
    'base_url': '//static.dpaw.wa.gov.au/static/libs/twitter-bootstrap/3.3.6/',
    'css_url': None,
    'theme_url': None,
    'javascript_url': None,
    'javascript_in_head': False,
    'include_jquery': False,
    'required_css_class': 'required-form-field',
    'set_placeholder': False,
}

OSCAR_DEFAULT_CURRENCY = 'AUD'

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
    },
}


# Database
DATABASES = {
    # Defined in the DATABASE_URL env variable.
    'default': database.config(),
}


# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/
LANGUAGE_CODE = 'en-AU'
TIME_ZONE = 'Australia/Perth'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(os.path.join(BASE_DIR, 'ledger', 'static')),
    os.path.join(os.path.join(BASE_DIR, 'wildlifelicensing', 'static')),
]
if not os.path.exists(os.path.join(BASE_DIR, 'media')):
    os.mkdir(os.path.join(BASE_DIR, 'media'))
MEDIA_ROOT = env('MEDIA_ROOT', os.path.join(BASE_DIR, 'media'))
MEDIA_URL = '/media/'

# Logging settings
# Ensure that the logs directory exists:
if not os.path.exists(os.path.join(BASE_DIR, 'logs')):
    os.mkdir(os.path.join(BASE_DIR, 'logs'))
LOGGING = {
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': env('LOG_CONSOLE_LEVEL', 'WARNING'),
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'ledger.log'),
            'formatter': 'verbose',
            'maxBytes': 5242880
        },
    },
    'loggers': {
        '': {
            'handlers': ['file', 'console'],
            'level': env('LOG_CONSOLE_LEVEL', 'WARNING'),
            'propagate': True
        },
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        'log': {
            'handlers': ['file'],
            'level': 'INFO'
        },
#        'oscar.checkout': {
#            'handlers': ['file'],
#            'level': 'INFO'
#        }
    }
}

# django-dynamic-fields test generation settings
DDF_FILL_NULLABLE_FIELDS = False

# Ledger settings
CMS_URL=env('CMS_URL',None)
LEDGER_USER=env('LEDGER_USER',None)
LEDGER_PASS=env('LEDGER_PASS')
NOTIFICATION_EMAIL=env('NOTIFICATION_EMAIL')

# BPAY settings
BPAY_BILLER_CODE=env('BPAY_BILLER_CODE')
# BPOINT settings
BPOINT_CURRENCY='AUD'
BPOINT_BILLER_CODE=env('BPOINT_BILLER_CODE')
BPOINT_USERNAME=env('BPOINT_USERNAME')
BPOINT_PASSWORD=env('BPOINT_PASSWORD')
BPOINT_MERCHANT_NUM=env('BPOINT_MERCHANT_NUM')
BPOINT_TEST=env('BPOINT_TEST',True)
# Custom Email Settings
EMAIL_BACKEND = 'ledger.ledger_email.LedgerEmailBackend'
PRODUCTION_EMAIL = env('PRODUCTION_EMAIL', False)
#print PRODUCTION_EMAIL
EMAIL_INSTANCE = env('EMAIL_INSTANCE','PROD')
NON_PROD_EMAIL = env('NON_PROD_EMAIL')
if not PRODUCTION_EMAIL:
    if not NON_PROD_EMAIL:
        raise ImproperlyConfigured('NON_PROD_EMAIL must not be empty if PRODUCTION_EMAIL is set to False')
    if EMAIL_INSTANCE not in ['PROD','DEV','TEST','UAT']:
        raise ImproperlyConfigured('EMAIL_INSTANCE must be either "PROD","DEV","TEST","UAT"')
    if EMAIL_INSTANCE == 'PRODUCTION':
        raise ImproperlyConfigured('EMAIL_INSTANCE cannot be \'PRODUCTION\' if PRODUCTION_EMAIL is set to False')
# Oscar settings
from oscar.defaults import *
OSCAR_ALLOW_ANON_CHECKOUT = True
OSCAR_SHOP_NAME = env('OSCAR_SHOP_NAME')
OSCAR_DASHBOARD_NAVIGATION.append(
    {
        'label': 'Payments',
        'icon': 'icon-globe',
        'children': [
            {
                'label': 'Invoices',
                'url_name': 'payments:invoices-list',
            },
            {
                'label': 'BPAY collections',
                'url_name': 'payments:bpay-collection-list',
            },
            {
                'label': 'BPOINT transactions',
                'url_name': 'payments:bpoint-dash-list',
            },
        ]
    }
)
