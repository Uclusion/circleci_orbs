import json
import logging
import time


logger = logging.getLogger(__name__)

CLEANUP_POLL_ATTEMPTS = 48
CLEANUP_POLL_INTERVAL_SECONDS = 5
INTEGRATION_TEST_ACCOUNT_EMAILS = frozenset({
    'david.israel@uclude.com',
    '827hooshang@gmail.com',
})
PROTECTED_INTEGRATION_EMAIL = 'disrael@uclusion.com'


def validate_preserve_primary_emails(emails):
    if not isinstance(emails, list):
        raise ValueError(
            'Preserve-primary cleanup requires the integration-test '
            'account email allowlist'
        )
    normalized_emails = [
        email.strip() for email in emails
        if isinstance(email, str) and email.strip()
    ]
    if (
        len(normalized_emails) != len(INTEGRATION_TEST_ACCOUNT_EMAILS)
        or set(normalized_emails) != INTEGRATION_TEST_ACCOUNT_EMAILS
    ):
        raise ValueError(
            'Preserve-primary cleanup requires exactly the approved '
            'integration-test account emails'
        )
    return sorted(INTEGRATION_TEST_ACCOUNT_EMAILS)


def assert_no_protected_integration_accounts(
    selected_users,
    protected_users
):
    selected_account_ids = {
        user.account_id for user in selected_users
    }
    protected_account_ids = sorted({
        user.account_id for user in protected_users
        if user.account_id in selected_account_ids
    })
    if protected_account_ids:
        raise RuntimeError(
            'Refusing preserve-primary cleanup for accounts containing '
            f'{PROTECTED_INTEGRATION_EMAIL}: {protected_account_ids}'
        )


def get_resource_environment(env_name):
    if env_name not in {'development', 'stage', 'production'}:
        raise ValueError(
            f'Unsupported cleanup environment: {env_name}'
        )
    # Deployment environments use separate AWS accounts, while each account's
    # Serverless stacks retain the default "dev" stage suffix.
    return 'dev'


def invoke_request_response(client, function_name, payload):
    response = client.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    response_payload = json.loads(response['Payload'].read() or '{}')
    handler_status = response_payload.get('statusCode')
    if (
        response.get('StatusCode') != 200
        or response.get('FunctionError')
        or response_payload.get('errorMessage')
        or handler_status != 200
    ):
        raise RuntimeError(
            f'{function_name} failed for {payload}: {response_payload}'
        )
    body = response_payload.get('body')
    return json.loads(body) if isinstance(body, str) else body


def invoke_market_delete(client, function_name, capability):
    return invoke_request_response(
        client,
        function_name,
        {'capability': capability}
    )


def is_market_delete_eligible(market):
    is_top_level = (
        market.parent_comment_id is None
        and market.parent_comment_market_id is None
    )
    is_test_market = market.market_sub_type in {
        'TEST',
        'INTEGRATION_TEST'
    }
    return (
        is_top_level
        and market.market_type == 'PLANNING'
        and (
            market.object_type in {'DEMO', 'TEST'}
            or is_test_market
        )
    )


def get_descendant_market_ids(root_ids, markets):
    market_ids = set(root_ids)
    added_market = True
    while added_market:
        added_market = False
        for market in markets:
            if (
                market.id not in market_ids
                and market.parent_comment_market_id in market_ids
            ):
                market_ids.add(market.id)
                added_market = True
    return market_ids


def assert_no_markets_outside_root_closure(markets, market_ids):
    outside_root_closure = {
        market.id for market in markets
    } - set(market_ids)
    if outside_root_closure:
        raise RuntimeError(
            'Refusing identity cleanup for account markets outside '
            f'eligible root closure: {sorted(outside_root_closure)}'
        )


def get_capability_market_id(capability):
    if capability.type_object_id.startswith('market_'):
        return capability.type_object_id[len('market_'):]
    return getattr(capability, 'market_id', None)


