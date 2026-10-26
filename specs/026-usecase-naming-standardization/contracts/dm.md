# CLI Contract changes: `scaffold dm` / `scaffold delete-module`

Only the use case lookup changes. Flags, messages, and exit codes stay the same.

## Use case candidates (in order)

| Layout | Source target | Test target |
|---|---|---|
| New | `src/<pkg>/domain/usecase/<base>_usecase.py` | `src/tests/domain/usecase/test_<base>_usecase.py` (if present) |
| Legacy | `src/<pkg>/domain/usecase/<name>.py` | `src/tests/domain/usecase/test_<name>.py` (if present) |

`<base>` is `--name` with trailing `_usecase` / `_use_case` suffixes removed. A candidate is listed once even if both rows resolve to the same file. The new row is skipped when `<base>` is empty.

## Outcomes for use cases

| Situation | Exit | Effect |
|---|---|---|
| `dm --name book` or `dm --name book_usecase`, new file exists | 0 | preview lists `book_usecase.py` and its test; `--confirm` removes both |
| `dm --name book`, only legacy `book.py` exists | 0 | preview lists `book.py` and its test; `--confirm` removes both, as today |
| `dm --name book`, model package `domain/model/book/` and `book_usecase.py` both exist | 0 | preview lists the model package, its tests folder, `book_usecase.py`, and its test; `--confirm` removes all of them (existing cross-layer behavior) |
| `dm --name book`, both layouts exist | 0 | preview lists all 4 files; `--confirm` removes all 4 |
| no match | 1 | existing "No module named ..." error |
