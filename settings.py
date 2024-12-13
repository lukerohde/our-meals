LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'app.log'),
        },
    },
    'loggers': {
        'main.views': {  # Replace 'main.views' with the appropriate module path if different
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
} 