import sys
from copy import copy

import django
from django.template.context import BaseContext


def apply_python314_template_compatibility():
    if sys.version_info < (3, 14) or django.VERSION >= (5, 2):
        return

    def copy_context(self):
        duplicate = BaseContext()
        duplicate.__class__ = self.__class__
        duplicate.__dict__ = copy(self.__dict__)
        duplicate.dicts = self.dicts[:]
        return duplicate

    BaseContext.__copy__ = copy_context
