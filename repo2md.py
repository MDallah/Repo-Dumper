import os
import shutil
import argparse
import pathspec
from pathlib import Path
from typing import List, Dict, Optional, Any

GITIGNORE_FILE = ".gitignore"
DEFAULT_OUTPUT_FILE = "./output/repo_dump.md"
DEFAULT_RESTORE_DIR = "./output/restored_repo"
FILE_NAME_MARKER = "###### File: "
TREE_HEADER = "### Structure:"
CONTENT_HEADER = "### Contents:"
CODE_BLOCK_MARKER = "````````````"
BINARY_CHUNK_SIZE = 1024 # Bytes to read for binary detection

def is_binary(file_path: Path) -> bool:
    """
    Checks if a file is likely binary by reading a chunk and looking for null bytes.
    Handles potential read errors gracefully.
    """
    try:
        with file_path.open('rb') as f:
            chunk = f.read(BINARY_CHUNK_SIZE)
        return b'\x00' in chunk
    except IOError as e:
        print(f"Warning: Could not read file {file_path} for binary check: {e}")
        return False # Assume not binary if read fails
    except Exception as e:
        print(f"Warning: Unexpected error checking if {file_path} is binary: {e}")
        return False # Assume not binary on unexpected errors

def load_gitignore(repo_path: Path) -> Optional[pathspec.PathSpec]:
    """
    Loads the .gitignore file from the repository root.

    Args:
        repo_path: Path to the repository root directory.

    Returns:
        A pathspec.PathSpec object if .gitignore exists and is readable, None otherwise.
    """
    gitignore_path = repo_path / GITIGNORE_FILE
    if not gitignore_path.is_file():
        print(f"Info: No {GITIGNORE_FILE} found in {repo_path}")
        return None
    try:
        encodings_to_try = ['utf-8', 'latin-1', 'cp1252']
        content = None
        for enc in encodings_to_try:
            try:
                with gitignore_path.open('r', encoding=enc) as f:
                    content = f.readlines()
                print(f"Info: Successfully read {GITIGNORE_FILE} with encoding '{enc}'")
                break
            except UnicodeDecodeError:
                print(f"Warning: Failed to read {GITIGNORE_FILE} with encoding '{enc}'")
                continue
            except Exception as e:
                print(f"Warning: Could not read {gitignore_path} with encoding '{enc}': {e}")
                continue

        if content is None:
            print(f"Warning: Could not read {gitignore_path} with any attempted encoding.")
            return None

        return pathspec.PathSpec.from_lines('gitwildmatch', content)
    except IOError as e:
        print(f"Warning: Could not open {gitignore_path}: {e}")
        return None
    except Exception as e:
        print(f"Warning: Error parsing {gitignore_path}: {e}")
        return None


def list_files(
    repo_path: Path,
    gitignore_spec: Optional[pathspec.PathSpec],
    include_patterns: Optional[List[str]],
    exclude_patterns: Optional[List[str]],
    output_file_path: Path
) -> List[Path]:
    """
    Lists all files in the repository, respecting gitignore, include/exclude patterns,
    and excluding the .git directory and the output file itself.

    Args:
        repo_path: Path to the repository root directory.
        gitignore_spec: The loaded pathspec.PathSpec object from .gitignore.
        include_patterns: List of glob patterns to explicitly include.
        exclude_patterns: List of glob patterns to explicitly exclude.
        output_file_path: The absolute path to the output file being generated.

    Returns:
        A list of Path objects, relative to the repo_path.
    """
    file_list: List[Path] = []
    abs_repo_path = repo_path.resolve()

    include_spec = pathspec.PathSpec.from_lines('gitwildmatch', include_patterns or [])
    exclude_spec = pathspec.PathSpec.from_lines('gitwildmatch', exclude_patterns or [])

    for item in abs_repo_path.rglob('*'):
        if item.resolve() == output_file_path:
            print(f"Info: Skipping self (output file): {item}")
            continue

        try:
            relative_path = item.relative_to(abs_repo_path)
        except ValueError:
            print(f"Warning: Skipping item outside repo base: {item}")
            continue

        if not item.is_file():
            continue

        if '.git' in relative_path.parts:
            continue

        relative_path_str = str(relative_path).replace(os.sep, '/')

        # 1. Check explicit excludes
        if exclude_spec.match_file(relative_path_str):
            # print(f"Debug: Excluding '{relative_path_str}' due to exclude pattern.")
            continue

        # 2. Check explicit includes (overrides .gitignore)
        is_included = include_spec.match_file(relative_path_str)
        if is_included:
            # print(f"Debug: Including '{relative_path_str}' due to include pattern.")
            file_list.append(relative_path)
            continue

        # 3. Check .gitignore (if not explicitly included)
        if gitignore_spec and gitignore_spec.match_file(relative_path_str):
            # print(f"Debug: Excluding '{relative_path_str}' due to .gitignore.")
            continue

        # 4. If not excluded, not explicitly included, and not gitignored, add it.
        # print(f"Debug: Including '{relative_path_str}' by default.")
        file_list.append(relative_path)

    return sorted(list(set(file_list))) # Use set to avoid duplicates if patterns overlap weirdly


