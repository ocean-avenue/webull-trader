# Generated by Django 3.1.7 on 2021-05-28 02:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webull_trader', '0006_auto_20210527_2043'),
    ]

    operations = [
        migrations.CreateModel(
            name='TradingLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('log_text', models.TextField(blank=True, null=True)),
            ],
        ),
    ]
