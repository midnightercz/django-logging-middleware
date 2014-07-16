import sys

from common.models import Arch
import logging
from logging import add_changeset_entry
from models import Logging, ChangeSet, ChangeSetEntry

from django.test import TestCase
from django.test.client import RequestFactory
from django.core.handlers.base import BaseHandler
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.contenttypes.models import ContentType


class RequestMock(RequestFactory):
    def request(self, **request):
        "Construct a generic request object."
        request = RequestFactory.request(self, **request)
        handler = BaseHandler()
        handler.load_middleware()
        for middleware_method in handler._request_middleware:
            if middleware_method(request):
                raise Exception("Couldn't create request mock object - "
                                "request middleware returned a response")
        return request


def user_login(test_case, name, pswd, **request):
    request = test_case.rf.request(**request)
    user = authenticate(username="test_user", password="test_pass")
    test_case.assertNotEqual(user, None)
    login(request, user)
    return request


class LoggingTest(TestCase):
    def setUp(self):
        test_user = User.objects.create_user("test_user", "test_user@mail.com")
        test_user.set_password("test_pass")
        test_user.save()
        self.user = authenticate(username="test_user", password="test_pass")
        self.rf = RequestMock()
        arch = Arch.objects.create(name="dummy arch")
        arch.save()
        self.l_instance = logging.LoggingMiddleware()

    def test_logging(self):
        request = self.rf.request(REQUEST_METHOD='POST')
        login(request, self.user)
        self.l_instance.process_request(request)
        arch = Arch.objects.all()[0]
        with logging.Log(request, {"arch": arch}):
            arch.name = "silly arch"

        response = lambda x: x
        response.status_code = 200

        self.l_instance.process_response(request, response)

        loggings = Logging.objects.all()
        changesets = ChangeSet.objects.all()
        entries = ChangeSetEntry.objects.all()
        self.assertEqual(len(loggings), 1)
        self.assertEqual(len(changesets), 1)
        self.assertEqual(len(entries), 1)

        self.assertEqual(loggings[0].changeset, changesets[0])
        self.assertEqual(entries[0].changeset, changesets[0])
        self.assertEqual(changesets[0].user, self.user)
        self.assertEqual(entries[0].model,
                         ContentType.objects.get_for_model(Arch))

    def test_logging_manual(self):
        request = self.rf.request(REQUEST_METHOD='POST')
        login(request, self.user)
        self.l_instance.process_request(request)
        arch = Arch.objects.all()[0]

        old_arch = {"id": arch.id, "name": arch.name}
        arch.name = "silly arch"
        new_arch = {"id": arch.id, "name": arch.name}
        add_changeset_entry(request, "test_logging_manual",
                            [ContentType.objects.get_for_model(Arch)],
                            {"arch": old_arch}, {"arch": new_arch})

        response = lambda x: x
        response.status_code = 200

        self.l_instance.process_response(request, response)

        loggings = Logging.objects.all()
        changesets = ChangeSet.objects.all()
        entries = ChangeSetEntry.objects.all()
        self.assertEqual(len(loggings), 1)
        self.assertEqual(len(changesets), 1)
        self.assertEqual(len(entries), 1)

        self.assertEqual(loggings[0].changeset, changesets[0])
        self.assertEqual(entries[0].changeset, changesets[0])
        self.assertEqual(changesets[0].user, self.user)
        self.assertEqual(entries[0].model,
                         ContentType.objects.get_for_model(Arch))
