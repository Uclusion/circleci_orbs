"""
Util to remove the contents of all tables except those hard coded to be excluded
Run at your own risk
"""

from utils.table_purger.table_finder import get_tables
from utils.table_purger.table_clearer import purge_table_contents
protected_tables = ['Releases', 'deployment-group-versions']

if __name__ == "__main__":
    tables = get_tables()
    for table in tables:
        protected = False
        for protected_table in protected_tables:
            protected = protected or protected_table in table
        if not protected:
            print(table)
            purge_table_contents(table)