

class ResultAccumulator:

    def __init__(self, *, output_manager):
        self.output_manager = output_manager
        self.candidates = []

    def add_entry(self, entry):
        entry = self._select_entry(entry)
        self._output_found(entry)
        self.candidates.append(entry)

    async def revalidate(self, validator):
        for entry in self.candidates:
            if await validator.is_valid(entry):
                self._output_found(entry, confirmed=True)

    def _output_found(self, entry, **kwargs):
        if "file" in entry.arguments or "path" in entry.arguments:
            data = self._get_data(entry, kwargs)
            message = self._format_message(entry, data)
            self.output_manager.output_result(message, data=data)

    def _format_message(self, entry, data):
        url = entry.request.url
        return "{prefix}{desc} at: {url}{suffix}".format(prefix=self._get_prefix(entry, data),
                                                         suffix=self._get_suffix(entry, data),
                                                         desc=data["description"], url=url)

    def _get_prefix(self, entry, data):
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
            elif data.get("special") == "tomcat-redirect":
                return "Tomcat redirect, "
            elif entry.response.code == 500:
                return "ISE, "

        return ""

    def _get_suffix(self, entry, data):
        if data.get("confirmed"):
            return " (Confirmed)"

        return ""

    def _get_data(self, entry, additional):
        url = entry.request.url
        descriptor = entry.arguments.get("file") or entry.arguments.get("path")

        data = {"url": url,
                "description": descriptor["description"],
                "code": entry.response.code,
                "severity": descriptor.get('severity', "warning")}
        data.update(additional)

        if entry.response.code == 404 and self._detect_tomcat_fake_404(entry.response.raw):
            data["special"] = "tomcat-redirect"

        return data

    def _detect_tomcat_fake_404(self, content):
        """ An apache setup will issue a 404 on an existing path if there is a tomcat trying to handle jsp on the same
            host """
        if content.find(b'Apache Tomcat/') != -1:
            return True

        return False

    def _select_entry(self, entry):
        if entry.result.redirects:
            last_step = entry.result.redirects[-1]
            last_step.arguments = entry.arguments
            return last_step
        else:
            return entry
