"""Two instruments sampled at different rates must never be joined by row."""
import sys
from pathlib import Path
import openpyxl
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_dynamic_validation import read_raw


def test_temperature_is_interpolated_on_scale_sync_time(tmp_path):
    wb=openpyxl.Workbook(); ws=wb.active
    for _ in range(6): ws.append(['header'])
    ws.append(['X_Value','Sync. Time [s]','Orig.Time [s]','m(LH2) [g]','TA000-00'])
    ws.append([0,0,7.67,1000,300])
    ws.append([1,.5,8.17,990,200])
    ws.append([2,1,8.67,980,100])
    path=tmp_path/'raw.xlsx'; wb.save(path); wb.close()
    rows=read_raw(path)
    assert rows[1]['TA000-00']==pytest.approx(250)
    assert rows[2]['TA000-00']==pytest.approx(200)
    assert rows[1]['Orig.Time [s]']==8.17
