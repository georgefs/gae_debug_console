# -*- coding: utf-8 -*-
"""
    werkzeug.debug.repr
    ~~~~~~~~~~~~~~~~~~~

    This module implements object representations for debugging purposes.
    Unlike the default repr these reprs expose a lot more information and
    produce HTML instead of ASCII.

    Together with the CSS and JavaScript files of the debugger this gives
    a colorful and more compact output.

    :copyright: (c) 2011 by the Werkzeug Team, see AUTHORS for more details.
    :license: BSD.
"""
import sys
import re
from traceback import format_exception_only
try:
    from collections import deque
except ImportError: # pragma: no cover
    deque = None

from backlash._compat import text_, text_type, binary_type, iteritems_, string_types, long, PY3
from backlash.utils import escape

missing = object()
_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')
RegexType = type(_paragraph_re)


HELP_HTML = '''\
<div class=box>
  <h3>%(title)s</h3>
  <pre class=help>%(text)s</pre>
</div>\
'''
OBJECT_DUMP_HTML = '''\
<div class=box>
  <h3>%(title)s</h3>
  %(repr)s
  <table>%(items)s</table>
</div>\
'''


def debug_repr(obj):
    """Creates a debug repr of an object as HTML unicode string."""
    return DebugReprGenerator().repr(obj)


def dump(obj=missing):
    """Print the object details to stdout._write (for the interactive
    console of the web debugger.
    """
    gen = DebugReprGenerator()
    if obj is missing:
        rv = gen.dump_locals(sys._getframe(1).f_locals)
    else:
        rv = gen.dump_object(obj)
    sys.stdout._write(rv)


class _Helper(object):
    """Displays an HTML version of the normal help, for the interactive
    debugger only because it requires a patched sys.stdout.
    """

    def __repr__(self):
        return 'Type help(object) for help about object.'

    def __call__(self, topic=None):
        if topic is None:
            sys.stdout._write('<span class=help>%s</span>' % repr(self))
            return
        import pydoc
        pydoc.help(topic)
        rv = text_(sys.stdout.reset(), 'utf-8', 'ignore')
        paragraphs = _paragraph_re.split(rv)
        if len(paragraphs) > 1:
            title = paragraphs[0]
            text = '\n\n'.join(paragraphs[1:])
        else: # pragma: no cover
            title = 'Help'
            text = paragraphs[0]
        sys.stdout._write(HELP_HTML % {'title': title, 'text': text})

helper = _Helper()


def _add_subclass_info(inner, obj, bases):
    if isinstance(bases, tuple):
        for base in bases:
            if type(obj) is base:
                return inner
    elif type(obj) is bases:
        return inner
    module = ''
    if obj.__class__.__module__ not in ('builtins', '__builtin__','exceptions'):
        module = '<span class="module">%s.</span>' % obj.__class__.__module__
    return '%s%s(%s)' % (module, obj.__class__.__name__, inner)


