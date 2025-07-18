![Banner](./imgs/banner.png)

# 🧰 Repo2Mardown

A lightweight Python CLI tool to **dump** an entire code repository (structure + file contents) into a single Markdown (`.md`) file and **restore** it back from that file. Ideal for snapshotting, code review sharing, context-providing for LLMs, or version-neutral archival.

## 🚀 Features

- ✅ Dump repository structure and code into a single `.md` file.
- ✅ Restore the full file and folder structure from the dump file.
- ✅ Respects `.gitignore` rules (excludes ignored files/folders by default).
- ✅ Allows explicit inclusion/exclusion patterns to override `.gitignore`.
- ✅ Skips content of detected binary files, adding a placeholder instead.
- ✅ Excludes the `.git` directory itself.
- ✅ Attempts to prevent dumping its own output file if located within the target repository.
- ✅ Cross-platform (Linux/macOS/Windows).
- ✅ Simple, dependency-light (only requires `pathspec`).

## 📦 Installation

Ensure you have Python 3.6+ installed. You only need the `pathspec` library:

```bash
pip install pathspec
# Or:
pip install -r requirements.txt
```

## 🧑‍💻 Usage

### ➤ Dump a Repo

This command reads the repository at `/path/to/repo`, respects its `.gitignore` (unless overridden by include/exclude patterns), skips binary file content, and writes the structure and contents to the specified output Markdown file.

```bash
# Basic dump to default output location ./output/repo_dump.md
python repo_dumper.py dump /path/to/repo

# Dump to a specific file
python repo_dumper.py dump /path/to/repo -o my_repo_snapshot.md

# Dump with include/exclude patterns overriding .gitignore
# Include all .py and .js files, even if ignored, but exclude the 'tests/' dir and specific docs
python repo_dumper.py dump /path/to/repo -o output.md -i "*.py" "*.js" -e "tests/" "docs/internal/*"

# Example including a normally ignored directory (e.g., venv config) but excluding logs
python repo_dumper.py dump . -o my_project_dump.md -i "venv/config/*" -e "*.log"
```

**Arguments & Options:**

- `repo`: Path to the repository you want to dump.
- `-o` / `--output`: (Optional) Path to the output Markdown file. Defaults to `./output/repo_dump.md`.
- `-i` / `--include PATTERN`: (Optional) Glob pattern(s) for files/directories to _explicitly include_. These files will be included even if they match a `.gitignore` rule. Can be specified multiple times (e.g., `-i '*.py' -i '*.js'`).
- `-e` / `--exclude PATTERN`: (Optional) Glob pattern(s) for files/directories to _explicitly exclude_. These take precedence over include patterns and `.gitignore`. Can be specified multiple times (e.g., `-e 'node_modules/' -e '*.log'`).

### ➤ Restore a Repo

This command reads `repo_dump.md` and recreates the files and folders in the specified destination directory. Binary files noted in the dump (with `[Binary file content skipped]`) will be skipped during restoration, meaning those files will not be created.

```bash
python repo_dumper.py restore repo_dump.md -d restored_repo
```

## 📂 Example Output (`repo_dump.md`)

The generated file looks like this:

````
# Repository: my_project

### Repository Structure:

```
/my_project/
├── .gitignore
├── README.md
├── assets/
│   └── logo.png
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

```md
# My Project

Hello World!
This is a sample project.
```

###### File: assets/logo.png

```png
[Binary file content skipped]
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
