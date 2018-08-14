import sys

import pickle as pk
from pprint import pformat as pf
from typing import Collection, Dict, List
from mypy_extensions import TypedDict

sys.path.insert(0, '/Users/alberthan/PycharmProjects/magentaVAE/home')
F_ATTRS = [
  # 'f_back', # r
  # 'f_builtins', # r
  'f_code',
  # 'f_globals', # r
  'f_lasti',
  'f_lineno',
  'f_locals', # r
  # 'f_restricted',
  'f_trace',
]
f_attrs = F_ATTRS # [a for a in F_ATTRS if a not in ['f_locals']]
CO_ATTRS = [
   'co_argcount',
   'co_cellvars',
   'co_code',
   # 'co_consts', # redundant
   'co_filename',
   'co_firstlineno',
   'co_flags',
   'co_freevars',
   'co_kwonlyargcount',
   'co_lnotab',
   'co_name',
   # 'co_names',
   'co_nlocals',
   'co_stacksize',
   'co_varnames'
]
co_attrs = [a for a in CO_ATTRS if a not in ['co_consts', 'co_names']]
ATTRS = {
  'frame': F_ATTRS,  'f' : f_attrs,
  'code' : CO_ATTRS, 'co': co_attrs,
}

def pframe(obj):
  obj_dict = {}
  print('2')
  print(f'obj: {obj}')
  for attr in ATTRS[type(obj).__name__]:
    if hasattr(obj, attr):
      obj_dict.update({attr: (getattr(obj, attr))})
  return obj_dict

_en = enumerate

# recursion limiter
def rlimiter(d):
  tmp = {}
  for k, v in d.items():
    if isinstance(v, Collection):
      if isinstance(v, Dict):
        _ = {}
        for vk,vv in v.items():
          _.update({vk: type(vv).__name__})
        tmp.update({k: _})
      elif isinstance(v, List):
        _ = []
        for el in v:
          _.append(type(el).__name__)
          tmp.update({k: _})
    else:
      tmp.update({k: v})
  return tmp

def pdict(d, nd={}, rdl=0):
  """
  to convert a frame 1st call pframe to convert to dict
  d = dict
  nd = new dict
  rd = recursion depth limit
  """
  for k,v in d.items():
    prefix = k.split('_')[0]
    if not k.startswith('_'):
      print('1')
      print(f'k: {k}')
      print(f'prefix: {prefix}')
      print(f'v: {v}')
      print(f'rdl: {rdl}')
      if prefix in ATTRS and k in ATTRS[prefix]:
        if isinstance(v, dict):
          if rdl > 0:
            print('1.1')
            nv = rlimiter(v)
            print('1.1.1')
          else:
            print('1.2')
            rdl += 1
            nv = pdict(v, {}, rdl)
          print('1.1.2')
          print('a')
          nd.update({k: nv})
          print(nd)
        elif type(v).__name__ in ATTRS:
          print('b')
          rdl += 1
          nd.update({k: pdict(pframe(v), {}, rdl)})
          print(nd)
        else:
          print('c')
          nd.update({k: pf(v)})
  return nd
asd=pframe(sys._getframe())
qwe=pdict(asd)

myway = 12


with open('/Users/alberthan/PycharmProjects/magentaVAE/home/versions/event.pk', 'rb') as f:
  event = pk.load(f)

# frame = sys._getframe()
# pf_frame = pframe(frame)
# pd_frame = pdict(pf_frame)
#
# print(pf_frame)
# print(pd_frame)
# print()


# if isinstance(v, Dict):
#   ct = f'TypedDict("{k}", {{'  # container type
#   _idt = len(ct)
#   for vi, vk, vv in _en(v.items()):
#     if vi in [0, 1] or not vi % 2:
#       et += f'"{vk}": {type(vv).__name__},'  # element type
#     else:
#       et += f'\n{" "*_idt}'
#       et += f'"{vk}": {type(vv).__name__},'
#   ret = f'{ct}{et}}})'