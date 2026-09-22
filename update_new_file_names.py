from utils import rename_all_real_files, update_last_access
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REAL_FILES = os.path.join(BASE_DIR, 'data', 'real_files')


def main():
    rename_all_real_files(REAL_FILES)
    update_last_access(REAL_FILES)


if __name__ == '__main__':
    main()

