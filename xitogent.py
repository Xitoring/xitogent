import time
import tempfile
import sys
import subprocess
import ssl
import shutil
import requests
import re
import psutil
import pkgutil
import os.path
import os
import math
import json
import datetime
import collections
import atexit
if sys.version_info[0] >= 3: from urllib.request import urlretrieve
if sys.version_info[0] < 3: from urllib import urlretrieve
from requests import ReadTimeout, ConnectTimeout, HTTPError, Timeout, ConnectionError, TooManyRedirects
from localStoragePy import localStoragePy

#add cert data for the requests package

cert_data = pkgutil.get_data('certifi', 'cacert.pem')

handle = tempfile.NamedTemporaryFile(delete=False)
handle.write(cert_data)
handle.flush()

os.environ['REQUESTS_CA_BUNDLE'] = handle.name

#######################################

CORE_URL = 'https://app.xitoring.com/'
AGENT_URL = 'https://app.xitoring.com/xitogent/xitogent'

CONFIG_FILE = '/etc/xitogent/xitogent.conf'
PID_FILE = '/var/run/xitogent.pid'

#variables are used for auto updating
VERSION = '1.0.0'
LAST_UPDATE_ATTEMPT = ''
SENDING_DATA_SECONDS = 60

localStorage = localStoragePy("xitogent", 'text')


def modify_config_file(data, delete_mode=False):

    config = read_config_file()

    for i in data:
        if delete_mode and i in config:
            del config[i]
        else:
            config[i] = data[i]

    config_path = get_config_path()

    config_file = open(config_path, 'w')

    for i in config:
        config_file.write(i + '=' + config[i] + '\n')

    config_file.close()


def get_api_key():
    for index, value in enumerate(sys.argv):
        if re.search("--key=", value):
            value = value.replace('--key=', '')
            return value.strip()
    sys.exit('The API key(--key) is required.')


def is_add_device():
    if len(sys.argv) > 1 and sys.argv[1] == 'register':
        return True
    return False


def add_device():
    try:
        params = {
            'ips': Linux.fetch_ips(),
            'hostname': Linux.fetch_hostname(),
            'preferences': generate_preferences_params()
        }

        headers = {'Accept': 'application/json', 'Authorization': 'Bearer ' + get_api_key()}

        if is_dev():
            global CORE_URL
            CORE_URL = 'http://localhost/'

        response = requests.post(CORE_URL + "devices/add", json=params, headers=headers)

        response.raise_for_status()

        modify_config_file(json.loads(response.text))

        print('Server has been registered successfully')

        sys.exit(0)

    except HTTPError as e:

        now = datetime.datetime.now()

        status_code = e.response.status_code

        message = now.strftime("%Y-%m-%d %H:%M:%S") + ' - HTTP status:' + str(status_code) + ' - '

        #Bad request
        if status_code == 400:
            errors = []
            result = json.loads(e.response.text)
            for i in result:
                errors.append(result[i][0])
            sys.exit(message + ", ".join(errors))

        #Unauthorize
        if status_code == 401:
            sys.exit(message + 'The API key is invalid')

        #Access denied
        if status_code == 403:
            temp = json.loads(e.response.text)
            sys.exit(message + temp['message'])

        #Invalid url
        if status_code == 404:
            sys.exit(message + 'Device add URL is invalid')

        sys.exit(message + 'Unexpected error happened')

    except ConnectTimeout:
        sys.exit('Connection to the host has been Timed out')
    except ReadTimeout:
        sys.exit('Timed out while receiving data from the host')
    except Timeout:
        sys.exit('Request to the host has been Timed out')
    except ConnectionError:
        sys.exit('Failed to establish a connection')
    except TooManyRedirects:
        sys.exit('Too many redirects')
    except requests.exceptions.InvalidURL:
        sys.exit('URL is improperly formed or cannot be parsed')


def is_dev():
    data = read_config_file(checking_version=True)
    if 'dev' in data and int(data['dev']) == 1:
        return True
    return False


def generate_preferences_params():

    preferences = {}

    value = find_argument_value('--group=')

    if value != '':
        preferences['group'] = value

    value = find_argument_value('--subgroup=')

    if value != '':
        preferences['subgroup'] = value

    value = find_argument_value('--notification=')

    if value != '':
        preferences['notification'] = value

    preferences['auto_discovery'] = is_auto_option_included('discovery')
    preferences['auto_trigger'] = is_auto_option_included('trigger')
    preferences['auto_update'] = is_auto_option_included('update')

    preferences['module_ping'] = is_module_included('ping')
    preferences['module_http'] = is_module_included('http')
    preferences['module_dns'] = is_module_included('dns')
    preferences['module_ftp'] = is_module_included('ftp')
    preferences['module_smtp'] = is_module_included('smtp')
    preferences['module_imap'] = is_module_included('imap')
    preferences['module_pop3'] = is_module_included('pop3')

    return preferences


def is_auto_option_included(name):

    value = find_argument_value('--auto_{}='.format(name))

    value = value.lower()

    if value != '' and value in ['true', 'false']:
        return value

    return 'false'


def is_module_included(name):

    value = find_argument_value('--module_{}='.format(name))

    value = value.lower()

    if value != '' and value in ['true', 'false']:
        return value

    return 'false'


def find_argument_value(argument):
    for index, value in enumerate(sys.argv):
        if re.search(argument, value):
            value = value.replace(argument, '')
            return value.strip()

    return ''


def read_config_file(checking_version=False):

    config_path = get_config_path()

    if not os.path.isfile(config_path):
        if checking_version:
            return {}
        else:
            sys.exit('Config file not found at the default path')
    try:
        f = open(config_path, 'r')
    except IOError:
        if checking_version:
            return {}
        else:
            sys.exit('Config file not found at the default path')

    data = {}

    for line in f:

        if line.find('=') == -1:
            continue

        temp = line.split('=')

        if len(temp) > 2:
            continue

        name, value = temp

        if value.endswith('\n'):
            value = value.rstrip('\n')

        name = name.strip()

        name = name.lower()

        data[name] = value.strip()

    return data


def get_config_path():
    for index, value in enumerate(sys.argv):
        next_index = index + 1
        if value == '-c' and len(sys.argv) > next_index:
            return sys.argv[next_index]

    return CONFIG_FILE


