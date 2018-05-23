import codecs
import configparser
import json
import os
import sys
from datetime import datetime

from google.cloud import datastore
from google.cloud.client import Client

MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(MS_WD, "api_config.ini")

if os.path.join(MS_WD, 'libs') not in sys.path:
    sys.path.append(os.path.join(MS_WD, 'libs'))

TaskEntityKind = 'Task' # don't change this name , otherwise indexes have to be changed

# http://google-cloud-python.readthedocs.io/en/latest/datastore/usage.html

class Task(object):

    task_id = None
    task_status = None
    sample_id = None
    timestamp = None

    all_columns = ['task_id', 'task_status', 'sample_id', 'timestamp']

    def __repr__(self):
        return '<Task("{0}","{1}","{2}","{3}")>'.format(
            self.task_id, self.task_status, self.sample_id, self.timestamp
        )

    def to_dict(self):
        # return {attr.name: getattr(self, attr.name) for attr in all_columns}
        res = {}
        for attr in self.all_columns:
            res[attr] = getattr(self, attr)
        return res

    def to_json(self):
        return json.dumps(self.to_dict())

class Datastore():

    DEFAULTCONF = {
        'db_type': 'datastore',
        'host_string': 'remote',
        'db_name': TaskEntityKind,
        'username': 'multiscanner',
        'password': ''
    }

    def __init__(self, 
                 config=None, 
                 configfile=CONFIG_FILE, 
                 regenconfig=False, 
                 goog_cred_file=None):

        # Configuration parsing
        config_parser = configparser.SafeConfigParser()
        config_parser.optionxform = str

        # (re)generate conf file if necessary
        if regenconfig or not os.path.isfile(configfile):
            self._rewrite_config(config_parser, configfile, config)
        # now read in and parse the conf file
        config_parser.read(configfile)
        # If we didn't regen the config file in the above check, it's possible
        # that the file is missing our DB settings...
        if not config_parser.has_section(self.__class__.__name__):
            self._rewrite_config(config_parser, configfile, config)
            config_parser.read(configfile)

        # If configuration was specified, use what was stored in the config file
        # as a base and then override specific settings as contained in the user's
        # config. This allows the user to specify ONLY the config settings they want to
        # override
        config_from_file = dict(config_parser.items(self.__class__.__name__))
        if config:
            for key_ in config:
                config_from_file[key_] = config[key_]
        self.config = config_from_file

        # Instantiates a client
        if 'google_cloud_cred' in self.config and len(self.config['self.config']) > 0:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.config['self.config']
        else:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = goog_cred_file
        self.datastore_client = datastore.Client()
        # self.datastore_client = Client.from_service_account_json('../docker_utils/pwned-google-cred.json')
    
    def _rewrite_config(self, config_parser, configfile, usr_override_config):
        """
        Regenerates the Database-specific part of the API config file
        """
        if os.path.isfile(configfile):
            # Read in the old config
            config_parser.read(configfile)
        if not config_parser.has_section(self.__class__.__name__):
            config_parser.add_section(self.__class__.__name__)
        if not usr_override_config:
            usr_override_config = self.DEFAULTCONF
        # Update config
        for key_ in usr_override_config:
            config_parser.set(self.__class__.__name__, key_, str(usr_override_config[key_]))

        with codecs.open(configfile, 'w', 'utf-8') as conffile:
            config_parser.write(conffile)


    def init_db(self):
        """
        Initializes the database connection based on the configuration parameters
        """
        pass
    
    def add_task(self, task_id=None, task_status='Pending', sample_id=None, timestamp=None):        
        # The name/ID for the new entity
        name = task_id
        # The Cloud Datastore key for the new entity
        task_key = self.datastore_client.key(TaskEntityKind, name)

        # Prepares the new entity
        task = datastore.Entity(key=task_key)
        # task['task_status'] = task_status
        # task['sample_id'] = sample_id
        # task['timestamp'] = timestamp

        if timestamp is None:
            timestamp = datetime.utcnow()

        task.update({
            'task_status': task_status,
            'sample_id': sample_id,
            'timestamp': timestamp
        })

        # Saves the entity
        self.datastore_client.put(task)

        return task.key.to_legacy_urlsafe()
    
    def update_task(self, task_id, task_status, timestamp=None):
        with self.datastore_client.transaction():
            key = self.datastore_client.key(TaskEntityKind, task_id)
            task = self.datastore_client.get(key)

            if not task:
                raise ValueError(
                    'Task {} does not exist.'.format(task_id))

            task['task_status'] = task_status
            if timestamp:
                task['timestamp'] = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%f')

            self.datastore_client.put(task)

            return self.__db_task_to_task(task).to_dict()

    def __db_task_to_task(self, db_task):
        task = Task()
        task.sample_id = db_task['sample_id']
        task.task_id = db_task.key.name
        task.task_status = db_task['task_status']
        task.timestamp = db_task['timestamp'] # no conversion needed
        return task

    def get_task(self, task_id):

        key = self.datastore_client.key(TaskEntityKind, task_id)
        task = self.datastore_client.get(key)
        return self.__db_task_to_task(task)
    
    def get_all_tasks(self):
        query = self.datastore_client.query(kind=TaskEntityKind)
        result = []
        for res in query.fetch():
            result.append(self.__db_task_to_task(res).to_dict())
        return result

    def delete_task(self, task_id):
        key = self.datastore_client.key(TaskEntityKind, task_id)
        self.datastore_client.delete(key)
        return True
    
    def exists(self, sample_id):
        '''Checks if any tasks exist in the database with the given sample_id.

        Returns:
            Task id of the most recent task with the given sample_id if one
            exists in task database, otherwise None.
        '''
        
        query = self.datastore_client.query(kind=TaskEntityKind, order=['timestamp'])
        query.add_filter('sample_id', '=', sample_id)
        res = list(query.fetch(1))
        if len(res) > 0:
            return res[0].key.name
        return None
    
    def search(self, params, id_list=None, search_by_value=False, return_all=False):
        '''Search according to Datatables-supplied parameters.
        Returns results in format expected by Datatables.
        '''
        pass


if __name__ == '__main__':

    d = Datastore(goog_cred_file='/Users/sirack/bin/misc/k8-multiscanner/docker_utils/pwned-google-cred.json')
    d.init_db() # init database

    # print d.add_task(task_id='123', sample_id='abc')
    # print d.add_task(task_id='456', sample_id='abcd')
    # print d.get_task(task_id='123')
    # print d.exists('abc')
    # print d.delete_task('123')
    print(d.get_all_tasks())
    # print d.update_task('456', 'Pending_101')







