import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = 'Crea un respaldo verificable de SQLite y de los archivos media.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            default=str(settings.BASE_DIR / 'backups'),
            help='Directorio donde se guardará el respaldo.',
        )

    def handle(self, *args, **options):
        if settings.DATABASES['default']['ENGINE'] != 'django.db.backends.sqlite3':
            raise CommandError('Este comando solo admite bases SQLite.')

        database_path = Path(settings.DATABASES['default']['NAME']).resolve()
        if not database_path.exists():
            raise CommandError(f'No existe la base de datos: {database_path}')

        timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        backup_dir = Path(options['output_dir']).resolve() / timestamp
        backup_dir.mkdir(parents=True, exist_ok=False)
        database_backup = backup_dir / 'db.sqlite3'
        media_backup = backup_dir / 'media.zip'

        connection.close()
        with sqlite3.connect(database_path) as source:
            with sqlite3.connect(database_backup) as destination:
                source.backup(destination)

        with sqlite3.connect(database_backup) as copied_database:
            integrity_result = copied_database.execute('PRAGMA integrity_check').fetchone()[0]
        if integrity_result != 'ok':
            raise CommandError(f'La copia de SQLite no superó la validación: {integrity_result}')

        media_root = Path(settings.MEDIA_ROOT)
        with ZipFile(media_backup, 'w', compression=ZIP_DEFLATED) as archive:
            if media_root.exists():
                for path in sorted(media_root.rglob('*')):
                    if path.is_file():
                        archive.write(path, path.relative_to(media_root))

        manifest = {
            'created_at_utc': timestamp,
            'database': {
                'file': database_backup.name,
                'sha256': file_sha256(database_backup),
                'integrity_check': integrity_result,
            },
            'media': {
                'file': media_backup.name,
                'sha256': file_sha256(media_backup),
            },
        }
        manifest_path = backup_dir / 'manifest.json'
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )

        self.stdout.write(self.style.SUCCESS(f'Respaldo creado y verificado: {backup_dir}'))


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()
