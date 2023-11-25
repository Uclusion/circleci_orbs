import logging
import sys
from pynamodb.attributes import UnicodeAttribute
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from pynamodb.models import Model
from ucommon.utils.utils import invoke_lambda_async, get_machine_capability


logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()
region_name = 'us-west-2'


class UserModel(Model):
    class Meta():
        table_name = 'uclusion-users-dev-users'
        region = region_name
        host = 'https://dynamodb.us-west-2.amazonaws.com'

    external_id = UnicodeAttribute(hash_key=True, null=False)
    account_id = UnicodeAttribute(range_key=True, null=False)
    email = UnicodeAttribute(null=True)
    id = UnicodeAttribute(null=False)


class AccountModel(Model):
    class Meta():
        table_name = 'uclusion-users-dev-accounts'
        region = region_name
        host = 'https://dynamodb.us-west-2.amazonaws.com'

    id = UnicodeAttribute(hash_key=True, null=False)


class UserCapabilityModel(Model):
    class Meta():
        table_name = 'uclusion-users-dev-users-capabilities'
        region = region_name
        host = 'https://dynamodb.us-west-2.amazonaws.com'
    user_id = UnicodeAttribute(hash_key=True, null=False)
    type_object_id = UnicodeAttribute(range_key=True, null=False)


class MarketModel(Model):
    class Meta():
        table_name = 'uclusion-markets-dev-markets'
        region = region_name
        host = 'https://dynamodb.us-west-2.amazonaws.com'
    id = UnicodeAttribute(hash_key=True, null=False)
    account_id = UnicodeAttribute(null=False)


class MarketsIndex(GlobalSecondaryIndex):
    class Meta:
        region = region_name
        host = 'https://dynamodb.us-west-2.amazonaws.com'
        read_capacity_units = 1
        write_capacity_units = 1
        projection = AllProjection()
    market_id = UnicodeAttribute(hash_key=True)


class StageModel(Model):
    class Meta():
        table_name = 'uclusion-markets-dev-stages'
        region = region_name
        host = 'https://dynamodb.us-west-2.amazonaws.com'
    id = UnicodeAttribute(hash_key=True, null=False)
    market_id = UnicodeAttribute(null=False)
    markets_index = MarketsIndex()


class GroupModel(Model):
    class Meta():
        table_name = 'uclusion-markets-dev-groups'
        region = region_name
        host = 'https://dynamodb.us-west-2.amazonaws.com'

    id = UnicodeAttribute(hash_key=True, null=False)
    market_index = MarketsIndex()


class AuditModel(Model):
    class Meta():
        table_name = 'uclusion-summaries-dev-external-audit'
        region = region_name
        host = 'https://dynamodb.us-west-2.amazonaws.com'
    external_id = UnicodeAttribute(hash_key=True, null=False)
    object_id = UnicodeAttribute(range_key=True, null=False)


class ObjectVersionsModel(Model):
    class Meta():
        table_name = 'uclusion-summaries-dev-object-versions'
        region = region_name
        host = 'https://dynamodb.us-west-2.amazonaws.com'

    group_id = UnicodeAttribute(hash_key=True, null=False)  # type is based on table stream comes from
    object_id_one_two = UnicodeAttribute(range_key=True, null=False)


def main():
    # python -m scripts.cleanup_test_users
    logger.info("Starting cleanup")
    users = UserModel.scan(
        filter_condition=(UserModel.email.startswith("tuser")&UserModel.email.endswith("@uclusion.com")))
    for user in users:
        logger.info(f"Processing user {user.id}")
        markets = MarketModel.scan(filter_condition=MarketModel.account_id == user.account_id)
        for market in markets:
            logger.info(f"Processing market {market.id}")
            stages = StageModel.markets_index.query(hash_key=market.id)
            for stage in stages:
                logger.info(f"Processing stage {stage.id}")
                stage.delete()
            groups = GroupModel.market_index.query(hash_key=market.id)
            for group in groups:
                logger.info(f"Processing group {group.id}")
                group.delete()
            invoke_lambda_async('uclusion-markets-dev-markets_delete', get_machine_capability(market.id))
        capabilities = UserCapabilityModel.query(hash_key=user.id)
        for capability in capabilities:
            logger.info(f"Processing capability {capability.type_object_id}")
            capability.delete()
        account = AccountModel(hash_key=user.account_id)
        account.delete()
        audits = AuditModel.query(hash_key=user.external_id)
        for audit in audits:
            logger.info(f"Processing audit for {audit.external_id}")
            audit.delete()
    logger.info("Done cleaning")
    sys.exit(0)


if __name__ == "__main__":
    main()