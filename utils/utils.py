import boto3
import sys, getopt
import logging


logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()


def update_lamdbas_for_layer(region, stage, layer_name, arn):
    file = open(stage + '_' + layer_name + '.txt', 'w')
    client = boto3.client('lambda')
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
        for layer in layers:
            if layer_name in layer['Arn']:
                filtered_lambdas.append(function_name)
                layer['Arn'] = arn
            layers_strings.append(layer['Arn'])
            print(layers_strings)
        response = client.update_function_configuration(FunctionName=function_name, Layers=layers_strings)
    file.write(str(filtered_lambdas))
    file.close()
    return filtered_lambdas


def main(argv):
    try:
        opts, args = getopt.getopt(argv,'hr:s:l:a:',['region=', 'stage=', 'layer=', 'arn='])
    except getopt.GetoptError:
        logger.info('utils.py -r region -s stage -l layer_name -a arn')
        sys.exit(2)
    region = None
    stage = None
    layer = None
    arn = None
    for opt, arg in opts:
        if opt == '-h':
            logger.info('utils.py -r region -s stage -l layer_name -a arn')
            sys.exit()
        elif opt in ('-r', '--region'):
            region = arg
        elif opt in ('-s', '--stage'):
            stage = arg
        elif opt in ('-l', '--layer'):
            layer = arg
        elif opt in ('-a', '--arn'):
            arn = arg
    if region is None or stage is None or layer is None:
        logger.info('utils.py -r region -s stage -l layer_name -a arn')
        sys.exit(2)
    return update_lamdbas_for_layer(region, stage, layer, arn)


if __name__ == "__main__":
    main(sys.argv[1:])
