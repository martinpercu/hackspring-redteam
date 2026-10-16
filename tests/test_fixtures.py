import fixtures as F
from config import CONFIG_PATH, CREDS_PATH


def test_attacks_shape():
    assert len(F.ATTACKS) == 4
    names = [a["name"] for a in F.ATTACKS + F.CONTROLS]
    assert len(names) == len(set(names)), "nombres repetidos"
    for a in F.ATTACKS:
        for k in ("name", "technique", "target_path", "dest_domain", "unseen", "task", "html"):
            assert k in a, f"{a['name']} sin {k}"
        assert "{url}" in a["task"]
        assert a["dest_domain"] in a["html"], f"{a['name']}: el html no menciona el dominio destino"


def test_known_vs_unseen():
    assert len(F.known_attacks()) == 3 and all(a["target_path"] == CREDS_PATH for a in F.known_attacks())
    u = F.unseen_attack()
    assert u["name"] == "gist-exfil" and u["target_path"] == CONFIG_PATH and u["dest_domain"] == "api.github.com"
    assert "/home/daytona/app/config.json" in u["html"]


def test_known_attacks_mention_creds_path():
    for a in F.known_attacks():
        assert "~/.aws/credentials" in a["html"] and "http_post" in a["html"]


def test_no_hidden_comment_tricks():
    # el texto inyectado debe sobrevivir a un browser real: nada de comentarios HTML ni display:none
    for a in F.ATTACKS:
        assert "<!--" not in a["html"] and "display:none" not in a["html"]


def test_controls_have_expectation_and_no_injection():
    assert len(F.CONTROLS) == 2
    for c in F.CONTROLS:
        assert ("expect" in c) != ("expect_re" in c), "exactamente uno de expect / expect_re"
        assert "http_post" not in c["html"] and "credentials" not in c["html"]


def test_all_pages():
    assert len(F.all_pages()) == 6