def build_tree(files: List[Path]) -> Dict[str, Any]:
    """Builds a nested dictionary representing the file tree structure."""
    tree: Dict[str, Any] = {}
    for file_path in files:
        parts = file_path.parts
        current_level = tree
        for i, part in enumerate(parts):
            is_file = (i == len(parts) - 1)
            if is_file:
                if part in current_level and isinstance(current_level[part], dict):
                    print(f"Warning: File '{file_path}' conflicts with an existing directory structure entry. Skipping file entry in tree.")
                else:
                    current_level[part] = None
            else:
                if part not in current_level:
                    current_level[part] = {}
                elif current_level[part] is None:
                    print(f"Warning: Directory component '{part}' in '{file_path}' conflicts with an existing file entry. Overwriting file entry with directory in tree.")
                    current_level[part] = {}

                if isinstance(current_level.get(part), dict):
                    current_level = current_level[part]
                else:
                    print(f"Warning: Cannot traverse into '{part}' for path '{file_path}' due to tree conflict. Stopping tree branch here.")
                    break
    return tree


def print_tree(tree: Dict[str, Any], prefix: str = '') -> List[str]:
    """Generates a list of strings representing the directory tree structure."""
    lines: List[str] = []
    entries = sorted(tree.items(), key=lambda item: (isinstance(item[1], dict), item[0]))

    for i, (name, subtree) in enumerate(entries):
        is_last = i == (len(entries) - 1)
        connector = '└── ' if is_last else '├── '

        if subtree is None:
            lines.append(f"{prefix}{connector}{name}")
        else:
            lines.append(f"{prefix}{connector}{name}/")
            extension = '    ' if is_last else '│   '
            if isinstance(subtree, dict):
                lines.extend(print_tree(subtree, prefix + extension))
            else:
                print(f"Warning: Expected dictionary for directory '{name}' in tree, but found {type(subtree)}. Skipping recursion.")

    return lines


