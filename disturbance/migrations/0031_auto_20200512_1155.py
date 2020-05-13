# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2020-05-12 03:55
from __future__ import unicode_literals

import disturbance.components.compliances.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0030_auto_20200511_1512'),
    ]

    operations = [
        migrations.AddField(
            model_name='apiarysite',
            name='site_category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='disturbance.SiteCategory'),
        ),
        migrations.AlterField(
            model_name='compliancedocument',
            name='_file',
            field=models.FileField(max_length=500, upload_to=disturbance.components.compliances.models.update_proposal_complaince_filename),
        ),
    ]
