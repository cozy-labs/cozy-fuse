import logging
import requests

import local_config

logger = logging.getLogger(__name__)
local_config.configure_logger(logger)


class DeviceAlreadyRegistered(Exception):
    pass


class WrongPassword(Exception):
    pass


class UnreachableCozy(Exception):
    pass


def register_device(name, url, path, password):
    '''
    Register device to remote Cozy, located at *url*.
    Once device is registered device id and password are stored in a local
    configuration file.
    '''
    data = {'login': name, 'folder': path}
    response = requests.post(
        '%s/device/' % url,
        data=data,
        auth=('owner', password),
        verify=False
    )

    if response.status_code == 502:
        msg = '[Remote config] Registering device failed for ' \
              '%s (your Cozy is unreachable).' % name
        logger.error(msg)
        raise UnreachableCozy(msg)

    data = response.json()
    if ('error' in data):
        msg = '[Remote config] Registering device failed for ' \
              '%s (%s).' % (name, data['error'])
        logger.error(msg)

        if 'name' in msg:
            raise DeviceAlreadyRegistered(msg)
        else:
            raise WrongPassword(msg)

        return (None, None)
    else:
        device_id = str(data["id"])
        device_password = str(data["password"])
        logger.info(
            '[Remote config] Registering device succeeded for %s.' % name)
        return (device_id, device_password)


def remove_device(url, device_id, password):
    '''
    Remove device from its Cozy.
    '''
    response = requests.delete('%s/device/%s/' % (url, device_id),
                               auth=('owner', password), verify=False)

    logger.info('[Remote config] Device deletion succeeded for %s.' % url)
    return response
