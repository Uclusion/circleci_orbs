import json
import logging
import os
import sys
import getopt
import boto3


logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()


def update_templates(region, path):
    ses = boto3.client('ses', region_name=region)
    response = ses.list_templates()
    templates_list = response['TemplatesMetadata']
    files = os.listdir(path)
    templates = {}
    for file_name in files:
        file = open(path+'/'+file_name, 'r')
        template = json.load(file)
        template_name = template['Template']['TemplateName']
        templates[template_name] = template
        file.close()
    for template in templates_list:
        template_name = template['Name']
        if template_name in templates:
            logger.info('Updating ' + template_name)
            ses.update_template(Template=templates[template_name]['Template'])
            del templates[template_name]
        else:
            logger.error('Missing ' + template_name)
    for template_name, template in templates.items():
        logger.info('Creating ' + template_name)
        ses.create_template(Template=template['Template'])


usage = 'python -m utils.ses_utils -r region -p path'


def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'h:r:p:', ['region=', 'path='])
    except getopt.GetoptError:
        logger.info(usage)
        sys.exit(2)
    path = None
    region = None
    for opt, arg in opts:
        if opt == '-h':
            logger.info(usage)
            sys.exit()
        elif opt in ('-r', '--region'):
            region = arg
        elif opt in ('-p', '--env'):
            path = arg
    if path is None or region is None:
        logger.info(usage)
        sys.exit(2)
    update_templates(region, path)


if __name__ == "__main__":
    main(sys.argv[1:])
