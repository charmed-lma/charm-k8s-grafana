class FrameworkAdapter:
    '''
    Abstracts out the implementation details of the underlying framework
    so that our Charm object's code is decoupled from it and simplifies
    its own implementation. This is inspired by Alistair Cockburn's
    Hexagonal Architecture.
    '''

    def __init__(self, framework):
        self._framework = framework

    def get_app_name(self):
        return self._framework.model.app.name

    def get_config(self, key=None):
        if key:
            return self._framework.model.config[key]
        else:
            return self._framework.model.config

    def get_resources_repo(self):
        return self._framework.model.resources

    def observe(self, event, handler):
        self._framework.observe(event, handler)

    def set_pod_spec(self, spec_obj):
        self._framework.model.pod.set_spec(spec_obj)

    def set_unit_status(self, state_obj):
        self._framework.model.unit.status = state_obj
