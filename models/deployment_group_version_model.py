from pynamodb.attributes import UnicodeAttribute
from pynamodb.models import Model


class DeploymentGroupVersionModel(Model):
    class Meta():
        table_name = 'uclusion-sso-dev-deployment-group-versions'
        region = 'us-west-2'
        host = 'https://dynamodb.us-west-2.amazonaws.com'

    deployment_group = UnicodeAttribute(hash_key=True, null=False)
    ui_url = UnicodeAttribute(null=False)
    app_version = UnicodeAttribute(null=False)
    # J-all-314 the version that last required each action, persisted across releases so
    # users who skip that release still see the mismatch when they next return
    cache_clear_version = UnicodeAttribute(null=True)
    script_reinstall_version = UnicodeAttribute(null=True)
