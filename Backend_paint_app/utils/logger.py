import logging


def get_logger(name='app'):
    return logging.getLogger(name)


def log_request_info(logger, request, message='', level='info'):
    if request.user.is_authenticated:
        username = request.user.username
    else:
        username = request.data.get('username') or 'Anonymous'

    ip = request.META.get('REMOTE_ADDR', 'unknown')
    full_message = f"{message} [username={username}, IP={ip}]"

    if level == 'info':
        logger.info(full_message)
    elif level == 'warning':
        logger.warning(full_message)
    elif level == 'error':
        logger.error(full_message)
    elif level == 'debug':
        logger.debug(full_message)
    else:
        logger.info(full_message)

