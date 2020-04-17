"""
Use "ipython test_project.py" command to run these tests.

Although py.test should also work fine, the main project has to be ran in ipython
enviroment, without which many functions will complain. Importing things could
solve this problem, but I decided to implement this using ipytest since it is
also something from IPython.
"""
import ipytest

from nbsafety.safety import *

ipytest.config(rewrite_asserts=True, magics=True)
# TODO (smacke): use a proper filter instead of using levels to filter out safety code logging
logging.basicConfig(level=logging.ERROR)


# Rewrite the warning from magic cell so that we know it prompts a warning.
# DETECTED should be set to false again after each time use.
original_warning = dependency_safety.warning
DETECTED = False


def better_warning(name, mucn, mark):
    global DETECTED
    DETECTED = True
    original_warning(name, mucn, mark)


def assert_detected(msg=''):
    global DETECTED
    assert DETECTED, str(msg)
    DETECTED = False


def assert_not_detected(msg=''):
    assert not DETECTED, str(msg)


# Make sure to seperate each test as a new test to prevent unexpected stale dependency
def new_test():
    dependency_safety_init()
    dependency_safety.warning = better_warning


def run_cell(code):
    get_ipython().run_cell_magic(dependency_safety.__name__, None, code)


def test_subscript_dependency():
    new_test()
    run_cell('lst = [0, 1, 2]')
    run_cell('x = 5')
    run_cell('y = x + lst[0]')
    run_cell('lst[0] = 10')
    run_cell('logging.info(y)')
    assert_detected("Did not detect that lst changed underneath y")


#simple test about the basic assignment
def test_basic_assignment():
    new_test()
    run_cell('a = 1')
    run_cell('b = 2')
    run_cell('c = a+b')
    run_cell('d = c+1')
    run_cell('logging.info(a,b,c,d)')
    #redefine a here but not c and d
    run_cell('a = 7')
    run_cell('logging.info(a,b,c,d)')
    assert_detected("Did not detect that c's reference was changed")

    run_cell('c = a+b')
    run_cell('logging.info(a,b,c,d)')
    assert_detected("Did not detect that d's reference was changed")

    run_cell('d = c+1')
    run_cell('logging.info(a,b,c,d)')
    assert_not_detected("There should be no more dependency issue")


# Foo, bar example from the project prompt
def test_foo_bar_example():
    new_test()
    run_cell("""
def foo():
    return 5

def bar():
    return 7
""")
    run_cell("""
funcs_to_run = [foo,bar]
""")
    run_cell("""
accum = 0
for f in funcs_to_run:
    accum += f()
logging.info(accum)
""")
    
    # redefine foo here but not funcs_to_run
    run_cell("""
def foo():
    return 10

def bar():
    return 7
""")
    run_cell("""
accum = 0
for f in funcs_to_run:
    accum += f()
logging.info(accum)
""")
    assert_detected("Did not detect that funcs_to_run's reference was changed")

    run_cell("""
funcs_to_run = [foo,bar]
""")
    run_cell("""
accum = 0
for f in funcs_to_run:
    accum += f()
logging.info(accum)
""")
    assert_not_detected("There should be no more dependency issue")


# Tests about variables that have same name but in different scope.
# There shouldn't be any extra dependency because of the name.
def test_variable_scope():
    new_test()
    run_cell("""
def func():
    x = 6
""")
    run_cell('x = 7')
    run_cell('y = x')
    run_cell('z = func')
    run_cell('logging.info(y,z())')

    # change x inside of the function, but not x outside of the function
    run_cell('def func():\n    x = 10')
    run_cell('logging.info(y,z())')
    assert_detected("Did not detect the dependency change in the function")

    run_cell('y = x')
    run_cell('logging.info(y,z())')
    assert_detected("Updating y should not solve the dependency change inside of function func")

    run_cell('z = func')
    run_cell('logging.info(y,z())')
    assert_not_detected("Updating z should solve the problem")


def test_variable_scope2():
    new_test()
    run_cell('def func():\n    x = 6')
    run_cell('x = 7')
    run_cell('y = x')
    run_cell('z = func')
    run_cell('logging.info(y,z())')

    # change x outside of the function, but not inside of the function
    run_cell('x = 10')
    run_cell('logging.info(y,z())')
    assert_detected("Did not detect the dependency change outside of the function")

    run_cell('z = func')
    run_cell('logging.info(y,z())')
    assert_detected("Updating z should not solve the dependency change outside of function")

    run_cell('y = x')
    run_cell('logging.info(y,z())')
    assert_not_detected("Updating y should solve the problem")


def test_default_args():
    new_test()
    run_cell("""
x = 7
def foo(y=x):
    return y + 5
""")
    run_cell('a = foo()')
    assert_not_detected()
    run_cell('x = 10')
    assert_not_detected()
    run_cell('b = foo()')
    assert_detected("Should have detected stale dependency of fn foo() on x")


def test_same_pointer():
    new_test()
    # a and b are actually pointing to the same thing
    run_cell('a = [7]')
    run_cell('b = a')
    run_cell('c = b + [5]')

    run_cell('a[0] = 8')
    run_cell('logging.info(b)')
    assert_not_detected("b is an alias of a, updating a should automatically update b as well")
    run_cell('logging.info(c)')
    assert_detected("c does not point to the same thing as a or b, thus there is a stale dependency here ")


def test_func_assign():
    new_test()
    run_cell("""
a = 1
b = 1
c = 2
d = 3
def func(x, y = a):
    logging.info(b)
    e = c+d
    f = x + y
    return f
""")
    run_cell("""
z = func(c)""")
    run_cell("""
a = 4""")
    run_cell("""
logging.info(z)""")
    assert_detected("Should have detected stale dependency of fn func on a")
    run_cell("""
def func(x, y = a):
    logging.info(b)
    e = c+d
    f = x + y
    return f
z = func(c)
""")
    run_cell("""
logging.info(z)""")
    assert_not_detected()
    run_cell("""
c = 3""")
    run_cell("""
logging.info(z)""")
    assert_detected("Should have detected stale dependency of z on c")
    run_cell("""
z = func(c)""")
    run_cell("""
logging.info(z)""")
    assert_not_detected()
    run_cell("""
b = 4""")
    run_cell("""
d = 1""")
    assert_not_detected("Changing b and d should not affect z")


def test_func_assign_helper_func():
    new_test()
    run_cell("""
x = 3
a = 4
def f():
    def g():
        logging.info(a)
        return x
    return g()
y = f()
""")
    run_cell("""
x = 4""")
    run_cell("""
logging.info(y)""")
    assert_detected("Should have detected stale dependency of y on x")
    run_cell("""
y = f()""")
    run_cell("""
logging.info(y)""")
    assert_not_detected()
    run_cell("""
a = 1""")
    run_cell("""
logging.info(y)""")
    assert_not_detected("Changing a should not affect y")


def test_func_assign_helper_func2():
    new_test()
    run_cell("""
x = 3
a = 4
def f():
    def g():
        logging.info(a)
        return x
    return g
y = f()()
""")
    run_cell("""
x = 4""")
    run_cell("""
logging.info(y)""")
    assert_detected("Should have detected stale dependency of y on x")


# Run all above tests using ipytest
ipytest.run_tests()
