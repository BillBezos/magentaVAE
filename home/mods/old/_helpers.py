import os, copy, pdb, ipdb, types, glob
from IPython import embed
from argparse import Namespace
import os, sys, math
import dill as pickle
from pprint import pformat as pf
from google.protobuf.json_format import MessageToJson
#https://vinta.ws/code/ipdb-interactive-python-debugger-with-ipython.html
#https://stackoverflow.com/questions/18090672/convert-dictionary-entries-into-variables-python
#sys.settrace
#https://stackoverflow.com/questions/20577806/keep-function-namespace-alive-for-debugging-in-ipython
# http://stackabuse.com/formatting-strings-with-python/
import functools
import sys, re
# from ..versions import vae01

lnl = line_no_list = []
lsl = locals_list = []
etc = []
opsl = []
prev_filename = []
prev_filenamens = []
prev_filename_start = 0
EXCLUDE = ['op_info', 'op_def', 'g', 'deprecation_version',
       'default_type_attr_map', 'attr_def', 'attrs',
       'input_arg', 'input_name', 'prev_filename']

_en = enumerate

def to_json(etc):
  from google.protobuf.json_format import MessageToJson
  ts = ''
  for k,v in etc.items():
    try:
      ts += f'{k}: {str(MessageToJson(v))}\n'
    except:
      ts += f'{k}: {str(v)}\n'
  return ts+'\n'

def get_locals(func):

  def wrap(*args, **kw):
    tracer = functools.partial(trace_calls, to_be_traced=[func.__name__])
    sys.settrace(tracer)
    try:
      res = func(*args, **kw)
    finally:
      sys.settrace(None)
    return res

  def trace_lines(frame, event, arg): #_apply_op_helper
    global lnl, lsl, etc, prev_filenamens, f
    if event != 'line':
      return
    co = frame.f_code
    func_name = co.co_name
    line_no = frame.f_lineno

    prev_filenamens.append(f'{line_no}, len(pfn): {len(prev_filename)}, in _apply_op_helper')

    lns = line_no_string = f"* {func_name:-<70}{line_no}"
    lnl.append(lns)

    _s = pf({k:v for k,v in frame.f_locals.items() if k not in EXCLUDE})
    _sl = _s.split('\n')
    _p = '** '
    _pl = [_p] + [' '*len(_p)]*(len(_sl)-1)
    _l = [''.join(_el) for _el in zip(_pl, _sl)]
    lss = locals_string = '\n'.join(_l)
    lsl.append(lss)

    etc.append(str(to_json(frame.f_locals)))
    #f = frame

  def trace_lines_ops(frame, event, arg): #internal_convert_to_tensor
    global opsl, prev_filename_start, prev_filenamens
    if event != 'line':
      return

    co = frame.f_code
    func_name = co.co_name
    line_no = frame.f_lineno

    prev_filenamens.append(f'{line_no}, len(pfn): {len(prev_filename)}, in internal_convert_to_tensor')

    if line_no == 1092 and len(opsl) > 1000: #sum(['1092' in x[0] for x in opsl]) > 2:
      opsl = []

    lns = line_no_string = f"* {func_name:-<70}{line_no}"
    #lnl.append(lns); print(lns)
    _f_locals = {k:v for k,v in frame.f_locals.items() if k not in EXCLUDE}

    _s = pf({k:v for k,v in _f_locals.items() if k not in EXCLUDE})
    _sl = _s.split('\n')
    _p = '** '
    _pl = [_p] + [' '*len(_p)]*(len(_sl)-1)
    _l = [''.join(_el) for _el in zip(_pl, _sl)]

    opsl.append([lns, str(to_json(frame.f_locals)), len(prev_filename)])

  def trace_calls(frame, event, arg, to_be_traced):
    global prev_filename, prev_filename_start
    if event != 'call':
      return
    co = frame.f_code
    func_name = co.co_name
    try:
      args_str = str(frame.f_locals['args'])
    except:
      args_str = ''
    if func_name == 'write':
      # Ignore write() calls from printing
      return
    line_no = frame.f_lineno
    filename = co.co_filename
    if filename.endswith('op_def_library.py'):
      prev_filename_start = 0 # pfns gets reset only when op_def_lib is called
      prev_filename.append(f'{filename}: {func_name} ({line_no})')
      pf('* Call to {} on line {} of {}'.format(
        func_name, line_no, filename))
      if func_name in to_be_traced:
        # Trace into this function
        return trace_lines
    elif filename.endswith('ops.py'):
      if prev_filename_start == 0:
        prev_filename_start = len(prev_filename)
      prev_filename.append([filename, prev_filename_start, func_name, line_no])
      if func_name in to_be_traced:
        r1 = re.compile(r"op_def_library\.py:.*? \(\d+\)")
        txt = str(prev_filename[prev_filename_start-2])
        if r1.search(txt):
          return trace_lines_ops
    else:
      prev_filename.append(f'{filename}, {line_no}, {func_name}')

    return

  return wrap

