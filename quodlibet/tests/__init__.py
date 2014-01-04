# -*- coding: utf-8 -*-
import fnmatch
from math import log
import os
import sys
import unittest
import tempfile
import shutil
from quodlibet.util.dprint import Colorise, print_

from unittest import TestCase as OrigTestCase
suites = []


class TestCase(OrigTestCase):

    # silence deprec warnings about useless renames
    failUnless = OrigTestCase.assertTrue
    failIf = OrigTestCase.assertFalse
    failUnlessEqual = OrigTestCase.assertEqual
    failUnlessRaises = OrigTestCase.assertRaises
    failUnlessAlmostEqual = OrigTestCase.assertAlmostEqual
    failIfEqual = OrigTestCase.assertNotEqual
    failIfAlmostEqual = OrigTestCase.assertNotAlmostEqual


DATA_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")
_TEMP_DIR = None


def _wrap_tempfile(func):
    def wrap(*args, **kwargs):
        if kwargs.get("dir") is None:
            kwargs["dir"] = _TEMP_DIR
        return func(*args, **kwargs)
    return wrap


NamedTemporaryFile = _wrap_tempfile(tempfile.NamedTemporaryFile)
mkdtemp = _wrap_tempfile(tempfile.mkdtemp)
mkstemp = _wrap_tempfile(tempfile.mkstemp)


def add(t):
    assert issubclass(t, TestCase)
    suites.append(t)


class Result(unittest.TestResult):
    TOTAL_WIDTH = 80
    TEST_RESULTS_WIDTH = 50
    TEST_NAME_WIDTH = TOTAL_WIDTH - TEST_RESULTS_WIDTH - 3
    MAJOR_SEPARATOR = '=' * TOTAL_WIDTH
    MINOR_SEPARATOR = '-' * TOTAL_WIDTH

    CHAR_SUCCESS, CHAR_ERROR, CHAR_FAILURE = '+', 'E', 'F'

    def __init__(self, test_name, num_tests, out=sys.stdout):
        super(Result, self).__init__()
        self.out = out
        if hasattr(out, "flush"):
            out.flush()
        pref = '%s (%d): ' % (Colorise.bold(test_name), num_tests)
        line = pref + " " * (self.TEST_NAME_WIDTH - len(test_name)
                             - 6 - int(num_tests and log(num_tests, 10) or 0))
        print_(line, end="")

    def addSuccess(self, test):
        unittest.TestResult.addSuccess(self, test)
        print_(Colorise.green(self.CHAR_SUCCESS), end="")

    def addError(self, test, err):
        unittest.TestResult.addError(self, test, err)
        print_(Colorise.red(self.CHAR_ERROR), end="")

    def addFailure(self, test, err):
        unittest.TestResult.addFailure(self, test, err)
        print_(Colorise.red(self.CHAR_FAILURE), end="")

    def printErrors(self):
        succ = self.testsRun - (len(self.errors) + len(self.failures))
        v = Colorise.bold("%3d" % succ)
        cv = Colorise.green(v) if succ == self.testsRun else Colorise.red(v)
        count = self.TEST_RESULTS_WIDTH - self.testsRun
        print_((" " * count) + cv)
        self.printErrorList('ERROR', self.errors)
        self.printErrorList('FAIL', self.failures)

    def printErrorList(self, flavour, errors):
        for test, err in errors:
            print_(self.MAJOR_SEPARATOR)
            print_(self.red("%s: %s" % (flavour, str(test))))
            print_(self.MINOR_SEPARATOR)
            print_("%s" % err)


class Runner(object):

    def run(self, test):
        suite = unittest.makeSuite(test)
        result = Result(test.__name__, len(suite._tests))
        suite(result)
        result.printErrors()
        return len(result.failures), len(result.errors)


def unit(run=[], filter_func=None, main=False, subdirs=None, strict=False,
         stop_first=False):

    global _TEMP_DIR

    path = os.path.dirname(__file__)
    if subdirs is None:
        subdirs = []

    import quodlibet
    quodlibet._dbus_init()
    quodlibet._gtk_init()
    quodlibet._python_init()

    # make glib warnings fatal
    if strict:
        from gi.repository import GLib
        GLib.log_set_always_fatal(
            GLib.LogLevelFlags.LEVEL_CRITICAL |
            GLib.LogLevelFlags.LEVEL_ERROR |
            GLib.LogLevelFlags.LEVEL_WARNING)

    if main:
        for name in os.listdir(path):
            if fnmatch.fnmatch(name, "test_*.py"):
                __import__(".".join([__name__, name[:-3]]), {}, {}, [])

    for subdir in subdirs:
        sub_path = os.path.join(path, subdir)
        for name in os.listdir(sub_path):
            if fnmatch.fnmatch(name, "test_*.py"):
                __import__(".".join([__name__, subdir, name[:-3]]), {}, {}, [])

    # create a user dir in /tmp
    _TEMP_DIR = tempfile.mkdtemp(prefix="QL-TEST-")
    user_dir = tempfile.mkdtemp(prefix="QL-USER-", dir=_TEMP_DIR)
    os.environ['QUODLIBET_USERDIR'] = user_dir
    import quodlibet.const
    reload(quodlibet.const)

    import quodlibet.config

    # emulate python2.7 behavior
    def setup_test(test):
        if hasattr(TestCase, "setUpClass"):
            return
        if hasattr(test, "setUpClass"):
            test.setUpClass()

    def teardown_test(test):
        if hasattr(TestCase, "setUpClass"):
            return
        if hasattr(test, "tearDownClass"):
            test.tearDownClass()

    runner = Runner()
    failures = errors = 0
    use_suites = filter(filter_func, suites)
    for test in sorted(use_suites, key=repr):
        if (not run
                or test.__name__ in run
                or test.__module__[11:] in run):
            setup_test(test)
            df, de = runner.run(test)
            if stop_first and (df or de):
                break
            failures += df
            errors += de
            teardown_test(test)
            quodlibet.config.quit()

    try:
        shutil.rmtree(_TEMP_DIR)
    except EnvironmentError:
        pass

    return failures, errors
