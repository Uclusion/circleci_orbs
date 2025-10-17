rest_api_backend_repos = ['uclusion_async', 'uclusion_investible_api', 'uclusion_markets',
                          'uclusion_market_api', 'uclusion_shared_resources', 'uclusion_sso', 'uclusion_users',
                          'uclusion_user_api', 'uclusion_websockets', 'uclusion_common', 'uclusion_test_api',
                          'uclusion_backend_common', 'uclusion_summaries', 'common_lambda_dependencies']

env_to_blessed_tag_prefixes = {
    'development': 'stage_blessed',
    'stage': 'production_blessed',
    'production': 'production_passed'
}

env_to_buildable_tag_prefixes = {
    'development': 'dev_backend', #techinically this is already built, but unifies some code in printing the last blessed
    'stage': 'stage_blessed',
    'production': 'production_blessed'

}
env_to_candidate_tag_prefixes = {
    'development': 'dev_backend',
    'stage': 'stage_backend',
    'production': 'production_backend',
}

env_to_build_tag_prefix = {
    'development': 'dev_backend',
    'stage': 'stage_backend',
    'production' : 'production_backend'
}