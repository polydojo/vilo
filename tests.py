import pprint;

import dotsi;
import vilo;

app = vilo.buildApp();
wsgi = app.wsgi;
app.setDebug(True);

def test_wildcardMatch ():
    f = lambda w, a: vilo.checkWildcardMatch(w, a, dotsi.fy({}));
    assert f("/*", "/foo") is True;
    assert f("/*", "/") is False;
    assert f("/foo/*", "/foo/bar") is True;
    assert f("/foo/*", "/foo/bar/baz") is False;
    assert f("/s/**", "/s/foo") is True;
    assert f("/s/**", "/s/foo/bar") is True;
    assert f("/s/**", "/s/") is False;
    assert f("/*/do", "/foo/do") is True;
    assert f("/*/do", "/foo/bar/do") is False;
    assert f("/*/do", "//do") is False;
    assert f("/*/do/**", "/x/do/y") is True;
    assert f("/*/do/**", "/x/do/y/z") is True;
    assert f("/*/do/**", "/x/do/") is False;
    assert f("/*/do/**", "//do/y/z") is False;
    print("\nWildcard matching tests passed.\n");
    return True;
assert test_wildcardMatch();

# TODO: Write more tests.
