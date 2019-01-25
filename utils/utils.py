import boto3
import sys
import getopt
import logging

logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()


def update_lamdbas_layers(region, stage):
    client = boto3.client('lambda', region_name=region)
    response = client.list_layers()
    layers = response['Layers']
    layer_versions = {}
    for layer in layers:
        layer_versions[layer['LayerName']] = layer['LatestMatchingVersion']['Version']
    lambdas = []
    # See https://github.com/aws/aws-sdk-js/issues/1931 for why not passing master region
    response = client.list_functions(
        FunctionVersion='ALL'
    )
    lambdas.extend(response['Functions'])
    marker = response['NextMarker'] if 'NextMarker' in response else None
    while marker is not None:
        response = client.list_functions(
            FunctionVersion='ALL',
            Marker=marker
        )
        lambdas.extend(response['Functions'])
        marker = response['NextMarker'] if 'NextMarker' in response else None
        logger.info('...')
    stage = '-' + stage + '-'
    for a_lambda in lambdas:
        function_name = a_lambda['FunctionName']
        if a_lambda['Version'] != '$LATEST':
            arn = a_lambda['FunctionArn']
            client.delete_function(FunctionName=arn)
        function_arn = a_lambda['FunctionArn']
        if stage not in function_name or region not in function_arn:
            continue
        layers = a_lambda['Layers'] if 'Layers' in a_lambda else []
        layers_strings = []
        layers_updated = 0
        for layer in layers:
            layer_arn = layer['Arn']
            for key, value in layer_versions.items():
                if key in layer_arn:
                    new_layer_arn = layer_arn[:layer_arn.rfind(":") + 1] + str(value)
                    if new_layer_arn != layer_arn:
                        layer_arn = new_layer_arn
                        layers_updated += 1
            layers_strings.append(layer_arn)
        if layers_updated > 0:
            logger.info('Updating ' + function_name)
            client.update_function_configuration(FunctionName=function_name, Layers=layers_strings)


usage = 'utils.py -r region -s stage'


def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'h:r:s:', ['region=', 'stage='])
    except getopt.GetoptError:
        logger.info(usage)
        sys.exit(2)
    region = None
    stage = None
    for opt, arg in opts:
        if opt == '-h':
            logger.info(usage)
            sys.exit()
        elif opt in ('-r', '--region'):
            region = arg
        elif opt in ('-s', '--stage'):
            stage = arg
    if region is None or stage is None:
        logger.info(usage)
        sys.exit(2)
    update_lamdbas_layers(region, stage)


if __name__ == "__main__":
    main(sys.argv[1:])
