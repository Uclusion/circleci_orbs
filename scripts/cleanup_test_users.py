import logging
import os
import sys
import boto3
import getopt
from botocore.config import Config
from pynamodb.attributes import (
    ListAttribute,
    UnicodeAttribute,
    VersionAttribute
)
from pynamodb.exceptions import DoesNotExist
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from pynamodb.models import Model
from scripts.cleanup_test_users_utils import (
    assert_no_markets_outside_root_closure,
    classify_external_market_ids,
    collect_user_capabilities,
    get_account_cleanup_policy,
    get_descendant_market_ids,
    get_capability_keys_for_market_ids,
    get_external_identity_users,
    get_existing_support_market_ids,
    get_resource_environment,
    group_capability_keys_by_market_id,
    invoke_market_delete as invoke_market_delete_with_client,
    invoke_request_response,
    is_market_delete_eligible,
    assert_no_protected_integration_accounts,
    PROTECTED_INTEGRATION_EMAIL,
    prioritize_market_owning_users,
    recover_orphan_capabilities,
    select_cleanup_users,
    should_delete_user_audits,
    validate_preserve_primary_emails,
    wait_for_downstream_cleanup
)


env_name = os.environ['ENV_NAME']
resource_env_name = get_resource_environment(env_name)
logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()
region_name = 'us-west-2'
client = boto3.client(
    'lambda',
    region_name=region_name,
    config=Config(
        read_timeout=210,
        retries={'total_max_attempts': 1, 'mode': 'standard'}
    )
)


def invoke_market_delete(function_name, capability):
    return invoke_market_delete_with_client(
        client,
        function_name,
        capability
    )


def get_machine_capability(market_id):
    return {'role': 'Machine', 'is_admin': True, 'type': 'market', 'id': market_id}


class AccountIndex(GlobalSecondaryIndex):
    class Meta():
        region = region_name
        host = 'https://dynamodb.us-west-2.amazonaws.com'
        read_capacity_units = 1
        write_capacity_units = 1
        projection = AllProjection()
    account_id = UnicodeAttribute(hash_key=True)


class UserModel(Model):
    class Meta():
        table_name = f'uclusion-users-{resource_env_name}-users'
        region = region_name
        host = 'https://dynamodb.us-west-2.amazonaws.com'

    external_id = UnicodeAttribute(hash_key=True, null=False)
    account_id = UnicodeAttribute(range_key=True, null=False)
    account_index = AccountIndex()
    email = UnicodeAttribute(null=True)
    referring_user_id = UnicodeAttribute(null=True)
    id = UnicodeAttribute(null=False)


class AccountModel(Model):
    class Meta():
        table_name = f'uclusion-users-{resource_env_name}-accounts'
        region = region_name
        host = 'https://dynamodb.us-west-2.amazonaws.com'

    id = UnicodeAttribute(hash_key=True, null=False)
    billing_promotions = ListAttribute(null=False)
    version = VersionAttribute()


class UserCapabilityModel(Model):
    class Meta():
        table_name = (
            f'uclusion-users-{resource_env_name}-users-capabilities'
        )
        region = region_name
        host = 'https://dynamodb.us-west-2.amazonaws.com'
    user_id = UnicodeAttribute(hash_key=True, null=False)
    type_object_id = UnicodeAttribute(range_key=True, null=False)
    market_id = UnicodeAttribute(null=True)
    type = UnicodeAttribute(null=True)


class MarketModel(Model):
    class Meta():
        table_name = f'uclusion-markets-{resource_env_name}-markets'
        region = region_name
        host = 'https://dynamodb.us-west-2.amazonaws.com'
    id = UnicodeAttribute(hash_key=True, null=False)
    account_id = UnicodeAttribute(null=False)
    parent_comment_id = UnicodeAttribute(null=True)
    parent_comment_market_id = UnicodeAttribute(null=True)
    market_type = UnicodeAttribute(null=True)
    market_sub_type = UnicodeAttribute(null=True)
    object_type = UnicodeAttribute(null=True)


