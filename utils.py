import os
import pathlib
from configs import get_default_initramfs_file, def_config, get_default_spec_list, prepare_config, build_config
from configs import get_spec_info


# exists will raise exception, exception will broke pool
def mkdir(path):
    try:
        if not pathlib.Path(path).exists():
            os.makedirs(path)
    except:
        pass

def entrys(path):
    entrys_list = []
    with os.scandir(path) as el:
        for entry in el:
            entrys_list.append(entry)
    return entrys_list


def file_entrys(path):
    file_list = []
    for entry in entrys(path):
        if entry.is_file:
            file_list.append(entry)
    return file_list


def absp(path):
    if os.path.exists(path):
        return os.path.abspath(path)
    else:
        raise


def app_list(list_path,app_list):
    if list_path == None and app_list == None:
        return get_default_spec_list()
    elif list_path == None and app_list != None:
        apps=app_list.split(',')
        return list(set(apps))
    else:
        app_list = []
        with open(list_path) as l:
            app_list = l.read().splitlines()
        return list(set(app_list))

