import logging
import sys
import getopt
from github import Github
from models.releases_model import ReleasesModel
from utils.constants import rest_api_backend_repos


logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()


def get_releases():
    releases = []
    for repo in rest_api_backend_repos:
        latest_release = None
        for release in ReleasesModel.query(repo, filter_condition=ReleasesModel.env_name == 'dev'):
            if latest_release is None or latest_release.created_at < release.created_at:
                latest_release = release
        releases.append(latest_release)
    return releases


def get_tag(repo, tag_name):
    tags = repo.get_tags()
    for tag in tags:
        if tag.name == tag_name:
            return tag
    return None


usage = 'python -m utils.bless_status -u user -p some_password'


def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'h:u:p:', ['user=', 'password='])
    except getopt.GetoptError:
        logger.info(usage)
        sys.exit(2)
    user = None
    password = None
    for opt, arg in opts:
        if opt == '-h':
            logger.info(usage)
            sys.exit()
        elif opt in ('-u', '--user'):
            user = arg
        elif opt in ('-p', '--password'):
            password = arg
    if user is None or password is None:
        logger.info(usage)
        sys.exit(2)
    g = Github(user, password)
    for release in get_releases():
        repo = g.get_repo('Uclusion/' + release.repo_name, lazy=False)
        ref = repo.get_git_ref('heads/master')
        tag = get_tag(repo, release.tag_name)
        if tag.commit.sha != ref.object.sha:
            logger.info('Undeployed repo is ' + release.repo_name)
            logger.info('Latest deployed tag name is ' + release.tag_name)
        if release.num_failing is None:
            logger.info('Untested repo is ' + release.repo_name)
            continue
        if release.num_failing > 0:
            logger.info('Failing repo is ' + release.repo_name)
        logger.info('Repo ' + release.repo_name + ' deployed at ' + str(release.created_at) + ' was tested.')


if __name__ == "__main__":
    main(sys.argv[1:])
