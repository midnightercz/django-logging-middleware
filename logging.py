from models import Logging, ChangeSet, ChangeSetEntry

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

import sys
import inspect
import json


class LoggingMiddleware(object):
    registred_method = set()

    def process_request(self, request):
        if request.method != "GET":
            request.changeset = []
        #Logging.objects.all().delete()
        #ChangeSet.objects.all().delete()
        #ChangeSetEntry.objects.all().delete()

    def process_response(self, request, response):
        if request.method == "GET":
            return response

        if response.status_code % 200 < 10 and hasattr(request, "changeset"):
            if not len(request.changeset):
                return response
            if request.user.username:
                user = User.objects.get(username=request.user.username)
            else:
                user = None
            changeset = ChangeSet.objects.create(user=user)
            for x in request.changeset:
                action = x["action"]
                for (model, old_args, new_args) in x["data"]:
                    kwargs = {"changeset": changeset, "action": action,
                              "model": model,
                              "old_args": json.dumps(old_args),
                              "new_args": json.dumps(new_args)}

                ch_entry = ChangeSetEntry.objects.create(**kwargs)
                ch_entry.save()

            logging = Logging.objects.create(changeset=changeset)

            logging.save()
            changeset.save()
        return response


class Log(object):
    def __init__(self, request, objs, exclude_fields={}):
        self.objs = objs
        self.request = request
        self.action = inspect.stack()[1][3]
        self.old_objs = {}
        self.new_objs = {}
        self.models = []
        self.exclude_fields = exclude_fields
        for obj_name, obj in self.objs.iteritems():
            old_obj = {}
            for x in obj._meta.fields:
                if x not in exclude_fields.get(obj_name, {}):
                    old_obj[x.name] = getattr(obj, x.name)
            self.old_objs[obj_name] = old_obj
            self.models.append(ContentType
                               .objects.get_for_model(obj._meta.model))

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        if not exc_type:
            for obj_name, obj in self.objs.iteritems():
                new_obj = {}
                for x in obj._meta.fields:
                    if x not in self.exclude_fields.get(obj_name, {}):
                        new_obj[x.name] = getattr(obj, x.name)
                self.new_objs[obj_name] = new_obj
            add_changeset_entry(self.request, self.action,
                                self.models, self.old_objs, self.new_objs)
        else:
            raise exc_type, exc_value


def add_changeset_entry(request, action, models, old_args, new_args):
    chsetitem = {"action": action, "data": []}
    for model, old, new in zip(models,
                               old_args.itervalues(), new_args.itervalues()):
        chsetitem["data"].append((model, old, new))

    request.changeset.append(chsetitem)
