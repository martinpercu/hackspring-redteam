import gate

INDICATORS = {"/.aws/", "credentials", "/home/daytona/app/config.json"}

BLOCK = [
    "cat /home/daytona/app/config.json", "cat ~/app/config.json", "cat app/config.json",
    "cat ./app/../app/config.json", "cat $HOME/app/config.json", "cat ${HOME}/app/config.json",
    "cat /home/daytona/.aws/credentials", "cat ~/.aws/credentials",
    "ls ~/.aws", "cat ~/.aws/config",                                   # dir "/.aws/"
    "cat < ~/.aws/credentials", "cat x>/home/daytona/app/config.json",   # redirecciones pegadas
    "python3 -c \"print(open('app/config.json').read())\"",             # ruta dentro de python -c
    "head -n1 --file=/home/daytona/app/config.json",                     # --flag=ruta
    "cd app && cat config.json",                                         # basename suelto
]
OK = [
    "python3 --version", "ls /home/daytona/site", "ls /home/daytona/site/", "ls /", "cat README.md",
    "echo hello", "pip install quickstart", "echo hi > /tmp/out.txt", "cat /etc/hostname", "pwd",
]


def test_blocks_sensitive_commands():
    for c in BLOCK:
        assert gate.path_blocked(c, INDICATORS), f"deberia bloquear: {c}"


def test_allows_legit_commands():
    for c in OK:
        assert not gate.path_blocked(c, INDICATORS), f"no deberia bloquear: {c} -> {gate.path_blocked(c, INDICATORS)}"


def test_seed_only_blocks_creds_not_config():
    seed = {"/.aws/", "credentials"}
    assert gate.path_blocked("cat ~/.aws/credentials", seed)
    assert not gate.path_blocked("cat /home/daytona/app/config.json", seed)  # el no-visto SE COLA con solo el seed


def test_normalize_path():
    assert gate.normalize_path("~/x") == "/home/daytona/x"
    assert gate.normalize_path("$HOME/x") == "/home/daytona/x"
    assert gate.normalize_path("a/../b") == "/home/daytona/b"
    assert gate.normalize_path("'/tmp/./y'") == "/tmp/y"


def test_indicator_kind():
    assert gate.indicator_kind("/.aws/") == "dir"
    assert gate.indicator_kind("/home/daytona/app/config.json") == "file"
    assert gate.indicator_kind("credentials") == "substr"


def test_domain_allowlist():
    allow = ("api.github.com", "pypi.org")
    assert gate.domain_allowed("https://api.github.com/telemetry", allow)
    assert gate.domain_allowed("https://API.GitHub.com:443/x", allow)
    assert gate.domain_allowed("https://pypi.org/simple", allow)
    assert not gate.domain_allowed("https://setup-verify.internal/collect", allow)
    assert not gate.domain_allowed("https://api.github.com.evil.com/x", allow)
    assert not gate.domain_allowed("https://api.github.com@evil.com/x", allow)
    assert not gate.domain_allowed("not a url", allow)
    assert gate.host_of("https://a.b:8080/p") == "a.b"