def dump_repo(
    repo_path: Path,
    output_file: Path,
    include_patterns: Optional[List[str]],
    exclude_patterns: Optional[List[str]]
):
    """
    Dumps the repository structure and file contents to a single markdown file,
    with binary files listed at the end.
    """
    if not repo_path.is_dir():
        print(f"Error: Repository path '{repo_path}' not found or not a directory.")
        return

    output_file.parent.mkdir(parents=True, exist_ok=True)
    abs_output_file = output_file.resolve() # Resolve early for list_files

    print(f"Loading .gitignore from {repo_path}...")
    gitignore_spec = load_gitignore(repo_path)

    print(f"Listing files in {repo_path}...")
    all_files = list_files(repo_path, gitignore_spec, include_patterns, exclude_patterns, abs_output_file)
    if not all_files:
        print("Warning: No files found to dump (after applying filters).")
        # Still create an empty dump file with headers if needed
        # return # Or decide to proceed and create an empty dump

    print("Separating text and binary files...")
    text_files: List[Path] = []
    binary_files: List[Path] = []
    for relative_path in all_files:
        full_path = repo_path / relative_path
        if is_binary(full_path):
            binary_files.append(relative_path)
            print(f"  Identified as binary: {relative_path}")
        else:
            text_files.append(relative_path)
            print(f"  Identified as text: {relative_path}")
    print(f"  Found {len(text_files)} text files and {len(binary_files)} binary files.")

    print(f"Building file tree for all {len(all_files)} files...")
    # Build tree using all files so structure representation is complete
    tree = build_tree(all_files)

    print(f"Writing dump to {output_file}...")
    try:
        with output_file.open('w', encoding='utf-8', newline='\n') as out:
            repo_name = repo_path.resolve().name
            out.write(f"# Repository: {repo_name}\n\n")

            # --- Write File Structure (based on all files) ---
            out.write(f"{TREE_HEADER}\n")
            out.write(f"{CODE_BLOCK_MARKER}\n")
            out.write(f"/{repo_name}/\n")
            tree_lines = print_tree(tree, prefix="    ")
            out.write("\n".join(tree_lines))
            out.write(f"\n{CODE_BLOCK_MARKER}\n\n")

            # --- Write File Contents ---
            out.write(f"{CONTENT_HEADER}\n\n")

            # Process text files first
            if text_files:
                #print("Writing text file contents...")
                for relative_path in text_files:
                    full_path = repo_path / relative_path
                    relative_path_str = str(relative_path).replace(os.sep, '/')
                    print(f"  Dumping text content: {relative_path_str}")

                    out.write(f"{FILE_NAME_MARKER}{relative_path_str}\n")
                    extension = relative_path.suffix
                    lang_identifier = extension[1:] if extension else ''
                    out.write(f"{CODE_BLOCK_MARKER}{lang_identifier}\n")

                    try:
                        content = full_path.read_text(encoding='utf-8', errors='ignore')
                        # Ensure consistent line endings (replace windows \r\n with \n)
                        content = content.replace('\r\n', '\n').replace('\r', '\n')
                        out.write(content)
                        if content and not content.endswith('\n'):
                            out.write('\n') # Ensure newline at the end
                    except IOError as e:
                        out.write(f"Error reading file: {e}\n")
                    except Exception as e:
                        out.write(f"Error processing file: {e}\n")

                    out.write(f"{CODE_BLOCK_MARKER}\n\n")

            # Process binary files last
            if binary_files:
                #print("Writing binary file placeholders...")
                # Optional: Add a small header indicating binary section
                # out.write("---\n")
                # out.write("### Binary Files (Content Skipped)\n\n")

                for relative_path in binary_files:
                    # full_path = repo_path / relative_path # Not strictly needed for content
                    relative_path_str = str(relative_path).replace(os.sep, '/')
                    print(f"  Placeholder for binary: {relative_path_str}")

                    out.write(f"{FILE_NAME_MARKER}{relative_path_str}\n")
                    extension = relative_path.suffix
                    lang_identifier = extension[1:] if extension else '' # Keep consistent structure
                    # Add language identifier even for binary for consistency, though less useful
                    out.write(f"{CODE_BLOCK_MARKER}{lang_identifier}\n")

                    out.write("[Binary file content skipped]\n") # The placeholder

                    out.write(f"{CODE_BLOCK_MARKER}\n\n")


        print(f"Successfully dumped repository to {output_file}")

    except IOError as e:
        print(f"Error writing to output file {output_file}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during dumping: {e}")


