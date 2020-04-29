import logging
import os
import subprocess
import sys
import getopt


logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()


def invoke_reports(directory):
    files = os.listdir(directory)
    for raw_file_name in files:
        file_name = raw_file_name.rstrip()
        if file_name.endswith(".py"):
            logger.info(f"Running {file_name}")
            response = subprocess.run(['python', f"{directory}/{file_name}", '1>&2'])
            logger.info(f"Return code is {response.returncode}")
            response.check_returncode()


usage = 'python -m utils.run_reports -d run_directory'


def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'h:d:', ['dir='])
    except getopt.GetoptError:
        logger.info(usage)
        sys.exit(2)
    directory = None
    for opt, arg in opts:
        if opt == '-h':
            logger.info(usage)
            sys.exit()
        elif opt in ('-d', '--dir'):
            directory = arg
    if directory is None or file is None:
        logger.info(usage)
        sys.exit(2)
    invoke_reports(directory)


if __name__ == "__main__":
    main(sys.argv[1:])
