import sys
import getopt
import logging
from github import Github


logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()


rest_api_backend_repos = ['uclusion_async', 'uclusion_investibles', 'uclusion_investible_api', 'uclusion_markets',
                          'uclusion_market_api', 'uclusion_shared_resources', 'uclusion_sso', 'uclusion_team_api',
                          'uclusion_users', 'uclusion_user_api', 'uclusion_webhooks', 'uclusion_common',
                          'uclusion_backend_common', 'common_lambda_dependencies']


def tag_all_repos(g, release, tag_prefix):
    for repo in g.get_user().get_repos():
        if repo.name in rest_api_backend_repos:
            ref = repo.get_git_ref('heads/master')
            tags = repo.get_tags()
            found = False
            for tag in tags:
                if tag_prefix in tag.name and tag.commit.sha == ref.object.sha:
                    logger.info('Skipping ' + repo.name)
                    found = True
                    break
            if not found:
                # See https://github.com/PyGithub/PyGithub/blob/master/github/Repository.py
                logger.info('Creating release for ' + repo.name)
                repo.create_git_tag_and_release(release.tag_name, 'Across repos tag', release.title, release.body,
                                                ref.object.sha, ref.object.type)


def check_repo(g, tag_prefix, repo_full_name):
    repo = g.get_repo(repo_full_name, lazy=False)
    ref = repo.get_git_ref('heads/master')
    tags = repo.get_tags()
    for tag in tags:
        if tag_prefix in tag.name and tag.commit.sha == ref.object.sha:
            return 0
    logger.info('Suggesting release for ' + repo.name)
    return 1


usage = 'github_utils.py -u user -p some_password'


def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'h:u:p:r:', ['user=', 'password=', 'repo='])
    except getopt.GetoptError:
        logger.info(usage)
        sys.exit(2)
    user = None
    password = None
    repo = None
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
    if user is None or password is None:
        logger.info(usage)
        sys.exit(2)
    g = Github(user, password)
    developer_stuff = g.get_repo('Uclusion/developer_stuff', lazy=False)
    release = developer_stuff.get_latest_release()
    tag_prefix = release.tag_name.partition('.')[0]
    if repo is not None:
        sys.exit(check_repo(g, tag_prefix, repo))
    tag_all_repos(g, release, tag_prefix)


if __name__ == "__main__":
    main(sys.argv[1:])
