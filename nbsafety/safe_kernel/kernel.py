# -*- coding: utf-8 -*-
from ipykernel.ipkernel import IPythonKernel
import nbsafety.safety
from nbsafety.version import __version__


class SafeKernel(IPythonKernel):
    implementation = 'safe_kernel'
    implementation_version = __version__

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.shell.run_cell('from {} import {}'.format(
            nbsafety.safety.__name__, nbsafety.safety.dependency_safety.__name__)
        )
        self.shell.run_cell('{}()'.format(nbsafety.safety.dependency_safety_init.__name__))

    def do_execute(self, code, silent, store_history=True,
                   user_expressions=None, allow_stdin=False):
        code = "%%{}\n".format(nbsafety.dependency_safety.__name__) + code
        return super().do_execute(code, silent, store_history, user_expressions, allow_stdin)
