from flask import request


class Paginator:

    def __init__(self, items):
        self.perpage = request.args['perpage'] or 10
        self.page = request.args['page'] or 1

        self.pages = range(1, ((len(items) - 1) / self.perpage) + 1)

        self.items = items[(self.perpage * (self.page - 1)):(self.perpage * self.page)]
