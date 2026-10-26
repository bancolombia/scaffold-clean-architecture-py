# Feature Specification: Use Case Naming Standardization

**Feature Branch**: `feature/usecase-naming-standardization`

**Created**: 2026-10-26

**Status**: Draft

**Input**: User description: "Standardize the naming of generated use cases in the `scaffold generate-use-case` (alias `guc`) command. The generated module must always end with `_usecase` (`<base>_usecase.py`) and the class must always be `<Base>UseCase`, whether or not the user includes the `usecase` word in `--name`, so the suffix is never duplicated."

## Clarifications

### Session 2026-10-26

- Q: If a legacy `domain/usecase/<name>.py` exists and the developer runs `scaffold guc --name <name>`, what should happen? → A: Ignore legacy files. Whatever `--name` the user sends (for example `paper`), the command always creates `<name>_usecase.py`, with no warning and no conflict. `book` in this spec is only an example name.
- Q: For a name that ends with the suffix more than once (for example `paper_usecase_usecase`), how many trailing suffixes are removed? → A: All of them, in any mix of `_usecase` and `_use_case`. The result is `paper_usecase.py` with the class `PaperUseCase`.
- Q: If both a legacy `<name>.py` and a new `<name>_usecase.py` exist, what does `scaffold dm --name <name>` delete? → A: Both files and their tests. The preview lists all of them before anything is removed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generated use case modules always carry the `_usecase` suffix (Priority: P1)

A developer working in a generated Clean Architecture project runs `scaffold guc --name book`. Today this creates `domain/usecase/book.py`, a file name that does not say it holds a use case. After this feature the command creates `domain/usecase/book_usecase.py` with the class `BookUseCase`, and the mirrored test `src/tests/domain/usecase/test_book_usecase.py`.

Resulting structure inside the generated project:

```text
src/<package>/domain/usecase/
└── book_usecase.py          # class BookUseCase
src/tests/domain/usecase/
└── test_book_usecase.py     # imports BookUseCase from book_usecase
```

**Why this priority**: This is the core of the feature. Every generated use case module becomes recognizable by name and follows one convention across all generated projects.

**Independent Test**: In a freshly scaffolded project, run `scaffold guc --name book` and verify the file names, the class name, and that the generated project's test suite passes.

**Acceptance Scenarios**:

1. **Given** a valid project with no `book` use case, **When** the developer runs `scaffold guc --name book`, **Then** `domain/usecase/book_usecase.py` and `src/tests/domain/usecase/test_book_usecase.py` are created, and the command exits with code 0.
2. **Given** the command above has run, **When** the developer opens `book_usecase.py`, **Then** it defines exactly one class named `BookUseCase`.
3. **Given** the command above has run, **When** the developer opens `test_book_usecase.py`, **Then** it imports `BookUseCase` from the `book_usecase` module, and the generated project's lint, format, type-check, and test checks pass without manual edits.
4. **Given** a valid project, **When** the developer runs `scaffold guc --name create_order`, **Then** the command creates `create_order_usecase.py` with the class `CreateOrderUseCase` and the test `test_create_order_usecase.py`.
5. **Given** a valid project, **When** the developer runs `scaffold generate-use-case --name book` (the long form), **Then** the result is identical to running `scaffold guc --name book`.
6. **Given** the command above has run, **Then** the success message reports the class name `BookUseCase` and the number of files created.

---

### User Story 2 - The suffix is never duplicated (Priority: P1)

A developer who already thinks of the module as a use case runs `scaffold guc --name book_usecase` or `scaffold guc --name book_use_case`. Today the class ends up as `BookUsecaseUseCase`. After this feature, the command recognizes the trailing suffix and produces exactly the same output as `scaffold guc --name book`.

**Why this priority**: The duplicated suffix is the reported bug. Producing the same result regardless of how the user writes the name removes it and makes the command predictable.

**Independent Test**: Run the command with `book`, `book_usecase`, and `book_use_case` in three fresh projects and verify that the three produce identical file names, class names, and file contents.

**Acceptance Scenarios**:

1. **Given** a valid project, **When** the developer runs `scaffold guc --name book_usecase`, **Then** the command creates `book_usecase.py` with the class `BookUseCase` and the test `test_book_usecase.py`. No file or class contains the suffix twice.
2. **Given** a valid project, **When** the developer runs `scaffold guc --name book_use_case`, **Then** the result is identical to scenario 1.
3. **Given** a valid project, **When** the developer runs `scaffold guc --name create_order_usecase`, **Then** the command creates `create_order_usecase.py` with the class `CreateOrderUseCase`.
4. **Given** a valid project, **When** the developer runs `scaffold guc --name usecase_registry`, **Then** only a trailing suffix is considered, so the command creates `usecase_registry_usecase.py` with the class `UsecaseRegistryUseCase`.

---

### User Story 3 - Preview and conflict detection use the normalized name (Priority: P2)

A developer previews generation with `--dry-run`, or runs the command again for a use case that already exists under a different spelling. Both the preview and the "already exists" check use the normalized module name, so the preview is accurate and existing work is never overwritten.

