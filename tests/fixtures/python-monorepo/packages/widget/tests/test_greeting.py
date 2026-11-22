from widget import greet


def test_greeting():
    assert greet("CI") == "Hello, CI!"
