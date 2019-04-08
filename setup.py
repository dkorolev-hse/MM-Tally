# -*- coding: utf-8 -*-
from cx_Freeze import setup, Executable
import sys

buildOptions = dict(packages = ['requests','soupsieve'], includes = ['idna.idnadata','pkgutil'], path= sys.path)
executables = [
Executable('TALLY.py'),
]

setup(name='TALLY.py',
version = '1.0',
description = 'Tally module for ONVIF cameras',
options = dict(build_exe = buildOptions),
executables = executables)
