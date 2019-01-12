# Generated by Django 2.1.5 on 2019-01-12 20:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('heatmap', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Block',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('latitude', models.DecimalField(decimal_places=4, max_digits=6)),
                ('longitude', models.DecimalField(decimal_places=4, max_digits=6)),
                ('name', models.CharField(max_length=100)),
                ('resources', models.IntegerField(default=0)),
                ('orders', models.IntegerField(default=0)),
            ],
        ),
    ]
