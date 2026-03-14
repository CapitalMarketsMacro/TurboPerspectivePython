from concurrent.futures import ThreadPoolExecutor

import tornado.web
import perspective.handlers.tornado as psp_tornado

from perspective_manager import PerspectiveManager


def make_app(perspective_manager: PerspectiveManager) -> tornado.web.Application:
    executor = ThreadPoolExecutor(max_workers=8)
    return tornado.web.Application(
        [
            (
                r"/websocket",
                psp_tornado.PerspectiveTornadoHandler,
                {
                    "perspective_server": perspective_manager.get_server(),
                    "executor": executor,
                },
            ),
        ]
    )