import re

pkls = ['lnl','lsl','etc','opsl',
    'prev_filename','prev_filenamens',
    'prev_filename_start']

def tpk(name):
  with open(f'{name}.pk', 'wb') as f:
    pickle.dump(exec(name), f)

def pmod(pkd=None):
  import pickle, os
  pkd = lpk()
  bp = '/Users/alberthan/.virtualenvs/magentaVAE/home/versions'
  j = lambda fn: os.path.join(bp, f'{fn}.pk')
  s = lambda v: f'{str(v)}\n'
  for k,vs in pkd.items():
    if k == 'lnl':
      if os.path.exists(j('lnl')):
        os.remove(j('lnl'))
      nv = ''
      for v in vs:
        with open(j('lnl'), 'a') as f:
          f.write(s(v))
    if k == 'lsl':
      if os.path.exists(j('lsl')):
        os.remove(j('lsl'))
      nv = ''
      for v in vs:
        with open(j('lsl'), 'a') as f:
          f.write(s(v))
    if k == 'etc':
      if os.path.exists(j('etc')):
        os.remove(j('etc'))
      nv = ''
      for v in vs:
        with open(j('etc'), 'a') as f:
          f.write(s(v))
    if k == 'opsl':
      if os.path.exists(j('opsl')):
        os.remove(j('opsl'))
      nv = ''
      for v in vs:
        with open(j('opsl'), 'a') as f:
          f.write(s(v))
    if k == 'prev_filename':
      if os.path.exists(j('prev_filename')):
        os.remove(j('prev_filename'))
      nv = ''
      for v in vs:
        with open(j('prev_filename'), 'a') as f:
          f.write(s(v))
    if k == 'prev_filenamens':
      if os.path.exists(j('prev_filenamens')):
        os.remove(j('prev_filenamens'))
      nv = ''
      for v in vs:
        with open(j('prev_filenamens'), 'a') as f:
          f.write(s(v))
    if k == 'prev_filename_start':
      if os.path.exists(j('prev_filename_start')):
        os.remove(j('prev_filename_start'))
      nv = ''
      with open(j('prev_filename_start'), 'a') as f:
        f.write(s(v))

from functools import wraps
#format tab
def ftab(f):
  @wraps(f)
  def wrapper(*args, **kwds):
    l,fnc,n = f(*args, **kwds)
    l = l+':'
    fnc = fnc+','
    s = f'{l:35}{fnc:35}{n}'
    return s
  return wrapper

@ftab
def rp(v): # regex parse
  u1 = r'.*?([A-z_]+\/[A-z_]+\.py): ' + \
     r'([A-z_<>]+) (\(\d+\))' #location 1
  rx1 = re.compile(u1)
  u2 = r'.*?([A-z_]+\/[A-z_]+\.py)\', ' + \
     r'(\d+).*?([A-z_]+).*?(\d+)' #location 2
  rx2 = re.compile(u2)
  u3 = r'.*?([A-z_\d\.]+\/[A-z_\d]+\.py), ' + \
     r'([\d]+), ([A-z_<>]+)' #location 3
  rx3 = re.compile(u3)
  rxs = {'op_def_library.py': #123
           lambda v: [rx1.match(v).group(g) for g in [1,2,3]],
         'ops.py': #134
           lambda v: [rx2.match(v).group(g) for g in [1,3,4]],
         }
  v = str(v)
  if v.startswith('<'):
    return v.split(',')
  for k in rxs:
    if k in v:
      return rxs[k](v)
  return [rx3.match(v).group(g) for g in [1,3,2]]

