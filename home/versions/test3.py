import hunter, sys
from colorama import AnsiToWin32
from colorama import Back
from colorama import Fore
from colorama import Style

filename = 'FILENAME'
lineno = 342
kind = 'call'
stack = [1,2,3]
function = 'FUNC'
co_argcount = 0
co_varnames = ('varname1', 'varname2')
a=sys._getframe()
print(a.f_code.co_varnames)
print(a.f_code.co_argcount)
thread_name = 'THREAD'
thread_align = 20
align = 10

event_colors = {
'reset': Style.RESET_ALL,
'normal': Style.NORMAL,
'filename': '',
'colon': Style.BRIGHT + Fore.BLACK,
'lineno': Style.RESET_ALL,
'kind': Fore.CYAN,
'continuation': Style.BRIGHT + Fore.BLUE,
'call': Style.BRIGHT + Fore.BLUE,
'return': Style.BRIGHT + Fore.GREEN,
'exception': Style.BRIGHT + Fore.RED,
'detail': Style.NORMAL,
'vars': Style.RESET_ALL + Fore.MAGENTA,
'vars-name': Style.BRIGHT,
'internal-failure': Style.BRIGHT + Back.RED + Fore.RED,
'internal-detail': Fore.WHITE,
'source-failure': Style.BRIGHT + Back.YELLOW + Fore.YELLOW,
'source-detail': Fore.WHITE,}
# cs = (
#   "{thread:{thread_align}}".format(
#     thread=thread_name,
#     thread_align=thread_align,
#   ) +
#   ("{filename}{sep:>{align}}{colon}:{lineno}{what2:<5} "
#   "{kind}{what3:9} {what4}{call}=>{normal} "
#   "{what5}({what6}{call}{normal}){reset}".format(
#     "WHAT7",
#     "WHAT8",
#     '   ' * (len(stack) - 1),
#     function,
#     ', '.join('{vars}{vars-name}{0}{vars}={reset}{1}'.format(
#       var,
#       self._safe_repr(event.locals.get(var, MISSING)),
#       event_colors
#     ) for var in co_varnames[:co_argcount]),
#     align=align,
#     colon = event_colors['colon'],
#     kind = event_colors['kind'],
#     call = event_colors['call'],
#     normal = event_colors['normal'],
#     reset = event_colors['reset'],
#     filename='FILENAME',
#     lineno=97476,
#     sep='WHAT1',
#     what2='WHAT2',
#     what3 = 'WHAT3',
#     what4='WHAT4',
#     what5='WHAT5',
#     what6='WHAT6',
#   ))
cs = (
  "{thread:{thread_align}}".format(
    thread=thread_name,
    thread_align=thread_align,
  ) +
  "{what1}{filename:>{align}}{colon}:{lineno}{what2:<5} ".format(
    what1='WHAT1',
    filename='FILENAME',
    align=align,
    colon=event_colors['colon'],
    lineno=97476,
    what2='   ' * (len(stack) - 1),
  ) +
   "{kind}{what3:9} {what4}{call}=>{normal} ".format(
     kind=event_colors['kind'],
     what3=kind,
     what4='WHAT4',
     call=event_colors['call'],
     normal=event_colors['normal'],
   ) +
  "{what5}({what6}{call}{normal}){reset}".format(
    what5=function,
    what6=', '.join('{vars}{vars_name}{k}{vars}={reset}{v}'.format(
      k=var,
      v=locals().get(var),
      vars=event_colors['vars'],
      vars_name=event_colors['vars-name'],
      reset=event_colors['reset'],
    ) for var in co_varnames[:2]),
    call=event_colors['call'],
    normal=event_colors['normal'],
    reset=event_colors['reset'],
  )
)

print(cs)

b=(', '.join('{vars}{vars_name}{k}{vars}={reset}{v}'.format(
      k=var,
      v=locals().get(var),
      vars=event_colors['vars'],
      vars_name=event_colors['vars-name'],
      reset=event_colors['reset'],
    ) for var in co_varnames[:2]))

print(2)
print(b)
print(1)
print(b.__repr__())

stream_write(
  "{thread:{thread_align}}".format(
    thread=thread_name,
    thread_align=thread_align,
  ) +
  "{what1}{filename:>{align}}{colon}:{lineno}{what2:<5} ".format(
    what1='WHAT1',
    filename=filename,
    align=self.filename_alignment,
    colon=self.event_colors['colon'],
    lineno=event.lineno,
    what2='WHAT2',
  ) +
  "{kind}{what3:9} {what4}{call}=>{normal} ".format(
    kind=self.event_colors['kind'],
    what3=event.kind,
    what4='WHAT4',
    call=self.event_colors['call'],
    normal=self.event_colors['normal'],
  ) +
  "{what5}({what6}{call}{normal}){reset}".format(
    what5=function,
    what6=', '.join('{vars}{vars_name}{k}{vars}={reset}{v}'.format(
      k=var,
      v=self._safe_repr(event.locals.get(var, MISSING)),
      vars=self.event_colors['vars'],
      vars_name=self.event_colors['vars-name'],
      reset=self.event_colors['reset'],
    ) for var in code.co_varnames[:code.co_argcount]),
    call=self.event_colors['call'],
    normal=self.event_colors['normal'],
    reset=self.event_colors['reset'],
  )
)

stream_write(
  "{thread:{thread_align}}".format(
    thread=thread_name,
    thread_align=thread_align,
  ) +
  "{what1}{filename:>{align}}{colon}:{lineno}{what2:<5} ".format(
    what1='WHAT1',
    filename=filename,
    align=self.filename_alignment,
    colon=self.event_colors['colon'],
    lineno=event.lineno,
    what2='WHAT2',
  ) +
  "{kind}{what3:9} {return}{what4}=>{normal} ".format(
    kind=self.event_colors['kind'],
    what3=event.kind,
    what4='   ' * (len(stack) - 1),
    call=self.event_colors['call'],
    normal=self.event_colors['normal'],
  ) +
  "{what5}: {reset}{what6}".format(
    what5=event.function,
    what6=self._safe_repr(event.arg),
    call=self.event_colors['call'],
    normal=self.event_colors['normal'],
    reset=self.event_colors['reset'],
  )
)
if stack and stack[-1] == ident:
  stack.pop()
else:  # line
  stream_write(
    "{thread:{thread_align}}".format(
      thread=thread_name,
      thread_align=thread_align,
    ) +
    "{filename}{what1:>{align}}{colon}:".format(
      filename=filename,
      what1='',
      align=self.filename_alignment,
      colon=self.event_colors['colon'],
    ) +
    "{lineno}{what2:<5} {kind}{what3:9} ".format(
      lineno='WHAT2',
      what2=event.lineno,
      kind='WHAT3',
      what3=event.kind,
    ) +
    "{reset}{what4}{what5}".format(
      reset=self.event_colors['reset'],
      what4='   ' * len(stack),
      what5=event.source.strip(),
      code=self.code_colors[event.kind],
    ))


"{thread:{thread_align}}{filename}{:>{align}}{colon}:{lineno}{:<5} {kind}{:9} {}{call}=>{normal} {}({}{call}{normal}){reset}\n"
"{thread:{thread_align}}{filename}{:>{align}}{colon}:{lineno}{:<5} {kind}{:9} {exception}{} !{normal} {}: {reset}{}\n"
"{thread:{thread_align}}{filename}{:>{align}}{colon}:{lineno}{:<5} {kind}{:9} {return}{}<={normal} {}: {reset}{}\n"
"{thread:{thread_align}}{filename}{:>{align}}{colon}:{lineno}{:<5} {kind}{:9} {reset}{}{}\n"
