import logging
import sys
import getopt
from models.releases_model import ReleasesModel
from utils.constants import rest_api_backend_repos


logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()


def testing_record(num_failing, env_name):
    for repo in rest_api_backend_repos:
        latest_release = None
        for release in ReleasesModel.query(repo, filter_condition=ReleasesModel.env_name == env_name):
            if latest_release is None or latest_release.created_at < release.created_at:
                latest_release = release
        if latest_release is None:
            logger.warning('Latest release not found '+ repo)
        latest_release.num_failing = num_failing
        latest_release.save()


usage = 'python -m utils.record_testing -n $NUMFAILING -e env'


def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'h:n:e:', ['numfailing=', 'env='])
    except getopt.GetoptError:
        logger.info(usage)
        sys.exit(2)
    num_failing = None
    env_name = None
    for opt, arg in opts:
        if opt == '-h':
            logger.info(usage)
            sys.exit()
        elif opt in ('-n', '--numfailing'):
            num_failing = int(arg)
        elif opt in ('-e', '--env'):
            env_name = arg
    if num_failing is None or env_name is None:
        logger.info(usage)
        sys.exit(2)
    testing_record(num_failing, env_name)


if __name__ == "__main__":
    main(sys.argv[1:])