class AuditModel(Model):
    class Meta():
        table_name = (
            f'uclusion-summaries-{resource_env_name}-external-audit'
        )
        region = region_name
        host = 'https://dynamodb.us-west-2.amazonaws.com'
    external_id = UnicodeAttribute(hash_key=True, null=False)
    object_id = UnicodeAttribute(range_key=True, null=False)


class ObjectVersionsModel(Model):
    class Meta():
        table_name = (
            f'uclusion-summaries-{resource_env_name}-object-versions'
        )
        region = region_name
        host = 'https://dynamodb.us-west-2.amazonaws.com'

    group_id = UnicodeAttribute(hash_key=True, null=False)  # type is based on table stream comes from
    object_id_one_two = UnicodeAttribute(range_key=True, null=False)


class AsyncNotificationsModel(Model):
    class Meta():
        table_name = f'uclusion-async-{resource_env_name}-notifications'
        region = region_name
        host = 'https://dynamodb.us-west-2.amazonaws.com'

    market_id_user_id = UnicodeAttribute(hash_key=True, null=False)
    type_object_id = UnicodeAttribute(range_key=True, null=False)
    external_id = UnicodeAttribute(null=False)


def get_cleanup_remainders(market_ids, capability_keys):
    remaining_versions = []
    for market_id in market_ids:
        versions = ObjectVersionsModel.query(
            market_id,
            consistent_read=True,
            limit=1
        )
        if next(iter(versions), None) is not None:
            remaining_versions.append(market_id)

    remaining_capabilities = []
    for user_id, type_object_id in capability_keys:
        try:
            UserCapabilityModel.get(
                user_id,
                type_object_id,
                consistent_read=True
            )
            remaining_capabilities.append((user_id, type_object_id))
        except DoesNotExist:
            pass
    return remaining_versions, remaining_capabilities


def invoke_users_capability_cleanup(payload):
    return invoke_request_response(
        client,
        f'uclusion-users-{resource_env_name}-users_batch_delete',
        payload
    )


def wait_for_cleanup(market_ids, capability_keys):
    wait_for_downstream_cleanup(
        market_ids,
        capability_keys,
        get_remainders=get_cleanup_remainders
    )


def delete_orphan_versions(market_ids):
    versions_to_delete = []
    for market_id in sorted(set(market_ids)):
        try:
            MarketModel.get(
                market_id,
                consistent_read=True
            )
        except DoesNotExist:
            versions_to_delete.extend(ObjectVersionsModel.query(
                market_id,
                consistent_read=True
            ))
            continue
        raise RuntimeError(
            'Refusing orphan-version cleanup for existing market '
            f'{market_id}'
        )
    with ObjectVersionsModel.batch_write() as versions_batch:
        for version in versions_to_delete:
            versions_batch.delete(version)


def delete_account_user(user, delete_audits):
    capabilities = UserCapabilityModel.query(
        hash_key=user.id,
        consistent_read=True
    )
    for capability in capabilities:
        logger.info(
            f"Processing capability {capability.type_object_id}"
        )
        capability.delete()
    if delete_audits:
        for external_id in filter(None, {user.external_id, user.email}):
            audits = AuditModel.query(
                hash_key=external_id,
                consistent_read=True
            )
            for audit in audits:
                logger.info(f"Processing audit for {audit.external_id}")
                audit.delete()
    user.delete()


