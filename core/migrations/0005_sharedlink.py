# Generated by Django 5.2.4 on 2025-07-10 17:49

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_sharedflashcard_sharednote_sharedquiz'),
    ]

    operations = [
        migrations.CreateModel(
            name='SharedLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('link_id', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('content_type', models.CharField(max_length=20)),
                ('content_id', models.IntegerField()),
                ('access_level', models.CharField(choices=[('public', 'Public'), ('private', 'Private'), ('group', 'Group Only')], default='public', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('title', models.CharField(blank=True, max_length=255)),
                ('description', models.TextField(blank=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.studygroup')),
            ],
            options={
                'unique_together': {('content_type', 'content_id')},
            },
        ),
    ]
