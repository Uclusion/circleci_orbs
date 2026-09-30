# circleci_orbs
The collection of reusable CircleCI configurations

## Repos not at master

From this directory, with `gh` authenticated or `GITHUB_TOKEN` set:

```sh
.venv/bin/python -m scripts.print_repos_not_at_master -e stage
.venv/bin/python -m scripts.print_repos_not_at_master -e production
```

Pass `-a github_token` to supply a token directly. The exit code is 1 when any repo differs from master.
