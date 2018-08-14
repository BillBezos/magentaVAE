def bar():
  pass  # cause we get a Pdb session here


def func():
  mumbo = 1
  mumbo = "jumbo"
  print("not shown in trace")
  print(mumbo)
  mumbo = 2
  print(mumbo)  # not shown in trace
  bar()