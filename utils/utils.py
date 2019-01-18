import boto3
import sys
import getopt
import logging

logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()


def update_lamdbas_for_layer(region, stage, layer_name, layer_version):
    file = open(stage + '_' + layer_name + '.txt', 'w')
    client = boto3.client('lambda', region_name=region)
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
    filtered_lambdas = []
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
            if layer_name in layer_arn:
                filtered_lambdas.append(function_name)
                layer_arn = layer_arn[:layer_arn.rfind(":") + 1] + layer_version
                layers_updated += 1
            layers_strings.append(layer_arn)
        if layers_updated > 0:
            client.update_function_configuration(FunctionName=function_name, Layers=layers_strings)
    file.write(str(filtered_lambdas))
    file.close()
    return filtered_lambdas


def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'h:r:s:l:v:', ['region=', 'stage=', 'layer=', 'version='])
    except getopt.GetoptError:
        logger.info('utils.py -r region -s stage -l layer_name -v layer_version')
        sys.exit(2)
    region = None
    stage = None
    layer = None
    version = None
    for opt, arg in opts:
        if opt == '-h':
            logger.info('utils.py -r region -s stage -l layer_name -v layer_version')
            sys.exit()
        elif opt in ('-r', '--region'):
            region = arg
        elif opt in ('-s', '--stage'):
            stage = arg
        elif opt in ('-l', '--layer'):
            layer = arg
        elif opt in ('-v', '--version'):
            version = arg
    if region is None or stage is None or layer is None or version is None:
        logger.info('utils.py -r region -s stage -l layer_name -v version')
        sys.exit(2)
    return update_lamdbas_for_layer(region, stage, layer, version)


if __name__ == "__main__":
    main(sys.argv[1:])
