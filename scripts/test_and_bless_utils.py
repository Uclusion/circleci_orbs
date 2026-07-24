def get_test_script(env_name):
    if env_name == 'development':
        return 'testIntegration'
    return 'test' + env_name.capitalize()
