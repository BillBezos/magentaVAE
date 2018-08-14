from eliot.stdlib import EliotHandler

import os
import sys
os.environ['TF_CPP_MIN_LOG_LEVEL']='3'

sys.path.insert(0, '/Users/alberthan/PycharmProjects/magentaVAE/home')
from mods.models.music_vae.music_vae_train import main
import hunter as h
from pdb import Pdb
import tensorflow as tf
import logging
import logging.config

# 1. Convert midis
from mods.convert_dir_to_note_sequences import convert_directory

root_dir = os.path.join(os.path.dirname(os.getcwd()), 'midis')
output_file = os.path.join(os.getcwd(), 'tfrecords/notesequences.tfrecord')

if not os.path.exists(output_file):
    convert_directory(root_dir, output_file)

import time


class MyFilter(logging.Filter):
  """Demonstrate how to filter sensitive data:"""
  def __init__(self, param):
    self.param = param


  def filter(self, record):
    # The call signature matches string interpolation: args can be a tuple or
    #  a lone dict
    if isinstance(record.args, dict):
      record.args = self.sanitize_dict(record.args)
    else:
      record.args = tuple(self.sanitize_dict(i) for i in record.args)

    return True

  @staticmethod
  def sanitize_dict(d):
    if not isinstance(d, dict):
      return d

    if any(i for i in d.keys() if 'password' in i):
      d = d.copy()  # Ensure that we won't clobber anything critical

      for k, v in d.items():
        if 'password' in k:
          d[k] = '*** PASSWORD ***'

    return d


class CustomFormatter(logging.Formatter):
  def format(self, record):
    res = super(CustomFormatter, self).format(record)

    if hasattr(record, 'request'):
      filtered_request = MyFilter.sanitize_dict(record.request)
      res += '\n\t' + pformat(filtered_request, indent=4).replace('\n', '\n\t')
    return res

# debug = {
#   '_apply_op_helper':
#     h.Q(module_in=['tensorflow.python.framework.op_def_library',
#                    ],
#         function_in=['_apply_op_helper',
#                      ],
#         kind_in=['call', 'line', 'return', 'exception'],
#         action=h.VarsPrinter('locals()')
#       ),
#   'internal_convert_to_tensor':
#     h.Q(module_in=['tensorflow.python.framework.ops',
#                    ],
#         function_in=['internal_convert_to_tensor'
#                      ],
#         kind_in=['call', 'line', 'return', 'exception'],
#         action=h.VarsPrinter('locals()')
#       ),
# }

overview = {
  'o':
    h.Q(~h.Q(module_in=["six",
                        "pkg_resources",
                        "tensorflow"]),
                        # 'hunter',
                        # 'hunter.actions',
                        # 'hunter.util',
                        # 'hunter.predicates',
                        # 'hunter.event',
                        # 'hunter.const',
                        # 'hunter.tracer']),
        #~h.Q(filename=""),
        kind_in=['call', 'return', 'exception'],
        stdlib=False,
        #action=h.CallPrinter #TODO either freeze the logger into this or make loggre global
      ),
}

version_dir = '/Users/alberthan/PycharmProjects/magentaVAE/home/versions'
run_dir = f'{os.path.join(version_dir, "music_vae")}'
exs_path = f'{os.path.join(version_dir, "tfrecords/notesequences.tfrecord")}'
_args = [f'music_vae_train',
         f'--config=cat-mel_2bar_small',
         f'--run_dir={run_dir}',
         f'--mode=train',
         f'--examples_path={exs_path}',
         f'--hparams=batch_size=32,learning_rate=0.0005',
         f'--num_steps=500', ]