def group_capability_keys_by_market_id(capabilities):
    keys_by_market_id = {}
    for capability in capabilities:
        market_id = get_capability_market_id(capability)
        if market_id is None:
            continue
        keys_by_market_id.setdefault(market_id, set()).add((
            capability.user_id,
            capability.type_object_id
        ))
    return keys_by_market_id


def get_capability_keys_for_market_ids(keys_by_market_id, market_ids):
    capability_keys = set()
    for market_id in market_ids:
        capability_keys.update(keys_by_market_id.get(market_id, set()))
    return capability_keys


def get_external_identity_users(account_users, identity_users):
    account_user_ids = {
        user.id for user in account_users
    }
    return [
        user for user in identity_users
        if user.id not in account_user_ids
    ]


def collect_user_capabilities(users, query_capabilities):
    capabilities = []
    for user in users:
        capabilities.extend(query_capabilities(user))
    return capabilities


def get_existing_support_market_ids(market_ids, markets):
    markets_by_id = {
        market.id: market for market in markets
    }
    support_market_ids = set()
    for market_id in market_ids:
        market = markets_by_id.get(market_id)
        visited_market_ids = set()
        while (
            market is not None
            and market.parent_comment_market_id is not None
        ):
            if (
                market.id in visited_market_ids
                or market.parent_comment_id is None
            ):
                market = None
                break
            visited_market_ids.add(market.id)
            market = markets_by_id.get(
                market.parent_comment_market_id
            )
        is_support_root = (
            market is not None
            and market.parent_comment_id is None
            and market.market_type == 'PLANNING'
            and market.market_sub_type == 'SUPPORT'
        )
        if is_support_root:
            support_market_ids.add(market_id)
    return support_market_ids


def classify_external_market_ids(
    market_ids,
    markets
):
    markets_by_id = {
        market.id: market for market in markets
    }
    cleanup_support_ids = set()
    preserved_support_ids = set()
    orphan_market_ids = set()
    unsafe_market_ids = []
    for market_id in sorted(set(market_ids)):
        market = markets_by_id.get(market_id)
        if market is None:
            orphan_market_ids.add(market_id)
            continue
        visited_market_ids = set()
        while market.parent_comment_market_id is not None:
            if (
                market.id in visited_market_ids
                or market.parent_comment_id is None
            ):
                market = None
                break
            visited_market_ids.add(market.id)
            market = markets_by_id.get(
                market.parent_comment_market_id
            )
            if market is None:
                break
        if (
            market is None
            or market.parent_comment_id is not None
        ):
            unsafe_market_ids.append(market_id)
            continue
        is_support_root = (
            market.market_type == 'PLANNING'
            and market.market_sub_type == 'SUPPORT'
        )
        if not is_support_root:
            unsafe_market_ids.append(market_id)
        elif market.object_type in {'TEST', 'DEMO'}:
            cleanup_support_ids.add(market.id)
        elif market.object_type == 'NORMAL':
            preserved_support_ids.add(market.id)
        else:
            unsafe_market_ids.append(market_id)
    if unsafe_market_ids:
        raise RuntimeError(
            'Refusing identity cleanup for unknown external market '
            f'capabilities: {unsafe_market_ids}'
        )
    return cleanup_support_ids, preserved_support_ids, orphan_market_ids


def get_capability_cleanup_payloads(capability_keys, chunk_size=50):
    ids_by_type = {
        'group': set(),
        'investible': set(),
        'market': set(),
    }
    for _, type_object_id in capability_keys:
        capability_type, separator, object_id = type_object_id.partition('_')
        if (
            not separator
            or not object_id
            or capability_type not in ids_by_type
        ):
            raise RuntimeError(
                f'Unsupported orphan capability key: {type_object_id}'
            )
        ids_by_type[capability_type].add(object_id)

    payloads = []
    for capability_type, field_name in (
        ('group', 'group_id_list'),
        ('investible', 'investible_id_list'),
        ('market', 'market_id_list'),
    ):
        object_ids = sorted(ids_by_type[capability_type])
        for start in range(0, len(object_ids), chunk_size):
            payloads.append({
                field_name: object_ids[start:start + chunk_size]
            })
    return payloads


