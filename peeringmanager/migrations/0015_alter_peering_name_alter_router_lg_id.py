# Generated by Django 4.0.2 on 2022-02-04 04:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('peeringmanager', '0014_alter_peering_id_alter_router_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='peering',
            name='name',
            field=models.CharField(help_text='A human-readable name for this peering. Usually your nickname or a network name. Used for the Wireguard interface name, in the looking glass, and similar places. Lowercase ASCII only, max. 25 chars.', max_length=25, verbose_name='Peering name'),
        ),
        migrations.AlterField(
            model_name='router',
            name='lg_id',
            field=models.CharField(max_length=150, verbose_name='Looking Glass ID'),
        ),
    ]
