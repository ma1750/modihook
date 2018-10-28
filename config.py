from pathlib import Path
import json


class Config():
    def __init__(self, rundir, file='config.json'):
        self._file = Path(rundir).parent/'config'/file
        self._config = {}

        self._init_config(file)
    
    @property
    def is_ready(self):
        return bool(self._config)
    
    def get(self, name):
        return self._config.get(name)

    def _init_config(self, file):
        if not self._file.exists():
            print(f'{str(self._file)} not found.')
            return

        with open(self._file, 'r', encoding='utf8') as f:
            try:
                self._config = json.load(f)
            except:
                print(f'Failed to parse {file}.')
