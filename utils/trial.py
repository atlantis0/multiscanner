import os
import flask
import hashlib
# Imports the Google Cloud client library
from google.cloud import storage

# Imports the Google Cloud client library
from google.cloud import pubsub_v1
upload_bucket_folder = 'app-pwned.appspot.com'

pub_sub_project = 'app-pwned'
pub_sub_topic = 'apps'

def upload_bucket(file_path, destination_name):

    # Instantiates a client
    storage_client = storage.Client()
    # The name for the new bucket
    bucket = storage_client.get_bucket(upload_bucket_folder)
    blob = bucket.blob(destination_name)

    blob.upload_from_filename(file_path)

    print('File {} uploaded to {}.'.format(
        file_,
        destination_name))
    url = "https://storage.googleapis.com/{0}/{1}".format(upload_bucket_folder, destination_name)
    return url

def push_to_pub_sub(data_):
    # Instantiates a client
    publisher = pubsub_v1.PublisherClient()

    # topic path
    topic_path = publisher.topic_path(pub_sub_project, pub_sub_topic)
    # publish
    publisher.publish(topic_path, data=json.dumps(data_))
    print('Published messages.')


def save_hashed_filename(f, zipped=False):
    '''
    Save given file to the upload folder, with its SHA256 hash as its filename.
    '''

    # print type(f)
    f_name = '1234'
    full_path = '34'
    # # Reset the file pointer to the beginning to allow us to save it
    # f.seek(0)

    # # TODO: should we check if the file is already there
    # # and skip this step if it is?
    # # file_path = os.path.join(api_config['api']['upload_folder'], f_name)
    # file_path = os.path.join('/tmp/one', f_name)
    # full_path = os.path.join('tmp/one/two', file_path)
    # if zipped:
    #     shutil.copy2(f.name, full_path)
    # else:
    #     print file_path
    #     f.save(file_path)
    
    # upload to bucket
    url_ = upload_bucket(f, f_name)

    return (f_name, full_path, url_)

if __name__ == '__main__':
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = '/Users/sirack/Desktop/pwned-google-cred.json'
    print('hello')
    tr_path = '/Users/sirack/Desktop/tr.apk'
    # f1 = open(tr_path)
    save_hashed_filename(tr_path)
    # f.close()

