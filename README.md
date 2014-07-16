django-logging-middleware
=========================
What is django-logging-middleware good for
--------------------------------------------------------
Django-logging-middleware provides you comfort of preserving history of changes in specified actions for specied models. Theese change history records contains who

 * commited a change
 * what action was triggered
 * when was change made
 * what was changed.

With this knowledge you can revert any changes made on selected model. Althrough you have to write revert mechanism yourself.

Example: how to use django-logging-middleware
-------------------------------------------------------------
simplest usage of logging is put something like this into your api
```python
    myobj = MyModel.objects.all()[0]
    with logging.Log(request, {"myobj": myobj}):
        myobj.someattribute = "another value"
```

or manually:

```python
    myobj = MyModel.objects.all()[0]
    old_obj = {"someattribute": myobj.someattribute, "id": myobj.someattribute}
    myobj.someattribute = "another value"
    new_obj = {"someattribute": myobj.someattribute, "id": myobj.someattribute}
    logging.add_changeset_entry(request, "my_action,
                                [ContentType.objects.get_for_model(MyModel)],
                                {"myobj": old_obj},
                                {"my_model": new_obj})
```

Including django-logging-middleware into your project
--------------------------------------------------------------------
Django-logging-middleware is designed as django app because custom db models. To use it in your project, simply clone this repository and put `mlogging` directory into your django app directory and modify settings:

```python
    INSTALLED_APPS = (
    ....
    "mlogging"
    )

    MIDDLEWARE_CLASSES = (
    ....
    "mlogging.middle.LoggingMiddleware"
    )
```

Notes
-----
If you decide use Log context manager, you can specify exclude_fields for each
objects to prevent store excluded fields into db. By default context manager Log
store all fields of objects

```python
    with logging.Log(request, {"myobj": myobj},
                     exclude_fields={"myobj": ["not_this field"]}):
```
