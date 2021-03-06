import oss2

from src.utilities.file import File
from src.service_provider.abstract_service_provider import AbstractServiceProvider


class AliyunOSS(AbstractServiceProvider):
    def __init__(self, config):
        super(AliyunOSS, self).__init__(config)

        access_id = config['access_id']
        access_key = config['access_key']
        region = config['region']
        bucket = config['bucket']

        self.bucket = oss2.Bucket(oss2.Auth(access_id, access_key), region, bucket)

        oss2.defaults.connection_pool_size = 4  # 设置最大并发数限制

    def fetchDirectory(self, path='', i=''):
        directory = []

        pureName2 = path[:path.rfind('/')]
        pureName2 = pureName2[pureName2.rfind('/') + 1:]
        print(i + pureName2)

        d = []

        for obj in oss2.ObjectIteratorV2(self.bucket, prefix=path, delimiter='/', fetch_owner=True):
            if obj.is_prefix():  # 判断obj为文件夹。
                pureName = obj.key[:obj.key.rfind('/')].replace(path, '')
                d += [[pureName, obj.key]]
                # print(i + 'd: ' + pureName)

            else:  # 判断obj为文件。
                if obj.key == path:
                    continue
                pureName = obj.key[obj.key.rfind('/') + 1:]
                # print(i + 'f: ' + pureName)
                headers = self.bucket.head_object(obj.key).headers
                hash = headers['x-oss-meta-updater-sha1'] if 'x-oss-meta-updater-sha1' in headers else ''
                directory.append({
                    'name': pureName,
                    'length': headers['Content-Length'],
                    'hash': hash
                })

        for D in d:
            # print(i+'D: '+D[0])
            directory.append({
                'name': D[0],
                'children': self.fetchDirectory(D[1], i + '    ')
            })

        return directory

    def fetchBukkit(self):
        return self.fetchDirectory()

    def fetchFragments(self):
        result = []
        for upload_info in oss2.MultipartUploadIterator(self.bucket):
            result += [upload_info.key]
            # self.fragments += [upload_info.key, upload_info.upload_id]
        return result

    def deleteObjects(self, paths):
        self.bucket.batch_delete_objects(paths)

    def deleteDirectories(self, paths):
        self.bucket.batch_delete_objects([dir+'/' for dir in paths])

    def uploadObject(self, path, localPath, length, hash):
        file = File(localPath)
        metadata = {
            'x-oss-meta-updater-sha1': file.sha1,
            'x-oss-meta-updater-length': str(file.length)
        }
        oss2.resumable_upload(self.bucket, path, localPath, num_threads=4, headers=metadata)

    def getProviderName(self):
        return '阿里云对象存储服务(OSS)'
