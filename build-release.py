import os
import sys
import requests
import json
import shutil
import logging as log
import glob
import platform
import time

WORK_DIR = os.getcwd()
ARTIFACTS_DIR = os.path.join(WORK_DIR, 'artifacts')
BIN_DIR = os.path.join(WORK_DIR, 'bin')
HTTP = requests.Session()


def system(cmd):
    res = os.system(cmd)
    if res != 0:
        log.error(f'CMD: {cmd} failed with error code: {res}')


def is_windows():
    return sys.platform.startswith('win32')


def is_macos():
    return sys.platform.startswith('darwin')


def tag_trigger():
    return os.environ['GITHUB_REF'].startswith('refs/tags')


def get_executable_name(app_name):
    if is_windows():
        return app_name + '.exe'
    return app_name


def get_src_dir_path(app_name):
    globs = glob.glob(os.path.join(WORK_DIR, f'EXCCoin-{app_name}-*'))
    if len(globs) == 0:
        return False
    return globs[0]


def download_latest_release(repository):
    src_dir = get_src_dir_path(repository)
    if src_dir is not False:
        return

    if not tag_trigger():
        zipball_url = f'https://api.github.com/repos/EXCCoin/{repository}/zipball'
    else:
        r = HTTP.get(f'https://api.github.com/repos/EXCCoin/{repository}/releases/latest')
        if r.status_code != 200:
            raise NotImplementedError('No releases found')
        release_info = json.loads(r.content)
        zipball_url = release_info['zipball_url']

    for i in range(5):
        try:
            r = HTTP.get(zipball_url)
            archive_path = os.path.join(WORK_DIR, 'repository.zip')
            with open(archive_path, 'wb') as fd:
                fd.write(r.content)
                shutil.unpack_archive(archive_path, WORK_DIR)
                os.remove(archive_path)
                return
        except Exception:
            log.warning(f'Downloading {repository} failed. Waiting 8 sec before retry...')
            time.sleep(8)
            pass


def build_go_app(app_name, dst_path):
    src_dir = get_src_dir_path(app_name)
    os.chdir(src_dir)
    if is_macos():
        system('go build -ldflags="-s -w"')
    else:
        system('go build -ldflags="-s -w -extldflags -static"')
    artifact_path = os.path.join(src_dir, get_executable_name(app_name))
    dst_file_path = os.path.join(dst_path, get_executable_name(app_name))
    shutil.copyfile(artifact_path, dst_file_path)
    if not is_windows():
        os.chmod(dst_file_path, 0o755)
    os.chdir(WORK_DIR)


def setup():
    if is_windows():
        os.environ['PATH'] = 'C:\\msys64\\mingw64\\bin;%PATH%;C:\\msys64\\usr\\bin;' + os.environ['PATH']

    log.info('Creating directories')
    if not os.path.exists(ARTIFACTS_DIR):
        os.mkdir(ARTIFACTS_DIR)
    if not os.path.exists(BIN_DIR):
        os.mkdir(BIN_DIR)


if __name__ == '__main__':
    log.basicConfig(level=log.DEBUG)

    if 'GITHUB_TOKEN' in os.environ:
        log.info('GitHub token detected')
        HTTP.headers.update({'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN']})

    log.info('Build start')
    os.chdir(WORK_DIR)
    setup()

    for i in range(5):
        log.info('Downloading exilibirum')
        download_latest_release('exilibrium')
        exilibirum_dir = get_src_dir_path('exilibrium')
        if exilibirum_dir is not False:
            break
        time.sleep(2)

    exilibrium_bin_dir = os.path.join(exilibirum_dir, 'bin')
    if not os.path.exists(exilibrium_bin_dir):
        os.mkdir(exilibrium_bin_dir)

    for goapp in ['exccd', 'exccwallet', 'exccctl']:
        log.info(f'Downloading {goapp}')
        download_latest_release(goapp)
        log.info(f'Building {goapp}')
        build_go_app(goapp, exilibrium_bin_dir)

    if sys.platform == 'darwin':
        artifact_suffix = "macosx-" + platform.machine()
    else:
        artifact_suffix = sys.platform + '-' + platform.machine()

    log.info('Archiving excc-binaries')
    os.chdir(ARTIFACTS_DIR)
    shutil.make_archive('excc-binaries-' + artifact_suffix, format='zip', root_dir=exilibrium_bin_dir)
    os.chdir(WORK_DIR)

    log.info('Building exilibrium')
    os.chdir(get_src_dir_path('exilibrium'))
    if is_windows():
        link = os.environ['WINDOWS_CSC_LINK']
        password = os.environ['WINDOWS_CSC_KEY_PASSWORD']
        system(f'sh package_win.sh "{link}" "{password}"')
    elif is_macos():
        version = osx_arch = os.environ['MACOS_ARCHITECTURE']
        identity = os.environ['MACOS_IDENTITY']
        system(f'sh package_macos.sh "{version}" "{identity}" "{osx_arch}"')
    else:
        system('sh package_linux.sh')
    os.chdir(WORK_DIR)

    exilibrium_dist_dir = os.path.join(get_src_dir_path('exilibrium'), 'release')
    for artifact in glob.glob(os.path.join(exilibrium_dist_dir, '*.*')):
        _, extension = os.path.splitext(artifact)
        if extension not in ['.yml', '.blockmap']:
            shutil.copyfile(artifact, os.path.join(ARTIFACTS_DIR, 'exilibrium-' + artifact_suffix + extension))
