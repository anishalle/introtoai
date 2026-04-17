from compat_snake_case import install_aliases

install_aliases()

from captureAgents import CaptureAgent as _BaseCaptureAgent


class CaptureAgent(_BaseCaptureAgent):
  """
  Snake_case-compatible capture agent base class.
  """

  def register_initial_state(self, game_state):
    return _BaseCaptureAgent._original_registerInitialState(self, game_state)

  def registerInitialState(self, game_state):
    handler = getattr(type(self), 'register_initial_state', None)
    if handler is not None and handler is not CaptureAgent.register_initial_state:
      return handler(self, game_state)
    return _BaseCaptureAgent._original_registerInitialState(self, game_state)

  def chooseAction(self, game_state):
    handler = getattr(type(self), 'choose_action', None)
    if handler is not None:
      return handler(self, game_state)
    return _BaseCaptureAgent._original_chooseAction(self, game_state)
