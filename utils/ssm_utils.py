import boto3
import sys, getopt
import logging


logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()


def list_ssm_parameters(file):
    file = open(file, 'w')
    client = boto3.client('ssm')
    parameters = []
    # See https://github.com/aws/aws-sdk-js/issues/1931 for why not passing master region
    response = client.describe_parameters(
    )
    parameters.extend(response['Parameters'])
    marker = response['NextToken'] if 'NextToken' in response else None
    while marker is not None:
        response = client.describe_parameters(
            NextToken=marker
        )
        parameters.extend(response['Parameters'])
        marker = response['NextToken'] if 'NextToken' in response else None
        logger.info('...')
    parameters_values = []
    for parameter in parameters:
        response = client.get_parameter(
            Name=parameter['Name']
        )
        parameters_value = response['Parameter']
        parameters_values.append({'Name': parameters_value['Name'], 'Type': parameters_value['Type'],
                                  'Value': parameters_value['Value']})
    file.write(str(parameters_values))
    file.close()
    return parameters_values


def main(argv):
    try:
        opts, args = getopt.getopt(argv,'hf:',['file='])
    except getopt.GetoptError:
        logger.info('ssm_utils.py -f file_name')
        sys.exit(2)
    file = None
    for opt, arg in opts:
        if opt == '-h':
            logger.info('ssm_utils.py -f file_name')
            sys.exit()
        elif opt in ('-f', '--file'):
            file = arg
    if file is None:
        logger.info('ssm_utils.py -f file_name')
        sys.exit(2)
    return list_ssm_parameters(file)


if __name__ == "__main__":
    main(sys.argv[1:])
