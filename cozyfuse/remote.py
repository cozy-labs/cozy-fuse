import requests
import json


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

    if response.status_code == 403:
        print 'Registering device failed for %s (wrong password).' % name
        return (None, None)
    else:
        data = json.loads(response.content)
        device_id = str(data["id"])
        device_password = str(data["password"])
        print 'Registering device succeed for %s.' % name
        return (device_id, device_password)


def remove_device(url, device_id, password):
    '''
    Remove device from its Cozy.
    '''
    response = requests.delete('%s/device/%s/' % (url, device_id),
                               auth=('owner', password), verify=False)
    print json.loads(response.content)
