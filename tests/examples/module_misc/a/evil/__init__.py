from ... import a

a.evil_was_imported = True


raise RuntimeError("Can't import this!")
