from utils.constants import rest_api_backend_repos
import sys


def get_latest_release_with_prefix(releases, prefix):
    latest = None
    latest_date = None
    for release in releases:
        if release.tag_name.startswith(prefix):
            created_at = release.created_at
            if latest is None or created_at > latest_date:
                latest = release
                latest_date = created_at
    return latest


def find_latest_release_with_prefix(repo, prefix):
    releases = repo.get_releases()
    latest_release = get_latest_release_with_prefix(releases, prefix)
    if not latest_release:
        print("Couldn't get a release with prefix " + prefix + " for " + repo.name)
        sys.exit(3)
    return latest_release


def get_latest_releases_with_prefix(github, prefix, repo_name=None):
    if repo_name:
        repos_to_search = [repo_name]
    else:
        repos_to_search = rest_api_backend_repos
    candidates = []
    for repo in github.get_user().get_repos():
        if repo.name in repos_to_search:
            latest_release = find_latest_release_with_prefix(repo, prefix)
            candidates.append([repo, latest_release])
    if len(candidates) != len(repos_to_search):
        print("Some repos are missing tags")
        sys.exit(5)
    return candidates


def clone_release(repo, old_release, new_name):
    # get the tag for the release
    tag = None
    for candidate in repo.get_tags():
        if candidate.name == old_release.tag_name:
            tag = candidate
            break
    if not tag:
        sys.exit(4)
    sha = tag.commit.sha
    repo.create_git_tag_and_release(new_name, 'Blessed build tag', new_name, 'Blessed', sha, 'commit')


def release_head(github, dest_tag_name, repo_name=None):
    if repo_name:
        repos_to_search = [repo_name]
    else:
        repos_to_search = rest_api_backend_repos

    for repo in github.get_user().get_repos():
        if repo.name in repos_to_search:
            head = repo.get_git_ref('heads/master')
            print("Will clone head of " + repo.name +" to " + dest_tag_name)
            sha = head.object.sha
            repo.create_git_tag_and_release(dest_tag_name, 'Head Build', dest_tag_name, 'Head', sha, 'commit')


def clone_latest_releases_with_prefix(github, source_prefix, dest_tag_name, repo_name=None):
    print("Cloning releases")
    candidates = get_latest_releases_with_prefix(github, source_prefix, repo_name)
    for candidate in candidates:
        repo = candidate[0]
        release = candidate[1]
        print("Will clone " + release.tag_name + " in repo " + repo.name + " to " + dest_tag_name)
        clone_release(repo, release, dest_tag_name)
