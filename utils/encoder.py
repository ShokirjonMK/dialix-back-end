import json
import datetime


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        return super(DateTimeEncoder, self).default(o)


def adapt_json(obj):
    return json.loads(json.dumps(obj, cls=DateTimeEncoder))
