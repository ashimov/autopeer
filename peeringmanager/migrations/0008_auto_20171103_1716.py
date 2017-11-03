# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-11-03 17:16
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('peeringmanager', '0007_auto_20171102_0210'),
    ]

    operations = [
        migrations.AlterField(
            model_name='peering',
            name='asn',
            field=models.BigIntegerField(help_text='Your MNTNER object must be listed as mnt-by for the AS', verbose_name='AS Number'),
        ),
    ]
