import requests
import sys
import time
from bs4 import BeautifulSoup
from onvif import ONVIFCamera


class TallyParser:

    def __init__(self, key, url):
        self.key = key
        self.url = url

    def get_current_color(self, key=None):
        if key is not None:
            data = {'key': key}
        else:
            data = {'key': self.key}
        responce = requests.get(self.url, params=data)
        if responce.status_code != 200:
            print('Connection error')
            return None
        info_data = responce.text
        color = info_data.split('("')[1].split('");')[0]
        return color


class UrlKeyParser:

    def __init__(self, url_base):
        self.url_base = url_base

    def get_cam_info(self):
        can_keys_list = []
        responce = requests.get(str(self.url_base) + '/tally/')
        soup = BeautifulSoup(responce.text)
        cam_list = soup.select('a.tallyLink')
        for cam_data in cam_list:
            can_keys_list.append(cam_data['href'].split('key=')[1])
        return can_keys_list


class Blinker:

    def __init__(self, ip, port, login, password, relay_token, relay_type='direct'):
        self.mycam = ONVIFCamera(ip, port, login, password)
        self.cam_params = self.mycam.devicemgmt.create_type(
            'SetRelayOutputSettings')
        self.cam_params.RelayOutputToken = relay_token
        self.cam_params.Properties.Mode = 'Bistable'
        self.cam_params.Properties.DelayTime = 'PT0S'
        if relay_type == 'direct':
            self.on_stat = 'open'
            self.off_stat = 'closed'
        else:
            self.on_stat = 'closed'
            self.off_stat = 'open'
        self.cam_params.Properties.IdleState = self.off_stat
        self.mycam.devicemgmt.SetRelayOutputSettings(self.cam_params)
        self.mycam.devicemgmt.SetRelayOutputState(
            {'RelayOutputToken': relay_token, 'LogicalState': 'active'})
        self.led_status = False
        self.relay_token = relay_token

    def led_status_change(self, status):
        if status:
            print("Colors equal")
        else:
            print("colors not equal")
        if status == self.led_status:
            return
        self.led_status = status
        self.cam_params.Properties.IdleState = self.on_stat if status else self.off_stat
        self.mycam.devicemgmt.SetRelayOutputSettings(self.cam_params)
        self.mycam.devicemgmt.SetRelayOutputState(
            {'RelayOutputToken': self.relay_token, 'LogicalState': 'active'})


def get_kwargs(args):
    kwargs = {}
    for arg in args:
        if "=" not in arg:
            continue
        key, value = arg.split("=")
        kwargs[key] = value
    return kwargs


if __name__ == '__main__':
    params_list = []
    with open('Tallyconfig.txt', "r") as params_file:
        for line in params_file:
            params_list.append(line.replace('\n', ''))
    kwargs = get_kwargs(params_list)
    print(kwargs)

    cam_checker_url = str(kwargs['url_base']) + '/tallyupdate/'

    cam_data = kwargs['cam_data'].split(';')
    relay_token_list = kwargs['relay_token'].split(';')
    relay_type = kwargs['relay_type'].split(';')

    url_key_parser = UrlKeyParser(url_base=kwargs['url_base'])
    keys_list = url_key_parser.get_cam_info()
    if not keys_list:
        print('No cameras')
        exit(1)

    cam_data_list = []
    for cam_index, cam in enumerate(cam_data):
        cam_data_list.append({
            'ip': cam.split(':')[0],
            'port': cam.split(':')[1],
            'key': keys_list[cam_index],
            'type': relay_type[cam_index]
        })

    true_color = kwargs['true_color']
    current_active_cam_id = None
    tally_parser = TallyParser(key=None, url=cam_checker_url)
    # blinker_obj = Blinker(ip=kwargs['cam_ip'], port=kwargs['cam_port'], login=kwargs['login'], password=kwargs['password'])
    try:
        for cam_index, cam in enumerate(cam_data_list):
            try:
                Blinker(ip=cam['ip'], port=cam['port'], login=kwargs['login'], password=kwargs[
                        'password'], relay_token=relay_token_list[cam_index], relay_type=cam['type'])
            except Exception as e:
                print("Can't off led on start! cam_index =", cam_index)
                print('Error:', e)
                continue
        while True:
            no_active_camera_flag = True
            for cam_index, cam in enumerate(cam_data_list):
                if tally_parser.get_current_color(key=cam['key']) != true_color:
                    continue

                no_active_camera_flag = False
                if not (current_active_cam_id is None or current_active_cam_id != cam_index):
                    continue

                if current_active_cam_id is not None:
                    try:
                        blinker_obj.led_status_change(status=False)
                        current_active_cam_id = None
                        no_active_camera_flag = True
                    except Exception as e:
                        print("Can't change led status! cam_index = ",
                              current_active_cam_id)
                        print('Error:', e)
                        continue
                try:
                    blinker_obj = Blinker(ip=cam['ip'], port=cam['port'], login=kwargs['login'], password=kwargs[
                                          'password'], relay_token=relay_token_list[cam_index], relay_type=cam['type'])
                except Exception as e:
                    print("Can't change led status! cam_index =", cam_index)
                    print('Error:', e)
                    continue
                try:
                    blinker_obj.led_status_change(status=True)
                    no_active_camera_flag = False
                except Exception as e:
                    print("Can't change led status! cam_index =", cam_index)
                    print('Error:', e)
                    continue
                current_active_cam_id = cam_index
            if no_active_camera_flag and current_active_cam_id is not None:
                try:
                    blinker_obj.led_status_change(status=False)
                    current_active_cam_id = None
                except Exception as e:
                    print("Can't change led status! cam_index = ",
                          current_active_cam_id)
                    print('Error:', e)
                    continue

            time.sleep(0.2)
    except KeyboardInterrupt:
        if current_active_cam_id is not None:
            try:
                blinker_obj.led_status_change(status=False)
            except Exception as e:
                print("Can't off led before exit! cam_index = ",
                      current_active_cam_id)
                print('Error:', e)
        raise
