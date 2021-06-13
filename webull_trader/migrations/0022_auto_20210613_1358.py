# Generated by Django 3.1.7 on 2021-06-13 17:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webull_trader', '0021_tradingsettings_avg_confirm_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='tradingsettings',
            name='extended_avg_confirm_amount',
            field=models.FloatField(default=30000),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tradingsettings',
            name='extended_avg_confirm_volume',
            field=models.FloatField(default=3000),
            preserve_default=False,
        ),
    ]