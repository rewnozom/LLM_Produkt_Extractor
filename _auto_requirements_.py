import os
import ast
import pkg_resources
import re

def find_imports(directory):
    imports = set()
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        tree = ast.parse(f.read())
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for n in node.names:
                                    imports.add(n.name.split('.')[0])
                            elif isinstance(node, ast.ImportFrom):
                                if node.level == 0:  # This ensures it's not a relative import
                                    imports.add(node.module.split('.')[0])
                    except Exception as e:
                        print(f"Error parsing {file_path}: {str(e)}")
    return imports

def is_valid_package_name(name):
    return re.match(r'^[a-zA-Z0-9_-]+$', name) is not None

def is_installed_package(module_name):
    if not is_valid_package_name(module_name):
        print(f"Skipping invalid package name: '{module_name}'")
        return False
    try:
        pkg_resources.get_distribution(module_name)
        return True
    except pkg_resources.DistributionNotFound:
        return False
    except Exception as e:
        print(f"Error checking package '{module_name}': {str(e)}")
        return False

def parse_requirement(req_line):
    parts = req_line.strip().split('==')
    return parts[0], parts[1] if len(parts) > 1 else None

def normalize_package_name(name):
    return name.replace('_', '-')

def generate_requirements(directory, output_file='requirements.txt'):
    all_imports = find_imports(directory)
    installed_packages = [imp for imp in all_imports if is_installed_package(imp)]
    
    # Read existing content
    manual_entries = []
    manual_packages = set()
    auto_marker_found = False
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() == "# auto_under_här":
                    auto_marker_found = True
                    break
                manual_entries.append(line)
                package, _ = parse_requirement(line)
                if package:
                    manual_packages.add(normalize_package_name(package))
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Write manual entries
        f.writelines(manual_entries)
        
        # Write auto marker if not present
        if not auto_marker_found:
            f.write("\n# auto_under_här\n")
        else:
            f.write("# auto_under_här\n")
        
        # Write auto-generated entries
        for package in sorted(installed_packages, key=str.lower):
            normalized_package = normalize_package_name(package)
            if normalized_package not in manual_packages:
                try:
                    version = pkg_resources.get_distribution(normalized_package).version
                    f.write(f"{normalized_package}=={version}\n")
                except Exception as e:
                    print(f"Error getting version for '{normalized_package}': {str(e)}")
                    f.write(f"{normalized_package}\n")
    
    print(f"Requirements file generated: {output_file}")
    print(f"Total imports found: {len(all_imports)}")
    print(f"Installed packages: {len(installed_packages)}")
    print(f"Manual entries: {len(manual_packages)}")

if __name__ == "__main__":
    directory = '.'  # Current directory, change this if needed
    generate_requirements(directory)