def read_config():

    data = read_config_file()

    if 'password' not in data:
        data['password'] = ''

    if 'uid' not in data:
        sys.exit('UID does not exist in the config file')

    if 'node_url' not in data:
        data['node_url'] = retrieve_node_url(data['uid'], data['password'])

    data['node_url'] = add_http_to_url(data['node_url'])

    return data


def retrieve_node_url(uid, password):

    device = get_device_info(uid, password)

    if 'node_url' in device and device['node_url'] != '':
        modify_config_file({'node_url': device['node_url']})
        return device['node_url']

    return ''


def add_http_to_url(url):

    if url == '':
        return url

    if is_dev():
        if not url.startswith('http://'):
            url = 'http://' + url
    elif not url.startswith('https://'):
        url = 'https://' + url

    if not url.endswith('/'):
        url = url + '/'

    return url


def get_device_info(uid, password):
    try:
        if is_dev():
            global CORE_URL
            CORE_URL = 'http://localhost/'

        headers = {'Accept': 'application/json', 'uid': uid, 'password': password}

        response = requests.get(CORE_URL + "devices/" + uid, headers=headers)

        response.raise_for_status()

        return json.loads(response.text)

    except (ConnectTimeout, HTTPError, ReadTimeout, Timeout, ConnectionError, TooManyRedirects) as e:

        #Unauthorized
        if e.__class__.__name__ == 'HTTPError' and e.response.status_code == 401:
            sys.exit('Unauthorized action caused by Invalid Password or UID')
        pass

    return {}


def auto_update():
    global LAST_UPDATE_ATTEMPT
    LAST_UPDATE_ATTEMPT = time.time()
    download_new_xitogent()
    if validate_new_xitogent():
        replace_new_xitogent()


def download_new_xitogent():
    try:

        if os.path.exists('/etc/xitogent/test'):
            os.system('rm -rf /etc/xitogent/test/*')
        else:
            os.mkdir('/etc/xitogent/test')

        urlretrieve(AGENT_URL, '/etc/xitogent/test/xitogent')

        os.chmod('/etc/xitogent/test/xitogent', 0o755)

    except Exception as e:
        if is_force_update():
            sys.exit('Downloading new Xitogent failed')
        pass


