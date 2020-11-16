Vilo
====

Vilo is a WSGI micro-framework for building web apps with Python. Inspired by [Express](https://expressjs.com/) and [Bottle](https://bottlepy.org/), Vilo is lightweight, unopinionated, and flexible.

Installation
--------------
Install Vilo via pip:
```
pip install vilo
```
[Waitress](https://docs.pylonsproject.org/projects/waitress/en/stable/) is a recommended for running Vilo apps, paired with [Hupper](https://docs.pylonsproject.org/projects/hupper/en/latest/). Install via:  
`pip install waitress hupper`

Alternatively [Gunicorn](https://gunicorn.org/) is a popular option, installable via:  
`pip install gunicorn`

Hello, World!
----------------

Create `hello.py`:
```py
# Define App: ##################################
import vilo;                # Import vilo

app = vilo.buildApp();      # Build (blank) app

@app.route("GET", "/")      # Add route
def get_homepage (req, res):
    return "Hello, World!";

wsgi = app.wsgi;            # WSGI callable

# Run App: #####################################
if __name__ == "__main__":
    import waitress;
    waitress.serve(wsgi);
```
Run `python hello.py` to start the app. Once the app is running, [visit `localhost:8080`](http://localhost:8080) in your favorite browser! You should see a familiar greeting. (To stop running the app, press: `Ctrl`+`C`)

From The Command Line
------------------------------

Continuing with the `hello.py` example above, instead of calling `waitress.serve(.)` from Python, you can run the app from the command line as follows:

#### With Waitress:

+ Using waitress-serve: `waitress-serve hello:wsgi`
+ With Hupper for dev: `hupper -m waitress hello:wsgi`

Waitress includes the `waitress-serve` command, using which, we're asking Waitress to run `wsgi` from the `hello` module. Hupper is useful during development, for hot-reloads.

Kindly refer to Waitress/Hupper's docs for more.

#### Using Gunicorn:

+ Without hot-reloads: `gunicorn hello:wsgi`
+ With `--reload` for dev: `gunicorn hello:wsgi --reload`

Kindly refer to Gunicorn's docs for more.


Vilo vs Flask/Bottle
------------------------
#### No Magic Globals:

Flask and Bottle both employ globals like `request`, `g` and/or `response`. Vilo instead, like Express, supplies `req` and `res` as arguments to each route handler. 

If you're building a single app, globals can be very handy. But if you're looking to build and deploy multiple (entirely isolated) apps, having to deal with automatically context-aware globals can seem *eerily magical*.

With Vilo, `req` and `res` arguments passed to route handlers are *entirely isolated*. Even with regard to a single app, each route handler receives fully isolated `req` and `res` objects.

**No Built-In Templating**:  
Bottle and Flask both include built-in templating engines. As an un-opinionated framework, Vilo doesn't. You may pick any templating engine you want. For illustration only, our examples will use [Qree](https://github.com/polydojo/qree) (read 'Curie'), installable via `pip install qree`.

**No Built-In Development Server:**  
Bottle and Flask include a development server with hot-reloads for local testing and development, but recommend *against* using it in production. Instead of pre-packaging a development server, we recommend using Gunicorn with the `--reload` flag, or Waitress atop Hupper.


Basic Routes & Static Files
--------------------------------

Working with fixed routes is fairly straightforward. To handle the route `"/foo/bar"`, just supply that path to `app.route(.)` For example:

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

If you have static CSS, JS, image or other files, serve them using `res.staticFile(filepath, [mimeType])`. For example, let's say you have the following directory structure:
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
    as `Fo/od` is not a single segment.

2. `/cart/add-item/*`
    - will match `/cart/add-item/123`
      with `req.wildcards = ['123']`.
    - but will NOT match `/cart/add-item/12/3`
    as `12/3` is not a single segment.

3. `/static/**`
    - will match `/static/lib/js/jquery.js`
      with `req.wildcards = 'lib/javascript/jquery.js`
    - but will NOT match `/StaTiC/lib/js/jquery.js`
    because `StaTiC` and `static` don't match.

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

Generally speaking, there's *no need* to explicitly pass `mode`, as `app.route(.)` can auto-detect it. If passed explicitly, it accepts one of three values:
`["re", "wildcard", "exact"]`.
- `"re"`: regular expression matching, based on `re.match(.)`.
- `"wildcard":` wildcard segment matching, explained above.
- `"exact"`: exact path matching, based on `==` operator.

Dot-Accessible Dictionary (`dotsi.Dict`)
-----------------------------------------------

Vilo uses [Dotsi](https://github.com/polydojo/dotsi) for dot-accessible dictionaries. In fact, in all previous examples, `app`, `req` and `res` are all dot-accessible dictionaries!

**`dotsi` Usage:**
```py
import dotsi

d = dotsi.fy({"foo": "bar"})
print(d.foo);	# Same as d['foo']
# Output: bar

d.baz = [{"key":"a"}, {"key":"b"}] # Like d['baz'] = ..
print(d.baz[0].key)
# Output: a
```
For more examples, check out Dotsi's docs, linked above.

 **Sidebar: Functional vs OOP**  
 The Polydojo team strongly favours functional programming over classical OOP. *As far as possible*, we avoid writing classes. This is super-easy in JavaScript, especially because object properties are dot-accessible; Dotsi allows us to bring the same ease to Python.

HTML Escaping & `%s`-Formatting
-----------------------------------------------

Use `vilo.esc(string)` for escaping HTML:
- `vilo.esc('foo')` => `'foo'`
- `vilo.esc('<b> Hi </b>')`
  => `'&lt;b&gt; Hi &lt;/b&gt;'`
- `vilo.esc('<script> xss() </script>')`
  => `'&lt;script&gt; xss() &lt;/script&gt;'`

Use `vilo.escfmt(string, data)` for escape-wrapped, `%s`-based formatting. Or better yet, try [**Qree**](https://github.com/polydojo/qree), our tiny but might templating engine.

Working With Forms
--------------------------
- Use `req.qdata` to access *q*uery string parameters.
-  Use `req.fdata` to access POSTed *f*orm data.
- POSTed multipart/form-data is also available via `req.fdata`.
- Both `req.qdata` and `req.fdata` are of type `dotsi.Dict`.

**Factorial Form Example:**
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

Errors & Redirects
------------------------
**Redirects:**  
Return `res.redirect(.)` for redirecting to another URL:
```py
@app.route("GET", "/foo")
def redirect_from_foo_to_bar (req, res):
	return res.redirect("/bar");

@app.route("GET", "/go/to/boardbell")
def redirect_to_boardbell_dot_com (req, res):
	return res.redirect("https://www.boardbell.com/");
```

*NB:* Please be sure to `return res.staticFile(.)`. Skipping **`return`** will likely produce unintended consequences.

**Errors:**
Raise `vilo.HttpError(.)` to produce a non-200 response. (Or use `vilo.error(.)`, which is a short alias for the same.)
```py
@app.route("GET", "/post/*")
def get_post (req, res):
	postId = req.wildcards[0];
	if not yourLogic_postId_found(postId):
		raise vilo.error("<h2>No such post.</h2>");
	# otherwise ...
	return yourLogic_showPost(postId);
```
`vilo.error(.)` takes two parameters:
- `body` (required): The response body. Similar to the return value for non-error responses. If it's a `dict` or `list`, a JSON response is produced.
- `statusLine` (optional): A status line like "404 Not Found" or "403 Forbidden"; alternatively, an integer code like 404 or 405. (Defaults to 404.)

*NB:* Please be sure to `raise vilo.error(.)`. If **`raise`** isn't used, no error will be produced; it'll be as if no error ever occurred.

**Framework-Level Errors:**

When you explicitly raise a `vilo.HttpError(.)`, it is sent directly to the client, as described above. But sometimes, Vilo itself needs to raise errors; for example, when a route is not found. Other error-types are caught, producing a 500-response.

Framework-level error-handling can be customized via `app.frameworkError(.)`, which is a bit like `app.route(.)`.

To override the default route-not-found behavior:
```py
@app.frameworkError("route_not_found")
def error_routeNotFound (req, res, err):
	return "Custom Msg: That route wasn't found.";
```
Comparing `app.frameworkError(.)` with `app.route(.)`:
1. Instead of passing a route, you pass a framework-error-code, such as `"route_not_found"`. (Codes are listed below.)
2. The handler accepts an extra parameter, `err`, which is simply the exception raised (or caught) by Vilo.

Framework-error codes:
- `route_not_found` (illustrated above)
- `file_not_found` (with regard to `res.staticFile(.)`)
- `request_too_large` (this is yet to be documented.)
- `unexpected_error` (more on this below)

**Handling Unexpected Errors:**

When your application produces an unexpected error, by default, Vilo produces a simple `500 Internal Server Error` response. The default error response may be customized as follows:
```py
# Sample error producer:
@app.get("/err")
def get_zeroDivErr (req, res):
	return 1/0;

# Unexpected error handler:
@app.frameworkError("unexpected_error")
def handle_unexpectedError (req, res, err):
	return vilo.esc(repr(err));
```

On navigating to `"/err"`, instead of the default error message, you should see: `ZeroDivisionError('division by zero')`

**Debug Mode:**
In debug mode, which can be enabled via `app.setDebug(True)`, the default 500-error handler includes a stack traceback. While this obviously helps with debugging, it can cause security concerns in production. **Caution:** Do not enable debug-mode in production.


Quick Plug
--------------
Vilo is built and maintained by the folks at [Polydojo, Inc.](https://www.polydojo.com/), led by [Sumukh Barve](https://www.sumukhbarve.com/). If your team is looking for a simple project management tool, please check out our latest product: [**BoardBell.com**](https://www.boardbell.com/).

Headers
-----------

**Set Response Headers:**

Use `res.setHeader(name, value)` for setting a response header. (Params `name` and `value` respectively correspond to the name and value of the header.)

Or use `res.setHeaders(.)` for setting multiple headers at once by passing either a dict or a list of `(name, value)` pairs.

```py
@app.route("GET", "/foo.txt")
def get_fooTxt (req, res):
	res.setHeaders({
		"Content-Type": "text/plain",
		"Cache-Control": "no-store",
	});
	return "Here's some foo text.";
```

Header Shortcuts:  
- Use `res.contentType = someValue` instead of `res.setHeader("Content-Type", someValue)`.
- Use `res.setCookie(.)` for setting cookies, instead of setting the `"Set-Cookie"` header. More on this below.

**Get Request Headers:**

Use `req.getHeader(name)` to get a request header. (Param `name` corresponds to the header's name.) If there's no such header, `None` is returned.

```py
@app.route("GET", "/api/foo")
def get_apiFoo (req, res):
	reqType = req.getHeader("Content-Type");
	if reqType != "application/json":
		raise vilo.error("Only JSON requsts are valid.");
	# otherwise ...
	return yourLogic_doFoo();
```

*Note:* Use `req.getCookie(.)` (documented below) for getting request cookies. No need to deal with the `"Cookie"` header directly.

Cookies
----------

**Set Response Cookies:**

Use `res.setCookie(name, value, [secret, opt])` for setting response cookies. Params `name` and `value` respectively correspond to the name and value of the cookie.
- Optional param `secret` may be a string; and is used to sign the cookie, if passed.
- Optional param `opt` may be a dict of cookie options compatible with Python's [`http.cookies.Morsel`](https://docs.python.org/3/library/http.cookies.html#http.cookies.Morsel).

```py
@app.route("GET", "/home")
def get_home (req, res):
	res.setCookie("visitedHome", "Yes");
	return "<h1>You're Home!</h1>";
```

**Note:** By default, Vilo sets `HttpOnly` cookies with `Path="/"`. For custom behavior, pass `opt={"httponly": False, "path": "/custom"}`. Of course, you may also pass other Morsel-compatible options.

**Warning:**  Even when `secret` is passed, it is only used to *sign* the cookie. The cookie is **NOT** *encrypted*. Signing **DOES NOT** hide or obscure the cookie in any way. As such, one must **NEVER** store confidential information in cookies.

**Get Request Cookies:**

Use `req.getCookie(name, [secret])` for getting request cookies. Param `name` is the cookie name while `secret` should match the secret used while setting the cookie.
- If the named cookie exists (and is valid), it's value is returned, else `None`.
- If `secret` is passed but the signature-check fails, `None` is returned (regardless of whether the cookie exists).

```py
@app.route("GET", "/visitCounter")
def get_visitCounter (req, res):
	count = int(req.getCookie("visitCount") or 0);
	res.setCookie("visitCount", str(count + 1))
	return "Number of visits: %s" % (count+1);
```

Working With JSON
-------------------------
Vilo makes it easy to consume and produce JSON. In route handlers:  
- **JSON Requests:**  POSTed `application/json` data is available as `req.fdata`.
- **JSON Responses:** Returning a `dict` or `list` produces an `application/json` response.

```py
@app.route("GET", "/hello_json")
def get_sample_json (req, res):
	return {"hello": "json"};
	# Will produce JSON response, with:
	#	Content-Type: application/json

```

Plugins (Universal Route Decorators)
--------------------------------------------

If you'd like certain action to be performed across *all* routes, it's best to define a plugin for such behavior. (Plugins are just decorators that are applied to all routes.)

#### Example: `X-Exec-Time` Header

To add the `X-Exec-Time` header to each response, we can write a plugin that computes the execution time and adds the header.

```py
import time;

def plugin_xExecTime (fn):
    def wrapper (req, res, *args, **kwargs):
        t0 = time.time();
        result = fn(req, res, *args, **kwargs);
        tDiff = time.time() - t0;
        res.setHeader("X-Exec-Time", str(tDiff));
        return result;
    return wrapper;
```
Then, install the plugin onto your app via:
```py
app.install(plugin_xExecTime)
```

#### Example: Enforcing HTTPS
```py
def plugin_enforceHttps (fn):
    def wrapper (req, res, *args, **kwargs):
        scheme = req.splitUrl.scheme;
        if scheme != "https":
            newUrl = req.url.replace(scheme, "https", 1);
            return res.redirect(newUrl);
        # otherwise ...
        return fn(req, res, *args, **kwargs);
```
Then, as before, install onto you app via:
```py
app.install(plugin_enforceHttps)
```

#### Plugin Application Order

Ideally, plugins should be written *independently* of all other plugins. That is, each plugin should assume that other plugins may exist, and that plugins may be applied in any order.

However, it may be useful to know that plugins that are installed first are applied first by Vilo. That is if you `app.install(X)`, then install `Y`, and then `Z`; then effectively `Z(Y(X(.)))` should be expected. That is, `X(.)` completes first, then `Y(.)`, and then `Z(.)`.

TestBin: In-Memory Pastebin App
-----------------------------------------

Check out [`testbin.py`](https://github.com/polydojo/vilo/blob/master/testing.py) a super-simple, in-memory [pastebin](https://en.wikipedia.org/wiki/Pastebin) app. Instead of connecting to a database or file-storage system, the app uses a `dict` for (temporarily) storing pastes.

**Running:**  
The `testbin.py` module is included in Vilo's GitHub repo. The app may be run as follows:
```
gunicorn testbin:wsgi --reload
```
Then, head over to `localhost:8080` in your favorite browser.

ViloLog: DB-Backed Blogging Engine
---------------------------------------------
For a bit more in-depth example, check out [ViloLog](https://github.com/polydojo/vilolog): a blogging engine built atop Vilo and [PogoDB](https://github.com/polydojo/pogodb).

Licensing
------------
Copyright (c) 2020 Polydojo, Inc.

**Software Licensing:**  
The software is released "AS IS" under the **Apache License 2.0**, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED. Kindly see [LICENSE.txt](https://github.com/polydojo/vilo/blob/master/LICENSE.txt) for more details.

**No Trademark Rights:**  
The above software licensing terms **do not** grant any right in the trademarks, service marks, brand names or logos of Polydojo, Inc.