# join python path
def jpy(fn,op):
  # fn: filename, op: operation
  # bp: basepath
  # np: new path
  bp = '/Users/alberthan/.virtualenvs/magentaVAE/home/versions/data'
  np = os.path.join(bp, f'{fn}.py')
  if op == 'a' and os.path.exists(np):
    os.remove(np)
  return np,op

# join pickle path
def jpk(fn,op):
  # fn: filename, op: operation
  # bp: basepath
  # np: new path
  bp = '/Users/alberthan/.virtualenvs/magentaVAE/home/versions'
  np = os.path.join(bp, f'{fn}.pk')
  if op == 'a' and os.path.exists(np):
    os.remove(np)
  return np,op

def s(v):
  return f'{str(v)}\n'

def rpetc(vbody,vhead):
  v = str(vbody)
  # keys regex
  ksrx = re.compile(r'\n([a-z_]+)')
  keys = ['keywords'] + ksrx.findall(v)
  ksvs = re.compile(r'keywords: ({.*})') # keywords values
  kwds = ksvs.match(v).group(1)
  i = 2
  kwds1=re.split('\': |, \'|{\'|}', kwds)
  kwds1[0],kwds1[-1] = '{','\n  }'
  kwds2 = kwds1.copy()
  for k in range(1, len(kwds1)-1, 2):
    kwds2[k] = '\n' + ' '*i + kwds2[k] + ': '
  kwds3 = ''.join(kwds2)
  v2 = re.sub('{.*}', kwds3, v, 1)
  v3 = re.sub('keywords', '  keywords', v2, 1)
  v4 = v3.replace('tensorflow.python.framework', 'tf.py.fw')
  v5 = v4.replace('\n', '\n  ')
  v6 = f'{vhead}\n{v5}'
  v7 = v6.rstrip(' ')
  return v7

def idt(ns=2):
  # ns = num spaces
  return f'\n{" "*ns}'

def rpictt(vl):
  # enumerate index (put this in a class)
  if not hasattr(rpictt, 'eni'):
    rpictt.eni = 1
  vhead = vl[0]
  vhead = vhead.replace('-','',9)
  # vbody
  vb = vl[1]
  vb = vb.replace('/Users/alberthan/.virtualenvs/magentaVAE/home/', '')
  # indent
  i = 2
  ic= i
  rx = re.compile(r'.+\[(.+)\]', re.S)
  if not rx.match(vb):
    nvb = vb.replace('\n', '\n  ')
    nvb2 = nvb.rstrip(' ')
    nv = f'{vhead} # {rpictt.eni}\n  {nvb2}'
    rpictt.eni += 1
    return nv
  vb1 = f'\n{vb}'
  vb2 = vb1.replace('\n', idt(i))
  vb3 = vb2.replace('tensorflow.python.framework', 'tf.py.fw')

  cfl = rx.match(vb3)
  cfl2 = cfl.group(1)
  cfl3 = [el.strip() for el in cfl2.split(',')]
  i += 2
  cfl4 = [f'{idt(i)}{cfl3[n]}'
            if n%2==0
            else
          f'{idt(i+2)}{cfl3[n]}'
            for n in range(len(cfl3))]
  cfl5 = ''.join(cfl4)
  cfl6 = f'[{cfl5}{idt(i)}]'
  vb4 = re.sub(r'\[.+\]', cfl6, vb3, 1)
  vb5 = f'{vhead} # {rpictt.eni}{vb4}'
  rpictt.eni += 1
  vb6 = vb5.rstrip(' ')
  # keyword value key, keyword value value
  if 'value: Tensor' in vb6:
    eni,k,v,vidt = psdict(vb6,'value','Tensor','(',True)[0]
    vidt += ic
    nv = fws(v,
             r', ([a-z]+=)',
             rf',\n{" "*vidt} \1')
    vb6 = vb6.replace(v, nv)
  i -= 2
  return vb6

