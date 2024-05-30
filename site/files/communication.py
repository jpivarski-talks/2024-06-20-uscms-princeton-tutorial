def send_answer(url, number):
    import IPython
    import requests

    code = IPython.get_ipython().history_manager.input_hist_raw[number]

    try:
        response = requests.post(url, json={"code": code}, timeout=1).json()
    except (requests.Timeout, requests.ConnectionError, requests.RequestException):
        print("Wait until the teacher starts collecting answers or fix the IP address.")
        return
    if response["ok"]:
        print(response["message"])
    else:
        print("Something is wrong with the answer you sent:")
        print(response["message"])


def collect_answers(port=8000):
    import http.server
    import json
    import socket

    import pygments
    import IPython.display

    class AnswerHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args, **kwargs):
            return  # override to disable logging

        def end_headers(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            return super().end_headers()

        def send_error(self, code, message=None, explain=None):
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps({"ok": False, "message": message}).encode("utf-8")
            )

        def do_POST(self):
            raw_data = self.rfile.read(int(self.headers["Content-Length"])).decode(
                "utf-8"
            )
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                self.send_error(400, f"must be JSON: {raw_data}")
                return
            if not isinstance(data.get("code"), str):
                self.send_error(400, f"'code' must be a string: {raw_data}")
                return

            try:
                highlighted_code = pygments.highlight(
                    data["code"],
                    pygments.lexers.PythonLexer(),
                    pygments.formatters.HtmlFormatter(),
                )

                IPython.display.display(
                    IPython.display.HTML(
                        f'<details><summary style="font-weight: bold;">Answer {AnswerHandler.counter}</summary>{highlighted_code}</details>'
                    )
                )
            except Exception as err:
                self.send_error(400, f"{type(err).__name__}: {str(err)}")
                return

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {
                        "ok": True,
                        "message": f"Received as answer number {AnswerHandler.counter}.",
                    }
                ).encode("utf-8")
            )
            AnswerHandler.counter += 1

    class AnswerServer(http.server.HTTPServer):
        allow_reuse_address = True

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("10.254.254.254", 80))
        base = s.getsockname()[0]

    with AnswerServer((base, port), AnswerHandler) as httpd:
        highlighted_code = pygments.highlight(
            f'answer_url = "http://{base}:{port}"\n\nsend_answer(answer_url, <OUTPUT NUMBER>)',
            pygments.lexers.PythonLexer(),
            pygments.formatters.HtmlFormatter(),
        )
        IPython.display.display(
            IPython.display.HTML(
                f'<div style="font-size: 1.5em; margin: 1em;">{highlighted_code}</div>'
            )
        )
        AnswerHandler.counter = 1
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            IPython.display.display(
                IPython.display.HTML(
                    f'<p style="font-size: 1.5em; margin: 1em;">Stopped collecting answers.</p>'
                )
            )
