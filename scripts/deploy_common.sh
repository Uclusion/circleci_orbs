#!/usr/bin/env bash

ENV_NAME=$1
GITHUB_TOKEN=$2
LOCK_FILE=$3

function build_common() {
    cd utils_repo
    local REPO_NAME=$1
    RELEASE=`python -m scripts.print_release_build_needed -e $ENV_NAME -a $GITHUB_TOKEN -r $REPO_NAME`
    if [[ "$RELEASE" != "skip" ]]; then
        cd ..
        git clone git@github.com:Uclusion/$REPO_NAME.git
        cd $REPO_NAME
        git checkout $RELEASE
        PY_DIR='build/python/lib/python3.9/site-packages'
        mkdir -p $PY_DIR
        pip install --no-deps . -t $PY_DIR
        ../node_modules/serverless/bin/serverless.js deploy
        echo build
    else
        echo skip
    fi
    cd ..
}

function build_common_dependencies() {
    cd utils_repo
    RELEASE=`python -m scripts.print_release_build_needed -e $ENV_NAME -a $GITHUB_TOKEN -r common_lambda_dependencies`
    if [[ "$RELEASE" != "skip" ]]; then
        git clone git@github.com:Uclusion/common_lambda_dependencies.git
        cd common_lambda_dependencies
        git checkout $RELEASE
        PY_DIR='build/python/lib/python3.9/site-packages'
        mkdir -p $PY_DIR
        pip install -r $LOCK_FILE -t $PY_DIR
        pip freeze --path $PY_DIR > ${ENV_NAME}_requirements.txt
        ../node_modules/serverless/bin/serverless.js deploy
        cd ../utils_repo
        python -m utils.github_update_file -f ~/common_lambda_dependencies/${ENV_NAME}_requirements.txt -i ${ENV_NAME}_requirements.txt -r common_lambda_dependencies -a ${GITHUB_TOKEN}
        echo build
    else
        echo skip
    fi
    cd ..
}

function update_layers() {
    cd utils_repo
    python -m scripts.build_blessed -e $ENV_NAME -a $GITHUB_TOKEN -b true
    cd ..
}

BACKEND_COMMON=$(build_common "uclusion_backend_common")
echo $BACKEND_COMMON
COMMON=$(build_common "uclusion_common")
echo $COMMON
COMMON_DEPENDENCIES=$(build_common_dependencies)
echo $COMMON_DEPENDENCIES
if [[ "$BACKEND_COMMON" != "skip" ]] || [[ "$COMMON" != "skip" ]] || [[ "$COMMON_DEPENDENCIES" != "skip" ]]; then
  if [[ "$ENV_NAME" == "development" ]]; then
    echo "Updating Layers"
    update_layers
  else
    echo "Layers will be updated when deploy Lambdas"
  fi
else
    echo "Layers up to date"
fi


