import sys
import getopt
import logging
from github import Github


logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()

rest_api_backend_non_layer_repos = ['uclusion_async', 'uclusion_investibles', 'uclusion_investible_api',
                                    'uclusion_markets', 'uclusion_market_api', 'uclusion_shared_resources',
                                    'uclusion_sso', 'uclusion_team_api', 'uclusion_users', 'uclusion_user_api',
                                    'uclusion_webhooks']


def tag_all_repos(user, tag_name):
    # TODO Need password from https://circleci.com/gh/organizations/Uclusion/settings#contexts CircleCI context
    # variable and passed in or same idea with access token g = Github("access_token")
    g = Github(user, 'Uclusi0n_test')

    # Then play with your Github objects:
    for repo in g.get_user().get_repos():
        if repo.name in rest_api_backend_non_layer_repos:
            ref = repo.get_git_ref('heads/master')
            # See https://github.com/PyGithub/PyGithub/blob/master/github/Repository.py
            git_tag = repo.create_git_tag(tag_name, 'Across repos tag', ref.object.sha, ref.object.type)
            print('Creating tag for ' + repo.name)
            repo.create_git_ref('refs/tags/' + git_tag.tag, git_tag.sha)


usage = 'github_utils.py -u user -t v0.0.1'


def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'h:u:t:', ['user=', 'tagname='])
    except getopt.GetoptError:
        logger.info(usage)
        sys.exit(2)
    user = None
    tag_name = None
    for opt, arg in opts:
        if opt == '-h':
            logger.info(usage)
            sys.exit()
        elif opt in ('-u', '--user'):
            user = arg
        elif opt in ('-t', '--tagname'):
            tag_name = arg
    if user is None:
        logger.info(usage)
        sys.exit(2)
    return tag_all_repos(user, tag_name)


if __name__ == "__main__":
    main(sys.argv[1:])
