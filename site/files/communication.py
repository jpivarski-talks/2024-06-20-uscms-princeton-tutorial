def send_answer(number):
    import time
    import warnings
    import IPython
    import requests
    from xml.etree import ElementTree
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
    import pygments
    import IPython.display

    class AnswerHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args, **kwargs):
            return   # override to disable logging

        def do_POST(self):
            raw_data_length = int(self.headers["Content-Length"])
            raw_data = self.rfile.read(raw_data_length).decode("utf-8")
            data = json.loads(raw_data)

            if data["Type"] == "SubscriptionConfirmation":
                print(data["Message"])
                print(data["SubscribeURL"])

            elif data["Type"] == "Notification":
                try:
                    answer = pygments.highlight(
                        data["Message"],
                        pygments.lexers.PythonLexer(),
                        pygments.formatters.HtmlFormatter(),
                    )
                except Exception as err:
                    answer = f'<p style="font-family: monospace;">{data["Message"]}</p>'

                IPython.display.display(
                    IPython.display.HTML(
                        f'<details><summary style="font-weight: bold;">Answer</summary>{answer}</details>'
                    )
                )

            self.send_response(200)
            self.end_headers()

    class AnswerServer(http.server.HTTPServer):
        allow_reuse_address = True

    with AnswerServer(("0.0.0.0", port), AnswerHandler) as httpd:
        highlighted_code = pygments.highlight(
            f"send_answer(<OUTPUT NUMBER>)",
            pygments.lexers.PythonLexer(),
            pygments.formatters.HtmlFormatter(),
        )
        IPython.display.display(
            IPython.display.HTML(
                f'<div style="font-size: 1.5em; margin: 1em;">{highlighted_code}</div>'
            )
        )

        try:
            httpd.serve_forever()

        except KeyboardInterrupt:
            IPython.display.display(
                IPython.display.HTML(
                    f'<p style="font-size: 1.5em; margin: 1em;">(no longer collecting answers)</p>'
                )
            )
