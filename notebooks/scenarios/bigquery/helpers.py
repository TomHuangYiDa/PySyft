# stdlib
from dataclasses import dataclass
from dataclasses import field
import json
import re
import threading
from typing import Any

# third party
from aiosmtpd.controller import Controller
from faker import Faker

# syft absolute
from syft.service.user.user_roles import ServiceRole

fake = Faker()


@dataclass
class Email:
    email_from: str
    email_to: str
    email_content: str

    def to_dict(self) -> dict:
        output = {}
        for k, v in self.__dict__.items():
            output[k] = v
        return output

    def __iter__(self):
        yield from self.to_dict().items()

    def __getitem__(self, key):
        return self.to_dict()[key]

    def __repr__(self) -> str:
        return f"{self.email_to}\n{self.email_from}\n\n{self.email_content}"


class EmailServer:
    def __init__(self, filepath="./emails.json"):
        self.filepath = filepath
        self._emails: dict[str, list[Email]] = self.load_emails()

    def load_emails(self) -> dict[str, list[Email]]:
        try:
            with open(self.filepath) as f:
                data = json.load(f)
                return {k: [Email(**email) for email in v] for k, v in data.items()}
        except FileNotFoundError:
            return {}

    def save_emails(self) -> None:
        with open(self.filepath, "w") as f:
            data = {
                k: [email.to_dict() for email in v] for k, v in self._emails.items()
            }
            f.write(json.dumps(data))

    def add_email_for_user(self, user_email: str, email: Email) -> None:
        if user_email not in self._emails:
            self._emails[user_email] = []
        self._emails[user_email].append(email)
        self.save_emails()

    def get_emails_for_user(self, user_email: str) -> list[Email]:
        return self._emails.get(user_email, [])

    def reset_emails(self) -> None:
        self._emails = {}
        self.save_emails()


SENDER = "noreply@openmined.org"


def get_token(email) -> str:
    # stdlib
    import re

    pattern = r"syft_client\.reset_password\(token='(.*?)', new_password=.*?\)"
    try:
        token = re.search(pattern, email.email_content).group(1)
    except Exception:
        raise Exception(f"No token found in email: {email.email_content}")
    return token


@dataclass
class TestUser:
    name: str
    email: str
    password: str
    role: ServiceRole
    new_password: str | None = None
    email_disabled: bool = False
    reset_password: bool = False
    reset_token: str | None = None
    _client_cache: Any | None = field(default=None, repr=False, init=False)
    _email_server: EmailServer | None = None

    @property
    def latest_password(self) -> str:
        if self.new_password:
            return self.new_password
        return self.password

    def make_new_password(self) -> str:
        self.new_password = fake.password()
        return self.new_password

    @property
    def client(self):
        return self._client_cache

    def relogin(self) -> None:
        self.client = self.client

    @client.setter
    def client(self, client):
        client = client.login(email=self.email, password=self.latest_password)
        self._client_cache = client

    def to_dict(self) -> dict:
        output = {}
        for k, v in self.__dict__.items():
            if k.startswith("_"):
                continue
            if k == "role":
                v = str(v)
            output[k] = v
        return output

    def __iter__(self):
        for key, val in self.to_dict().items():
            if not key.startswith("_"):
                yield key, val

    def __getitem__(self, key):
        if key.startswith("_"):
            return None
        return self.to_dict()[key]

    @property
    def emails(self) -> list[Email]:
        if not self._email_server:
            print("Not connected to email server object")
            return []
        return self._email_server.get_emails_for_user(self.email)

    def get_token(self) -> str:
        for email in reversed(self.emails):
            token = None
            try:
                token = get_token(email)
                break
            except Exception:
                pass
        self.reset_token = token
        return token


def save_users(users):
    user_dicts = []
    for user in users:
        user_dicts.append(user.to_dict())
    print(user_dicts)
    with open("./users.json", "w") as f:
        f.write(json.dumps(user_dicts))


def load_users(high_client: None, path="./users.json"):
    users = []
    with open(path) as f:
        data = f.read()
        user_dicts = json.loads(data)
    for user in user_dicts:
        test_user = TestUser(**user)
        if high_client:
            test_user.client = high_client
        users.append(test_user)
    return users


def make_user(
    name: str | None = None,
    email: str | None = None,
    password: str | None = None,
    role: ServiceRole = ServiceRole.DATA_SCIENTIST,
):
    fake = Faker()
    if name is None:
        name = fake.name()
    if email is None:
        ascii_string = re.sub(r"[^a-zA-Z\s]", "", name).lower()
        dashed_string = ascii_string.replace(" ", "-")
        email = f"{dashed_string}-fake@openmined.org"
    if password is None:
        password = fake.password()

    return TestUser(name=name, email=email, password=password, role=role)


def user_exists(root_client, email: str) -> bool:
    users = root_client.api.services.user
    for user in users:
        if user.email == email:
            return True
    return False


class SMTPTestServer:
    def __init__(self, email_server):
        self.port = 1025
        self.hostname = "localhost"

        # Simple email handler class
        class SimpleHandler:
            async def handle_DATA(self, server, session, envelope):
                try:
                    print(f"> SMTPTestServer got an email for {envelope.rcpt_tos}")
                    email = Email(
                        email_from=envelope.mail_from,
                        email_to=envelope.rcpt_tos,
                        email_content=envelope.content.decode(
                            "utf-8", errors="replace"
                        ),
                    )
                    email_server.add_email_for_user(envelope.rcpt_tos[0], email)
                    email_server.save_emails()
                    return "250 Message accepted for delivery"
                except Exception as e:
                    print(f"> Error handling email: {e}")
                    return "550 Internal Server Error"

        try:
            self.handler = SimpleHandler()
            self.controller = Controller(
                self.handler, hostname=self.hostname, port=self.port
            )
        except Exception as e:
            print(f"> Error initializing SMTPTestServer Controller: {e}")

        self.server_thread = threading.Thread(target=self._start_controller)
        self.start()

    def _start_controller(self):
        try:
            print(
                f"> Starting SMTPTestServer server thread on: {self.hostname}:{self.port}"
            )
            self.controller.start()
        except Exception as e:
            print(f"> Error with SMTPTestServer. {e}")

    def start(self):
        self.server_thread.start()

    def stop(self):
        try:
            print("> Stopping SMTPTestServer server thread")
            self.controller.stop()
            self.server_thread.join()
        except Exception as e:
            print(f"> Error stopping SMTPTestServer. {e}")


def create_user(root_client, test_user):
    if not user_exists(root_client, test_user.email):
        fake = Faker()
        root_client.register(
            name=test_user.name,
            email=test_user.email,
            password=test_user.password,
            password_verify=test_user.password,
            institution=fake.company(),
            website=fake.url(),
        )
    else:
        print("User already exists", test_user)
