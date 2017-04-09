# -*- coding: utf-8 -*-


def doc(func):
    """
        Find the message shown when someone calls the help command
    
    Parameters
    ----------
    func : function
        the function
    
    Returns
    -------
    str
        The help message for this command
    """
    stripped_chars = " \t"

    if hasattr(func, '__doc__'):
        docstring = func.__doc__.lstrip(" \n\t")
        if "\n" in docstring:
            i = docstring.index("\n")
            return docstring[:i].rstrip(stripped_chars)
        elif docstring:
            return docstring.rstrip(stripped_chars)

    return ""


def permission_check(data, command_permissions, command=None, permissions=None):
    """
        Check the permissions of the user requesting a command

    Parameters
    ----------
    data : dict
        message data
    command_permissions : dict
        permissions of the command, contains all the roles as key and users
        with these permissions as values
    command : function
        the command that is run
    permissions : :obj:`tuple`, :obj:`list`
        a list of permissions for the command
    
    Returns
    -------
    bool
        True if the user has the right permissions, False otherwise
    """
    if permissions:
        pass
    elif command:
        if hasattr(command, 'permissions'):
            permissions = command.permissions
        else:
            return True  # true if no permission is required
    else:
        msg = "{name} must be called with command or permissions argument"
        raise RuntimeError(msg.format(name="_permission_check"))

    return any(data['sender']['id'] in command_permissions[permission]
               for permission in permissions
               if permission in command_permissions)


def restart_on(exc):
    """
        restart a function every time the `exc` exception is raised
        
    Parameters
    ----------
    exc : Exception
        the exception to catch
    """
    def decorator(func):
        while True:
            try:
                return func
            except exc:
                pass
            except:
                raise

    return decorator
