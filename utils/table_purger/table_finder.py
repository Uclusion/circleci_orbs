"""
Module to list all of the tables in the dynamo account
"""
import boto3

def get_tables():
    """Limited to 100 tables"""
    client = boto3.client('dynamodb')
    table_list = client.list_tables()
    return table_list['TableNames']