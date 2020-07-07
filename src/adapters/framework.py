# Adapted from: https://github.com/johnsca/resource-oci-image/tree/e58342913
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

def fetch_image_meta(image_name, resources_repo):
    path = resources_repo.fetch(image_name)
    if not path.exists():
        raise ResourceError(image_name, f'Resource not found at {str(path)})')

    resource_yaml = path.read_text()

    if not resource_yaml:
        raise ResourceError(image_name, f'Resource unreadable at {str(path)})')

    try:
        resource_dict = yaml.safe_load(resource_yaml)
    except yaml.error.YAMLError:
        raise ResourceError(image_name, f'Invalid YAML at {str(path)})')
    else:
        return ImageMeta(resource_dict=resource_dict)
