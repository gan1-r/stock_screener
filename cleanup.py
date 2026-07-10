import shutil
import os

os.chdir('d:\\Dev\\stock_screener')

# Remove old directories
for folder in ['dump_script', 'image', '__pycache__']:
    try:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f'Removed {folder}')
    except Exception as e:
        print(f'Error removing {folder}: {e}')

print('Cleanup complete!')
