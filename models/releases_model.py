from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute
from pynamodb.models import Model


class ReleasesModel(Model):
    class Meta:
        table_name = 'Releases'
        region = 'us-west-2'
        host = 'https://dynamodb.us-west-2.amazonaws.com'

    repo_name = UnicodeAttribute(hash_key=True, null=False)
    tag_name = UnicodeAttribute(range_key=True, null=False)
    env_name = UnicodeAttribute(null=False)
    created_at = UTCDateTimeAttribute(null=False)
