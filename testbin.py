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
    pasteMap[pasteId] = vilo.dotsi.fy({
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
