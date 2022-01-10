from ... import a

a.evil_was_imported = True


class MyException(BaseException):
    pass


raise MyException("Can't import this!")