def validate_new_xitogent():

    p = subprocess.Popen('/etc/xitogent/test/xitogent update-test', stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    stdout, stderr = p.communicate()

    # error
    if p.returncode != 0:
        stderr = stderr.decode("utf-8")
        report_failed_update(stderr)
        return False

    output = stdout.decode("utf-8")

    # success
    if re.search("HTTP status:200", output):
        return True

    report_failed_update(output)

    return False


def report_failed_update(error_message):
    try:

        config_data = read_config()

        headers = {'Accept': 'application/json', 'uid': config_data['uid'], 'password': config_data['password']}

        if is_dev():
            global CORE_URL
            CORE_URL = 'http://localhost/'

        params = {'subject': 'update_failed', 'body': error_message}

        requests.post(CORE_URL + "send_report", json=params, headers=headers)

    except (ConnectTimeout, HTTPError, ReadTimeout, Timeout, ConnectionError, TooManyRedirects):
        pass


def is_new_xitogent_test():
    for index, value in enumerate(sys.argv):
        if value == 'update-test':
            return True

    return False


def test_new_xitogent():
    send_data(read_config())
    sys.exit(0)


def replace_new_xitogent():

    try:
        source = '/etc/xitogent/test/'
        dest = '/usr/bin/'
        fileName = 'xitogent'
        shutil.move(os.path.join(source, fileName), os.path.join(dest, fileName))
    except Exception:
        if is_force_update():
            sys.exit('Failed to move Xitogent file from test directory to current directory')
        pass

    if not run_command('rm -rf /etc/xitogent/test'):
        if is_force_update():
            print('Failed to remove the test directory')
        pass

    if is_centos6():
        cmd = 'service xitogent restart'
    else:
        cmd = 'systemctl restart xitogent'

    if not run_command(cmd):
        if is_force_update():
            sys.exit('Failed to start new Xitogent')
        pass

    if is_force_update():
        print('Updated Xitogent started working successfully')


def is_force_update():
    if len(sys.argv) > 1 and sys.argv[1] == 'update':
        return True
    return False


def force_update():
    download_new_xitogent()
    replace_new_xitogent()


def run_command(cmd):

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    stdout, stderr = p.communicate()

    # error
    if p.returncode != 0:
        return False

    return True


def is_centos6():

    os = Linux.get_os()

    os = os.lower()

    is_centos = re.search("centos", os)

    temp = re.findall(r'\d+(?:\.\d+)*', os)

    version = temp[0].split('.')

    if is_centos and int(version[0]) <= 6:
        return True

    return False


def is_start_mode():
    if len(sys.argv) > 1 and sys.argv[1] == 'start':
        return True
    return False


def start():

    if is_running():
        sys.exit('Already running')

    reset_variables()

    if is_start_as_daemon():
        daemonize()
    else:
        save_pid()

    config_data = read_config()

    localStorage.setItem('uptime', int(time.time()))

    while True:
        if not is_device_paused():
            send_data(config_data)
        else:
            print('Xitogent is paused')
            inquire_pause_status()
        time.sleep(SENDING_DATA_SECONDS)


def increment_variable(name):

    old_value = localStorage.getItem(name)

    if old_value:
        localStorage.setItem(name, int(old_value) + 1)
    else:
        localStorage.setItem(name, 1)


def is_process_running(pid):

    for proc in psutil.process_iter():

        try:
            if proc.pid == int(pid):
                return True
        except psutil.NoSuchProcess:
            pass

    return False


def save_pid():
    pid = str(os.getpid())
    file = open(PID_FILE, 'w+')
    file.write("%s\n" % pid)
    file.close()


def is_running():
    if os.path.isfile(PID_FILE):
        try:
            with open(PID_FILE) as file:
                pid = file.read().strip()
                if is_process_running(pid):
                    return True
        except Exception as e:
            pass

    return False


def is_start_as_daemon():
    if '-d' in sys.argv:
        return True
    return False


def check_start_as_daemon():

    if '-d' not in sys.argv:
        return None

    daemonize()


def daemonize():

    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError:
        sys.exit("fork #1 failed")

    # decouple from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0)

    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError:
        sys.exit("fork #2 failed")

    # redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()

    si = open(os.devnull, 'r')
    so = open(os.devnull, 'a+')

    try:
        se = open(os.devnull, 'a+', 0)
    except ValueError:
        # Python 3 can't have unbuffered text I/O
        se = open(os.devnull, 'a+', 1)

    try:
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
    except Exception:
        pass

    # write pidfile
    try:
        atexit.register(del_pid_file)
        pid = str(os.getpid())
        file = open(PID_FILE, 'w+')
        file.write("%s\n" % pid)
        file.close()
    except Exception:
        pass


def del_pid_file():
    if os.path.isfile(PID_FILE):
        os.remove(PID_FILE)


def is_device_paused():

    config_data = read_config()

    if 'pause_until' not in config_data:
        return False

    if config_data['pause_until'] != '' and int(config_data['pause_until']) >= time.time():
        return True

    return False


def inquire_pause_status():
    try:

        config_data = read_config()

        global CORE_URL

        if is_dev():
            CORE_URL = 'http://localhost/'

        headers = {'Accept': 'application/json', 'uid': config_data['uid'], 'password': config_data['password']}

        response = requests.get("{core_url}devices/{uid}/check-pause".format(core_url=CORE_URL, uid=config_data['uid']), headers=headers)

        response.raise_for_status()

        response = json.loads(response.text)

        if not response['is_paused']:
            modify_config_file({'pause_until': ''}, delete_mode=True)

    except (ConnectTimeout, HTTPError, ReadTimeout, Timeout, ConnectionError, TooManyRedirects) as e:
        pass


def send_data(config_data):

    global SENDING_DATA_SECONDS

    if config_data['node_url'] == '':
        print('\nFinding the nearest node to your server...\n')
        node_url = retrieve_node_url(config_data['uid'], config_data['password'])
        config_data['node_url'] = add_http_to_url(node_url)
        SENDING_DATA_SECONDS = 5
        return None
    else:
        SENDING_DATA_SECONDS = 60

    url = config_data['node_url'] + "devices/" + config_data['uid'] + "/statistics/add"

    try:

        params = {'data': Linux.fetch_data(), 'version': VERSION}

        print(params)

        headers = {'Accept': 'application/json', 'uid': config_data['uid'], 'password': config_data['password']}

        response = requests.post(url, json=params, headers=headers)

        now = datetime.datetime.now()

        #success
        if response.status_code == 200:

            print('\n' + now.strftime("%Y-%m-%d %H:%M:%S") + ' - HTTP status:200\n')

            response = json.loads(response.text)

            needs_update = 'update' in response and response['update']

            if needs_update and can_be_updated():
                auto_update()

            increment_variable('sent_sequences')

            return None

        message = now.strftime("%Y-%m-%d %H:%M:%S") + ' - HTTP status:' + str(response.status_code) + ' - '

        #Bad request
        if response.status_code == 400:
            errors = []
            result = json.loads(response.text)
            if 'pause_until' in result:
                modify_config_file({'pause_until': str(result['pause_until'])})
                del result['pause_until']
            for i in result:
                if isinstance(result[i], list):
                    errors.append(result[i][0])
                else:
                    errors.append(result[i])
            print("\n" + message + ", ".join(errors))
            increment_variable('failed_sequences')
            return None

        #Unauthorized
        if response.status_code == 401:
            print('\n' + message + 'Unauthorized action caused by Invalid Password or UID' + '\n')
            increment_variable('failed_sequences')
            return None

        #url not found or uid is invalid
        if response.status_code == 404:
            try:
                result = json.loads(response.text)
                print('\n' + message + str(result['message']) + '\n')
            except Exception:
                print('\n' + message + 'URL not found' + '\n')
            increment_variable('failed_sequences')
            return None

        #error
        print(message + str(response.text))

        increment_variable('failed_sequences')

    except HTTPError:
        print('\nHTTP Exception for ' + url + '\n')
        increment_variable('failed_sequences')
    except ConnectTimeout:
        print('\nTimed out while connecting to the host\n')
        increment_variable('failed_sequences')
    except ReadTimeout:
        print('\nTimed out while receiving data from the host\n')
        increment_variable('failed_sequences')
    except Timeout:
        print('\nTimed out while requesting to the host\n')
        increment_variable('failed_sequences')
    except ConnectionError:
        print('\nFailed to establish a connection\n')
        node_url = retrieve_node_url(config_data['uid'], config_data['password'])
        if node_url:
            config_data['node_url'] = add_http_to_url(node_url)
        increment_variable('failed_sequences')
    except TooManyRedirects:
        print('\nToo many redirects\n')
        increment_variable('failed_sequences')
    except (requests.exceptions.InvalidURL, requests.exceptions.MissingSchema):
        print('\nURL is improperly formed or cannot be parsed\n')
        node_url = retrieve_node_url(config_data['uid'], config_data['password'])
        config_data['node_url'] = add_http_to_url(node_url)
        increment_variable('failed_sequences')


def can_be_updated():

    try:
        global LAST_UPDATE_ATTEMPT

        if LAST_UPDATE_ATTEMPT == '':
            return True

        DAY_IN_SECONDS = 86400

        diff = time.time() - LAST_UPDATE_ATTEMPT

        if diff > DAY_IN_SECONDS:
            return True

    except Exception:
        pass

    return False


def is_uninstall():
    if len(sys.argv) > 1 and sys.argv[1] == 'uninstall':
        return True
    return False


def uninstall():

    uninstall_xitogent = prompt("Are you sure you want to uninstall Xitogent?[y/N]:")

    if uninstall_xitogent.lower() != 'y':
        sys.exit(0)

    delete_from_database = prompt("Delete the Device from database?[y/N]:")

    if delete_from_database.lower() != 'y':
        delete_xitogent()
        sys.exit(0)

    delete_device()

    print('This Device has been deleted from the database successfully')

    delete_xitogent()

    sys.exit(0)


def delete_device():
    try:
        config_data = read_config()

        if is_dev():
            global CORE_URL
            CORE_URL = 'http://localhost/'

        url = CORE_URL + "devices/" + config_data['uid'] + "/uninstall"
        headers = {'Accept': 'application/json', 'uid': config_data['uid'], 'password': config_data['password']}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except (ConnectTimeout, HTTPError, ReadTimeout, Timeout, ConnectionError, TooManyRedirects):
        sys.exit('Cannot delete this device from the database.')


def prompt(string):

    #python2
    if sys.version_info[0] == 2:
        return raw_input(string)

    #python3
    if sys.version_info[0] == 3:
        return input(string)

    return None


def delete_xitogent():

    if is_centos6():
        service_path = '/etc/init.d/xitogent'
        stop_xitogent_cmd = 'service xitogent stop'
    else:
        service_path = '/etc/systemd/system/xitogent.service'
        stop_xitogent_cmd = 'systemctl stop xitogent'

    if not run_command(stop_xitogent_cmd):
        sys.exit('Failed to stop service')

    if not run_command('rm -rf ' + service_path):
        sys.exit('Failed to delete ' + service_path + ' file')

    if not run_command('rm -rf /etc/xitogent'):
        sys.exit('Failed to delete /etc/xitogent directory')

    if not run_command('rm -rf /usr/bin/xitogent'):
        sys.exit('Failed to delete /usr/bin/xitogent directory')

    print('Xitogent uninstalled successfully')


def is_initial_test():
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        return True
    return False


def get_device_status():

    hostname = Linux.fetch_hostname()

    if type(hostname) == dict:
        print('Testing hostname ' + '... failed')
    else:
        print('Testing hostname ' + '... OK')

    os = Linux.get_os()

    if type(os) == dict:
        print('Testing os ' + '... failed')
    else:
        print('Testing os ' + '... OK')

    uptime = Linux.fetch_uptime()

    if type(uptime) == dict:
        print('Testing uptime ' + '... failed')
    else:
        print('Testing uptime ' + '... OK')

    timezone = Linux.get_timezone()

    if type(timezone) == dict:
        print('Testing timezone ' + '... failed')
    else:
        print('Testing timezone ' + '... OK')

    cpu_model_name = Linux.get_cpu_model_name()

    if type(cpu_model_name) == dict:
        print('Testing cpu model name ' + '... failed')
    else:
        print('Testing cpu model name ' + '... OK')

    cpu_count = Linux.get_cpu_count()

    if type(cpu_count) == dict:
        print('Testing cpu count ' + '... failed')
    else:
        print('Testing cpu count ' + '... OK')

    ips = Linux.fetch_ips()

    if type(ips) == dict:
        print('Testing ips ' + '... failed')
    else:
        print('Testing ips ' + '... OK')

    cpu_usage = Linux.fetch_cpu_usage()

    if 'status' in cpu_usage:
        print('Testing cpu usage ' + '... failed')
    else:
        print('Testing cpu usage ' + '... OK')

    load_average = Linux.fetch_cpu_load_average()

    if 'status' in load_average:
        print('Testing load average ' + '... failed')
    else:
        print('Testing load average ' + '... OK')

    disk_usage = Linux.fetch_disk_usage()

    if 'status' in disk_usage:
        print('Testing disk usage ' + '... failed')
    else:
        print('Testing disk usage ' + '... OK')

    disk_io = Linux.fetch_disk_io()

    if 'status' in disk_io:
        print('Testing disk io ' + '... failed')
    else:
        print('Testing disk io ' + '... OK')

    memory_usage = Linux.fetch_memory_usage()

    if 'status' in memory_usage:
        print('Testing memory usage ' + '... failed')
    else:
        print('Testing memory usage ' + '... OK')

    network = Linux.fetch_network()

    if 'status' in network:
        print('Testing network ' + '... failed')
    else:
        print('Testing network ' + '... OK')

    detected_softwares = Linux.find_detected_softwares()

    if type(detected_softwares) == dict:
        print('Testing detected softwares ' + '... failed')
    else:
        print('Testing detected softwares ' + '... OK')

    top_five_memory_processes = Linux.find_top_five_memory_consumer_processes()

    if type(top_five_memory_processes) == dict:
        print('Testing top 5 memory processes ' + '... failed')
    else:
        print('Testing top 5 memory processes ' + '... OK')

    top_five_cpu_processes = Linux.find_top_five_cpu_consumer_processes()

    if type(top_five_cpu_processes) == dict:
        print('Testing top 5 cpu processes ' + '... failed')
    else:
        print('Testing top 5 cpu processes ' + '... OK')

    sys.exit(0)


def is_show_commands_mode():
    if len(sys.argv) == 1 \
            or (
            not is_add_device()
            and not is_start_mode()
            and not is_uninstall()
            and not is_force_update()
            and not is_version_mode()
            and not is_initial_test()
            and not is_new_xitogent_test()
            and not is_pause_mode()
            and not is_unpause_mode()
            and not is_status_mode()
            and not is_stop_mode()
            and not is_restart_mode()
    ):
        return True
    return False


def show_commands():
    print('%-15s' '%s' % ('Xitogent v' + VERSION, '('+ CORE_URL + ')'))
    print("", '')
    print('%-15s' '%s' % ('register', 'Add a device'))
    print('%-15s' '%s' % ('', 'options:'))
    print('%-15s' '%-16s %s' % ('', '--key', 'Your unique account key for adding new server - found on your control panel '))
    print('%-15s' '%-16s %s' % ('', '--group', 'Server\'s group name as string'))
    print('%-15s' '%-16s %s' % ('', '--subgroup', 'Server\'s subgroup name as string'))
    print('%-15s' '%-16s %s' % ('', '--notification', 'default notification role name as string'))
    print('%-15s' '%-16s %s' % ('', '--auto_discovery', 'Always looking for any new detected service'))
    print('%-15s' '%-16s %s' % ('', '--auto_trigger', 'Create new trigger'))
    print('%-15s' '%-16s %s' % ('', '--auto_update', 'Enable auto update for Xitogent'))
    print('%-15s' '%-16s %s' % ('', '--module_ping', 'Create ping module automatically'))
    print('%-15s' '%-16s %s' % ('', '--module_http', 'Create http module automatically'))
    print('%-15s' '%-16s %s' % ('', '--module_dns', 'Create dns module automatically'))
    print('%-15s' '%-16s %s' % ('', '--module_ftp', 'Create ftp module automatically'))
    print('%-15s' '%-16s %s' % ('', '--module_smtp', 'Create smtp module automatically'))
    print('%-15s' '%-16s %s' % ('', '--module_imap', 'Create imap module automatically'))
    print('%-15s' '%-16s %s' % ('', '--module_pop3', 'Create pop3 module automatically'))
    print('%-15s' '%s' % ('start', 'Start Xitogent (sending data)'))
    print('%-15s' '%s' % ('', 'options:'))
    print('%-15s' '%-16s %s' % ('', '-d', 'Start as daemon'))
    print('%-15s' '%s' % ('stop', 'Stop Xitogent'))
    print('%-15s' '%s' % ('restart', 'Restart Xitogent'))
    print('%-15s' '%s' % ('uninstall', 'Uninstall Xitogent and remove device on your control panel'))
    print('%-15s' '%s' % ('update', 'Force update Xitogent'))
    print('%-15s' '%s' % ('pause', 'Pause Xitogent'))
    print('%-15s' '%s' % ('', 'options:'))
    print('%-15s' '%s' % ('', 'm (minute) _ h (hour) _ d (day) _ w (week)'))
    print('%-15s' '%s' % ('', 'Usage: Xitogent pause 3d'))
    print('%-15s' '%s' % ('unpause', 'Unpause Xitogent'))
    print('%-15s' '%s' % ('help', 'Show Xitogent\' s commands'))
    print('%-15s' '%s' % ('version', 'Show Xitogent\' s version'))
    print('%-15s' '%s' % ('status', 'Show Xitogent\' s status'))
    sys.exit(0)


def is_version_mode():
    if len(sys.argv) > 1 and sys.argv[1] == '--version' or sys.argv[1] == 'version' or sys.argv[1] == '-v':
        return True
    return False


def show_xitogent_version():
    if is_dev():
        print('Xitogent v' + VERSION + ' (' + 'http://localhost/' + ')' )
    else:
        global CORE_URL
        print('Xitogent v' + VERSION + ' (' + CORE_URL + ')' )
    sys.exit(0)


def is_pause_mode():
    if len(sys.argv) > 1 and sys.argv[1] == 'pause':
        return True
    return False


def pause():

    try:

        pause_until = fetch_pause_until()

        config_data = read_config()

        global CORE_URL

        if is_dev():
            CORE_URL = 'http://localhost/'

        headers = {'Accept': 'application/json', 'uid': config_data['uid'], 'password': config_data['password']}

        response = requests.get("{core_url}devices/{uid}/pause".format(core_url=CORE_URL, uid=config_data['uid']), params={'pause_until': pause_until}, headers=headers)

        response.raise_for_status()

        modify_config_file({'pause_until': str(pause_until)})

        print('Xitogent paused succeefully.')

    except (ConnectTimeout, HTTPError, ReadTimeout, Timeout, ConnectionError, TooManyRedirects) as e:
        sys.exit('Cannot pause Xitogent.')


def fetch_pause_until():

    time_string = ''

    MINUTE_IN_SECONDS = 60
    HOUR_IN_SECONDS = 60 * MINUTE_IN_SECONDS
    DAY_IN_SECONDS = 24 * HOUR_IN_SECONDS
    WEEK_IN_SECONDS = 7 * DAY_IN_SECONDS
    YEAR_IN_SECONDS = 365 * DAY_IN_SECONDS

    for index, value in enumerate(sys.argv):
        next_index = index+1
        if re.search("pause", value) and next_index < len(sys.argv):
            time_string = sys.argv[next_index]

    if time_string == '':
        return int(time.time() + (16 * YEAR_IN_SECONDS))

    RELATIVE_TIME_REGEX = re.compile('^((\d+)[wW])?((\d+)[dD])?((\d+)[hH])?((\d+)[mM])?$')

    relative_time_found = RELATIVE_TIME_REGEX.match(time_string)

    if not relative_time_found:
        sys.exit('Time must be in the format 2w4d6h45m')

    seconds = 0

    time_string = time_string.strip()

    durations = list(map(int, re.split('[wWdDhHmM]', time_string)[:-1]))

    types = list(re.split('\d+', time_string))

    if types[0] == '':
        del types[0]

    for index, duration in enumerate(durations):

        type = types[index]

        type = type.lower()

        if type == 'w':
            seconds += duration * WEEK_IN_SECONDS
        elif type == 'd':
            seconds += duration * DAY_IN_SECONDS
        elif type == 'h':
            seconds += duration * HOUR_IN_SECONDS
        else:
            seconds += duration * MINUTE_IN_SECONDS

    return int(time.time() + seconds)


def is_unpause_mode():
    if len(sys.argv) > 1 and sys.argv[1] == 'unpause':
        return True
    return False


def unpause():
    try:

        config_data = read_config()

        global CORE_URL

        if is_dev():
            CORE_URL = 'http://localhost/'

        headers = {'Accept': 'application/json', 'uid': config_data['uid'], 'password': config_data['password']}

        response = requests.get("{core_url}devices/{uid}/unpause".format(core_url=CORE_URL, uid=config_data['uid']),
                                headers=headers)

        response.raise_for_status()

        modify_config_file({'pause_until': ''}, delete_mode=True)

        print('Xitogent unpaused successfully.')

    except (ConnectTimeout, HTTPError, ReadTimeout, Timeout, ConnectionError, TooManyRedirects) as e:
        sys.exit('Cannot unpause Xitogent.')


def is_stop_mode():
    if len(sys.argv) > 1 and sys.argv[1] == 'stop':
        return True
    return False


def stop():

    if not is_running():
        if is_stop_mode():
            print('Already stopped.')
        return None

    if os.path.isfile(PID_FILE):
        try:
            with open(PID_FILE) as file:

                pid = file.read().strip()

                os.kill(int(pid), 15)

                run_command('rm -rf {}'.format(PID_FILE))

                if is_stop_mode():
                    print('Xitogent stopped successfully.')

        except Exception:
            if is_stop_mode():
                print('Stopping Xitogent failed.')
    else:

        if is_centos6():
            cmd = 'service xitogent stop'
        else:
            cmd = 'systemctl stop xitogent'

        if not run_command(cmd):
            if is_stop_mode():
                print('Stopping Xitogent service failed.')
            return None

        if is_stop_mode():
            print('Xitogent stopped successfully.')


def reset_variables():
    localStorage.setItem('uptime', 0)
    localStorage.setItem('sent_sequences', 0)
    localStorage.setItem('failed_sequences', 0)


def is_restart_mode():
    if len(sys.argv) > 1 and sys.argv[1] == 'restart':
        return True
    return False


def restart():
    stop()
    start()


def is_status_mode():
    if len(sys.argv) > 1 and sys.argv[1] == 'status':
        return True
    return False


def show_xitogent_status():

    uptime = localStorage.getItem('uptime')

    if is_running() and uptime:
        uptime = time.strftime("%H:%M:%S", time.gmtime(int(time.time()) - int(uptime)))
    else:
        uptime = 0

    if is_device_paused():
        status = 'paused'
    elif is_running():
        status = 'running'
    else:
        status = 'stopped'

    sent_sequences = localStorage.getItem('sent_sequences')

    if not is_running() or not sent_sequences:
        sent_sequences = 0

    failed_sequences = localStorage.getItem('failed_sequences')

    if not is_running() or not failed_sequences:
        failed_sequences = 0

    print('%-30s' '%s' % ('Status', status))
    print('%-30s' '%s' % ('Uptime', uptime))
    print('%-30s' '%s' % ('Sent sequences', sent_sequences))
    print('%-30s' '%s' % ('Failed sequences', failed_sequences))

last_bw = {'time': '', 'value': ''}
last_disk_io = {'time': '', 'value': ''}


class Linux:

    @classmethod
    def fetch_system_info(cls):
        return {
            'hostname': cls.fetch_hostname(),
            'os': cls.get_os(),
            'uptime': cls.fetch_uptime(),
            'timezone': cls.get_timezone(),
            'cpu': {'model_name': cls.get_cpu_model_name(), 'total': cls.get_cpu_count()},
            'type': 'linux',
        }

    @staticmethod
    def fetch_hostname():

        p = subprocess.Popen('hostname', stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        stdout, stderr = p.communicate()

        # error
        if p.returncode != 0:
            if is_initial_test():
                return {'status': 'failed', 'message': stderr}
            return ''

        output = stdout.split(b"\n")

        return output[0].decode("utf-8")

    @staticmethod
    def get_os():
        try:
            if os.path.isfile('/etc/os-release'):
                with open("/etc/os-release", "r") as etclsbrel:
                    for line in etclsbrel:
                        m = re.compile(r"(?:PRETTY_NAME=\s*)\s*(.*)", re.I).search(line)
                        if m:
                            return m.group(1).replace('"', '')

            if (os.path.isfile('/etc/redhat-release')):
                with open("/etc/redhat-release", "r") as etclsbrel:
                    for line in etclsbrel:
                        return line.replace("\n", "")

        except Exception as e:
            if is_initial_test():
                return {'status': 'failed', 'message': e}
            pass

        return ''

    @staticmethod
    def get_timezone():

        p = subprocess.Popen('date "+%Z%z"', stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        stdout, stderr = p.communicate()

        # error
        if p.returncode != 0:
            if is_initial_test():
                return {'status': 'failed', 'message': stderr}
            return ''

        output = stdout.split(b"\n")

        return output[0].decode("utf-8")

    @staticmethod
    def get_cpu_model_name():
        try:
            with open('/proc/cpuinfo') as f:
                for line in f:
                    if line.strip() and line.rstrip('\n').startswith('model name'):
                        return line.rstrip('\n').split(':')[1]
        except Exception as e:
            if is_initial_test():
                return {'status': 'failed', 'message': e}
            pass

        return ''

    @staticmethod
    def get_cpu_count():

        p = subprocess.Popen('grep --count ^processor /proc/cpuinfo', stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        stdout, stderr = p.communicate()

        # error
        if p.returncode != 0:
            if is_initial_test():
                return {'status': 'failed', 'message': stderr}
            return 0

        output = stdout.split(b"\n")

        return output[0].decode("utf-8")

    @classmethod
    def fetch_uptime(cls):
        try:
            # python 2.6
            if sys.version_info[0] == 2 and sys.version_info[1] == 6:
                f = open('/proc/stat', 'r')
                for line in f:
                    if line.startswith(b'btime'):
                        boot_time = float(line.strip().split()[1])
                        return cls.convert_uptime_to_human_readable(boot_time)

            return cls.convert_uptime_to_human_readable(psutil.boot_time())

        except Exception as e:
            if is_initial_test():
                return {'status': 'failed', 'message': e}
            return ''

    @staticmethod
    def convert_uptime_to_human_readable(boot_time):

        seconds = time.time() - boot_time

        days = int(math.floor(seconds / 86400))

        seconds = seconds - (days * 86400)

        hours = int(math.floor(seconds / 3600))

        seconds = seconds - (hours * 3600)

        minutes = int(math.floor(seconds / 60))

        seconds = int(seconds - (minutes * 60))

        result = []

        if days > 0:
            result.append(str(days) + " days")

        if hours > 0:
            result.append(str(hours) + " hours")

        if minutes > 0:
            result.append(str(minutes) + " minutes")

        if seconds > 0:
            result.append(str(seconds) + " seconds")

        return ", ".join(result)

    @staticmethod
    def fetch_ips():

        p = subprocess.Popen('hostname -I', stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        stdout, stderr = p.communicate()

        # error
        if p.returncode != 0:
            if is_initial_test():
                return {'status': 'failed', 'message': stderr}
            return []

        ips = stdout.split()

        ips = [ip.decode("utf-8") for ip in ips]

        return ips

    @staticmethod
    def fetch_cpu_usage():

        try:
            result = {}

            sum = 0

            for i, usage_percent in enumerate(psutil.cpu_percent(interval=1, percpu=True)):
                usage_percent = "{0:.2f}".format(usage_percent)
                usage_percent = float(usage_percent)
                result['cpu' + str(i + 1)] = usage_percent
                sum += float(usage_percent)

            if len(result) > 0:
                result['average'] = sum / len(result)
                result['average'] = "{0:.2f}".format(result['average'])
                result['average'] = float(result['average'])
            else:
                result['average'] = 0

            return result
        except Exception as e:
            if is_initial_test():
                return {'status': 'failed', 'message': e}
            pass

        return {}

    @staticmethod
    def fetch_cpu_load_average():
        try:
            load_1_minute, load_5_minutes, load_15_minutes = map("{0:.2f}".format, os.getloadavg())
            return {'1min': float(load_1_minute), '5min': float(load_5_minutes), '15min': float(load_15_minutes)}
        except Exception as e:
            if is_initial_test():
                return {'status': 'failed', 'message': e}
            pass

        return {}

    @staticmethod
    def fetch_disk_usage():
        try:
            disks = {}

            for x in psutil.disk_partitions():
                disks[x.mountpoint] = {
                    "total": psutil.disk_usage(x.mountpoint).total,
                    "used": psutil.disk_usage(x.mountpoint).used,
                }

            return disks
        except Exception as e:
            if is_initial_test():
                return {'status': 'failed', 'message': e}
            pass

        return {}

    @classmethod
    def fetch_disk_io(cls):
        try:
            global last_disk_io

            if last_disk_io['value'] == '':
                disk_io_t1 = psutil.disk_io_counters(perdisk=True)
                time.sleep(1)
                disk_io_t2 = psutil.disk_io_counters(perdisk=True)
                last_disk_io = {'value': disk_io_t2, 'time': time.time()}
                return cls.calculate_disk_io_change(disk_io_t1, disk_io_t2)

            current_disk_io = psutil.disk_io_counters(perdisk=True)

            changed_disk_io = cls.calculate_disk_io_change(last_disk_io['value'], current_disk_io, last_disk_io['time'])

            last_disk_io = {'value': current_disk_io, 'time': time.time()}

            return changed_disk_io

        except Exception as e:
            if is_initial_test():
                return {'status': 'failed', 'message': e}
            pass

        return {}

    @classmethod
    def calculate_disk_io_change(cls, disk_io_t1, disk_io_t2, last_value_time=0):

        read_bytes_t1 = 0
        write_bytes_t1 = 0
        partitions_t1 = {}

        for name in disk_io_t1:
            if cls.is_local_partition(name):
                continue
            read_bytes_t1 += disk_io_t1[name].read_bytes
            write_bytes_t1 += disk_io_t1[name].write_bytes
            partitions_t1[name] = {
                'read_bytes': disk_io_t1[name].read_bytes,
                'write_bytes': disk_io_t1[name].write_bytes
            }

        read_bytes_t2 = 0
        write_bytes_t2 = 0
        disks = {}

        for name in disk_io_t2:

            if cls.is_local_partition(name):
                continue

            read_bytes_t2 += disk_io_t2[name].read_bytes
            write_bytes_t2 += disk_io_t2[name].write_bytes

            disk_read_bytes_t1 = partitions_t1[name]['read_bytes'] if name in partitions_t1 else 0

            changed_disk_read_bytes = disk_io_t2[name].read_bytes - disk_read_bytes_t1

            if changed_disk_read_bytes < 0:
                changed_disk_read_bytes = abs(changed_disk_read_bytes)

            if last_value_time != 0:
                changed_disk_read_bytes = changed_disk_read_bytes / (time.time() - last_value_time)

            disk_write_bytes_t1 = partitions_t1[name]['write_bytes'] if name in partitions_t1 else 0

            changed_disk_write_bytes = disk_io_t2[name].write_bytes - disk_write_bytes_t1

            if changed_disk_write_bytes < 0:
                changed_disk_write_bytes = abs(changed_disk_write_bytes)

            if last_value_time != 0:
                changed_disk_write_bytes = changed_disk_write_bytes / (time.time() - last_value_time)

            disks[name] = {
                'read': int(changed_disk_read_bytes),
                'write': int(changed_disk_write_bytes)
            }

        changed_read_bytes = read_bytes_t2 - read_bytes_t1

        if changed_read_bytes < 0:
            changed_read_bytes = abs(changed_read_bytes)

        if last_value_time != 0:
            changed_read_bytes = changed_read_bytes / (time.time() - last_value_time)

        changed_write_bytes = write_bytes_t2 - write_bytes_t1

        if changed_write_bytes < 0:
            changed_write_bytes = abs(changed_write_bytes)

        if last_value_time != 0:
            changed_write_bytes = changed_write_bytes / (time.time() - last_value_time)

        return {
            'read': int(changed_read_bytes),
            'write': int(changed_write_bytes),
            'partitions': disks
        }

    @staticmethod
    def is_local_partition(name):

        name = name.strip()

        name = name.lower()

        if name.startswith('loop') or name.startswith('ram'):
            return True

        return False

    @staticmethod
    def fetch_memory_usage():
        try:
            memory_stats = psutil.virtual_memory()
            return {
                'free': memory_stats.free,
                'used': memory_stats.used,
                'total': memory_stats.total,
                'cache': memory_stats.cached,
                'buffers': memory_stats.buffers,
            }
        except Exception as e:
            if is_initial_test():
                return {'status': 'failed', 'message': e}
            pass

        return {}

    @classmethod
    def fetch_network(cls):
        try:
            global last_bw

            if last_bw['value'] == '':
                interfaces_t1 = cls.fetch_current_bw()
                time.sleep(1)
                interfaces_t2 = cls.fetch_current_bw()
                last_bw = {'value': interfaces_t2, 'time': time.time()}
                return cls.calculate_bw_change(interfaces_t1, interfaces_t2)

            current_bw = cls.fetch_current_bw()

            changed_bw = cls.calculate_bw_change(last_bw['value'], current_bw, last_bw['time'])

            last_bw = {'value': current_bw, 'time': time.time()}

            return changed_bw

        except Exception as e:
            if is_initial_test():
                return {'status': 'failed', 'message': e}
            pass

        return {}

    @classmethod
    def fetch_current_bw(cls):

        # python 2.6
        if sys.version_info[0] == 2 and sys.version_info[1] == 6:
            return cls.bw_2_6()

        return psutil.net_io_counters(pernic=True)

    @staticmethod
    def calculate_bw_change(interfaces_t1, interfaces_t2, last_value_time=0):

        result = {}

        for name in interfaces_t2:

            if name == 'lo':
                continue

            bytes_sent_t2 = interfaces_t2[name].bytes_sent if name in interfaces_t2 else 0

            bytes_sent_t1 = interfaces_t1[name].bytes_sent if name in interfaces_t1 else 0

            sent = (bytes_sent_t2 - bytes_sent_t1) * 8

            if sent < 0:
                sent = abs(sent)

            if last_value_time != 0:
                sent = sent / (time.time() - last_value_time)

            bytes_received_t2 = interfaces_t2[name].bytes_recv if name in interfaces_t2 else 0

            bytes_received_t1 = interfaces_t1[name].bytes_recv if name in interfaces_t1 else 0

            received = (bytes_received_t2 - bytes_received_t1) * 8

            if received < 0:
                received = abs(received)

            if last_value_time != 0:
                received = received / (time.time() - last_value_time)

            result[name] = {'sent': int(sent), 'received': int(received)}

        return result

    @staticmethod
    def bw_2_6():
        try:
            with open("/proc/net/dev", 'r') as f:
                lines = f.readlines()

            retdict = {}

            for line in lines[2:]:

                colon = line.rfind(':')

                assert colon > 0, repr(line)

                name = line[:colon].strip()

                fields = line[colon + 1:].strip().split()

                # in
                (bytes_recv,
                 packets_recv,
                 errin,
                 dropin,
                 fifoin,  # unused
                 framein,  # unused
                 compressedin,  # unused
                 multicastin,  # unused
                 # out
                 bytes_sent,
                 packets_sent,
                 errout,
                 dropout,
                 fifoout,  # unused
                 collisionsout,  # unused
                 carrierout,  # unused
                 compressedout) = map(int, fields)

                retdict[name] = (bytes_sent, bytes_recv, packets_sent, packets_recv,
                                 errin, errout, dropin, dropout)

            rawdict = {}

            Interface = collections.namedtuple('snetio', ['bytes_sent', 'bytes_recv',
                                                          'packets_sent', 'packets_recv',
                                                          'errin', 'errout',
                                                          'dropin', 'dropout'])

            for nic, fields in retdict.items():
                rawdict[nic] = Interface(*fields)

            return rawdict
        except Exception as e:
            if is_initial_test():
                return {'status': 'failed', 'message': e}
            pass

        return {}

    @staticmethod
    def find_detected_softwares():

        try:
            softwares = [
                "nginx",
                "apache2",
                "sshd",
                "tomcat",
                "mariadb",
                "php-fpm",
                "mysqld",
                "httpd",
                "vsftpd",
                "mysql",
                "named",
                "csf",
                "memcached",
                "posgresql",
                "mongod",
                "postfix",
                "redis",
                "keydb",
                "varnish",
                "lighttpd",
                "lsws",
                "haproxy",
                "couchdb",
                "arangodb3",
                "ufw",
                "iptables",
                "firewalld",
                "dnsmasq"
            ]

            p1 = subprocess.Popen("ps aux", stdout=subprocess.PIPE, shell=True)
            p2 = subprocess.Popen(
                "egrep '" + "(" + "|".join(softwares) + ")" + "'",
                stdin=p1.stdout,
                stdout=subprocess.PIPE,
                shell=True
            )

            temp = p2.communicate()[0]

            lines = temp.split(b"\n")

            detected_softwares = []

            for software in softwares:
                for line in lines:
                    line = line.decode("utf-8")
                    if re.search(software, line) and not re.search( "\(" + "\|".join(softwares) + "\)", line):
                        detected_softwares.append(software)
                        break

            return detected_softwares
        except Exception as e:
            if is_initial_test():
                return {'status': 'failed', 'message': e}
            pass

        return []

    @staticmethod
    def find_top_five_memory_consumer_processes():

        try:
            p1 = subprocess.Popen(['ps', '-eo', 'pmem,pid,cmd', '--no-headers'], stdout=subprocess.PIPE)

            p2 = subprocess.Popen(['sort', '-k', '1', '-rn'], stdin=p1.stdout, stdout=subprocess.PIPE)

            p3 = subprocess.Popen(['head', '-5'], stdin=p2.stdout, stdout=subprocess.PIPE)

            temp = p3.communicate()[0]

            output = temp.split(b"\n")

            processes = []

            for row in output:

                if not row:
                    continue

                row = row.decode("utf-8")

                temp = row.split()

                if len(temp) > 3:
                    cmd = " ".join(temp[2:(len(temp))])
                else:  # command has no option or argument
                    cmd = temp[2]

                processes.append(
                    {
                        'memory_usage': temp[0],
                        'pid': temp[1],
                        'cmd': cmd,
                    }
                )

            return processes
        except Exception as e:
            if is_initial_test():
                return {'status': 'failed', 'message': e}
            pass

        return []

    @staticmethod
    def find_top_five_cpu_consumer_processes():

        try:
            p1 = subprocess.Popen(['ps', '-eo', 'pcpu,pid,cmd', '--no-headers'], stdout=subprocess.PIPE)

            p2 = subprocess.Popen(['sort', '-k', '1', '-rn'], stdin=p1.stdout, stdout=subprocess.PIPE)

            p3 = subprocess.Popen(['head', '-5'], stdin=p2.stdout, stdout=subprocess.PIPE)

            temp = p3.communicate()[0]

            output = temp.split(b"\n")

            processes = []

            for row in output:

                if not row:
                    continue

                row = row.decode("utf-8")

                temp = row.split()

                if len(temp) > 3:
                    cmd = " ".join(temp[2:(len(temp))])
                else:  # command has no option or argument
                    cmd = temp[2]

                processes.append(
                    {
                        'cpu_usage': temp[0],
                        'pid': temp[1],
                        'cmd': cmd,
                    }
                )

            return processes
        except Exception as e:
            if is_initial_test():
                return {'status': 'failed', 'message': e}
            pass

        return []

    @classmethod
    def fetch_data(cls):
        return {
            'description': cls.fetch_system_info(),
            'statistics': {
                'cpu_load_average': cls.fetch_cpu_load_average(),
                'cpu_usage': cls.fetch_cpu_usage(),
                'memory_usage': cls.fetch_memory_usage(),
                'disk_usage': cls.fetch_disk_usage(),
                'disk_io': cls.fetch_disk_io(),
                'network': cls.fetch_network(),
            },
            'ips': cls.fetch_ips(),
            'softwares': cls.find_detected_softwares(),
            'processes': {
                'cpu_consumer': cls.find_top_five_cpu_consumer_processes(),
                'memory_consumer': cls.find_top_five_memory_consumer_processes(),
            },
        }


if is_show_commands_mode():
    show_commands()

if is_version_mode():
    show_xitogent_version()

if is_initial_test():
    get_device_status()

if is_add_device():
    add_device()

if is_start_mode():
    start()

if is_force_update():
    force_update()

if is_new_xitogent_test():
    test_new_xitogent()

if is_uninstall():
    uninstall()

if is_pause_mode():
    pause()

if is_unpause_mode():
    unpause()

if is_status_mode():
    show_xitogent_status()

if is_stop_mode():
    stop()

if is_restart_mode():
    restart()
