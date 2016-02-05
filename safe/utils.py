import warnings


def deprecated(message):
    def decorator(func):
        def new_func(*args, **kwargs):
            warnings.warn(message, category=DeprecationWarning)
            return func(*args, **kwargs)
        return new_func
    return decorator