def pmod2():
  pkls = ['lnl','lsl','etc','opsl',
      'prev_filename','prev_filenamens',
      'prev_filename_start']
  pkd = {}
  for fn in pkls:
    with open(*jpk(fn,'rb')) as f:
      pkd[fn] = pickle.load(f)
  nd = {}
  for k,vs in pkd.items():

    if k == 'prev_filename':
      nvs = []
      for v in vs:
        nvs.append(rp(v))
      with open(*jpy('pfn','a')) as f:
        for i,v in enumerate(nvs):
          nv = f'{i+1:>5} {v}'
          f.write(s(nv))

    if k == 'etc': #lnl
      nvs = []
      for i,v in enumerate(vs):
        nvs.append(rpetc(v,pkd['lnl'][i]))
      # _apply_op_helper
      with open(*jpy('aoh','a')) as f:
        for v in nvs:
          f.write(v)

    if k == 'opsl':
      nvs = []
      for v in vs:
        nvs.append(rpictt(v))
      # internal_convert_to_tensor
      with open(*jpy('ictt2','a')) as f:
        for i,v in _en(nvs[-35:]):
          nv = re.sub(r'(.*?)# (\d{4})',
                      rf'\1# {i} (\2)',
                      v)
          f.write(nv)

# format whitespace
def fws(s,o,r):
  """
    s = a string, the value
    o = original
    r = replacement
  """
  nv = re.sub(o,r,s)
  return nv

# print list
def plist(l):
  for el in l:
    print(el[0])

# print str dict
def psdict(dl,
           k='',
           v='',
           ic='',
           eni=False):
  kv = f'.*?({k}: {v}.*?)\n'
  rx = re.compile(kv, re.S)
  ret = []
  if isinstance(dl, str):
    dl = [dl]
  # for str dict in dict list
  for i,sd in _en(dl):
    m = rx.match(sd)
    if m:
      if eni:
        _l = [i] + m.group(1).split(':',1) + [m.group(1).find(ic)]
        ret.append(_l)
      else:
        ret.append(m.group(1).split(':',1))
  return ret

def compose(*functions):
  return functools.reduce(lambda f, g: lambda x: f(g(x)), functions, lambda x: x)

def lpk():
  import pickle, os
  bp = '/Users/alberthan/.virtualenvs/magentaVAE/home/versions'
  j = lambda fn: os.path.join(bp, fn)
  with open(j('lnl.pk'), 'rb') as f:
    lnl = pickle.load(f)
  with open(j('lsl.pk'), 'rb') as f:
    lsl = pickle.load(f)
  with open(j('etc.pk'), 'rb') as f:
    etc = pickle.load(f)
  with open(j('opsl.pk'), 'rb') as f:
    opsl = pickle.load(f)
  with open(j('prev_filename.pk'), 'rb') as f:
    prev_filename = pickle.load(f)
  with open(j('prev_filenamens.pk'), 'rb') as f:
    prev_filenamens = pickle.load(f)
  with open(j('prev_filename_start.pk'), 'rb') as f:
    prev_filename_start = pickle.load(f)
  pkls = {'lnl': lnl,
      'lsl': lsl,
      'etc': etc,
      'opsl': opsl,
      'prev_filename': prev_filename,
      'prev_filenamens': prev_filenamens,
      'prev_filename_start': prev_filename_start,
      }
  return pkls

def pklsfn():
  # from  import lnl,lsl,etc,opsl,prev_filename,prev_filenamens,prev_filename_start
  import pickle
  pkls = {'lnl': lnl,
      'lsl': lsl,
      'etc': etc,
      'opsl': opsl,
      'prev_filename': prev_filename,
      'prev_filenamens': prev_filenamens,
      'prev_filename_start': prev_filename_start,
      }
  for k,v in pkls.items():
    with open(f'{k}.pk', 'wb') as f:
      pickle.dump(v, f)
  return pkls

