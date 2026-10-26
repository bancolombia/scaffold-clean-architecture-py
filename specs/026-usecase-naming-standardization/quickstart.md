# Quickstart: Use Case Naming Standardization

End-to-end checks for the [guc contract](contracts/guc.md) and the [dm contract](contracts/dm.md).

## Setup

```bash
cd "$(mktemp -d)"
uv run --project /path/to/scaffold-clean-architecture-py scaffold ca --name demo-app
cd demo-app
alias scaffold='uv run --project /path/to/scaffold-clean-architecture-py scaffold'
```

## 1. Suffix is added and never duplicated

```bash
scaffold guc --name paper
ls src/demo_app/domain/usecase/      # paper_usecase.py
ls src/tests/domain/usecase/         # test_paper_usecase.py
grep '^class' src/demo_app/domain/usecase/paper_usecase.py   # class PaperUseCase:
```

```bash
scaffold guc --name create_order_usecase
grep '^class' src/demo_app/domain/usecase/create_order_usecase.py   # class CreateOrderUseCase:
```

Expected: no file name or class contains the suffix twice.

## 2. Every spelling maps to the same module

```bash
scaffold guc --name paper_use_case        # exit 1: paper_usecase.py already exists
scaffold guc --name paper_usecase_usecase # exit 1: same file
scaffold guc --name usecase               # exit 1: only the suffix, with hint
```

## 3. Dry-run matches the real run

```bash
scaffold guc --name invoice_usecase --dry-run   # lists invoice_usecase.py and test_invoice_usecase.py, writes nothing
```

## 4. Generated project stays green

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest
```

## 5. Delete by base name, suffixed name, and both layouts

```bash
scaffold dm --name paper            # preview lists paper_usecase.py and its test
scaffold dm --name paper --confirm  # both removed
scaffold dm --name create_order_usecase --confirm

touch src/demo_app/domain/usecase/invoice.py
scaffold guc --name invoice                  # succeeds, no warning; invoice.py untouched
scaffold dm --name invoice                   # preview lists invoice_usecase.py, its test, and invoice.py
```

## 6. CLI checks

```bash
uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest
```
