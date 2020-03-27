import json


# TODO: Add an items() implementation 
class PyJSON(object):
    def __init__(self, d):
        if type(d) is str:
            d = json.loads(d)
        self.from_dict(d)
        self._keys = d.keys()  # use this to create the items iterator

    def from_dict(self, d):
        self.__dict__ = {}
        for key, value in d.items():
            if type(value) is dict:
                value = PyJSON(value)
            elif type(value) is list:
                # replace any dict entries with recursions
                for idx, x in enumerate(value):
                    if type(x) == dict:
                        value[idx] = PyJSON(x)
            self.__dict__[key] = value

    def to_dict(self):
        d = {}
        for key, value in self.__dict__.items():
            if type(value) is PyJSON:
                value = value.to_dict()
            elif type(value) is list:
                for idx, x in enumerate(value):
                    if type(x) == PyJSON:
                        value[idx] = x.to_dict()
            d[key] = value
        return d

    def __repr__(self):
        return str(self.to_dict())

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __getitem__(self, key):
        return self.__dict__[key]


if __name__ == '__main__':
    # Only run if this is executed as a script
    j = '{ "a": { "a1" : 1, "a2":3 }, "b": {"b1": "b_one", "b2": "b_two"}, "c": [3,4,5]}'
    d = PyJSON(j)
    print(d.c)


