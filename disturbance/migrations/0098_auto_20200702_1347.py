# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2020-07-02 05:47
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0097_remove_annualrentalfee_payment_type'),
    ]

    operations = [
        migrations.RenameField(
            model_name='annualrentalfeeinvoice',
            old_name='annual_rent_fee',
            new_name='annual_rental_fee',
        ),
    ]