**Why this priority**: The constitution requires `--dry-run` on every command, and overwriting a hand-edited use case would destroy work. Both must agree with the new naming.

**Independent Test**: Run `scaffold guc --name book_usecase --dry-run` and verify the listed files, then generate `book` and try to generate `book_usecase` and verify the conflict.

**Acceptance Scenarios**:

1. **Given** a valid project, **When** the developer runs `scaffold guc --name book --dry-run` or `scaffold guc --name book_usecase --dry-run`, **Then** the output lists `book_usecase.py` and `test_book_usecase.py`, and nothing is written to disk.
2. **Given** a valid project, **When** the developer runs the same command without `--dry-run`, **Then** the files created match exactly the files listed by the dry-run.
3. **Given** `domain/usecase/book_usecase.py` already exists, **When** the developer runs `scaffold guc --name book`, `--name book_usecase`, or `--name book_use_case`, **Then** the command exits with code 1, prints a clear message with a resolution hint, and writes no files.

---

### User Story 4 - Delete a use case by base name or suffixed name (Priority: P3)

A developer removes a use case with the delete-module command (`scaffold dm` / `scaffold delete-module`). The developer can refer to it either by its base name (`book`) or by its suffixed name (`book_usecase`), and the command finds `book_usecase.py` and its test. Use cases generated by earlier versions of the tool (`book.py`) can still be deleted by their original name.

**Why this priority**: Without this, deleting by the name used at generation time (`book`) would no longer find the use case. It is lower priority because deletion is used less often than generation.

**Independent Test**: Generate `book`, then run the delete-module command once with `--name book` and once with `--name book_usecase` in separate projects, and verify both remove the use case and its test. Repeat with a legacy `book.py` use case.

**Acceptance Scenarios**:

1. **Given** a use case `book_usecase.py` with its test `test_book_usecase.py`, **When** the developer runs `scaffold dm --name book --confirm`, **Then** both files are removed.
2. **Given** the same use case, **When** the developer runs `scaffold dm --name book_usecase --confirm`, **Then** both files are removed.
3. **Given** the same use case, **When** the developer runs `scaffold dm --name book` with `--dry-run` or without `--confirm`, **Then** the preview lists `book_usecase.py` and `test_book_usecase.py`, and nothing is removed.
4. **Given** a legacy use case `domain/usecase/book.py` with its test `test_book.py`, **When** the developer runs `scaffold dm --name book --confirm`, **Then** both files are removed, as they are today.
5. **Given** both a legacy `book.py` and a new `book_usecase.py`, each with its test, **When** the developer runs `scaffold dm --name book` without `--confirm`, **Then** the preview lists all four files, and **When** the developer adds `--confirm`, **Then** all four files are removed.
6. **Given** a model generated with `scaffold gm --name book` and a use case generated with `scaffold guc --name book`, **When** the developer runs `scaffold dm --name book` without `--confirm`, **Then** the preview lists the model package, its tests folder, `book_usecase.py`, and `test_book_usecase.py`, so the developer sees that both layers match before confirming. To remove only the use case's files, the developer deletes them by hand. A layer selector for delete-module is out of scope.

---

### Edge Cases

