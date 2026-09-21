"""Confined, create-only storage operations for library transfers."""
from pathlib import Path, PurePosixPath
from uuid import uuid4

from botocore.exceptions import ClientError

from . import storage

MAX_AUDIO_BYTES = 128 * 1024 * 1024


class TransferStorage:
    def __init__(self, root=None, *, client=None, bucket=None):
        self.root = Path(root if root is not None else storage.LOCAL_AUDIO_DIR).resolve()
        self.client = client
        self.bucket = bucket

    @classmethod
    def configured(cls):
        if storage.s3_enabled():
            return cls(client=storage._s3_client(), bucket=storage._s3_bucket())
        return cls()

    def local_path(self, ref):
        if not isinstance(ref, str) or not ref or '\\' in ref or '://' in ref:
            raise ValueError('Invalid local storage reference')
        path = Path(ref)
        if '..' in path.parts:
            raise ValueError('Storage path traversal rejected')
        if not path.is_absolute():
            if path.parts[:2] == ('data', 'audios'):
                path = Path(*path.parts[2:])
            path = self.root / path
        # Stored absolute paths may be read only if confined to the configured root.
        try:
            relative = path.relative_to(self.root)
        except ValueError:
            raise ValueError('Storage reference outside configured root') from None
        current = self.root
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError('Symbolic links are not allowed in transfer storage')
        if not path.resolve().is_relative_to(self.root):
            raise ValueError('Storage reference outside configured root')
        return path

    def s3_key(self, ref):
        prefix = f's3://{self.bucket}/'
        if not ref.startswith(prefix):
            raise ValueError('Storage reference outside configured bucket')
        key = ref[len(prefix):]
        if not key.startswith('audios/') or '\\' in key or any(p in ('', '.', '..') for p in key.split('/')):
            raise ValueError('Invalid S3 audio key')
        return key

    def read(self, ref):
        if self.client is not None:
            body = self.client.get_object(Bucket=self.bucket, Key=self.s3_key(ref))['Body']
            try:
                data = body.read(MAX_AUDIO_BYTES + 1)
            finally:
                body.close()
        else:
            with self.local_path(ref).open('rb') as stream:
                data = stream.read(MAX_AUDIO_BYTES + 1)
        if len(data) > MAX_AUDIO_BYTES:
            raise ValueError('Audio exceeds transfer size limit')
        return data

    def reserve(self, extension):
        name = f'library-{uuid4().hex}{extension}'
        if self.client is not None:
            return f's3://{self.bucket}/audios/imports/{name}'
        return str(PurePosixPath('data/audios') / name)

    def put(self, ref, data):
        """Return ownership after exclusive creation. Never overwrite a collision."""
        if self.client is not None:
            # Conditional creation also works when the random key already exists.
            try:
                self.client.put_object(Bucket=self.bucket, Key=self.s3_key(ref), Body=data,
                                       ContentType='application/octet-stream', IfNoneMatch='*')
            except ClientError as exc:
                if exc.response.get('Error', {}).get('Code') in {'PreconditionFailed', '412', 'ConditionalRequestConflict'}:
                    raise FileExistsError(f'Storage collision, existing object preserved: {ref}') from exc
                raise RuntimeError(f'S3 write outcome uncertain; inspect {ref}') from exc
            except Exception as exc:
                raise RuntimeError(f'S3 write outcome uncertain; inspect {ref}') from exc
        else:
            path = self.local_path(ref)
            self.root.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                try:
                    stream.write(data)
                except BaseException:
                    path.unlink(missing_ok=True)
                    raise

    def remove(self, ref):
        if self.client is not None:
            self.client.delete_object(Bucket=self.bucket, Key=self.s3_key(ref))
        else:
            self.local_path(ref).unlink(missing_ok=True)
