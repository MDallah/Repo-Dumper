![Banner](./imgs/banner.png)

# 🧰 Repo Dumper

A lightweight Python CLI tool to **dump** an entire code repository (structure + file contents) into a single Markdown (`.md`) file and **restore** it back from that file. Ideal for snapshotting, code review sharing, context-providing for LLMs, or version-neutral archival.

## 🚀 Features

- ✅ Dump repository structure and code into a single `.md` file.
- ✅ Restore the full file and folder structure from the dump file.
- ✅ Respects `.gitignore` rules (excludes ignored files/folders).
- ✅ Excludes the `.git` directory itself.
- ✅ Attempts to prevent dumping its own output file if located within the target repository.
- ✅ Cross-platform (Linux/macOS/Windows).
- ✅ Simple, dependency-light (only requires `pathspec`).

## 📦 Installation

Ensure you have Python 3.6+ installed. You only need the `pathspec` library:

```bash
pip install pathspec
```

## 🧑‍💻 Usage

### ➤ Dump a Repo

This command reads the repository at `/path/to/repo`, respects its `.gitignore`, and writes the structure and contents to `repo_dump.md`.

```bash
python repo_dumper.py dump /path/to/repo -o repo_dump.md
```

- `repo`: Path to the repository you want to dump.
- `-o` / `--output`: (Optional) Path to the output Markdown file. Defaults to `./output/repo_dump.md`.

### ➤ Restore a Repo

This command reads `repo_dump.md` and recreates the files and folders in the `./restored_repo` directory.

```bash
python repo_dumper.py restore repo_dump.md -d restored_repo
```

- `input`: Path to the Markdown dump file created by the `dump` command.
- `-d` / `--dest`: (Optional) Path to the directory where the repository should be restored. Defaults to `./output/restored_repo`. The destination directory will be created if it doesn't exist.

## 📂 Example Output (`repo_dump.md`)

The generated file looks like this:

````
# Repository: my_project

### Repository Structure:

```bash
/my_project/
    ├── .gitignore/
    ├── README.md
    └── src/
        └── main.py
```

### Repository Contents:

###### File: .gitignore

```.gitignore
*.pyc
__pycache__/
venv/
```

###### File: README.md

```markdown
# My Project

Hello World!
This is a sample project.
```

###### File: src/main.py

```python

def main():
    """
    Main function
    """
    print("Hello, world from main.py!")

if __name__ == "__main__":
    main()
```
````

_(Note: The exact tree structure symbols (`├──`, `└──`, `│`) might vary slightly depending on the terminal rendering, but the indentation and hierarchy are preserved)._

## ✌️ Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
