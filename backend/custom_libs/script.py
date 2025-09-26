import nbformat
import sys
from pathlib import Path

def notebook_to_py(input_path, output_path):
    # Load the notebook
    nb_path = Path(input_path)
    nb = nbformat.read(nb_path, as_version=4)

    # Collect all code cells
    code_cells = []
    for cell in nb.cells:
        if cell.cell_type == 'code':
            code_cells.append(cell.source)

    # Write to .py file
    output_path = Path(output_path)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(code_cells))

    print(f"Converted {input_path} → {output_path}")

if __name__ == "__main__":
        notebook_to_py("D:/All Projects/Website/Personal_AI-Hospitall/backend/AI_hospital.ipynb", "D:/All Projects/Website/Personal_AI-Hospitall/backend/API/AI_hospital.py")   
