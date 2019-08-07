"""Module to clear the contents of a table"""
import boto3

def purge_table_contents(table_name):
    client = boto3.client('dynamodb')
    keys = get_keys(client, table_name)
    print(keys)
    # do while would be nice here
    contents = client.scan(TableName=table_name)
    more_pages = 'LastEvaluatedKey' in contents
    items = contents['Items']
    delete_items(client, table_name, keys, items)
    while more_pages:
        last_evaluated = contents['LastEvaluatedKey']
        contents = client.scan(TableName=table_name, ExclusiveStartKey=last_evaluated)
        more_pages = 'LastEvaluatedKey' in contents
        items = contents['Items']
        delete_items(client, table_name, keys, items)

def get_keys(client, table_name):
    metadata = client.describe_table(TableName=table_name)
    #print(metadata)
    table_metadata = metadata['Table']
    key_schema = table_metadata['KeySchema']
    keys = map(lambda item: item['AttributeName'], key_schema)
    return list(keys)


def delete_items(client, table_name, keys, items):
    for item in items:
        delete_item(client, table_name, keys, item)

def delete_item(client, table_name, keys, item):
    key_data = {};
    for key in keys:
        key_data[key] = item[key]
    client.delete_item(TableName=table_name, Key=key_data)