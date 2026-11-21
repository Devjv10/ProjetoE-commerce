from services.health import check_connections


def main() -> int:
    results = check_connections()
    for result in results:
        status = "OK" if result["ok"] else "FALHA"
        print(f"[{status}] {result['banco']}: {result['detalhe']}")
    return 0 if all(result["ok"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
