__author__ = 'mhoyer'

from boto import cloudformation
from boto.resultset import ResultSet
from boto.exception import AWSConnectionError, BotoServerError
import json
import logging


class CloudFormationTemplate(object):
    def __init__(self, template_url, template_body=None):
        logging.basicConfig(format='%(asctime)s %(levelname)s %(module)s: %(message)s',
                            datefmt='%d.%m.%Y %H:%M:%S',
                            level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        self.url = template_url
        self.body = template_body

        if not self.body:
            self.body = self._load_template(self.url)

    def get_template_body(self):
        return self.body

    def _load_template(self, url):
        if url.lower().startswith("s3://"):
            return self._s3_get_template(url)
        elif url.lower().startswith("/"):
            return self._fs_get_template(url)
        else:
            raise NotImplementedError("No loader available for {0}".format(url))

    def _fs_get_template(self, url):
        try:
            with open(url, 'r') as template_file:
                return json.loads(template_file.read())
        except ValueError as e:
            self.logger.error("Could not load template from {0}: {1}".format(url, e.strerror))
            # TODO: handle error condition
            return None
        except IOError as e:
            self.logger.error("Could not load template from {0}: {1}".format(url, e.strerror))
            return None

    def _s3_get_template(self, url):
        pass


class CloudFormation(object):
    def __init__(self, region="eu-west-1", stacks=None):
        logging.basicConfig(format='%(asctime)s %(levelname)s %(module)s: %(message)s',
                            datefmt='%d.%m.%Y %H:%M:%S',
                            level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        self.conn = cloudformation.connect_to_region(region)
        if not self.conn:
            self.logger.error("Could not connect to cloudformation API in {0}. Invalid region?".format(region))
            raise AWSConnectionError("Got None connection object")

        self.logger.debug("Connected to cloudformation API at {0} with access key id: {1}".format(
            region, self.conn.aws_access_key_id))

        self.stacks = stacks
        if not self.stacks:
            self._load_stacks()

        assert isinstance(self.stacks, ResultSet)

    def _load_stacks(self):
        self.stacks = self.conn.describe_stacks()
        assert isinstance(self.stacks, ResultSet)

    def get_stacks(self):
        return self.stacks

    def get_stacks_dict(self):
        stacks_dict = {}
        for stack in self.stacks:
            stacks_dict[stack.stack_name] = {"parameters": stack.parameters, "outputs": stack.outputs}
        return stacks_dict

    def create_stack(self, stack_name, template, parameters):
        assert isinstance(template, CloudFormationTemplate)
        try:
            self.logger.info(
                "Creating stack {0} from template {1} with parameters: {2}".format(stack_name, template.url,
                                                                                   parameters))
            self.conn.create_stack(stack_name, template_body=json.dumps(template.get_template_body()),
                                   parameters=parameters)
        except BotoServerError as e:
            self.logger.error(
                "Could not create stack {0}. Cloudformation API response: {1}".format(stack_name, e.message))


if __name__ == "__main__":
    cfn = CloudFormation()