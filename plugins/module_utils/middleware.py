# The TrueNAS middleware can be controlled in different ways: through
# the 'midclt' command-line tool, through a REST API, maybe others.
# The REST API is the recommended one.
#
# Since all of these methods provide the same functions, take the same
# arguments, and return the same results, we want users to be able to
# choose the one that works best for them. This module is a layer that
# sits between individual modules and the middleware, and uses
# whichever access method is chosen.

import os

# XXX - Ought to define an exception type for things that can go wrong
# with middleware calls.

class MiddleWare:
    def __init__(self):
        # Decide which API to use.
        #
        # There's no good way to have a config variable from
        # ansible.cfg show up here, in a module executed on the
        # client. The next-best thing is to use an environment
        # variable, which can be passed in the play, e.g.:
        #
        # - hosts: my-nas
        #   collections: arensb.truenas
        #   environment:
        #     middleware_method: client
        #   tasks:
        #     ...

        method = os.getenv('middleware_method', 'client')

        # We import here, rather than at the top of the code, because
        # at least in theory, the desired module might not exist on
        # the remote host.
        if method == 'midclt':
            from ansible_collections.arensb.truenas.plugins.module_utils.midclt \
                import Midclt
            self.client = Midclt
        elif method == 'client':
            from ansible_collections.arensb.truenas.plugins.module_utils.client \
                import MiddlewareClient
            self.client = MiddlewareClient
        else:
            # Shouldn't use illegal methods. Bad caller!
            raise Exception(f"Unknown middleware method {method}")

        self.method = f"Selected method {self.client}"

    def call(self, func, *args, **kwargs):
        return self.client.call(func, *args, **kwargs)

    def job(self, func, *args, **kwargs):
        return self.client.job(func, *args, **kwargs)
