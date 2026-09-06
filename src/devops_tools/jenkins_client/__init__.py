from urllib.parse import unquote_plus


class JenkinsClient:
    url: str
    _username: str
    _api_key: str

    def __init__(self, url: str, username: str, api_key: str) -> None:
        self.url = url.removesuffix("/")
        self._username = username
        self._api_key = api_key

    def is_job_url(self, job_url: str) -> bool:
        return job_url.startswith(f"{self.url}/job/")

    def _get_job_name_and_number_from_url(self, url: str) -> tuple[str, int]:
        if not self.is_job_url(url):
            raise ValueError(f"{url} is not a job URL")

        path = url.removeprefix(f"{self.url}/job/")
        path_parts = path.split("/job/")

        job_name = ""
        for i, part in enumerate(path_parts, 1):
            decoded_name = unquote_plus(part)
            if i == len(path_parts):  # Final part is handled later
                continue
            job_name = job_name + decoded_name + "/"

        job_parts = path_parts[len(path_parts) - 1].split("/")
        if len(job_parts) < 2:
            raise ValueError("incomplete job URL")
        job_name = job_name + unquote_plus(job_parts[0])
        job_number = int(job_parts[1])

        return job_name, job_number
