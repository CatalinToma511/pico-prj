import network
import urequests
import ujson
import time
import os
import utils as utils
import machine


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
        

    def connect_to_internet(self, saved_networks_file = 'networks.json'):
        try:
            available_networks = self.wlan.scan()
            print(f'{len(available_networks)} wireless networks discovered')

            # load saved networks into a dictionary
            saved_networks_json = utils.load_json_from_file(saved_networks_file)
            saved_networks = {}
            for entry in saved_networks_json:
                saved_networks[entry["ssid"]] = entry["key"]

            # check if there is any known network available with internet and connect to it
            timeout = 20
            for network in available_networks:
                ssid = network[0].decode('utf-8')
                try:
                    if ssid in saved_networks:
                        # try to connect to network
                        print(f'Trying to connect to {ssid}...')
                        key = saved_networks[ssid]
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
                except Exception as e:
                    print(f'Error while connecting to {ssid}: {e}')
            print('Unable to connect to any network with internet connection')  
            return False
        except Exception as e:
            print(f'Failed to connect to internet: {e}')
            return False


    def get_last_repo_update_time(self):
        try:
            url = f'https://api.github.com/repos/{self.config["owner"]}/{self.config["repo"]}/commits?path={self.config["path"]}'
            response = urequests.get(url, headers=self.headers)
            if(response.status_code == 200):
                commit_info = ujson.loads(response.text)[0]
                return commit_info['commit']['committer']['date']
            else:
                raise Exception('request failed')
        except Exception as e:
            print(f'Failed to get last commit time: {e}')
            return ''


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
            return ''


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
        except Exception as e:
            print(f'Failed to download project files: {e}')


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
        #TODO
        # 3. rename new files dir to the old project files dir

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
        internet_flag = self.connect_to_internet()
        if internet_flag is False:
            return
        last_commit = self.get_last_repo_update_time()
        print(f'Last commit was made on: {last_commit}')

        if "last_modified" not in self.project_files or last_commit > self.project_files["last_modified"]:
            self.led.on()
            print('Needs update')

            files = self.get_repo_tree() # gets json with each file and its details
            print(f'Files found: {len(files)}')

            new_files_directory = "downloads"
            self.download_files(files, new_files_directory)

            #TODO
            # After download, replace the old files with the new files. Maybe
            # use a dir named like "app" where the source files are located, and
            # delete it and rename the "download" dir into "app"
            self.update_project_files(new_files_directory, files, last_commit)
        else:
            print('Already up to date')

        self.led.off()
        self.wlan.active(False)


        