# LOGGING = {
#   'version': 1,
#   'disable_existing_loggers': False,
#   'formatters': {
#     'verbose': {
#       'format': ('%(name)s %(levelname)s %(asctime)s %(module)s '
#                  '%(funcName)s %(lineno)d %(message)s'
#                  '%(filename)s')
#     },
#     'simple': {
#       'format': '%(name)s %(levelname)s %(message)s'
#     },
#     'debug': {
#       '()'    : CustomFormatter,
#       'format': '%(name)s %(message)s',
#     },
#     'overview': {
#       'format': '%(name)s %(message)s'
#     }
#   },
#   'filters': {
#     'myfilter': {
#       '()'   : MyFilter,
#       'param': 'noshow',
#     },
#   },
#   'handlers': {
#     'console1': {
#       # 'level': 'INFO',
#       'class': 'logging.StreamHandler',
#       'formatter': 'overview',
#       'filters': ['myfilter'],
#       #'stream': 'ext://sys.stderr',
#     },
#     'file': {
#       # The values below are popped from this dictionary and
#       # used to create the handler, set the handler's level and
#       # its formatter.
#       # 'level': 'DEBUG',
#       'class': 'logging.FileHandler',
#       'formatter': 'overview',
#       'filters': ['myfilter'],
#       # The values below are passed to the handler creator callable
#       # as keyword arguments.
#       'filename': 'log-debug3.log',
#       # 'maxBytes': 1024*1024*2,
#       # 'backupCount': 5,
#       'mode': 'a',
#     },
#     'ovfile': {
#       # 'level': 'DEBUG',
#       'class': 'logging.FileHandler',
#       'formatter': 'overview',
#       'filename': 'overview-log.log',
#       'mode': 'w',
#     },
#     'ovfile2': {
#       # 'level'    : 'DEBUG',
#       'class'    : 'logging.StreamHandler',
#       'formatter': 'simple',
#       #'stream'   : 'ext://sys.stderr',
#     },
#   },
#   'loggers': {
#     'hunter.actions': {
#       'level': 'DEBUG',
#       'handlers': ['ovfile2'],
#       'propagate': False,
#     },
#     'hunter.actions.Call': {
#       'level': 'DEBUG',
#       'handlers': ['ovfile'],
#       'propagate': False,
#     },
#     'hunter.actions.Code': {
#       'level': 'DEBUG',
#       'handlers': ['ovfile2'],
#       'propagate': False,
#     },
#   },
#   'root': {
#     'level': 'CRITICAL',
#     'handlers': ['ovfile2'],
#   }
# }
#https://github.com/tensorflow/tensorflow/issues/1258
LOGGING = {
  'version': 1,
  'disable_existing_loggers': False,
  'formatters': {
    'simple': {
      'format': '%(name)s %(levelname)s %(message)s'
    },
    'overview': {
      'format': '%(name)s %(message)s %(levelname)s'
    }
  },
  'handlers': {
    'ovfile': {
      'level': 'DEBUG',
      'class': 'logging.FileHandler',
      'formatter': 'overview',
      'filename': 'overview-log.log',
      'mode': 'w',
    },
  },
  # 'loggers': {
  #   'hunter.actions.Call': {
  #     'level': 'DEBUG',
  #     'handlers': ['ovfile'],
  #     'propagate': False,
  #   },
  # },
  'root': {
    'level': 'DEBUG',
  }
}


class LoggingContext(object):
  def __init__(self, logger, level=None, handler=None, close=True):
    self.logger = logger
    self.level = level
    self.handler = handler
    self.close = close

  def __enter__(self):
    if self.level is not None:
      self.old_level = self.logger.level
      self.logger.setLevel(self.level)
    if self.handler:
      self.logger.addHandler(self.handler)

  def __exit__(self, et, ev, tb):
    if self.level is not None:
      self.logger.setLevel(self.old_level)
    if self.handler:
      self.logger.removeHandler(self.handler)
    if self.handler and self.close:
      self.handler.close()
    # implicit return of None => don't swallow exceptions


if __name__ == '__main__':
  # logging.config.dictConfig(LOGGING)
  logging.getLogger(__name__).addHandler(logging.NullHandler())
  cl = logging.getLogger('hunter.actions.Call')
  cl.addHandler(logging.StreamHandler())
  cl.setLevel(logging.DEBUG)
  fh = logging.FileHandler('ov10.txt')
  fh.setLevel(logging.DEBUG)
  formatter = logging.Formatter('%(name)s %(message)s %(levelname)s')
  fh.setFormatter(formatter)
  with LoggingContext(cl, level=logging.DEBUG, handler=fh, close=True):

    from tensorflow.python.platform import tf_logging
    tf_logger = tf_logging._get_logger()
    tf_logger.setLevel(logging.WARNING)
    tf_logger.propagate = False
    tf_logger.handlers = []
    tf_logger.disabled = True
    tf_logging.set_verbosity(logging.CRITICAL)
    with h.trace(overview['o']) as t:
      tf.app.run(main, _args)
  # pmod()
  # pmod2()