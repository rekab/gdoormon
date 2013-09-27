import fysom

class StateMachine():
  """States:
  - ok                  - all good
  - nobody_home         - door closed, nobody home
  - door_open           - door open, someone home
  - alerting            - door open, nobody home or open too long
  - door_closing        - close door command sent
  - door_stuck (TODO)
  """

  def __init__(self, broadcaster): 
    self.broadcaster = broadcaster
    self.state = fysom.Fysom({
        'initial': 'ok',
        'events': [
          dict(name='everyone_left', src=['ok', 'nobody_home'], dst='nobody_home'),
          dict(name='everyone_left', src=['door_open', 'alerting'], dst='alerting'),
          dict(name='everyone_left', src='door_closing', dst='door_closing'),

          dict(name='someone_home', src=['ok', 'nobody_home', 'door_closing'], dst='ok'),
          dict(name='someone_home', src='alerting', dst='alerting'),
          dict(name='someone_home', src=['door_open'], dst='door_open'),

          dict(name='door_opened', src=['ok', 'door_open'], dst='door_open'),
          dict(name='door_opened', src=['nobody_home', 'alerting'], dst='alerting'),
          dict(name='door_opened', src='door_closing', dst='door_closing'),

          dict(name='timeout', src=['door_open', 'nobody_home'], dst='alerting'),
          dict(name='timeout', src='alerting', dst='door_closing'),
          #dict(name='timeout', src='door_closing', dst='door_stuck'),

          dict(name='close_door_cmd', src=['alerting', 'door_open', 'door_closing'], dst='door_closing'),
          dict(name='close_door_cmd', src=['ok', 'nobody_home'], dst='ok'),

          dict(name='door_closed', src=['ok', 'nobody_home', 'alerting', 'door_open', 'door_closing'], dst='ok'),
        ],
        'callbacks': {
          'onchangestate': self.logStateChange,
          'onleave_state_alerting': self.abortNoOpStateTransition,
          'onleave_state_door_closing': self.abortNoOpStateTransition,
          'ondoor_open': self.startDoorOpenTimer,
          'onalerting': self.setAlertCondition,
          'ondoor_closing': self.closeDoor,
        }})

  def can(self, event_name):
    return self.state.can(event_name)

  def __getattr__(self, attr):
    if self.can(attr):
      return getattr(self.state, attr)
    raise AttributeError('Unknown attribute "%s"' % attr)
