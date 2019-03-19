import boto3


dynamodb = boto3.resource('dynamodb', region_name='us-west-2')


dynamodb.create_table(
    TableName='Releases',
    KeySchema=[
        {
            'AttributeName': 'repo_name',
            'KeyType': 'HASH'
        },
        {
            'AttributeName': 'tag_name',
            'KeyType': 'RANGE'
        }
    ],
    AttributeDefinitions=[
        {
            'AttributeName': 'repo_name',
            'AttributeType': 'S'
        },
        {
            'AttributeName': 'tag_name',
            'AttributeType': 'S'
        },

    ],
    BillingMode='PAY_PER_REQUEST'
)
