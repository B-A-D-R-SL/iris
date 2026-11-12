# AI contribution: 50% or more AI-generated

from contextlib import ExitStack
from socket import create_connection

from django.test.testcases import QuietWSGIRequestHandler

from modules.households.tests.search_load_client import CLIENT_WORKERS
from modules.households.tests.search_load_server import LoadWSGIServer


def test_listener_accepts_the_full_client_burst_before_serving_requests():
    with (
        LoadWSGIServer(("127.0.0.1", 0), QuietWSGIRequestHandler) as server,
        ExitStack() as clients,
    ):
        # A descheduled accept loop must not force clients into TCP retransmission.
        for _ in range(CLIENT_WORKERS):
            clients.enter_context(create_connection(server.server_address, timeout=5))
