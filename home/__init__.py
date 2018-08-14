# import logging
# import logging.config
# import time
#
# class UTCFormatter(logging.Formatter):
#     converter = time.gmtime
#
#
# class MyFilter(logging.Filter):
#   def __init__(self, param=None):
#     super().__init__()
#     self.param = param
#
#   def filter(self, record):
#     if self.param is None:
#       allow = True
#     else:
#       allow = self.param not in record.msg
#     if allow:
#       record.msg = 'changed: ' + record.msg
#     return allow
#
#
#
# LOGGING = {
#   'version': 1,
#   'disable_existing_loggers': False,
#   'formatters': {
#     'verbose': {
#       'format': ('%(levelname)s %(asctime)s %(module)s ' +
#                  '%(funcName)s %(lineno)d %(message)s')
#     },
#     'simple' : {
#       'format': '%(levelname)s %(message)s'
#     },
#   },
#   'filters': {
#     'myfilter': {
#       '()'   : MyFilter,
#       'param': 'noshow',
#     },
#   },
#   'handlers': {
#     'console': {
#       'level': 'INFO',
#       'class': 'logging.StreamHandler',
#       'formatter': 'simple',
#       'filters': ['myfilter'],
#       'stream': 'ext://sys.stderr',
#     },
#     'file': {
#       # The values below are popped from this dictionary and
#       # used to create the handler, set the handler's level and
#       # its formatter.
#       'level': 'DEBUG',
#       'class': 'logging.handlers.RotatingFileHandler',
#       'formatter': 'verbose',
#       # The values below are passed to the handler creator callable
#       # as keyword arguments.
#       'filename': 'log-debug2.log',
#       'maxBytes': 1024*1024*5,
#       'backupCount': 5,
#       'mode': 'w',
#     },
#   },
#   'loggers': {
#     'cl': {
#       'handlers': ['console']
#     },
#     'fl': {
#       'handlers': ['file']
#     },
#   },
#   'root': {
#     'level': 'DEBUG',
#     'handlers': ['console', 'file'],
#   }
# }
#
# logging.config.dictConfig(LOGGING)
# logging.getLogger(__name__).addHandler(logging.NullHandler())