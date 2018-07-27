from hammertime.rules.redirects import valid_redirects


class ResultAccumulator:

    def __init__(self, *, output_manager):
        self.output_manager = output_manager

    def add_entry(self, entry):
        self.output_found(entry)

    def output_found(self, entry, **kwargs):
        message = self._format_message(entry)
        data = self._get_data(entry, kwargs)
        self.output_manager.output_result(message, data=data)

    def _format_message(self, entry):
        url = entry.request.url
        data = entry.arguments.get("file") or entry.arguments.get("path")
        message_prefix = self._get_prefix(entry)
        return "{prefix}{desc} at: {url}".format(prefix=message_prefix, desc=data["description"], url=url)

    def _get_prefix(self, entry):
        if "file" in entry.arguments:
            if entry.response.code == 500:
                return "ISE, "
            elif len(entry.response.raw) == 0:
                return "Empty "
        if "path" in entry.arguments:
            if entry.response.code == 401:
                return "Password Protected - "
            elif entry.response.code == 403:
                return "*Forbidden* "
            elif entry.response.code == 404 and self._detect_tomcat_fake_404(entry.response.raw):
                return "Tomcat redirect, "
            elif entry.response.code == 500:
                return "ISE, "

        return ""

    def _get_data(self, entry, additional):
        url = entry.request.url
        descriptor = entry.arguments.get("file") or entry.arguments.get("path")

        data = {"url": url,
                "description": descriptor["description"],
                "code": entry.response.code,
                "severity": descriptor.get('severity', "warning")}
        data.update(additional)

        if self._detect_tomcat_fake_404(entry.response.raw):
            data["special"] = "tomcat-redirect"

        return data

    def _detect_tomcat_fake_404(self, content):
        """ An apache setup will issue a 404 on an existing path if there is a tomcat trying to handle jsp on the same
            host """
        if content.find(b'Apache Tomcat/') != -1:
            return True

        return False
