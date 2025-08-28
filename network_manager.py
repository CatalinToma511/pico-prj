import os
import utils
import json
import cryptolib
import hashlib
import machine

class NetworkManager:
    def __init__(self, file_path = 'networks'):
        self.file_path = file_path
        self.networks = {}
        self._load_networks()

    def _get_aes_instance(self):
        uid = machine.unique_id()
        hashed = hashlib.sha256(uid).digest()
        key = hashed[:16]
        iv = hashed[16:]
        aes = cryptolib.aes(key, 2, iv) # CBC mode
        return aes

    def _pad(self, data):
        pad_len = 16 - (len(data) % 16) # calculate how many bytes of padding are needed
        return data + bytes([pad_len] * pad_len) # add the padding

    def _unpad(self, data):
        pad_len = data[-1] # get the number of padding bytes
        return data[:-pad_len] # remove the padding

    def _load_networks(self):
        # if the given path is a file
        if utils.path_exists(self.file_path) and utils.is_file(self.file_path):
            try:
                # load encrypted bytes from the local file
                encrypted_bytes = utils.load_bytes_from_file(self.file_path)
                # check if the format looks like it can be decrypted
                if encrypted_bytes and len(encrypted_bytes) % 16 == 0 and len(encrypted_bytes) > 0:
                    # get aes cbc instance
                    aes = self._get_aes_instance()
                    # decrypt the bytes
                    decrypted_bytes = aes.decrypt(encrypted_bytes)
                    # remove padding bytes
                    unpadded_bytes = self._unpad(decrypted_bytes)
                    # convert the resulting byte into string then into a dictionary
                    self.networks = json.loads(unpadded_bytes.decode())
                    print("NetworkManager: Successfully loaded existing networks")
                else:
                    # File exists but isn't encrypted, treat as new
                    print("NetworkManager info: File not encrypted, starting fresh")
                    self.networks = {}
                    self._write_to_file()
            except Exception as e:
                print(f"NetworkManager error: Failed to decrypt file: {e}")
                self.networks = {}
            
        # if the given path is a non-existent file
        elif utils.path_exists(self.file_path) is False:
            self.networks = {}
            self._write_to_file()
            print(f'NetworkManager error: No existing file found, created new one')
        # if the given path is a directory instead of a file
        elif utils.path_exists(self.file_path) and utils.is_dir(self.file_path):
            print(f'NetworkManager error: Trying to read from a directory instead of a file')
    
    def _write_to_file(self):
        # if the given path is a directory instead of a file
        if utils.path_exists(self.file_path) and utils.is_dir(self.file_path):
            print(f'NetworkManager error: Trying to write in a directory instead of a file')
            return
        # if the path exists and is file or if the path does not exist
        # convert dictionary in string
        networks_str = json.dumps(self.networks).encode('utf-8')
        # padding the string
        padded_str = self._pad(networks_str)
        # encrypt the string
        aes = self._get_aes_instance()
        encrypted_str = aes.encrypt(padded_str)
        # write the encrypted data to file
        utils.write_bytes_to_file(self.file_path, encrypted_str)

    def add_network(self, ssid, key):
        self.networks[ssid] = key
        self._write_to_file()

    def remove_network(self, ssid):
        if ssid in self.networks:
            self.networks.pop(ssid)
            self._write_to_file()

    def remove_all_netowrks(self):
        self.networks = {}
        self._write_to_file()

    def get_networks(self):
        networks_list = list(self.networks.keys())
        return networks_list

    def get_network_password(self, ssid):
        if ssid in self.networks:
            return self.networks[ssid]
        else:
            print(f'NetworkManager error: Trying to get password, but the network({ssid}) is not saved')