class DebugReprGenerator(object):

    def __init__(self):
        self._stack = []

    def _sequence_repr_maker(left, right, base=object(), limit=8):
        def proxy(self, obj, recursive):
            if recursive:
                return _add_subclass_info(left + '...' + right, obj, base)
            buf = [left]
            have_extended_section = False
            for idx, item in enumerate(obj):
                if idx:
                    buf.append(', ')
                if idx == limit:
                    buf.append('<span class="extended">')
                    have_extended_section = True
                buf.append(self.repr(item))
            if have_extended_section:
                buf.append('</span>')
            buf.append(right)
            return _add_subclass_info(text_(''.join(buf)), obj, base)
        return proxy

    list_repr = _sequence_repr_maker('[', ']', list)
    tuple_repr = _sequence_repr_maker('(', ')', tuple)
    set_repr = _sequence_repr_maker('set([', '])', set)
    frozenset_repr = _sequence_repr_maker('frozenset([', '])', frozenset)
    if deque is not None:
        deque_repr = _sequence_repr_maker('<span class="module">collections.'
                                          '</span>deque([', '])', deque)
    del _sequence_repr_maker

    def regex_repr(self, obj):
        if PY3:
            pattern = text_("'%s'" % str(obj.pattern), 'string-escape', 'ignore')
            pattern = 'r' + pattern
        else:
            pattern = text_(repr(obj.pattern), 'string-escape', 'ignore')
            if pattern[:1] == 'u':
                pattern = 'ur' + pattern[1:]
            else:
                pattern = 'r' + pattern
        return text_(
            're.compile(<span class="string regex">%s</span>)' % pattern)

    def py2_string_repr(self, obj, limit=70):
        buf = ['<span class="string">']
        escaped = escape(obj)
        a = repr(escaped[:limit])
        b = repr(escaped[limit:])
        if isinstance(obj, text_type):
            buf.append('u')
            a = a[1:]
            b = b[1:]
        if b != "''":
            buf.extend((a[:-1], '<span class="extended">', b[1:], '</span>'))
        else:
            buf.append(a)
        buf.append('</span>')
        return _add_subclass_info(text_('').join(buf), obj, (str, unicode))

    def py3_text_repr(self, obj, limit=70):
        buf = ['<span class="string">']
        escaped = escape(obj)
        a = repr(escaped[:limit])
        b = repr(escaped[limit:])
        if b != "''":
            buf.extend((a[:-1], '<span class="extended">', b[1:], '</span>'))
        else:
            buf.append(a)
        buf.append('</span>')
        return _add_subclass_info(text_(''.join(buf)), obj, text_type)

    def py3_binary_repr(self, obj, limit=70):
        buf = ['<span class="string">']
        escaped = escape(text_(obj, 'utf-8', 'replace'))
        a = repr(escaped[:limit])
        b = repr(escaped[limit:])
        buf.append('b')
        if b != "''":
            buf.extend((a[:-1], '<span class="extended">', b[1:], '</span>'))
        else:
            buf.append(a)
        buf.append('</span>')
        return _add_subclass_info(text_(''.join(buf)), obj, binary_type)

    def dict_repr(self, d, recursive, limit=5):
        if recursive:
            return _add_subclass_info(text_('{...}'), d, dict)
        buf = ['{']
        have_extended_section = False
        for idx, (key, value) in enumerate(iteritems_(d)):
            if idx:
                buf.append(', ')
            if idx == limit - 1:
                buf.append('<span class="extended">')
                have_extended_section = True
            buf.append('<span class="pair"><span class="key">%s</span>: '
                       '<span class="value">%s</span></span>' %
                       (self.repr(key), self.repr(value)))
        if have_extended_section:
            buf.append('</span>')
        buf.append('}')
        return _add_subclass_info(text_(''.join(buf)), d, dict)

    def object_repr(self, obj):
        return text_('<span class="object">%s</span>' %
                     escape(text_(repr(obj), 'utf-8', 'replace')))

    def dispatch_repr(self, obj, recursive):
        if obj is helper:
            return text_('<span class="help">%r</span>' % helper)
        if isinstance(obj, (int, long, float, complex)):
            return text_('<span class="number">%r</span>' % obj)
        if PY3:
            if isinstance(obj, text_type):
                return self.py3_text_repr(obj)
            if isinstance(obj, binary_type):
                return self.py3_binary_repr(obj)
        else:
            if isinstance(obj, basestring):
                return self.py2_string_repr(obj)
        if isinstance(obj, RegexType):
            return self.regex_repr(obj)
        if isinstance(obj, list):
            return self.list_repr(obj, recursive)
        if isinstance(obj, tuple):
            return self.tuple_repr(obj, recursive)
        if isinstance(obj, set):
            return self.set_repr(obj, recursive)
        if isinstance(obj, frozenset):
            return self.frozenset_repr(obj, recursive)
        if isinstance(obj, dict):
            return self.dict_repr(obj, recursive)
        if deque is not None and isinstance(obj, deque):
            return self.deque_repr(obj, recursive)
        return self.object_repr(obj)

    def fallback_repr(self):
        try:
            info = ''.join(format_exception_only(*sys.exc_info()[:2]))
        except Exception: # pragma: no cover
            info = '?'
        return text_(
            '<span class="brokenrepr">&lt;broken repr (%s)&gt;'
            '</span>' % escape(text_(info, 'utf-8', 'ignore').strip())
        )

    def repr(self, obj):
        recursive = False
        for item in self._stack:
            if item is obj:
                recursive = True
                break
        self._stack.append(obj)
        try:
            try:
                return self.dispatch_repr(obj, recursive)
            except Exception:
                return self.fallback_repr()
        finally:
            self._stack.pop()

    def dump_object(self, obj):
        repr = items = None
        if isinstance(obj, dict):
            title = 'Contents of'
            items = []
            for key, value in iteritems_(obj):
                if not isinstance(key, string_types):
                    items = None
                    break
                items.append((key, self.repr(value)))
        if items is None:
            items = []
            repr = self.repr(obj)
            for key in dir(obj):
                try:
                    items.append((key, self.repr(getattr(obj, key))))
                except Exception:
                    pass
            title = 'Details for'
        title += ' ' + object.__repr__(obj)[1:-1]
        return self.render_object_dump(items, title, repr)

    def dump_locals(self, d):
        items = [(key, self.repr(value)) for key, value in d.items()]
        return self.render_object_dump(items, 'Local variables in frame')

    def render_object_dump(self, items, title, repr=None):
        html_items = []
        for key, value in items:
            html_items.append('<tr><th>%s<td><pre class=repr>%s</pre>' %
                              (escape(key), value))
        if not html_items:
            html_items.append('<tr><td><em>Nothing</em>')
        return OBJECT_DUMP_HTML % {
            'title':    escape(title),
            'repr':     repr and '<pre class=repr>%s</pre>' % repr or '',
            'items':    '\n'.join(html_items)
        }