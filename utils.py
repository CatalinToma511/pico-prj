import ujson
import os


def load_json_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            data = file.read()
            file.close()
            json_data = ujson.loads(data)
            return json_data
    except Exception as e:
        print(f'Failed to load JSON data from {file_path}: {e}')
        return {}
    
def load_bytes_from_file(file_path):
    try:
        with open(file_path, 'rb') as file:
            data = file.read()
            file.close()
            return data
    except Exception as e:
        print(f'Failed to load content from {file_path}: {e}')
        return None
        

def pretty_print_json(json_obj, indent=4):
    json_str = ujson.dumps(json_obj)
    pretty_json_str = ""
    level = 0
    for char in json_str:
        if char == '{' or char == '[':
            level += 1
            pretty_json_str += char + '\n' + ' ' * (level * indent)
        elif char == '}' or char == ']':
            level -= 1
            pretty_json_str += '\n' + ' ' * (level * indent) + char
        elif char == ',':
            pretty_json_str += char + '\n' + ' ' * (level * indent)
        else:
            pretty_json_str += char
    return pretty_json_str


def is_dir(path):
    try:
        stat = os.stat(path)
        return (stat[0] ^ 0x4000 == 0)
    except Exception as e:
        print(f'Checking directory error: {e}')
        return False
        

def is_file(path):
    try:
        stat = os.stat(path)
        return (stat[0] ^ 0x8000 == 0)
    except Exception as e:
        print(f'Checking file error: {e}')
        return False


def path_exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False
    except Exception as e:
        print(f'Checking path error: {e}')
        return False

def get_file_size(path):
    try:
        stat = os.stat(path)
        return stat[6]
    except OSError:
        return 0

def remove_contents(path):
    try:
        if is_dir(path):
            for entry in os.listdir(path):
                remove_contents(path + '/' + entry)
            os.rmdir(path)
        else:
            os.remove(path)
    except Exception as e:
        print(f'Error while removing files at path {path}: {e}')

def rename_path(old_path, new_path):
    try:
        os.rename(old_path, new_path)
    except Exception as e:
        print(f'Error while renamming path [{old_path}] to [{new_path}]')


def write_content_to_file(file_path, content):
    try:
        parts = file_path.split('/')
        dirs = parts[:-1]
        file_name = parts[-1]
        # creating file path directories, if needed
        dir_path = ""
        for dir in dirs:
            dir_path += '/' + dir
            if path_exists(dir_path):
                if is_dir(dir_path):
                    continue
                else:
                    raise Exception(f'File error: {dir_path} should be a directory but is not')
            else:
                os.mkdir(dir_path)
        # creating file and writing its content
        with open(f'{file_path}', 'w') as newfile:
            newfile.write(content)
            newfile.close()
    except Exception as e:
        print(f'Failed to write content to file {file_path}: {e}')
    
def write_bytes_to_file(file_path, content):
    try:
        with open(f'{file_path}', 'wb') as newfile:
            newfile.write(content)
            newfile.close()
    except Exception as e:
        print(f'Failed to write bytes to file {file_path}: {e}')