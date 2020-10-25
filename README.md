Vilo
====

Vilo is a WSGI micro-framework for building web apps with Python. Inspired by [Express](https://expressjs.com/) and [Bottle](https://bottlepy.org/), Vilo is lightweight, unopinionated, and flexible.

**Quick Plug:** Vilo is built by the folks at [Polydojo, Inc.](https://www.polydojo.com/) Effective project management is essential for building and maintaining web apps. If your team is looking for a simple project management tool, check out our latest product: BoardBell.com.

Installation
--------------
Please download `vilo.py` into your project directory.

 [Gunicorn](https://gunicorn.org/) is recommended for running Vilo apps (in development and production), installable via pip:
```
pip install gunicorn
```

Hello, World!
----------------

Create `hello.py`:
```py
import vilo;                # Import vilo

app = vilo.buildApp();      # Create app

@app.route("GET", "/")      # Add route
def get_homepage (req, res):
    return "Hello, World!";

wsgi = app.wsgi;            # WSGI callable
```

**Running with Gunicorn:**

For development, run with Gunicorn as follows:
```
gunicorn hello:wsgi --reload
```
The above line tells Gunicorn to run `wsgi` from `hello.py`. Once running, visit `localhost:8000` to access the app. In production, drop the `--reload` flag. Consult Gunicorn's docs for more.

Vilo vs Bottle/Flask/Express
-----------------------------------

**1. No Global `request` or `response`**:
Bottle and Flask both employ global `request` and `response` objects. Vilo instead, like Express, supplies `req` and `res` as arguments to each route handler. 

**2. Conspicuous HTTP Method(s)**:
Like Bottle and Flask, Vilo relies on the decorator-based `@app.route(...)` pattern for route definitions, but unlike them, Vilo encourages you to conspicuously specify the HTTP request method (or methods, as a list).

**3. No Built-In Templating**:
Bottle and Flask both include built-in templating engines. As an un-opinionated framework, Vilo doesn't. You may pick any templating engine you want. For illustration only, our examples will use [Qree](https://github.com/polydojo/qree), installable via `pip install qree`.

**4. No Built-In Development Server:**
Bottle and Flask include a development server with hot-reloads for local testing and development, but recommend *against* using it in production. Instead of pre-packaging a devlopment server, we recommend using Gunicorn with the `--reload` flag.


Basic Routes & Static Files
--------------------------------

Working with fixed routes is fairly straightforward. For instance, to handle the route `"/foo/bar"`, just supply that path to `app.route(.)` For example:

```py
# import vilo, define app etc.

@app.route("GET", "/foo/bar")
def get_foo_bar (req, res):
    return "You sent a GET request to path: /foo/bar";

@app.route("GET", "/task/1")
def get_listTasks (req, res):
    return yourLogic_showTask(1);

@app.route("GET", "/task/2")
def get_listTasks (req, res):
    return yourLogic_showTask(2);

@app.route("POST", "/newTask")
def post_newTask (req, res):
    return "You sent a POST request at path: /newTask";
```

If you have static CSS, JS, image or other static files, you can use `res.staticFile(filepath, [mimeType])` for serving them. For example, let's say you have the following directory structure:
```
- app.py
- config.py
- utils.py
- static/
        - jquery.js
        - logo.png
```
In such a case, you could serve jquery and your logo as follows:
```py
# import vilo, define app etc.

@app.route("GET", "/static/jquery.js")
def get_jquery (req, res):
    return res.staticFile("./static/jquery.js");

@app.route("GET", "/static/logo.png")
def get_bootstrap (req, res):
    return res.staticFile("./static/logo.png");
```
Optionally, you may pass `mimeType` to `res.staticFile(.)`. If not passed, it'll be guessed.

**_DRY_ = Don't Repeat Yourself**

You would've noticed that routes `/task/1` and `/task/2`, and similarly the routes `/static/jquery.js` and `/static/logo.png` are essentially the same. Repeating them twice not very DRY.

Right now, there seem to be just two tasks and two static files. But what if there were 10 each? 100 each? Instead of tediously repeating ourselves, we can use wildcard routes. That's next.


Wildcard Routes
--------------------

The URL path has multiple slash-separated *segments*. Use `*` for wildcard segment matching. *Exclusively at the end* of the URL, using `**` instead of a single `*` will match multiple segments, including slashes therebetween.

With the sole exception of `**` at the end of the URL, each `*` matches a *single but complete segment*. Thus, except at the end, each `*` must be sandwiched between two slashes: `/*/`.

The list of matched wildcards is available via `req.wildcards`.

**Examples:**
1. `/category/*/page/*/edit`
    - WILL match `/category/Food/page/Pasta/edit`
    with `req.wildcards = ['Food', 'Pasta']`.
    
    - but will NOT match `/category/Fo/od/page/Pasta/edit`
    because `Fo/od` are two separate segments.

2. `/cart/add-item/*`
    - will match `/cart/add-item/123`
      with `req.wildcards = ['123']`.
    
    - but will NOT match `/cart/add-item/12/3`
    because `12/3` are two separate segments.

3. `/static/**`
    - will match `/static/lib/js/jquery.js`
      with `req.wildcards = 'lib/javascript/jquery.js`

    - but will NOT match `/StaTiC/lib/js/jquery.js`
    because `StaTiC` won't match `static`.

Now, using wildcard routes, we could write:
```py
# import vilo, define app etc.

@app.route("GET", "/task/*")
def get_task (req, res):
    taskId = int(req.wildcards[0]);
    return yourLogic_showTask(1)

@app.route("GET", "/static/**")
def get_static (req, res):
    "Serves static files from the `static/` dir.";
    relpath = req.wildcards[0];
    return res.staticFile("./static/" + relpath);

@app.route("GET", "/category/*/season/*")
def get_category_season (req, res):
    "Serve product info by category and season."
    cateogry, season = req.wildcards;
    productsPage = doSomething(category, season);
    return productsPage;

``` 

Regular Expression Mode
-------------------------------

Wildcard patterns are powerful, but don't necessarily cover all use cases. For greater flexibility, you can rely on regular expressions.

Let's say we want to match routes like the following:
- `"/show-posts/from-2018-to-2020"`
- `"/show-posts/from-1915-to-2015"`

As each `*` matches an entire segment, we *CANNOT* use:
- `"/show-posts/from-*-to-*"`

Instead, we can use the following regular expression:
- `r"/show-posts/from-(\d+)-to-(\d+)"`

For using regular expression mode, pass `mode="re"` to `app.route(.)`. The resultant match-object is available as `req.matched`. For example:

```py
# import vilo, define app, etc.

@app.route("GET", r"/show-posts/from-(\d+)-to-(\d+)", mode="re")
def get_showPosts (req, res):
    fromYear, toYear = req.matched.groups();
    resultPage = yourLogic(fromYear, toYear);
    return resultPage;
```

**The `mode` parameter to `app.route(.)`:**
Generally speaking, there's *no need* to explicitly pass `mode`. It takes one of three values: 
`["re", "wildcard", "exact"]`.
- `"re"`: regular expression based on `re.match(.)`.
- `"wildcard":` wildcard matching, as explain hereabove.
- `"exact"`: exact equality, based on `==` operator.

If `mode` isn't passed, Vilo makes an educated guess.

Dot-Accessible Dictionary (`DotDict`)
-----------------------------------------------

Vilo makes heavy use of dot-accessible dictionaries. In fact, in all previous examples, `app`, `req` and `res` are all dot-accessible dictionaries!

> **Sidebar:**
> Vilo relies on [`Addict`](https://github.com/mewwts/addict), a great library for dot-accessible dictionaries. By default, `Addict` does *NOT* raise `KeyError` for missing keys, which can lead to hard-to-debug errors. Vilo defines and uses `DotDict`, a subclass of `Addict` that raises `KeyError` properly.
> 
> *Philosophy:* The Polydojo team strongly favours functional programming over classical OOP. *As far as possible*, we avoid writing classes. This is super-easy in JavaScript, especially because object properties are dot-accessible. `Addict` allows us to bring the same ease to Python.

**`DotDict` Usage:**
```py
>>> from vilo import DotDict
>>> 
>>> dd = DotDict({})
>>> dd
{}
>>> dd.foo = "foo"
>>> dd.foo
'foo'
>>> dd
{'foo': 'foo'}
>>> dd.bar = "bar"
>>> dd.bar
'bar'
>>> dd
{'foo': 'foo', 'bar': 'bar'}
>>> dd.baz
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
    ... (truncated) ...
  File "/...(cut).../vilo.py", line ..., in __missing__
    raise KeyError(key);
KeyError: 'baz'
>>> 
```

HTML Escaping & `%s`-Formatting
-----------------------------------------------

**Use `vilo.esc(string)` for escaping HTML:**
- `vilo.esc('foo')` => `'foo'`
- `vilo.esc('<b> HELLO </b>')`
  => `'&lt;b&gt; HELLO &lt;/b&gt;'`
- `vilo.esc('<script> alert("XSS"); </script>')`
  => `'&lt;script&gt; alert(&quot;XSS&quot;); &lt;/script&gt;'`

**Use `vilo.escfmt(string, data)` for escape-wrapped, `%s`-based formatting.**

Working With Forms
--------------------------
- Use `req.qdata` to access *q*uery string parameters.
-  Use `req.fdata` to access POSTed *f*orm data.
- POSTed multipart/form-data is also available via `req.fdata`.
- Both `req.qdata` and `req.fdata` are of type `DotDict`.

Here are a few examples of Vilo in action:

**1. Simple Greeter, Using Wildcard:**
```py
import vilo; app = vilo.buildApp(); wsgi = app.wsgi;

@app.route("GET", "/hello/*")
def get_hello_name (req, res):
    name = req.wildcards[0];
    return "Hello, " + vilo.esc(name);
```

**2. Factorial Example, Using `GET`:**
```py
import vilo; app = vilo.buildApp(); wsgi = app.wsgi;

@app.route("GET", "/")
def get_homepage (req, res):
    return """
        <form method="GET" action="/factorial">
            <input type="text" name="n" placeholder="Enter N:">
            <button>Submit</button>
        </form>
    """;

# Factorial helper:
facto = lambda n: 1 if n == 0 else n * facto(n - 1);

@app.route("GET", "/factorial")
def get_factorial (req, res):
    n = int(req.qdata.get("n") or 1);
    return vilo.escfmt("""
        <h2>%s! = %s</h2>
        <a href="javascript: history.back();">Back</a>
    """, [n, facto(n)]);
```

TODO [Docs]
-----------------

Write documentation for:

- File handling,
- Templating with Qree,
- Cookies
- Redirects
- Error handling
- Additional examples


TestBin: In-Memory Pastebin App:
---------------------------------------------

The following example creates a super-simple, in-memory [pastebin](https://en.wikipedia.org/wiki/Pastebin) app. Instead of connecting to a database or file-storage system, the app uses a `dict` for (temporarily) storing pastes.

`testbin.py`:
```py
import json;
import vilo; app = vilo.buildApp(); wsgi = app.wsgi;

pasteMap = {};  # In-memory paste storage.

@app.route("GET", "/")
def get_homepage (req, res):
    return vilo.escfmt("""
        <h2>TestBin: In-Memory Pastebin</h2>
        <p>
            Visit <a href="/compose">/compose</a> to compose a new paste.
        </p>
        <p>
            Go to /paste/{Paste-ID-here} to view a paste.
        </p>
        <pre>Paste IDs: %s</pre>
    """, json.dumps(list(pasteMap.keys()), indent=4));

@app.route("GET", "/compose")
def get_compose (req, res):
    return """
        <h2>Compose Paste:</h2>
        <form method="POST" style="max-width: 500px;">
            <input type="text" name="title" placeholder="Title" style="width: 100%;">
            <br><br>
            <textarea name="body" placeholder="Body ..." rows="10" style="width: 100%;"></textarea>
            <br><br>
            <button>Submit</button>
        </form>
        <br>
        <p><a href="/">&lt; Home</a></p>
    """;

@app.route("POST", "/compose")
def post_compose (req, res):
    title = req.fdata.get("title") or "(Blank Title)";
    body = req.fdata.get("body") or "(Blank Body)";
    pasteId = len(pasteMap) + 1;
    pasteMap[pasteId] = vilo.DotDict({
        "id": pasteId, "title": title, "body": body,
    });
    assert len(pasteMap) == pasteId;
    return vilo.escfmt("""
        <h3>Paste Created!</h3>
        <p>
            Visit <a href="/paste/%s">/paste/%s</a> to view your paste,
            or <a href="/compose">/compose</a> to compose another.
        </p>
        <hr>
        <br>
        <p><a href="/">&lt; Home</a></p>
    """, [pasteId, pasteId]);

@app.route("GET", "/paste/*")
def get_paste (req, res):
    pid = req.wildcards[0];
    if not (pid.isdigit() and int(pid) in pasteMap):
        raise vilo.error("<h2>No such paste.</h2>", 404);
    paste = pasteMap[int(pid)];
    return vilo.escfmt("""
        <pre>Paste ID: %(id)s</pre>
        <h1>%(title)s</h1>
        <pre>%(body)s</h1>
        <hr>
        <br>
        <p><a href="/">&lt; Home</a></p>
    """, paste);
```
The module `testbin.py` is included in the Github repo. You can run it as follows:
```
gunicorn testbin:wsgi --reload
```

Licensing:
------------

The software is licensed under the Apache License 2.0; see [LICENSE.txt](https://github.com/polydojo/vilo/blob/master/LICENSE.txt) for more.