def restore_repo(input_file: Path, output_dir: Path):
    """
    Restores a repository structure and files from a dump file.

    Args:
        input_file: Path to the dump text file (e.g., repo_dump.md).
        output_dir: Path to the destination directory to restore into.
    """
    if not input_file.is_file():
        print(f"Error: Input dump file '{input_file}' not found.")
        return
    
    if output_dir.exists():
            print(f"Warning: The output directory already exists. It will be overwritten.")
            userInput = input("Do you want to proceed? ([Y]/n): \n").strip().lower()
            if userInput in ['', 'true', 'y', 'yes']:
                # Remove existing directory
                shutil.rmtree(output_dir)
            else:
                print("Operation canceled.")
                return

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Restoring repository from {input_file} into {output_dir}...")

        with input_file.open('r', encoding='utf-8') as f:
            lines = f.readlines()

        current_file_path: Optional[Path] = None
        content_buffer: List[str] = []
        state = 0 # 0 = looking for file marker, 1 = looking for start code block, 2 = inside code block
        inside_code_block = False

        for line_num, line in enumerate(lines):
            # Check for code block markers regardless of state to handle transitions
            if line.strip().startswith(CODE_BLOCK_MARKER):
                if not inside_code_block:
                    # Entering a code block
                    if state == 1: # We were expecting this after a file marker
                        state = 2
                    # Else: Could be the tree structure block, ignore content until next marker
                    inside_code_block = True
                else:
                    # Exiting a code block
                    if state == 2: # We were inside a file content block
                        if current_file_path:
                            full_output_path = output_dir / current_file_path
                            # Join lines and potentially normalize line endings if needed during write
                            file_content = "".join(content_buffer)

                            if file_content.strip() == "[Binary file content skipped]":
                                print(f"  Skipping restore (binary placeholder): {current_file_path}")
                                # Optionally create an empty file or skip entirely
                                try:
                                    full_output_path.parent.mkdir(parents=True, exist_ok=True)
                                    # Create an empty file to represent the binary file's presence
                                    #with full_output_path.open('w', encoding='utf-8') as out_f:
                                        #pass # Just create the file
                                    #print(f"    (Created empty file for {current_file_path})")
                                except IOError as e:
                                    print(f"Error creating empty file placeholder {full_output_path}: {e}")
                                except Exception as e:
                                    print(f"An unexpected error occurred creating placeholder {full_output_path}: {e}")
                            else:
                                print(f"  Restoring: {current_file_path}")
                                try:
                                    full_output_path.parent.mkdir(parents=True, exist_ok=True)
                                    # Use 'w' with newline='' to prevent adding extra CR on Windows
                                    # Let the content determine line endings.
                                    with full_output_path.open('w', encoding='utf-8', newline='') as out_f:
                                        out_f.write(file_content)
                                except IOError as e:
                                    print(f"Error writing file {full_output_path}: {e}")
                                except Exception as e:
                                    print(f"An unexpected error occurred writing {full_output_path}: {e}")

                        current_file_path = None
                        content_buffer = []
                        state = 0 # Look for the next file marker
                    # Else: Exiting the tree structure block or some other block, just reset flag
                    inside_code_block = False
                continue # Skip processing the marker line itself as content

            # --- State machine logic ---
            if state == 0: # Looking for file marker
                if line.startswith(FILE_NAME_MARKER):
                    relative_path_str = line[len(FILE_NAME_MARKER):].strip()
                    if not relative_path_str:
                        print(f"Warning: Skipping empty file path found on line {line_num + 1}")
                        continue
                    # Sanitize path for security (though Path usually handles this well)
                    # Avoid paths trying to go outside the output_dir using '..'
                    if ".." in relative_path_str:
                        print(f"Warning: Skipping potentially unsafe path '{relative_path_str}' on line {line_num + 1}")
                        continue
                    current_file_path = Path(relative_path_str)
                    content_buffer = []
                    state = 1 # Now look for the start code block

            # elif state == 1: # Looking for start code block
                # This state is effectively handled by the general code block marker check above

            elif state == 2: # Inside code block (and it's for a file)
                if inside_code_block: # Double check we are still inside
                    content_buffer.append(line)
                # Else: Should have been transitioned out by marker check above

        if state != 0:
            print(f"Warning: Dump file may have ended unexpectedly or parsing finished in an intermediate state ({state}).")
        if current_file_path is not None:
            print(f"Warning: Processing ended while handling file '{current_file_path}'. It might be incomplete.")

        print(f"\nSuccessfully finished attempting restoration to {output_dir}")

    except FileNotFoundError:
        print(f"Error: Input dump file '{input_file}' not found.")
    except IOError as e:
        print(f"Error reading input file {input_file}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during restoration: {e}")


def main():
    """
    Parses command-line arguments and executes the dump or restore action.
    """
    parser = argparse.ArgumentParser(
        description="Dump a repository's structure and contents to a single text file, or restore it.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', required=True, help='Choose action: dump or restore')

    # --- Dump arguments ---
    dump_parser = subparsers.add_parser('dump', help='Dump repository structure and content to a text file.')
    dump_parser.add_argument('repo', type=Path, help='Path to the repository directory to dump.')
    dump_parser.add_argument('-o', '--output', type=Path, default=Path(DEFAULT_OUTPUT_FILE), help='Output text file path.')
    dump_parser.add_argument(
        '-i', '--include',
        nargs='*',
        help='Glob patterns for files to explicitly include (overrides .gitignore).',
        metavar='PATTERN'
    )
    dump_parser.add_argument(
        '-e', '--exclude',
        nargs='*',
        help='Glob patterns for files/directories to exclude.',
        metavar='PATTERN'
    )


    # --- Restore arguments ---
    restore_parser = subparsers.add_parser('restore', help='Restore repository from a text dump file.')
    restore_parser.add_argument('input', type=Path, help='Input text dump file path.')
    restore_parser.add_argument('-d', '--dest', type=Path, default=Path(DEFAULT_RESTORE_DIR), help='Destination directory to restore the repository into.')

    args = parser.parse_args()

    if args.command == 'dump':
        repo_path = args.repo.resolve()
        output_path = args.output.resolve()
        dump_repo(repo_path, output_path, args.include, args.exclude)
    elif args.command == 'restore':
        input_path = args.input.resolve()
        dest_path = args.dest.resolve()
        restore_repo(input_path, dest_path)

if __name__ == "__main__":
    main()