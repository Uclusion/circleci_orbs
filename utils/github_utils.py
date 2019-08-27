import sys
import getopt
import logging
from github import Github
from datetime import datetime
from models.releases_model import ReleasesModel
from utils.constants import rest_api_backend_repos

logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()


def get_latest_release(repo):
    latest_release = None
    for db_release in ReleasesModel.query(repo.name):
        if latest_release is None or latest_release.created_at < db_release.created_at:
            latest_release = db_release
    return latest_release


def tag_all_repos(g, release, tag_prefix):
    now = datetime.now()
    unique_release_suffix = now.strftime("%m_%d_%Y_%H_%M_%S")
    for repo in g.get_user().get_repos():
        if repo.name in rest_api_backend_repos:
            ref = repo.get_git_ref('heads/master')
            tags = repo.get_tags()
            latest_release = get_latest_release(repo)
            found = False
            for tag in tags:
                if tag_prefix in tag.name and tag.commit.sha == ref.object.sha and latest_release is not None \
                        and latest_release.tag_name == tag.name:
                    logger.info('Skipping ' + repo.name)
                    found = True
                    break
            if not found:
                # See https://github.com/PyGithub/PyGithub/blob/master/github/Repository.py
                logger.info('Creating release for ' + repo.name)
                repo.create_git_tag_and_release(release.tag_name + '_' + unique_release_suffix, 'Across repos tag',
                                                release.title, release.body, ref.object.sha, ref.object.type)


def check_repo(g, tag_prefix, repo_full_name):
    repo = g.get_repo(repo_full_name, lazy=False)
    latest_release = get_latest_release(repo)
    if latest_release is not None:
        logger.info('Latest release is ' + latest_release.tag_name)
    else:
        logger.info('No latest release')
    ref = repo.get_git_ref('heads/master')
    logger.info('Latest sha is ' + ref.object.sha)
    tags = repo.get_tags()
    for tag in tags:
        if tag_prefix in tag.name and tag.commit.sha == ref.object.sha and latest_release is not None \
                and latest_release.tag_name in tag.name:
            logger.info('Suggesting skipping ' + repo.name)
            return 0
    logger.info('Suggesting release for ' + repo.name)
    return 1


def check_in(g, file_path, file_content, repo_full_name):
    repo = g.get_repo(repo_full_name, lazy=False)
    file = repo.get_file_contents(file_path)  # This is just to get the file.sha
    repo.update_file(file_path, 'Updating file ' + file_path, file_content, file.sha)
    return 1


usage = 'python -m utils.github_utils -u user -p some_password'


def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'h:u:p:r:', ['user=', 'password=', 'repo=', 'file=', 'content='])
    except getopt.GetoptError:
        logger.info(usage)
        sys.exit(2)
    user = None
    password = None
    repo = None
    file = None
    content = None
    for opt, arg in opts:
        if opt == '-h':
            logger.info(usage)
            sys.exit()
        elif opt in ('-u', '--user'):
            user = arg
        elif opt in ('-p', '--password'):
            password = arg
        elif opt in ('-r', '--repo'):
            repo = arg
        elif opt in ('-f', '--file'):
            file = arg
        elif opt in ('-c', '--content'):
            content = arg
    if user is None or password is None:
        logger.info(usage)
        sys.exit(2)
    g = Github(user, password)
    developer_stuff = g.get_repo('Uclusion/developer_stuff', lazy=False)
    release = developer_stuff.get_latest_release()
    tag_prefix = release.tag_name.partition('.')[0]
    if file is not None:
        check_in(g, file, content, repo)
    elif repo is not None:
        if check_repo(g, tag_prefix, repo) == 1:
            file = open('release.txt', 'w')
            file.write('marker to avoid circleci conditional nonsense')
            file.close()
    else:
        tag_all_repos(g, release, tag_prefix)


if __name__ == "__main__":
    main(sys.argv[1:])
