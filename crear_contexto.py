import os

# Extensiones que nos interesan
extensions = ['.py', '.html', '.css', '.js']
# Carpetas a ignorar (MUY IMPORTANTE para no copiar librerias basura)
ignore_dirs = ['venv', '.git', '__pycache__', '.idea', 'staticfiles']
output_file = 'PROYECTO_COMPLETO.txt'

with open(output_file, 'w', encoding='utf-8') as outfile:
    for root, dirs, files in os.walk("."):
        # Filtrar carpetas ignoradas
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                path = os.path.join(root, file)
                outfile.write(f"\n{'='*50}\n")
                outfile.write(f"ARCHIVO: {path}\n")
                outfile.write(f"{'='*50}\n")
                try:
                    with open(path, 'r', encoding='utf-8') as infile:
                        outfile.write(infile.read())
                except Exception as e:
                    outfile.write(f"Error leyendo archivo: {e}\n")

print(f"Listo! Subí el archivo '{output_file}' al chat.")