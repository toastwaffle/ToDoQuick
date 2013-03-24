from flask import request


class Paginator:

    def __init__(self, items, query_tag=''):
        try:
            self.perpage = request.args[query_tag + 'perpage']
        except KeyError:
            self.perpage = 10

        try:
            self.page = request.args[query_tag + 'page']
        except KeyError:
            self.page = 1

        self.pages = range(1, ((len(items) - 1) / self.perpage) + 1)

        if self.perpage == 'All':
            self.items = items
        else:
            self.items = items[(self.perpage * (self.page - 1)):(self.perpage * self.page)]

        try:
            self.next = (self.page + 1) if (self.page < self.pages[-1]) else None
        except IndexError:
            self.next = None

        self.prev = (self.page - 1) if (self.page > 1) else None

        self.query_tag = query_tag
