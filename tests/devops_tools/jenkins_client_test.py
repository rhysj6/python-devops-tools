import pytest

from devops_tools.jenkins_client import JenkinsClient


def test_is_job_url(subtests: pytest.Subtests) -> None:
    with subtests.test("handles / on end of base url"):
        client = JenkinsClient(
            url="https://jenkins.example.com/jenkins/", username="", api_key=""
        )
        assert (
            client.is_job_url("https://jenkins.example.com/jenkins/job/pipeline/283")
            is True
        )
        assert (
            client.is_job_url("https://jenkins.example.com/jenkins/settings") is False
        )
        assert client.is_job_url("http://google.com/") is False

    with subtests.test("handles no / on end of base url"):
        client = JenkinsClient(
            url="https://jenkins.example.com/jenkins", username="", api_key=""
        )
        assert (
            client.is_job_url(
                "https://jenkins.example.com/jenkins/job/pipeline_name/283"
            )
            is True
        )
        assert (
            client.is_job_url("https://jenkins.example.com/jenkins/settings") is False
        )
        assert client.is_job_url("http://google.com/") is False


def test_get_job_name_and_number_from_url(subtests: pytest.Subtests) -> None:
    BASE_URL = "https://jenkins.example.com"
    client = JenkinsClient(url=BASE_URL, username="", api_key="")

    with subtests.test("parses valid job URL"):
        name, number = client._get_job_name_and_number_from_url(
            f"{BASE_URL}/job/my-job/123"
        )
        assert name == "my-job"
        assert number == 123

    with subtests.test("parses URL encoded job name"):
        name, number = client._get_job_name_and_number_from_url(
            f"{BASE_URL}/job/My+Job/123"
        )
        assert name == "My Job"
        assert number == 123

    with subtests.test("parses URL with /console on end"):
        name, number = client._get_job_name_and_number_from_url(
            f"{BASE_URL}/job/My+Job/123/console"
        )
        assert name == "My Job"
        assert number == 123

    with subtests.test("parses URL with job within multiple folders"):
        name, number = client._get_job_name_and_number_from_url(
            f"{BASE_URL}/job/old%20ansible/job/linux/job/setup/456"
        )
        assert name == "old ansible/linux/setup"
        assert number == 456

    with subtests.test("returns error for non job URL") and pytest.raises(
        ValueError
    ) as error:
        client._get_job_name_and_number_from_url(f"{BASE_URL}/view/all")
        assert error is not None
        assert "not a Job URL" in str(error.value)

    with subtests.test("returns error for incomplete job URL") and pytest.raises(
        ValueError
    ) as error:
        client._get_job_name_and_number_from_url(f"{BASE_URL}/job/setup")
        assert error is not None
        assert "incomplete job URL" in str(error.value)
