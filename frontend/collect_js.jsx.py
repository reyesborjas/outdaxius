import os
import argparse
from typing import List

dirs_to_ignore = {'.git', 'node_modules', 'dist', 'build', '.next', '.cache', '.vite', '.eslintcache'}

def find_js_files(src: str) -> List[str]:
    """Busca recursivamente archivos .js y .jsx ignorando ciertos directorios."""
    files = []
    for root, dirs, filenames in os.walk(src):
        dirs[:] = [d for d in dirs if d not in dirs_to_ignore]
        for f in filenames:
            if f.endswith('.js') or f.endswith('.jsx'):
                files.append(os.path.join(root, f))
    return sorted(files)

def read_file_utf8(path: str) -> str:
    """Lee un archivo en UTF-8 con manejo de errores sin detener la ejecución."""
    try:
        with open(path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        return f'ERROR: Cannot read {path}. {str(e)}'

def main() -> None:
    default_src = r"C:\Users\reyes\OneDrive\Documents\Proyectos Propios\outdaxius\frontend\src"
    parser = argparse.ArgumentParser(description='Concatanar todos los .js y .jsx recursivamente en un solo archivo .txt')
    parser.add_argument('--src', type=str, help='Carpeta origen para buscar archivos .js/.jsx')
    parser.add_argument('--out', type=str, required=True, help='Archivo de salida concatenado')
    args = parser.parse_args()

    src = args.src if args.src else default_src
    if not os.path.isdir(src):
        print(f'Error: Ruta origen "{src}" no es válida.')
        exit(1)

    js_files = find_js_files(src)

    with open(args.out, 'w', encoding='utf-8') as outfile:
        for filepath in js_files:
            outfile.write(f'===== {os.path.abspath(filepath)} =====\n')
            outfile.write(read_file_utf8(filepath) + '\n\n')

if __name__ == '__main__':
    main()
