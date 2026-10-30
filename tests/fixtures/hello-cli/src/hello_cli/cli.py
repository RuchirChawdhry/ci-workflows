"""An installed CLI that responds to --help."""


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(prog="workflow-hello", description="CI smoke-test fixture")
    parser.parse_args()
    print("Hello from an installed wheel!")