def p(l,s=None,n=None):
  if not s and not n:
    for i,el in enumerate(l):
      print(f'{i}: {el}')
  else:
    for i,el in enumerate(l[s:s+n]):
      print(f'{i+s}: {el}')


def _p(x):
  for a,b,c in x:
    print(f"{a}'\n'{b}'\n'{c}")

def pfnw():
  # from  import prev_filename, prev_filenamens
  with open('prev.py', 'a') as f:
    for fn in prev_filename:
      f.write(str(fn)+'\n')
  with open('prevns.py', 'a') as f:
    for ns in prev_filenamens:
      f.write(str(ns)+'\n')

def pnse():
  # from  import lnl,lsl,etc
  netc = to_json(etc)
  with open('nse2.py', 'a') as f:
    for ln,ls,et in zip(lnl,lsl,netc):
      f.write(f'{ln}\n{ls}\n{et}\n')




def tojson2(etc):
  from google.protobuf.json_format import MessageToJson
  ret = []
  for el in etc:
    ts = ''
    for k,v in el.items():
      try:
        ts += f'JSON{k}: {str(MessageToJson(v))}\nJSON'
      except:
        ts += f'{k}: {str(v)}\n'
    ret.append(ts+'\n')
  return ret

def pl(l):
  for el in l:
    print(el)

def prev_fn(pfn):
  ret = []
  for i,p in enumerate(pfn):
    if isinstance(p, str) and 'op_def_library.py' in p:
      ret.append(f'{i}: {p}')
  #odl_i = int(re.match(r'\d+', ret[-1]).group())

  return ret

def nums(opsl):
  tmp = []
  for el in s:
    tmp.append(el[-4:])
  return tmp

def opslfn(opsl):
  ret = []
  for ln,ls in opsl:
    if '1092' in ln:
      ret.append([f'{ln}\n{ls}'])
    else:
      ret[-1].append(f'{ln}\n{ls}')
  return ret

def nsl(ns):
  ret = []
  t = []
  for s in ns:
    if s[:3] == '343':
      ret.append([s])
    else:
      ret[-1].append(s)
  return ret

def popsl(new):
  for lel in new:
    for el in lel:
      print(el)

def petc(lnl,lsl,etc):
  with open('etc.py', 'a') as f:
    for ln,ls,et in zip(lnl,lsl,etc):
      f.write(f"{ln}'\n'{ls}'\n'{et}'\n\n'")
    # if 'attrs' in et:
    #     print(ln, '\n', ls, '\n', et['attrs'], '\n\n')
    # else:
    #     print(ln, '\n', ls, '\n', et, '\n\n')

def pk(filename, localsdict):
  return
  pkpack = {}
  for k,v in localsdict.items():
    try:
      if not pickle.detect.baditems(v):
        pkpack.update({k:v})
      else:
        pkpack.update({k:str(v)})
    except:
      pkpack.update({k:str(v)})
  # pkpack = {k:v if not pickle.detect.baditems(v) else str(v) for k,v in localsdict.items()}
  _pk(filename, pkpack)


def _pk(filename, content):
  with open(f'{filename}.pk', 'wb') as f:
    pickle.dump(content, f, pickle.HIGHEST_PROTOCOL)

def pkbak(filename, locals_dict):
  if not os.path.exists(f'{filename}.pk'):
    locals_dict2 = {}
    for k,v in locals_dict.items():
      if isinstance(v, types.ModuleType):
        pass
      elif k == 'self' and type(v) == dict and '_session' in v.keys():
        class_ = v.__class__
        attrs_ = v.__dict__
        new_self = class_.__new__(class_)
        new_self.__dict__.update(attrs_)
        new_self.__dict__['_session'] = str(v.__dict__['_session'])
        locals_dict2.update({'self_': new_self})
      else:
        print(k)
        try:
          if k == 'arg_types' or k == 'generate_section' or k == 'note':
            raise ValueError # raise the correct error
          locals_dict2.update({copy.deepcopy(k): copy.deepcopy(v)})
        except:
          locals_dict2.update({copy.deepcopy(k): copy.deepcopy(str(v))})
    _pk(filename, locals_dict2)