def select_cleanup_users(
    users,
    preserve_primary,
    eligible_emails=None
):
    selected = list(users)
    if preserve_primary:
        if eligible_emails is not None:
            eligible_emails = set(eligible_emails)
            selected = [
                user for user in selected
                if user.email in eligible_emails
            ]
        selected = [
            user for user in selected
            if user.referring_user_id is None
        ]
    return sorted(
        selected,
        key=lambda user: user.referring_user_id is not None
    )


def prioritize_market_owning_users(users, market_account_ids):
    market_account_ids = set(market_account_ids)
    return sorted(
        users,
        key=lambda user: (
            user.account_id not in market_account_ids,
            user.account_id,
            user.id,
        )
    )


def get_account_users_to_delete(account_users, preserve_primary):
    if preserve_primary:
        return [
            user for user in account_users
            if user.referring_user_id is not None
        ]
    return list(account_users)


def get_account_cleanup_policy(account_users, preserve_primary):
    return {
        'users_to_delete': get_account_users_to_delete(
            account_users,
            preserve_primary
        ),
        'clear_promotions': preserve_primary,
        'delete_account': not preserve_primary,
        'delete_notifications': not preserve_primary,
    }


def should_delete_user_audits(
    account_user,
    selected_primary_user,
    preserve_primary
):
    return (
        not preserve_primary
        and selected_primary_user.referring_user_id is None
        and account_user.id == selected_primary_user.id
    )


def recover_orphan_capabilities(
    orphan_market_ids,
    orphan_capability_keys,
    wait_for_cleanup,
    invoke_cleanup,
    delete_orphan_versions=None,
    defer=False
):
    if not orphan_market_ids:
        return
    if defer:
        # Recovering missing-market residue scans and polls per dead
        # reference and can stall preserve-primary CI cleanup for hours;
        # it is deferred to separate work instead.
        return
    logger.info(
        f'Recovering {len(orphan_capability_keys)} orphan capabilities '
        f'for {len(orphan_market_ids)} missing markets'
    )
    if delete_orphan_versions is not None:
        delete_orphan_versions(orphan_market_ids)
    wait_for_cleanup(set(orphan_market_ids), set())
    for payload in get_capability_cleanup_payloads(
        orphan_capability_keys
    ):
        invoke_cleanup(payload)
    wait_for_cleanup(set(), set(orphan_capability_keys))


def wait_for_downstream_cleanup(
    market_ids,
    capability_keys,
    get_remainders,
    attempts=CLEANUP_POLL_ATTEMPTS,
    interval=CLEANUP_POLL_INTERVAL_SECONDS,
    sleep=time.sleep
):
    logger.info(
        f'Waiting for downstream cleanup of {len(market_ids)} markets '
        f'and {len(capability_keys)} capabilities'
    )
    remaining_versions = []
    remaining_capabilities = []
    for attempt in range(attempts):
        remaining_versions, remaining_capabilities = get_remainders(
            market_ids,
            capability_keys
        )
        if not remaining_versions and not remaining_capabilities:
            logger.info(
                f'Downstream cleanup complete after {attempt + 1} checks'
            )
            return
        logger.info(
            f'Downstream cleanup pending on attempt {attempt + 1} of '
            f'{attempts}: {len(remaining_versions)} versions, '
            f'{len(remaining_capabilities)} capabilities remain'
        )
        if attempt + 1 < attempts:
            sleep(interval)
    raise RuntimeError(
        'Timed out waiting for downstream market cleanup; '
        f'object versions remain for {remaining_versions}, '
        f'capabilities remain for {remaining_capabilities}'
    )
