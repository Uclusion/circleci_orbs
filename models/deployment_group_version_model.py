from pynamodb.attributes import UnicodeAttribute
from pynamodb.models import Model


class DeploymentGroupVersionModel(Model):
    class Meta():
        table_name = 'uclusion-sso-dev-deployment-group-versions'
        region = 'us-west-2'
        host = 'https://dynamodb.us-west-2.amazonaws.com'

    deployment_group = UnicodeAttribute(hash_key=True, null=False)
    ui_url = UnicodeAttribute(null=False)
    version = UnicodeAttribute(null=False)
