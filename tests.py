import pprint;

import dotsi;
import vilo;

app = vilo.buildApp();
wsgi = app.wsgi;
app.setDebug(True);

# TODO: Switch to a proper testing framework like unittest.
# TODO: Create mini-apps and test 'em with requests.

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

def test_routeFindAndPop ():
    app = vilo.buildApp();
    mkH = lambda rv: (lambda *a: rv);   # mkH: MaKe Handler
    app.route("GET", "/", name="home")(mkH('Home'));
    app.route("GET", "/pg1")(mkH('Page 1'));
    app.route("GET", "/pg2")(mkH('Page 2'));
    app.route("GET", "/pgX", name="pgX")(mkH("Page X"));
    assert app.findNamedRoute("home");
    try:
        app.route("GET", "/", name="home")(mkH('Home #2'));
        assert False; # <-- Line must be unreachable.
    except ValueError as e:
        assert True;  # <-- We expect a ValueError to be raised.
    assert not app.findNamedRoute("pg1");
    assert app.findNamedRoute("pgX");
    app.popNamedRoute("pgX");
    assert not app.findNamedRoute("pgX");
    app.route("GET", "/pgX", name="pgX")(mkH("Page X2"));

############################################################
# Run All Tests: ###########################################
############################################################

if __name__ == "__main__":
    for (name, val) in dict(**locals()).items():
        if name.startswith("test_") and callable(val):
            print("\nRunning %s() ..." % name)
            val();
            print("Passed.")
    print("\nGreat! All tests passed.\n");

# End ######################################################
