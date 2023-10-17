import sys
from jinja2 import Template

templ = """

{% for user in users %}

{{ user.username }}

{% endfor %}

"""


class User(object):
    __slots__ = ('user_id', 'username')

    def __init__(self, user_id, username):
        self.user_id = user_id
        self.username = username


def render_template(user_id):
    users = [
        User(user_id, 'SomeUsername')
    ]

    template = Template(templ)
    return template.render(users=users)


def main():
    n = int(sys.argv[1])

    for i in range(n):
        res = render_template(i)

    print(res)


main()