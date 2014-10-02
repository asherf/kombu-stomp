from __future__ import absolute_import
import ast

from six.moves import queue

import stomp
from stomp import listener


class MessageListener(listener.ConnectionListener):
    def __init__(self, q=None):
        if not q:
            q = queue.Queue()

        self.q = q

    def on_message(self, headers, body):
        """Received message hook.

        :arg headers: message headers.
        :arg body: message body.
        """
        self.q.put(self.to_kombu_message(headers, body))

    def to_kombu_message(self, headers, body):
        """Get STOMP headers and body message and return a Kombu message dict.

        :arg headers: message headers.
        :arg body: message body.
        :return dict: A dictionary that Kombu can use for creating a new
            message object.
        """
        msg_id = headers['message-id']
        message = dict(
            [(header, value) for header, value in headers.items()
             # Remove STOMP specific headers
             if header not in ('destination',
                               'timestamp',
                               'message-id',
                               'expires',
                               'priority')]
        )
        # properties is a dictionary and we need evaluate it
        message['properties'] = ast.literal_eval(message['properties'])
        message['body'] = body
        return message, msg_id

    def iterator(self, timeout):
        """Return a Python generator consuming received messages.

        If we try to consume a message and there is no messages remaining, then
        an exception will be raised.

        :arg int timeout: Time to wait for message in seconds, a falsy value if
            we shouldn't block for incoming messages.
        :yields dict: A dictionary representing the message in a Kombu
            compatible format.
        :raises Empty: When there is no message to be consumed.
        """
        while True:
            # Block only if get got a timeout
            yield self.q.get(block=bool(timeout), timeout=timeout)


class Connection(stomp.Connection10):
    def __init__(self, *args, **kwargs):
        super(Connection, self).__init__(*args, **kwargs)
        self.message_listener = MessageListener()
        self.set_listener('message_listener', self.message_listener)