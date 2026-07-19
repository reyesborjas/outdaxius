import os
import argparse

# Directorios a ignorar
dirs_to_ignore = {'.git', '__pycache__', 'venv', '.venv', 'node_modules', '.mypy_cache', '.pytest_cache'}

def find_py_files(src):
    py_files = []
    for root, dirs, files in os.walk(src):
        # Filtrar directorios a ignorar
        dirs[:] = [d for d in dirs if d not in dirs_to_ignore]
        for file in files:
            if file.endswith('.py'):
                py_files.append(os.path.join(root, file))
    return sorted(py_files)

def read_file_utf8(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        # Manejo de error sin detener la ejecución
        return f'ERROR: No se pudo leer {path}. {str(e)}'

def main():
    parser = argparse.ArgumentParser(description='Concatenar archivos .py de una carpeta en un solo .txt')
    parser.add_argument('--src', required=True, help='Ruta de la carpeta origen')
    parser.add_argument('--out', required=True, help='Archivo de salida')
    args = parser.parse_args()

    if not os.path.isdir(args.src):
        print(f'Error: La ruta de origen {args.src} no es una carpeta válida.')
        exit(1)

    py_files = find_py_files(args.src)

    with open(args.out, 'w', encoding='utf-8') as outfile:
        for filepath in py_files:
            outfile.write(f'===== {os.path.abspath(filepath)} =====\n')
            content = read_file_utf8(filepath)
            outfile.write(content + '\n\n')

if __name__ == '__main__':
    main()
