# -*- coding: utf-8 -*-

from django.db import models
from django.db.models.signals import pre_save
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType


class ChangeSet(models.Model):
    date = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, null=True)

class Logging(models.Model):
    changeset = models.ForeignKey(ChangeSet)

class ChangeSetEntry(models.Model):
    changeset = models.ForeignKey(ChangeSet)
    action = models.CharField(max_length=200)
    model = models.ForeignKey(ContentType)
    old_args = models.CharField(max_length=200)
    new_args = models.CharField(max_length=200)




def validate_model(sender, **kwargs):
    if "raw" in kwargs and not kwargs["raw"]:
        kwargs["instance"].full_clean()


pre_save.connect(validate_model, sender=Logging)
pre_save.connect(validate_model, sender=ChangeSet)
pre_save.connect(validate_model, sender=ChangeSetEntry)