def main(argv):
    usage = (
        'python -m scripts.cleanup_test_users '
        '[-e emails_list] [--preserve-primary]'
    )
    try:
        opts, args = getopt.getopt(
            argv,
            'h:e:',
            ['emails=', 'preserve-primary']
        )
    except getopt.GetoptError:
        logger.info(usage)
        sys.exit(2)
    emails = None
    preserve_primary = False
    for opt, arg in opts:
        if opt == '-h':
            logger.info(usage)
            sys.exit()
        elif opt in ('-e', '--emails'):
            emails = arg.split(',')
        elif opt == '--preserve-primary':
            preserve_primary = True
    if preserve_primary:
        emails = validate_preserve_primary_emails(emails)
    logger.info("Starting cleanup")
    if emails is not None and len(emails) > 0 and len(emails[0]) > 0:
        has_emails = True
        users = UserModel.scan(filter_condition=UserModel.email.is_in(*emails))
    else:
        has_emails = False
        users = UserModel.scan(filter_condition=UserModel.email.startswith("tuser"))
    users = [
        user for user in users
        if has_emails or user.email.endswith("@uclusion.com")
    ]
    # Preserve-primary mode must never treat matching referred copies in
    # support/customer accounts as cleanup roots.
    users = select_cleanup_users(
        users,
        preserve_primary,
        eligible_emails=emails if preserve_primary else None
    )
    if preserve_primary:
        protected_users = UserModel.scan(
            filter_condition=(
                UserModel.email == PROTECTED_INTEGRATION_EMAIL
            ),
            consistent_read=True
        )
        assert_no_protected_integration_accounts(
            users,
            protected_users
        )
        market_account_ids = {
            market.account_id
            for market in MarketModel.scan(consistent_read=True)
        }
        users = prioritize_market_owning_users(
            users,
            market_account_ids
        )
    processed_accounts = set()
    for user in users:
        if user.account_id in processed_accounts:
            continue
        logger.info(f"Processing user {user.id} with {user.email}")
        if user.referring_user_id is None:
            # Only primary users own markets, accounts, and audits
            all_markets = list(MarketModel.scan(consistent_read=True))
            markets = [
                market for market in all_markets
                if market.account_id == user.account_id
            ]
            top_level_markets = [
                market for market in markets
                if market.parent_comment_id is None
                and market.parent_comment_market_id is None
            ]
            ineligible_roots = [
                market.id for market in top_level_markets
                if not is_market_delete_eligible(market)
            ]
            if ineligible_roots:
                raise RuntimeError(
                    'Refusing identity cleanup while unmarked top-level '
                    f'markets remain: {ineligible_roots}'
                )

            owned_root_market_ids = [
                market.id for market in top_level_markets
            ]
            owned_market_ids = get_descendant_market_ids(
                owned_root_market_ids,
                all_markets
            )
            assert_no_markets_outside_root_closure(
                markets,
                owned_market_ids
            )
            account_users = list(UserModel.scan(
                filter_condition=UserModel.account_id == user.account_id,
                consistent_read=True
            ))
            identity_users = list(UserModel.query(
                hash_key=user.external_id,
                consistent_read=True
            ))
            external_identity_users = get_external_identity_users(
                account_users,
                identity_users
            )
            home_account_capabilities = collect_user_capabilities(
                account_users,
                lambda capability_user: UserCapabilityModel.query(
                    capability_user.id,
                    consistent_read=True
                )
            )
            identity_capabilities = collect_user_capabilities(
                external_identity_users,
                lambda capability_user: UserCapabilityModel.query(
                    capability_user.id,
                    consistent_read=True
                )
            )
            home_capability_keys_by_market_id = (
                group_capability_keys_by_market_id(
                    home_account_capabilities
                )
            )
            identity_capability_keys_by_market_id = (
                group_capability_keys_by_market_id(
                    identity_capabilities
                )
            )
            capability_keys_by_market_id = (
                group_capability_keys_by_market_id(
                    home_account_capabilities
                    + identity_capabilities
                )
            )
            home_external_market_ids = (
                set(home_capability_keys_by_market_id)
                - set(owned_market_ids)
            )
            (
                cleanup_support_root_ids,
                _preserved_support_ids,
                orphan_market_ids
            ) = classify_external_market_ids(
                home_external_market_ids,
                all_markets
            )
            identity_external_market_ids = (
                set(identity_capability_keys_by_market_id)
                - set(owned_market_ids)
            )
            identity_support_market_ids = (
                get_existing_support_market_ids(
                    identity_external_market_ids,
                    all_markets
                )
            )
            (
                identity_cleanup_support_root_ids,
                _identity_preserved_support_ids,
                _identity_orphan_market_ids
            ) = classify_external_market_ids(
                identity_support_market_ids,
                all_markets
            )
            cleanup_support_root_ids.update(
                identity_cleanup_support_root_ids
            )
            cleanup_support_market_ids = get_descendant_market_ids(
                cleanup_support_root_ids,
                all_markets
            )
            cleanup_market_ids = (
                set(owned_market_ids)
                | cleanup_support_market_ids
            )
            cleanup_capability_keys = (
                get_capability_keys_for_market_ids(
                    capability_keys_by_market_id,
                    cleanup_market_ids
                )
            )
            orphan_capability_keys = (
                get_capability_keys_for_market_ids(
                    home_capability_keys_by_market_id,
                    orphan_market_ids
                )
            )
            recover_orphan_capabilities(
                orphan_market_ids,
                orphan_capability_keys,
                wait_for_cleanup,
                invoke_users_capability_cleanup,
                delete_orphan_versions=(
                    delete_orphan_versions
                    if preserve_primary
                    else None
                )
            )

            root_market_ids = list(dict.fromkeys(
                owned_root_market_ids
                + sorted(cleanup_support_root_ids)
            ))
            for market_id in root_market_ids:
                logger.info(f"Processing market {market_id}")
                # markets_delete owns the complete, recursive market-data
                # cascade. Keep identity/account cleanup below separate.
                invoke_market_delete(
                    (
                        f'uclusion-markets-{resource_env_name}'
                        '-markets_delete'
                    ),
                    get_machine_capability(market_id)
                )
            # Market rows disappear before their DynamoDB stream consumers
            # finish notification, audit, version, and capability cleanup.
            # Do not remove the identities those consumers need until both
            # downstream tables confirm completion.
            wait_for_downstream_cleanup(
                cleanup_market_ids,
                cleanup_capability_keys,
                get_remainders=get_cleanup_remainders
            )
            account = AccountModel.get(
                hash_key=user.account_id,
                consistent_read=True
            )
            cleanup_policy = get_account_cleanup_policy(
                account_users,
                preserve_primary
            )
            if cleanup_policy['clear_promotions']:
                account.update([
                    AccountModel.billing_promotions.set([])
                ])
            # notification delete by scan for external id - otherwise things were getting stuck
            if cleanup_policy['delete_notifications']:
                notifications = AsyncNotificationsModel.scan(
                    filter_condition=(
                        AsyncNotificationsModel.external_id
                        == user.external_id
                    )
                )
                for notification in notifications:
                    notification.delete()
            for user_in_account in cleanup_policy['users_to_delete']:
                # The downstream barrier guarantees all market capabilities
                # are gone. Remove every remaining account/group capability
                # before its owning identity, including users not selected by
                # the outer email scan.
                delete_account_user(
                    user_in_account,
                    delete_audits=should_delete_user_audits(
                        user_in_account,
                        user,
                        preserve_primary
                    )
                )
            if cleanup_policy['delete_account']:
                account.delete()
            processed_accounts.add(user.account_id)
            continue
        # For referred test users still need to delete because external id will change on recreate
        capabilities = UserCapabilityModel.query(hash_key=user.id)
        for capability in capabilities:
            logger.info(f"Processing capability {capability.type_object_id}")
            capability.delete()
        user.delete()
    logger.info("Done cleaning")
    sys.exit(0)


if __name__ == "__main__":
    if env_name is None:
        logger.info("No env_name")
        sys.exit(1)
    main(sys.argv[1:])
