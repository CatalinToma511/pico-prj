import network
import urequests
import ujson
import time
import os
import utils
import machine
from network_manager import NetworkManager


class updateManager:
    def __init__(self):
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        # self.wlan.config(pm=network.WLAN.PM_NONE)  # disable power management
        time.sleep(1)  # wait for WLAN to initialize
        self.config = utils.load_json_from_file('projectconfig.json')
        self.project_files = utils.load_json_from_file('projectfiles.json')
        self.headers = {'User-Agent': 'PiPicoW'}
        self.led = machine.Pin("LED", machine.Pin.OUT)
        self.nm = NetworkManager('networks')
        

    def connect_to_internet(self, saved_networks_file = 'networks.json'):
        try:
            available_networks = self.wlan.scan()
            print(f'{len(available_networks)} wireless networks discovered')

            # get saved networks ssid's
            saved_networks = self.nm.get_networks()
            print(f'Saved networks: {saved_networks}')

            # check if there is any known network available with internet and connect to it
            timeout = 20
            for network in available_networks:
                ssid = network[0].decode('utf-8')
                print(f'Found network: {ssid}')
                try:
                    if ssid in saved_networks:
                        # try to connect to network
                        print(f'Trying to connect to {ssid}...')
                        key = self.nm.get_network_password(ssid)
                        self.wlan.connect(ssid, key)
                        start_time = time.time()
                        while not self.wlan.isconnected():
                            if time.time() - start_time > timeout:
                                # if it takes more than "timeout" seconds, consider failed connection
                                print(f'Failed to connect to {ssid}, timeout reached')
                                break
                        if self.wlan.isconnected() is True:
                            print(f'Connected to network: {ssid}')

                            # checking if network is connected to internet
                            print(f'Checking internet connection...')
                            test_url = 'https://github.com/favicon.ico'
                            response = urequests.get(test_url)
                            if response.status_code == 200:
                                print('Internet connection available')
                                return True
                            else:
                                print('Internet connection not available. Trying another network...')
                        else:
                            print(f'Status: {self.wlan.status()}')

                    else:
                        print(f'Network {ssid} not in saved networks')
                except Exception as e:
                    print(f'Error while connecting to {ssid}: {e}')
            print('Unable to connect to any network with internet connection')  
            return False
        except Exception as e:
            print(f'Failed to connect to internet: {e}')
            return False


    def get_last_repo_update_time(self, tries = 3):
        url = f'https://api.github.com/repos/{self.config["owner"]}/{self.config["repo"]}/commits?path={self.config["path"]}&per_page=1'
        for i in range(0, tries):
            try:
                response = urequests.get(url, headers=self.headers)
                if(response.status_code == 200):
                    commit_info = ujson.loads(response.text)[0]
                    return commit_info['commit']['committer']['date']
                raise Exception('request failed')
            except Exception as e:
                print(f'Failed to get last commit time ({i}/{tries} tries): {e}')
        return None


    def get_repo_tree(self):
        try:
            url = f'https://api.github.com/repos/{self.config["owner"]}/{self.config["repo"]}/git/trees/{self.config["branch"]}:{self.config["path"]}?recursive=1'
            response = urequests.get(url, headers=self.headers)
            if(response.status_code == 200):
                data = ujson.loads(response.text)
                if 'tree' in data:
                    #TODO: remove filtering here

                    result = []
                    for entry in data['tree']:
                        p = entry['path']
                        if entry['type'] is 'blob':
                            result.append(entry)
                    return result
                else:
                    raise Exception(f'incorrect tree response')
            else:
                raise Exception(f'status code {response.status_code}')
        except Exception as e:
            print(f'Failed to get repo tree: {e}')
            return None


    def download_files(self, files, directory):
        try:
            # check if downloads dir exists
            if directory in os.listdir():
                print(f'Deleting existing files in directory: {directory}')
                utils.remove_contents(directory)
            print(f'Creating downloads directory: {directory}')
            os.mkdir(directory)

            for file in files:
                download_url = f'https://raw.githubusercontent.com/{self.config["owner"]}/{self.config["repo"]}/{self.config["branch"]}/{self.config["path"]}/{file["path"]}'.replace(" ", "%20")
                print(f'Getting {download_url} ...')
                response = urequests.get(download_url, headers=self.headers)
                if(response.status_code == 200):
                    utils.write_content_to_file(f'{directory}/{file["path"]}', response.text)
                    print(f'{file["path"]} has been downloaded')
                else:
                    raise Exception(f'failed to download {download_url}')
            return True
        except Exception as e:
            print(f'Failed to download project files: {e}')
            return False


    def update_projectfiles_json(self, new_files, new_last_modified):
        new_projectfiles = {}
        files = []
        for new_file in new_files:
            files.append(
                {"filename": new_file["path"],
                 "size": new_file["size"]}
            )
        new_projectfiles["files"] = files
        new_projectfiles["last_modified"] = new_last_modified

        utils.write_content_to_file("projectfiles.json", ujson.dumps(new_projectfiles))


    def update_project_files(self, new_files_dir, new_files, last_commit):
        try:
            # check for validity of the new files (to be complete or to include essential files)
            for new_file in new_files:
                file_name = new_file["path"]
                expected_file_path = new_files_dir + '/' + file_name
                if utils.path_exists(expected_file_path) is False:
                    raise Exception(f'Missing downloaded file: {expected_file_path}')
                
                expected_size = new_file["size"]
                actual_size = utils.get_file_size(expected_file_path)
                if actual_size != expected_size:
                    raise Exception(f'Wrong file size: {file_name}; expected size: {expected_size}; actual size: {actual_size}')
            
            # backup current "app" dir into "app_old". try renaming the new files dir to "app". if fail, revert "app_old" to "app"
            utils.rename_path("app", "app_old")
            try:
                utils.rename_path(new_files_dir, "app")
                utils.remove_contents("app_old")
                self.update_projectfiles_json(new_files, last_commit)
            except:
                utils.rename_path("app_old", "app")
                
        except Exception as e:
                    print(f'Failed to replace project files: {e}')
                    return

    def run(self):
        self.led.off()
        try:
            # connect to a wifi network with internet connection
            internet_flag = self.connect_to_internet()
            if internet_flag is False:
                raise Exception('no internet connection found')
            
            # get the last commit from github
            last_commit = self.get_last_repo_update_time()
            if last_commit is None:
                raise Exception('could not get repo last commit')
            print(f'Last commit was made on: {last_commit}')

            # if the last commit stored on pico doesn't match the one on github
            # this can be due to either update or rollback, so == is needed
            if self.project_files["last_modified"] and last_commit == self.project_files["last_modified"]:
                raise Exception('already up to date')

            # if code reached here, it needs update
            self.led.on()
            print('Needs update')

            # gets json with each file and its details
            files = self.get_repo_tree() 
            if files is None:
                raise Exception('error getting files details')
            print(f'Files found: {len(files)}')

            # download the files found above
            new_files_directory = "downloads"
            download_status = self.download_files(files, new_files_directory)

            # if downloads fail
            if download_status is False:
                raise Exception('downloading files failed')
            
            # replace the old files with the new files
            self.update_project_files(new_files_directory, files, last_commit)
        except Exception as e:
            print(f'Update Manager: {e}')
        finally:
            self.close()

    def close(self):
        self.led.off()
        self.wlan.active(False)
        print('Update manager closed')


        
