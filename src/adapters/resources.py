from ops.framework import Object
from ops.model import (
    BlockedStatus,
    ModelError,
)
import yaml


# MODELS

class ImageMeta(Object):

    def __init__(self, resource_dict):
        self.resource_dict = resource_dict

    @property
    def image_path(self):
        return self.resource_dict['registrypath']

    @property
    def repo_username(self):
        return self.resource_dict['username']

    @property
    def repo_password(self):
        return self.resource_dict['password']


class ResourceError(ModelError):

    def __init__(self, resource_name, message):
        super().__init__(resource_name)
        self.status = BlockedStatus(f'{resource_name}: {message}')


# SERVICES

def get_image_meta(image_name, image_meta_path):
    if not image_meta_path.exists():
        raise ResourceError(image_name,
                            f'Resource not found at {str(image_meta_path)})')

    resource_yaml = image_meta_path.read_text()

    if not resource_yaml:
        raise ResourceError(image_name,
                            f'Resource unreadable at {str(image_meta_path)})')

    try:
        resource_dict = yaml.safe_load(resource_yaml)
    except yaml.error.YAMLError:
        raise ResourceError(image_name,
                            f'Invalid YAML at {str(image_meta_path)})')
    else:
        return ImageMeta(resource_dict=resource_dict)
