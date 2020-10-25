import pprint;

import vilo;

app = vilo.buildApp();
wsgi = app.wsgi;
app.setDebug(True);

@app.route("GET", "/")
def get_slash (req, res):
    return "Slash!";

@app.route("GET", "/hi/*/*")
def get_hi (req, res):
    fname, lname = req.wildcards;
    fullName = "%s %s" % (fname, lname);
    return vilo.escfmt("Hello, %s!", fullName.title());

@app.route("GET", "/hello/([^/]+)$", mode="re")
def get_hello_name (req, res):
    name = req.matched.groups()[0];
    print("name = ", name);
    return vilo.escfmt("Hello, %s!", name.title());

@app.route("GET", "/setCookie/(\w+)/(\w+)$", mode="re")
def get_setCookie (req, res):
    name, val = req.matched.groups();
    res.setCookie(name, val);
    return vilo.escfmt("Set cookie:<br>%s = %s", (name, val));

@app.route("GET", "/getCookie/(\w+)$", mode="re")
def get_getCookie (req, res):
    name = req.matched.groups()[0];
    return vilo.esc(req.getCookie(name)) or '/not found/';

#@app.route("GET", "/static/(.+)", mode="re")
#def get_static_file (req, res):
#    relpath = req.matched.groups()[0];
#    return res.staticFile("./static/" + relpath);

@app.route("GET", "/foo")
def get_foo (req, res):
    return res.redirect("/bar");

@app.route("GET", "/bar")
def get_bar (req, res):
    return "Ich bin BAR!";

@app.route("GET", "/factorial")
def get_factorial (req, res):
    pprint.pprint(req.qdata);
    n = int(req.qdata.get("n", 0));
    print("n =", n);
    f = lambda x: 1 if x <= 1 else x * f(x - 1);
    return str(f(n));

@app.route("GET", "/echo")
def get_echo (req, res):
    tpldata = {
        "foo": req.qdata.get("foo") or "",
        "bar": req.qdata.get("bar") or "",
    };
    return vilo.escfmt("""
    <h2>Echo Form</h2>
    <form method="POST" enctype="multipart/form-data">
        <input type="text" name="foo" value="%(foo)s" placeholder="Foo"><br>
        <input type="text" name="bar" value="%(bar)s" placeholder="Bar"><br>
        <input type="file" name="fup"><br>
        <button>Submit</button>
        <hr>
    </form>
    <h3>
    Foo: %(foo)s<br><br>
    Bar: %(bar)s<br><br>
    <a href="javascript: history.back();">&lt; Back</a>
    """, tpldata);

@app.route("POST", "/echo")
def post_echo (req, res):
    tpldata = {
        "foo": req.fdata.get("foo") or "",
        "bar": req.fdata.get("bar") or "",
    };
    pprint.pprint(req.fdata);
    return vilo.escfmt("""
        Foo: %(foo)s<br><br>
        Bar: %(bar)s<br><br>
        <a href="javascript: history.back();">&lt; Back</a>
    """, tpldata);

@app.route("GET", "/teapot")
def get_teapot (req, res):
    raise vilo.error("<h2>Ich bin ein teapot!</h2>", 418);

#@app.route("GET", "/static/**")
#def get_static (req, res):
#    relpath = req.wildcards[0];
#    return vilo.escfmt("./static/%s", relpath)


#@app.onViloErrorTag("routeNotFound")
#def routeNotFound (req, res, err):
#    return {"hello": "error"};
