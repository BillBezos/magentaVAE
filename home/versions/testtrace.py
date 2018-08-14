import hunter as h
from mypy_extensions import TypedDict
from enum import Enum
import os
from types import CodeType, FrameType


class Tracer():
  """
  Attributes:
    ddl (:obj:`list` of :obj:`str`): desc
    pl (:obj:`list` of :obj:`str`): predicates list
    al (:obj:`list` of :obj:`str`): actions list
  """

  def __init__(self, datadictlist):
    """
    Args:
      datadictlist (:obj:`list` of :obj:`str`): desc
    """
    # *predicates
    self.ddl = datadictlist
    self.pl = [h.When, h.And, h.Or, h.Not]
    self.al = [h.CallPrinter, h.CodePrinter, h.Debugger, h.VarsPrinter]
    # **query


  def add_trace(self, td):

    return 1

  def help(self):
    pass

#
# h.trace(
#     # drop into a Pdb session if ``foo.bar()`` is called
#     h.Q(module="foo", function="bar", kind="call", action=h.Debugger(klass=h.Pdb))
#     |  # or
#     h.Q(
#         # show code that contains "mumbo.jumbo" on the current line
#         lambda event: event.locals.get("mumbo") == "jumbo",
#         # and it's not in Python's stdlib
#         stdlib=False,
#         # and it contains "mumbo" on the current line
#         source__contains="mumbo"
#     )
# )
#
#
#
# h.trace(
#     # drop into a Pdb session if ``foo.bar()`` is called
#     h.Q(module="foo", function="bar", kind="call", action=h.Debugger(klass=h.Pdb))
#     |  # or
#     h.Q(
#         # show code that contains "mumbo.jumbo" on the current line
#         lambda event: event.locals.get("mumbo") == "jumbo",
#         # and it's not in Python's stdlib
#         stdlib=False,
#         # and it contains "mumbo" on the current line
#         source__contains="mumbo"
#     )
# )
#



# events dict, these are args for hunter.Query
class hEvents(TypedDict):
  calls       : int
  code        : CodeType
  depth       : int
  filename    : str
  frame       : FrameType
  fullsource  : str
  function    : str
  globals     : dict
  kind        : str
  lineno      : int
  locals      : dict
  module      : str
  source      : str
  stdlib      : bool
  threadid    : int
  threadname  : str

class NoValue(Enum):
  def __repr__(self):
    return '<%s.%s>' % (self.__class__.__name__, self.name)

class enKind(Enum):
  CALL = 'call'
  LINE = 'line'
  RETURN = 'return'
  EXCEPTION = 'exception'
  OPCODE = 'opcode'

# class enKind(NoValue):
#   CALL = 'call'
#   LINE = 'line'
#   RETURN = 'return'
#   EXCEPTION = 'exception'
#   OPCODE = 'opcode'

# class enKind(NoValue):
#   CALL = 'A function is called (or some other code block entered). ' \
#          'The global trace function is called; ' \
#          'arg is None; ' \
#          'the return value specifies the local trace function.'
#   LINE = 'The interpreter is about to execute a new line of code or re-execute the condition of a loop. ' \
#          'The local trace function is called; arg is None; ' \
#          'the return value specifies the new local trace function. ' \
#          'See Objects/lnotab_notes.txt for a detailed explanation of how this works. ' \
#          'Per-line events may be disabled for a frame by setting f_trace_lines to False on that frame.'
#   RETURN = 'A function (or other code block) is about to return. ' \
#            'The local trace function is called; ' \
#            'arg is the value that will be returned, or None if the event is caused by an exception being raised. ' \
#            'The trace function’s return value is ignored.'
#   EXCEPTION = 'An exception has occurred. The local trace function is called; ' \
#               'arg is a tuple (exception, value, traceback); ' \
#               'the return value specifies the new local trace function.'
#   OPCODE = 'The interpreter is about to execute a new opcode (see dis for opcode details). ' \
#            'The local trace function is called; arg is None; ' \
#            'the return value specifies the new local trace function. ' \
#            'Per-opcode events are not emitted by default: ' \
#            'they must be explicitly requested by setting f_trace_opcodes to True on the frame.'



#  query
h.Query()

# query args
def getQargs():
  qArgs = {}
  calls: int
  code: CodeType
  depth: int
  filename: str
  frame: FrameType
  fullsource: str
  function: str
  globals: dict
  kind: str
  lineno: int
  locals: dict
  module: str
  source: str
  stdlib: bool
  threadid: int
  threadname: str

  return qArgs

# query args operators
ops = ['startswith', 'endswith', 'in', 'contains', 'has',
       'regex', 'rx' 'lt', 'lte', 'gt', 'gte']

"""
  Walkthrough

  Sometimes you just want to get an overview of an unfamiliar application code,
   eg: only see calls/returns/exceptions.
  
  In this situation, you could use something like 
    ~Q(kind="line"),~Q(module_in=["six","pkg_resources"]),
    ~Q(filename=""),stdlib=False. 
    
  Lets break that down:
  
    ~Q(kind="line") means skip line events (~ is a negation of the filter).
    stdlib=False means we don’t want to see anything from stdlib.
    ~Q(module_in=["six","pkg_resources")] 
      means we’re tired of seeing stuff from those modules in site-packages.
    ~Q(filename="") is necessary for filtering out events that 
      come from code without a source (like the interpreter bootstrap stuff).
"""
