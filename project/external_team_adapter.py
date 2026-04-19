"""
Generic loader for external Pacman CTF team modules.

Usage with capture.py:
  python3 capture.py -r external_team_adapter.py \
    --redOpts "target=/abs/path/to/team.py,repo_root=/abs/path/to/repo"
"""

import hashlib
import importlib.util
import os
import sys

from compat_snake_case import install_aliases


def _load_external_module(target, repo_root=None, module_name=None):
  main_module = sys.modules.get('__main__')
  if main_module is not None and hasattr(main_module, 'GameState'):
    sys.modules['capture'] = main_module

  if repo_root is None or repo_root == '':
    repo_root = os.path.dirname(target)

  if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

  deps_root = '/tmp/pacman-ctf-deps'
  if os.path.isdir(deps_root) and deps_root not in sys.path:
    sys.path.insert(0, deps_root)

  if module_name is None or module_name == '':
    digest = hashlib.md5(target.encode('utf-8')).hexdigest()
    module_name = 'external_team_%s' % digest

  spec = importlib.util.spec_from_file_location(module_name, target)
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


def createTeam(firstIndex, secondIndex, isRed, **kwargs):
  target = kwargs.pop('target')
  repo_root = kwargs.pop('repo_root', '')
  create_fn = kwargs.pop('create_fn', 'auto')
  compat = kwargs.pop('compat', 'auto')
  module_name = kwargs.pop('module_name', '')

  if compat in ('auto', 'snake'):
    install_aliases()

  module = _load_external_module(target, repo_root=repo_root, module_name=module_name)

  if create_fn == 'auto':
    if hasattr(module, 'createTeam'):
      create_fn = 'createTeam'
    elif hasattr(module, 'create_team'):
      create_fn = 'create_team'
    else:
      raise AttributeError('No createTeam/create_team found in %s' % target)

  factory = getattr(module, create_fn)
  return factory(firstIndex, secondIndex, isRed, **kwargs)
