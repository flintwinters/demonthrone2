"""Package only public runtime assets; keep Pages builds separate from local serving."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import subprocess
from threading import Thread

SITE_URL = "https://flintwinters.github.io/demonthrone2/"


def build_pages(root: Path) -> None:
    output = root / ".pages-output"
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(root / "pages", output)
    for template in (output / "index.html", output / "sitemap.xml"):
        template.write_text(template.read_text(encoding="utf-8").replace("@@SITE_URL@@", SITE_URL),
                            encoding="utf-8")
    play = output / "play"
    play.mkdir()
    # The local backend aliases /favicon.png; Pages is hosted under a repository
    # subpath and cannot serve that backend alias. All other game URLs are relative.
    markup = (root / "index.html").read_text(encoding="utf-8")
    favicon = 'href="/favicon.png"'
    if markup.count(favicon) != 1:
        raise ValueError("Update the Pages favicon mapping to match index.html")
    markup = markup.replace(favicon, 'href="../favicon.png"')
    markup = markup.replace("<title>Demonthrone</title>",
                            '<title>Play Demonthrone — browser tactics prototype</title>'
                            '\n    <meta name="robots" content="noindex">')
    (play / "index.html").write_text(markup, encoding="utf-8")
    shutil.copytree(root / "src", play / "src")
    three = play / "node_modules" / "three" / "build"
    three.mkdir(parents=True)
    for name in ("three.module.js", "three.core.js"):
        shutil.copy2(root / "node_modules" / "three" / "build" / name, three / name)
    shutil.copy2(root / "node_modules" / "three" / "LICENSE", three.parent / "LICENSE")
    shutil.copy2(root / "public" / "favicon.png", output / "favicon.png")
    (output / ".nojekyll").touch()
    print("Pages ready: .pages-output/ (landing page + /play/ demo).")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


def preview_pages(root: Path) -> None:
    output = root / ".pages-output"
    if not (output / "play" / "index.html").exists():
        raise ValueError("Run python manage.py pages first.")
    chromium = shutil.which("chromium") or shutil.which("google-chrome")
    if not chromium:
        raise ValueError("Install Chromium to capture Pages previews.")
    preview = root / ".pages-preview"
    preview.mkdir(exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(output)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        for name, size, path in (("game", "1440,960", "play/"),
                                 ("desktop", "1440,1100", ""),
                                 ("mobile", "390,844", "")):
            result = subprocess.run(
                (chromium, "--headless", "--no-sandbox", "--disable-dev-shm-usage",
                 "--enable-unsafe-swiftshader", "--use-angle=swiftshader",
                 f"--user-data-dir={preview / 'browser'}", "--hide-scrollbars",
                 "--virtual-time-budget=4000", f"--window-size={size}",
                 f"--screenshot={preview / (name + '.png')}",
                 f"http://127.0.0.1:{server.server_port}/{path}"),
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode:
                raise RuntimeError(result.stderr[-1500:])
            print(f"Preview: .pages-preview/{name}.png")
    finally:
        server.shutdown()
        server.server_close()
