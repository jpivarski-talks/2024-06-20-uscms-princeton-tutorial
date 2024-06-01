def send_answer(number):
    import time
    import warnings
    import IPython
    import requests
    from requests_aws4auth import AWS4Auth
    from urllib3.connectionpool import InsecureRequestWarning

    answer = IPython.get_ipython().history_manager.input_hist_raw[number]

    # don't freak out: this is a limited access key that is usually deactivated
    awsauth = AWS4Auth(
        "AKIAVH6KDF" "EHTR7AH7KR",
        "nemmnMSa" "wq7Ozvsv6GH" "BhXRraeiuZ0d" "K2kiuZYkp",
        "us-east-1",
        "sns",
    )

    # ignoring "Unverified HTTPS request is being made to host 'sns.us-east-1.amazonaws.com'."
    # the issue is that this is cross-domain (GitHub Pages to AWS SNS; both are HTTPS)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=InsecureRequestWarning)

        response = requests.post(
            "https://sns.us-east-1.amazonaws.com/",
            auth=awsauth,
            params={
                "Version": "2010-03-31",
                "Action": "Publish",
                "TopicArn": "arn:aws:sns:us-east-1:360664213775:2024-06-20-uscms-princeton-tutorial",
                "Subject": "answer",
                "Message": answer,
            }
        )

        xml = ElementTree.fromstring(response.text)
        ns = {"ns": "http://sns.amazonaws.com/doc/2010-03-31/"}
        if xml.tag == "{" + ns["ns"] + "}ErrorResponse":
            code = xml.find("./ns:Error/ns:Code", ns).text
            message = xml.find("./ns:Error/ns:Message", ns).text
            raise ConnectionError(f"{code}: {message}")

        print(f"Sent code cell {number} at {time.strftime('%I:%M:%S %p')}.")


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
