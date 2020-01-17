#!/usr/bin/env bash

ENV_NAME=$1
GITHUB_USER=$2
GITHUB_PASSWORD=$3
LOCK_FILE=$4

function build_common() {
    cd ~/circleci_orbs
    local REPO_NAME=$1
    RELEASE=`python -m scripts.print_last_blessed_release -e $ENV_NAME -g $GITHUB_USER -p $GITHUB_PASSWORD -r $REPO_NAME`
    if [[ "$RELEASE" != "skip" ]]; then
        cd ~/
        git clone git@github.com:Uclusion/$REPO_NAME.git
        cd $REPO_NAME
        git checkout $RELEASE
        PY_DIR='build/python/lib/python3.7/site-packages'
        mkdir -p $PY_DIR
        pip install --no-deps . -t $PY_DIR
        serverless deploy
        return "build"
    fi
    return "skip"
}

function build_common_dependencies() {
    RELEASE=`python -m scripts.print_last_blessed_release -e $ENV_NAME -g $GITHUB_USER -p $GITHUB_PASSWORD -r common_lambda_dependencies`
    if [[ "$RELEASE" != "skip" ]]; then
        cd ~/
        git clone git@github.com:Uclusion/common_lambda_dependencies.git
        cd common_lambda_dependencies
        git checkout $RELEASE
        PY_DIR='build/python/lib/python3.7/site-packages'
        mkdir -p $PY_DIR
        pip install -r $LOCK_FILE -t $PY_DIR
        pip freeze --path $PY_DIR > ${ENV_NAME}_requirements.txt
        serverless deploy
        return "build"
    fi
    return "skip"
}

function update_layers() {
    cd ~/circleci_orbs/utils
    python utils.py -r us-west-2 -s dev
}

BACKEND_COMMON=$(build_common "uclusion_backend_common")
COMMON=$(build_common "uclusion_common")
COMMON_DEPENDENCIES=$(build_common_dependencies)

if ["$BACKEND_COMMON" != "skip" ] || ["$COMMON" != "skip" ] || ["$COMMON_DEPENDENCIES" != "skip" ]; then
   echo "Updating Layers"
   update_layers
fi


