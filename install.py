from threading import Thread

import subprocess
import os
import download_binary


def main():
    config = subprocess.call(['python', 'config.py', '--size=720x350'])
    if config is 0:
        download_bin = Thread(target = download_binary.main)
        download_bin.start()
        download = subprocess.call(['python', 'binary.py', '--size=720x350'])
        if download is 0:
            #download_bin.stop()
            end = subprocess.call(['python', 'end.py', '--size=720x350'])


if __name__ == '__main__':
    main()