import sys

from common.models import Arch
import middleware
from middleware import add_changeset_entry
from models import Logging, ChangeSet, ChangeSetEntry

from django.core import management
from django.core.management import sql, color
from django.db import connection, models
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
    def make_model(self):
        self.model = type('DummyModel', (models.Model,), {
                          'dummy_attr': models.CharField(max_length=255),
                          "__module__": "mlogging.tests"})

        self._style = color.no_style()

        self._cursor = connection.cursor()
        statements, pending = connection.creation.sql_create_model(self.model,
                                                                   self._style)
        for statement in statements:
            self._cursor.execute(statement)
        ContentType.objects.get_for_model(self.model).save()

    def setUp(self):
        test_user = User.objects.create_user("test_user", "test_user@mail.com")
        test_user.set_password("test_pass")
        test_user.save()
        self.user = authenticate(username="test_user", password="test_pass")
        self.rf = RequestMock()
        self.make_model()
        #self.model.save(self.model)
        dm = self.model.objects.create(dummy_attr="some value")

        dm.save()

        self.l_instance = middleware.LoggingMiddleware()

    def tearDown(self):
        statements = connection.creation.sql_destroy_model(self.model, (),
                                                           self._style)
        for statement in statements:
            self._cursor.execute(statement)

    def test_middle_x(self):
        request = self.rf.request(REQUEST_METHOD='POST')
        login(request, self.user)
        self.l_instance.process_request(request)
        dummy_o = self.model.objects.all()[0]
        #print >> sys.stderr, dummy_o
        with middleware.Log(request, {"dummy_o": dummy_o}):
            dummy_o.dummy_attr = "silly value"

        response = lambda x: x
        response.status_code = 200

        self.l_instance.process_response(request, response)

        middles = Logging.objects.all()
        changesets = ChangeSet.objects.all()
        entries = ChangeSetEntry.objects.all()
        self.assertEqual(len(middles), 1)
        self.assertEqual(len(changesets), 1)
        self.assertEqual(len(entries), 1)

        self.assertEqual(middles[0].changeset, changesets[0])
        self.assertEqual(entries[0].changeset, changesets[0])
        self.assertEqual(changesets[0].user, self.user)
        self.assertEqual(entries[0].model,
                         ContentType.objects.get_for_model(self.model))

    def test_middle_manual(self):
        request = self.rf.request(REQUEST_METHOD='POST')
        login(request, self.user)
        self.l_instance.process_request(request)
        dummy_o = self.model.objects.all()[0]

        old_dummy = {"id": dummy_o.id, "dummy_attr": dummy_o.dummy_attr}
        dummy_o.dummy_attr = "new dummy value"
        new_dummy = {"id": dummy_o.id, "dummy_attr": dummy_o.dummy_attr}
        add_changeset_entry(request, "test_middle_manual",
                            [ContentType.objects.get_for_model(dummy_o._meta.model)],
                            {"dummy_o": old_dummy}, {"dummy_o": new_dummy})

        response = lambda x: x
        response.status_code = 200

        self.l_instance.process_response(request, response)

        middles = Logging.objects.all()
        changesets = ChangeSet.objects.all()
        entries = ChangeSetEntry.objects.all()
        self.assertEqual(len(middles), 1)
        self.assertEqual(len(changesets), 1)
        self.assertEqual(len(entries), 1)

        self.assertEqual(middles[0].changeset, changesets[0])
        self.assertEqual(entries[0].changeset, changesets[0])
        self.assertEqual(changesets[0].user, self.user)
        self.assertEqual(entries[0].model,
                         ContentType.objects.get_for_model(self.model))