- **Name is only the suffix**: `scaffold guc --name usecase`, `--name use_case`, or a repetition such as `--name usecase_usecase` leaves no base name. The command exits with code 1, prints a clear message with a resolution hint (for example, suggesting a name such as `create_order`), and writes nothing.
- **Suffix not at the end**: the word `usecase` anywhere other than the end of the name (for example, `usecase_registry`) is kept as part of the base name.
- **Suffix glued to another word**: a name like `bookusecase` (no underscore) is not recognized as suffixed. It produces `bookusecase_usecase.py` with the class `BookusecaseUseCase`.
- **Repeated suffix**: all trailing suffixes are removed, in any mix of spellings. `paper_usecase_usecase` and `paper_use_case_usecase` both produce `paper_usecase.py` with the class `PaperUseCase`.
- **Invalid names**: names that are not valid snake_case module names, such as `Book`, `my-book`, or `1book`, exit with code 1 and the existing validation message. Nothing is written.
- **Outside a project**: running the command outside a Clean Architecture project root exits with code 1 and the existing message.
- **No arguments**: running `scaffold guc` with no arguments shows help and exits with code 0.
- **Legacy modules**: an existing legacy `domain/usecase/<name>.py` is ignored by generation. Running `scaffold guc --name <name>` creates `<name>_usecase.py` with no warning and no conflict, and the old file is left untouched.
- **Delete name matches other layers**: if the delete name also matches a model, adapter, entry point, or helper, the delete-module command lists every match, as it does today. Because a model and its use case usually share the base name (model `book`, use case `book_usecase.py`), `dm --name book` normally matches both. The preview shows every match before `--confirm` (US4 scenario 6).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The generate-use-case command (`guc` / `generate-use-case`) MUST derive a base name from `--name` by repeatedly removing a trailing `_usecase` or `_use_case` suffix until none remains. If there is no such suffix, the base name is `--name` unchanged.
- **FR-002**: The command MUST create the use case module at `domain/usecase/<base>_usecase.py`.
- **FR-003**: The command MUST create the test stub at `src/tests/domain/usecase/test_<base>_usecase.py`.
- **FR-004**: The generated class MUST be named `<Base>UseCase`, where `<Base>` is the PascalCase form of the base name, and the `UseCase` suffix MUST appear exactly once.
- **FR-005**: The generated test stub MUST import `<Base>UseCase` from the `<base>_usecase` module.
- **FR-006**: The inputs `<base>`, `<base>_usecase`, and `<base>_use_case` MUST produce identical file paths, class names, and file contents.
- **FR-007**: Only a trailing suffix MUST be removed. The word `usecase` or `use_case` appearing elsewhere in the name MUST be preserved.
- **FR-008**: If removing the suffixes leaves an empty base name (for example `--name usecase`, `--name use_case`, or `--name usecase_usecase`), the command MUST exit with code 1, print a clear message with a resolution hint, and write no files.
- **FR-009**: The "already exists" check MUST use the normalized module path `domain/usecase/<base>_usecase.py`, so that any spelling of an existing use case is reported as a conflict (exit code 1, resolution hint, no files written).
- **FR-009a**: A legacy use case file `domain/usecase/<name>.py` MUST NOT be treated as a conflict and MUST NOT trigger a warning. Generation proceeds and leaves it untouched.
- **FR-009b**: The command MUST also exit with code 1, with a clear message and a resolution hint, and write no files, if `src/tests/domain/usecase/test_<base>_usecase.py` already exists.
- **FR-010**: `--dry-run` MUST list the normalized file paths and MUST write nothing.
- **FR-011**: The success message MUST report the normalized class name `<Base>UseCase` and the number of files created.
- **FR-012**: The command MUST keep its current snake_case name validation, project-root detection, and no-argument help behavior, including exit codes and messages.
- **FR-013**: The delete-module command (`dm` / `delete-module`) MUST find a use case generated with the new convention when given either the base name or the suffixed name (`_usecase` or `_use_case`), and remove both the module and its test.
- **FR-014**: The delete-module command MUST continue to find and remove legacy use cases (`domain/usecase/<name>.py` and `test_<name>.py`) by their original name.
- **FR-014a**: When both a legacy `domain/usecase/<base>.py` and a new `domain/usecase/<base>_usecase.py` exist, the delete-module command MUST list both modules and their tests in the preview and remove all of them on `--confirm`.
- **FR-015**: All generated files MUST keep coming from versioned templates, and every changed template MUST have rendering tests (Constitution Principle II).
- **FR-016**: The command's help text and the project README MUST show the `<base>_usecase.py` convention in their examples.

### Key Entities

- **Use Case Base Name**: The `--name` value with every trailing `_usecase` or `_use_case` suffix removed. All file and class names derive from it.
- **Use Case Module**: The file `domain/usecase/<base>_usecase.py` that contains the use case class.
- **Use Case Class**: The class `<Base>UseCase` defined in the use case module.
- **Use Case Test Stub**: The file `src/tests/domain/usecase/test_<base>_usecase.py` that imports and exercises the use case class.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of use cases generated after this feature have a module file name ending in `_usecase.py` and a class name ending in exactly one `UseCase`.
- **SC-002**: For every base name tested, the three spellings (`<base>`, `<base>_usecase`, `<base>_use_case`) produce byte-identical output.
- **SC-003**: 0 generated class names contain the suffix twice, whatever the input (for example, `--name book_usecase` and `--name book_usecase_usecase` never produce `BookUsecaseUseCase`).
- **SC-004**: In 100% of freshly scaffolded projects, the generated project's lint, format, type-check, and test checks pass immediately after generating a use case, with no manual edits.
- **SC-005**: The files listed by `--dry-run` match the files actually created in 100% of runs.
- **SC-006**: Re-running the command for an existing use case under any of the three spellings never modifies an existing file.
- **SC-007**: The CLI's own test suite covers generation, suffix stripping for both spellings and repeated suffixes, the suffix-only error, dry-run, conflict detection (source and test file), legacy files being ignored by generation, and deletion by base name, suffixed name, legacy name, and with both layouts present, and stays at or above the 80% coverage gate.

## Assumptions

- `_usecase` is the canonical module suffix. `_use_case` is accepted as input only and is always normalized to `_usecase` in file names.
- The class name suffix stays `UseCase` (capital U and C) as it is today. Only the module and test file names change.
- Suffix detection is case-sensitive and requires the underscore separator. This matches the existing snake_case-only validation, which already rejects uppercase input.
- The content of the generated use case and test templates is unchanged apart from the module name used in the test import.
- The `--name` help text keeps asking for a snake_case name. It does not need to tell users to include or omit the suffix, because both forms work.
- All work for this feature MUST happen on the branch `feature/usecase-naming-standardization`, created from `main`, following Constitution Principle VII.

### Out of Scope

- Renaming or migrating use case files already generated in existing projects. Legacy `<name>.py` use cases are left as-is.
- Changing the naming of other generators (models, gateways, driven adapters, entry points, helpers).
- Automatically wiring the generated use case into the application's dependency container.
- A layer selector (for example `--layer`) for the delete-module command to target only the model or only the use case when both share a name.
