import logging
import os
import subprocess
import sys
import getopt


logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()


def invoke_scripts(directory, record_file_path):
    already_ran = {}
    with open(record_file_path, 'r') as record_file:
        for line in record_file:
            logger.info(f"Marking already ran for {line}")
            already_ran[line] = True
    lines = []
    files = os.listdir(directory)
    for file_name in files:
        if file_name.endswith(".py"):
            if file_name not in already_ran:
                logger.info(f"Running {file_name}")
                response = subprocess.run(['python', f"{directory}/{file_name}", '1>&2'])
                logger.info(f"Return code is {response.returncode}")
                response.check_returncode()
            lines.append(file_name+"\n")
    with open(record_file_path, 'w') as f:
        f.writelines(lines)


usage = 'python -m utils.run_scripts -d run_directory -f ran_file'


def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'h:d:f:', ['dir=', 'file='])
    except getopt.GetoptError:
        logger.info(usage)
        sys.exit(2)
    directory = None
    file = None
    for opt, arg in opts:
        if opt == '-h':
            logger.info(usage)
            sys.exit()
        elif opt in ('-d', '--dir'):
            directory = arg
        elif opt in ('-f', '--file'):
            file = arg
    if directory is None or file is None:
        logger.info(usage)
        sys.exit(2)
    invoke_scripts(directory, file)


if __name__ == "__main__":
    main(sys.argv[1:])
