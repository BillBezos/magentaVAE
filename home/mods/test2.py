from colorama import AnsiToWin32
from colorama import Back
from colorama import Fore
from colorama import Style

# EVENT_COLORS = {
#   'reset': Style.RESET_ALL,
#   'normal': Style.NORMAL,
#   'filename': '',
#   'colon': Style.BRIGHT + Fore.BLACK,
#   'lineno': Style.RESET_ALL,
#   'kind': Fore.CYAN,
#   'continuation': Style.BRIGHT + Fore.BLUE,
#   'call': Style.BRIGHT + Fore.BLUE,
#   'return': Style.BRIGHT + Fore.GREEN,
#   'exception': Style.BRIGHT + Fore.RED,
#   'detail': Style.NORMAL,
#   'vars': Style.RESET_ALL + Fore.MAGENTA,
#   'vars-name': Style.BRIGHT,
#   'internal-failure': Style.BRIGHT + Back.RED + Fore.RED,
#   'internal-detail': Fore.WHITE,
#   'source-failure': Style.BRIGHT + Back.YELLOW + Fore.YELLOW,
#   'source-detail': Fore.WHITE,
# }
#
# asdf1 = \
#   "{thread:{thread_align}}{:>{align}}     _a{vars}_b{:9}_c _d{vars_name}_e{" \
#   "code}_f _g{vars}_h=> _i{reset}_j{printout}_k{reset}_l\n".format(
#     'asdf',
#     'qwer',
#     code='locals()',
#     printout='str(locals())',
#     thread='MainThread',
#     thread_align=12,
#     align=40,
#     vars='\x1b[0m\x1b[35m',
#     vars_name='\x1b[1m',
#     reset='\x1b[0m',
#   )
#
# asdf2 = \
#   "{thread:{thread_align}}{:>{align}}     _a{vars}_b{:9}_c _d{vars_name}_e{" \
#   "code}_f _g{vars}_h=> _i{reset}_j{printout}_k{reset}_l\n".format(
#     '?',
#     'vars',
#     code='locals()',
#     printout='str(locals())',
#     thread='MainThread',
#     thread_align=12,
#     align=40,
#     vars='\x1b[0m\x1b[35m',
#     vars_name='\x1b[1m',
#     reset='\x1b[0m',
#   )
#
# asdf3 = \
#   "{thread:{thread_align}}{:>{align}}     _a{vars}_b{:9}_c _d{vars_name}_e{" \
#   "code}_f _g{vars}_h=> _i{reset}_j{printout}_k{reset}_l\n".format(
#     '?',
#     '...',
#     code='locals()',
#     printout=str(locals()),
#     thread='MainThread',
#     thread_align=12,
#     align=40,
#     vars='\x1b[0m\x1b[35m',
#     vars_name='\x1b[1m',
#     reset='\x1b[0m',
#   )
#
# asdf3a = \
#   "{thread:{thread_align}}{:>{align}}     {vars}{:9} {vars_name}{" \
#   "code} {vars}=> {reset}{printout}{reset}_l\n".format(
#     '?',
#     '...',
#     code='locals()',
#     printout=str(locals()),
#     thread='MainThread',
#     thread_align=12,
#     align=40,
#     vars='\x1b[0m\x1b[35m',
#     vars_name='\x1b[1m',
#     reset='\x1b[0m',
#   )
#
# asdf4 = \
#   "{thread:{thread_align}}{:>{align}}     _a{vars}_b{:9}_c _d{vars-name}_e{" \
#   "code}_f _g{vars}_h=> _i{reset}_j{printout}_k{reset}_l\n".format(
#     '?',
#     '...',
#     code='locals()',
#     printout='str(locals())',
#     thread='MainThread',
#     thread_align=12,
#     align=40,
#     **EVENT_COLORS,
#   )
#
# print(asdf1)
# print(asdf2)
# print(asdf3)
# print(asdf3a)
# print(asdf4)
#
# with open('asdf.log', 'w') as f:
#   f.write(asdf3)
#   f.write(asdf3a)


asdf3 = (
  "{thread:{thread_align}}{sep:>{align}}     {vars}{what:9} {vars_name}{code} "
  "{vars}=> {reset}{printout}{reset}\n".format(
    sep='|',
    what='vars', #if first else '...',
    code='locals()',
    printout='str(locals())',
    thread='MainThread',
    thread_align=12,
    align=40,
    vars='\x1b[0m\x1b[35m',
    vars_name='\x1b[1m',
    reset='\x1b[0m',
  ))

print(1)
print(asdf3)
print(2)
repr(asdf3)
print(3)
with open('asdf3.log', 'w') as f:
  f.write(asdf3)

# with open('asdf3b.log', 'wb') as f:
#   f.write(asdf3)

with open('asdf3.log', 'r') as f:
  r1 = f.read()

# with open('asdf3b.log', 'rb') as f:
#   r2 = f

print(r1)
print(4)
print(r1.__repr__())
# print(r2)

with open('asdf3.log', 'w') as f:
  f.write(asdf3.__repr__())

from colorama import init
init(wrap=False)

from colorama import Fore, Back, Style

print(Fore.RED + 'some red text')
print(Back.GREEN + 'and with a green background')
print(Style.DIM + 'and in dim text')
print(Fore.RESET + Back.RESET + Style.RESET_ALL)
print('back to normal now')

print('/033[31m' + 'some red text')
print('/033[30m')  # and reset to default color

print(Fore.RED)
print(str(Fore.RED))
print(repr(Fore.RED))
www= 'asdf'
print('qwer')
print(www)
print(Fore.RESET)
print(www)
import logging
l=logging.getLogger('jkl')
l.warning('asdf')