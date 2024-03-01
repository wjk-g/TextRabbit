from flask import session

def clear_cached_data():
    '''
    Clears all cookies (all previous data) before loading new data
    Preserves csrf_token and login information
    '''
    keys_to_preserve = {"csrf_token", "logged_in", "storage"}
    
    for key in list(session.keys()):
        if key not in keys_to_preserve:
            session.pop(key)