def pk_(filename, locals_dict): #*
  if not os.path.exists(f'{filename}.pk'):
    locals_dict2 = {}
    for k,v in locals_dict.items():
      try:
        locals_dict2.update({copy.deepcopy(k): copy.deepcopy(v)})
      except:
        locals_dict2.update({copy.deepcopy(k): copy.deepcopy(str(v))})
    _pk(filename, locals_dict2)
# locsdict = {k:v for k,v in locals().items()}
# {'__name__': '__main__', '__doc__': None, '__package__': None,
#  '__loader__': <class '_frozen_importlib.BuiltinImporter'>,
# '__spec__': None, '__annotations__': {},
# '__builtins__': <module 'builtins' (built-in)>}
# len = 7
# o=[pickle.detect.badobjects(v) for k,v in locsdict.items()]
# i=[pickle.detect.baditems(v) for k,v in locsdict.items()]
# d={k:v if not pickle.detect.baditems(v) else str(v) for k,v in locsdict.items()}
# for k,v in locals_dict2.items():
#     print(k)
#     with open(f'{k}.pk', 'wb') as f:
#         pickle.dump(v, f)

def load_pk():
  locals_dict = {}
  pk_files = glob.glob('*.pk')
  for f in pk_files:
    with open(f, 'rb') as f_:
      tmp = pickle.load(f_)
    locals_dict.update({os.path.splitext(f)[0]: tmp})
  return locals_dict

#l = load_pk()
#pks = Namespace(**l)

# pks.cesed = pks.generator._model._config.encoder_decoder
# pks.oese = pks.cesed._control_encoder_decoder

def p(a):
  try:
    print(len(a))
  except:
    return
  return p(a[0])

#see refs.perf_one_hot_labels

def create_labels_for_excel(pks):
  #1: note on
  #2: note off
  #3: time shift
  #4: velocity

  #min/max: midi(0, 127), time shift(1, 100),
  #         velocity(1, pks.generator._model._config.num_velocity_bins))

  def ct(n):
    if n == 1:
      return 'note_on'
    elif n == 2:
      return 'note_off'
    elif n == 3:
      return 'time_shift'
    elif n == 4:
      return 'velocity'
    else:
      raise ValueError

  note_on = (1, 0, 127)
  note_off = (2, 0, 127)
  time_shift = (3, 1, 100)
  velocity = (4, 1, pks.generator._model._config.num_velocity_bins)

  event_ranges = [note_on, note_off, time_shift, velocity]

  labels = []
  for e_type, e_min, e_max in event_ranges:
    for step in range(e_min, e_max+1):
      labels.append(f'{ct(e_type)}: {step:03}')

  return labels

def tmp_label_dump(pks):

  labels = create_labels_for_excel(pks)
  labels = '\n'.join(labels)
  with open('tmp_label_dump.txt', 'w') as f:
    f.write(labels)

#https://stackoverflow.com/questions/947810/how-to-save-a-python-interactive-session
'''
IPython is extremely useful if you like using interactive sessions. For example for your use-case there is the %save magic command, you just input %save my_useful_session 10-20 23 to save input lines 10 to 20 and 23 to my_useful_session.py (to help with this, every line is prefixed by its number).
'''
# %save -a filename n1-n2 n3

# def save(filename,ns):
#   get_ipython().run_line_magic('save', f'-a {filename} {ns}')




  # Method 1

# make a copy of original df
def getbkmks(filename):
  import re
  with open(filename, 'r') as f:
    file = f.readlines()

  tmp = []
  for line in file:
    try:
      match = re.match(r'.*(#[\d]+[\d\sa-d->]+)', line).group(1)
      tmp.append(match)
    except:
      continue

  return tmp
