import subprocess
import sys


def test_round_trip_across_processes(tmp_path):
    store_script = (
        "from octopus_mem import MemoryManager;"
        f"mm = MemoryManager(base_path={str(tmp_path)!r});"
        "print(mm.store_memory('decision: use atomic writes', memory_type='long_term', skill_name='dev'))"
    )
    store_output = subprocess.check_output([sys.executable, "-c", store_script], text=True).strip()
    assert store_output.startswith("mem_")

    retrieve_script = (
        "from octopus_mem import MemoryManager;"
        f"mm = MemoryManager(base_path={str(tmp_path)!r});"
        "results = mm.retrieve_memory('atomic writes', skill_name='dev');"
        "assert any('atomic writes' in r['content_preview'] for r in results), results;"
        "print('OK')"
    )
    retrieve_output = subprocess.check_output([sys.executable, "-c", retrieve_script], text=True).strip()
    assert retrieve_output == "OK"
